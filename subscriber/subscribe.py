import json
import ssl
import time
from datetime import datetime

from nostr.filter import Filter, Filters
from nostr.event import Event, EventKind
from nostr.relay_manager import RelayManager
from nostr.message_type import ClientMessageType


import sys
sys.path.append('./common')
import db
from models import Event, NotifyQueue

import yaml

import util

today = datetime.now()

with open('./common/config.yml', 'r') as yml:
  config = yaml.safe_load(yml)

since = today.timestamp()
# since = datetime.strptime("2023-02-16 0:0:0", '%Y-%m-%d %H:%M:%S').timestamp()

filters = Filters([
    Filter(kinds=[EventKind.TEXT_NOTE], since=since),
    # Filter(kinds=[EventKind.TEXT_NOTE]),
])
subscription_id = "nostify"

relay_manager = RelayManager()
for relay_server in config["relay_servers"]:
  relay_manager.add_relay(relay_server)

relay_manager.add_subscription_on_all_relays(subscription_id, filters)
time.sleep(1.25)


while True:
  while relay_manager.message_pool.has_events():
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

    texts = [
        datetime.fromtimestamp(event_msg.event.created_at).strftime("%Y/%m/%d %H:%M:%S"),
        util.get_note_id(event_msg.event.id),
        event_msg.event.public_key,
        str(event_msg.event.kind),
        event_msg.event.content,
        event_msg.event.signature,
    ]
    print("\n".join(texts))
    print(event_msg.event.tags)
    tag_json = json.dumps(event_msg.event.tags)
    event_datetime = datetime.fromtimestamp(event_msg.event.created_at)
    event = Event(event_msg.event.id, event_msg.event.public_key, event_msg.event.kind, event_msg.event.content, tag_json, event_msg.event.signature, event_datetime)
    event_id = db.addEvent(event)
    filters = db.getFilters()
    for filter in filters:
      match_pub = False
      match_kind = False
      match_keyword = False
      addQueue = False

      if filter.pubkeys:
        for pubkey in filter.pubkeys.split(","):
          if pubkey == event_msg.event.public_key:
            match_pub = True
      if filter.kinds is not None:
        for kind in filter.kinds.split(","):
          if kind == event_msg.event.kind:
            match_kind = True
      if filter.keywords is not None:
        for keyword in filter.keywords.split("\n"):
          if keyword in event_msg.event.content:
            match_keyword = True

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

      if addQueue:
        notifyQueue = NotifyQueue(event_id, filter.target_channel_id)
        db.addNotifyQueue(notifyQueue)

  time.sleep(1)
