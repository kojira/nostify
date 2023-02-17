from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.sql.functions import current_timestamp
from datetime import datetime
from enum import IntEnum

Base = declarative_base()

class EventStatus(IntEnum):
  ENABLE = 0
  DELETED = 1

class Event(Base):
  id = Column(Integer, autoincrement=True, primary_key=True)
  status = Column(Integer, index=True) # EventStatus
  hex_event_id = Column(String(64), unique=True)
  pubkey = Column(String(64), index=True)
  kind = Column(Integer, index=True)
  content = Column(Text)
  tags = Column(Text)
  signature = Column(Text)
  event_created_at = Column(DATETIME(fsp=3))
  received_at = Column(DATETIME(fsp=3), server_default=current_timestamp(3))

  __tablename__ = 'events'

  def __init__(self, hex_event_id, pubkey, kind, content, tags, signature, created_at):
    self.status = EventStatus.ENABLE.value
    self.hex_event_id = hex_event_id
    self.pubkey = pubkey
    self.kind = kind
    self.content = content
    self.tags = tags
    self.signature = signature
    self.event_created_at = created_at


class FilterStatus(IntEnum):
  ENABLE = 0
  SUSPEND = 1
  DELETED = -1

  def __str__(self):
    if self == FilterStatus.ENABLE:
      return '有効'
    elif self == FilterStatus.SUSPEND:
      return 'サスペンド'
    elif self == FilterStatus.DELETED:
      return '削除済み'
    else:
      return 'unknown'


class Filter(Base):
  id = Column(Integer, autoincrement=True, primary_key=True)
  status = Column(Integer, index=True) # FilterStatus
  target_server_id = Column(BigInteger)
  target_channel_id = Column(BigInteger)
  pubkeys = Column(Text, nullable=True)
  kinds = Column(Text, nullable=True)
  authors = Column(Text, nullable=True)
  since = Column(Integer, nullable=True)
  until = Column(Integer, nullable=True)
  event_refs = Column(Text, nullable=True)
  pubkey_refs = Column(Integer, nullable=True)
  keywords = Column(Text, nullable=True)
  created_at = Column(DateTime, default=datetime.utcnow)

  __tablename__ = 'filters'

  def __init__(self, target_server_id, target_channel_id, pubkeys=None, kinds=None, authors=None, since=None, until=None, event_refs=None, pubkey_refs=None, keywords=None, ng_keywords=None):
    self.status = FilterStatus.ENABLE.value
    self.target_server_id = target_server_id
    self.target_channel_id = target_channel_id
    self.pubkeys = pubkeys
    self.kinds = kinds
    self.authors = authors
    self.since = since
    self.until = until
    self.event_refs = event_refs
    self.pubkey_refs = pubkey_refs
    self.keywords = keywords
    self.ng_keywords = ng_keywords


class QueueStatus(IntEnum):
  NOT_YET = 0
  DONE = 1
  FORBIDDEN = 403
  NOT_FOUND = 404
  EVENT_NOT_FOUND = 4040
  GIVE_UP = -100


class NotifyQueue(Base):
  id = Column(Integer, autoincrement=True, primary_key=True)
  event_id = Column(Integer)
  status = Column(Integer) # QueueStatus
  target_channel_id = Column(BigInteger)
  error_count = Column(Integer)
  created_at = Column(DateTime, default=datetime.utcnow)

  __tablename__ = 'notify_queue'

  def __init__(self, event_id, target_channel_id):
    self.event_id = event_id
    self.status = QueueStatus.NOT_YET.value
    self.target_channel_id = target_channel_id
    self.error_count = 0


class NgWord(Base):
  id = Column(Integer, autoincrement=True, primary_key=True)
  status = Column(Integer)
  word = Column(Text)
  created_at = Column(DateTime, default=datetime.utcnow)

  __tablename__ = 'ng_words'

  def __init__(self, word):
    self.status = 0
    self.word = word
