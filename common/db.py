import socket
import time
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update, desc
from sqlalchemy.dialects.mysql import insert

from sqlalchemy import create_engine

from common.models import (
    Base,
    Event,
    EventStatus,
    Filter,
    FilterStatus,
    NotifyQueue,
    QueueStatus,
    NgWord,
)

from contextlib import contextmanager

import os
from easydict import EasyDict as edict

MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")


def wait_db(host="db", port=3306, retries=30):
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  for x in range(retries):
    try:
      s.connect((host, port))
      s.close()
      return True
    except socket.error:
      print(f"waiting db...{x}")
      time.sleep(1)

  s.close()
  return False


wait_db()

url = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@db/{MYSQL_DATABASE}?charset=utf8mb4"
)
engine = create_engine(url, echo=False, pool_recycle=3600, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)
Session = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


@contextmanager
def session_scope():
  session = Session()
  try:
    yield session
    session.commit()
  except:
    import sys
    import traceback
    from datetime import datetime

    exc_type, exc_value, exc_traceback = sys.exc_info()
    err_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + repr(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )
    sys.stderr.write(err_text)
    print(err_text)
    session.rollback()
    raise
  finally:
    session.close()


def addEvent(event: Event):
  with session_scope() as session:
    insert_stmt = (
        insert(Event)
        .values(
            status=event.status,
            hex_event_id=event.hex_event_id,
            pubkey=event.pubkey,
            kind=event.kind,
            content=event.content,
            tags=event.tags,
            signature=event.signature,
            event_created_at=event.event_created_at,
        )
        .prefix_with("IGNORE")
    )
    result = session.execute(insert_stmt)
    session.commit()
    if result.rowcount == 0:
      # duplicated insert
      return False
    else:
      return True


def getEvent(hex_event_id):
  with session_scope() as session:
    query = session.query(Event).filter(Event.hex_event_id == hex_event_id)
    event = query.order_by(desc(Event.received_at)).first()
    return event


def getEvents():
  with session_scope() as session:
    query = session.query(Event).filter(Event.status == EventStatus.ENABLE.value)
    events = query.all()
    return events


def updateEventStatus(_id, status: EventStatus):
  with session_scope() as session:
    stmt = update(Event).where(Event.id == _id).values(status=status.value)
    session.execute(stmt)
    session.commit()


def doneEventCheck(_id):
  return updateEventStatus(_id, EventStatus.CHECKED)


def addFilter(
    server_id,
    channel_id,
    pubkeys,
    kinds=None,
    authors=None,
    since=None,
    until=None,
    event_refs=None,
    pubkey_refs=None,
    keywords=None,
    ng_keywords=None,
):
  with session_scope() as session:
    keywords = None if not keywords else keywords
    filter = Filter(
        server_id,
        channel_id,
        pubkeys,
        kinds,
        authors,
        since,
        until,
        event_refs,
        pubkey_refs,
        keywords,
        ng_keywords,
    )
    session.add(filter)
    session.commit()
    return filter.id


def getFilters():
  with session_scope() as session:
    query = session.query(Filter).filter(Filter.status == FilterStatus.ENABLE.value)
    filters = query.all()
    return filters


def getFiltersWithChannelId(channel_id):
  with session_scope() as session:
    query = session.query(Filter).filter(Filter.target_channel_id == channel_id)
    result_list = []
    filters = query.all()
    for filter in filters:
      if filter.status == FilterStatus.DELETED:
        continue
      filter_status = edict()
      filter_status.id = filter.id
      filter_status.status = str(FilterStatus(filter.status))
      filter_status.pubkeys = filter.pubkeys
      filter_status.keywords = filter.keywords
      result_list.append(filter_status)

    return result_list


def clearFilters(channel_id):
  with session_scope() as session:
    stmt = (
        update(Filter)
        .where(Filter.target_channel_id == channel_id)
        .values(status=FilterStatus.DELETED.value)
    )
    session.execute(stmt)
    session.commit()


def suspendFilters(channel_id):
  with session_scope() as session:
    stmt = (
        update(Filter)
        .where(
            (Filter.target_channel_id == channel_id)
            & (Filter.status == FilterStatus.ENABLE.value)
        )
        .values(status=FilterStatus.SUSPEND.value)
    )
    session.execute(stmt)
    session.commit()


def resumeFilters(channel_id):
  with session_scope() as session:
    stmt = (
        update(Filter)
        .where(
            (Filter.target_channel_id == channel_id)
            & (Filter.status == FilterStatus.SUSPEND.value)
        )
        .values(status=FilterStatus.ENABLE.value)
    )
    session.execute(stmt)
    session.commit()


def addNotifyQueue(notifyQueue):
  with session_scope() as session:
    # check queued
    old_queue = session.query(NotifyQueue).filter(NotifyQueue.target_channel_id == notifyQueue.target_channel_id)\
        .filter(NotifyQueue.hex_event_id == notifyQueue.hex_event_id)\
        .one_or_none()
    if old_queue is None:
      session.add(notifyQueue)
      session.commit()
      return notifyQueue.id


def getNotifyQueues():
  with session_scope() as session:
    query = session.query(NotifyQueue).filter(
        NotifyQueue.status == QueueStatus.NOT_YET.value
    )
    notifyQueues = query.all()
    return notifyQueues


def updateNotifyQueue(_id, status: QueueStatus, error_count: int):
  with session_scope() as session:
    stmt = (
        update(NotifyQueue)
        .where(NotifyQueue.id == _id)
        .values(status=status.value, error_count=error_count)
    )
    session.execute(stmt)
    session.commit()


def getNgWords():
  with session_scope() as session:
    query = session.query(NgWord).filter(NgWord.status == 0)
    ngWords = query.all()
    return [ngWord.word for ngWord in ngWords]
