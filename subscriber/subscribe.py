import json
import time
from datetime import datetime, timedelta

from pynostr.filters import FiltersList, Filters
from pynostr.event import Event, EventKind
from pynostr.relay_manager import RelayManager
import uuid

import sys
sys.path.append('./common')
import db
from models import Event, NotifyQueue

import yaml

import util


with open('./common/config.yml', 'r') as yml:
  config = yaml.safe_load(yml)

subscription_id = uuid.uuid1().hex


def connect_relay():
  today = datetime.now()
  before_min = today - timedelta(minutes=20)
  since = before_min.timestamp()
  # since = datetime.strptime("2023-02-16 0:0:0", '%Y-%m-%d %H:%M:%S').timestamp()

  filters = FiltersList([
      Filters(kinds=[EventKind.TEXT_NOTE], since=since),
      # Filters(kinds=[EventKind.TEXT_NOTE]),
  ])
  relay_manager = RelayManager()
  add_all_relay(relay_manager, config["relay_servers"])

  relay_manager.add_subscription_on_all_relays(subscription_id, filters)
  relay_manager.run_sync()
  while relay_manager.message_pool.has_notices():
    notice_msg = relay_manager.message_pool.get_notice()
    print(notice_msg.content)

  return relay_manager


def add_all_relay(relay_manager, relay_servers):
  for relay_server in relay_servers:
    relay_manager.add_relay(relay_server)


def close_relay(relay_manager):
  relay_manager.close_all_relay_connections()


def reconnect_all_relay(relay_manager):
  print("reconnect_all_relay start")
  close_relay(relay_manager)
  time.sleep(2)
  relay_manager = connect_relay()
  time.sleep(2)
  print("reconnect_all_relay done")
  return relay_manager


relay_manager = connect_relay()

no_event_count = 0

while True:
  events = 0
  while relay_manager.message_pool.has_events():
    events += 1
    now = datetime.now()
    event_msg = relay_manager.message_pool.get_event()
    words = db.getNgWords()
    detect_ng = False
    for word in words:
      if word in event_msg.event.content:
        detect_ng = True
        break
    if detect_ng:
      continue

    tag_json = json.dumps(event_msg.event.tags)
    event_datetime = datetime.fromtimestamp(event_msg.event.created_at)
    event = Event(event_msg.event.id, event_msg.event.pubkey, event_msg.event.kind, event_msg.event.content, tag_json, event_msg.event.sig, event_datetime)
    inserted = db.addEvent(event)
    print(".", end="")
    if inserted:
      texts = [
          datetime.fromtimestamp(event_msg.event.created_at).strftime("%Y/%m/%d %H:%M:%S"),
          util.get_note_id(event_msg.event.id),
          event_msg.event.pubkey,
          str(event_msg.event.kind),
          event_msg.event.content,
          event_msg.event.sig,
      ]
      print("\n".join(texts))
      print(event_msg.event.tags)
      filters = db.getFilters()
      for filter in filters:
        match_pub = False
        match_kind = False
        match_keyword = False
        addQueue = False

        if filter.pubkeys:
          for pubkey in filter.pubkeys.split(","):
            if pubkey == event_msg.event.pubkey:
              match_pub = True
              break
        if filter.kinds is not None:
          for kind in filter.kinds.split(","):
            if kind == event_msg.event.kind:
              match_kind = True
              break
        lower_content = event_msg.event.content.lower()
        if filter.keywords is not None:
          for keyword in filter.keywords.split("\n"):
            keyword = keyword.lower()
            if keyword in lower_content:
              match_keyword = True
              break

        if len(filter.pubkeys) > 0:
          if match_pub:
            if filter.kinds:
              if filter.keywords:
                if match_keyword:
                  addQueue = True
            elif filter.keywords:
              if match_keyword:
                addQueue = True
            else:
              addQueue = True
        else:
          if match_keyword:
            addQueue = True

        if addQueue:
          notifyQueue = NotifyQueue(event_msg.event.id, filter.target_channel_id)
          db.addNotifyQueue(notifyQueue)

  if events == 0:
    no_event_count += 1
    if no_event_count % 100 == 0:
      print("no events", no_event_count)
  else:
    no_event_count = 0

  if no_event_count >= 300:
    relay_manager = reconnect_all_relay(relay_manager)
    no_event_count = 0

  relay_manager.run_sync()
