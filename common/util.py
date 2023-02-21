
import time
import yaml
import json
import ssl
import re
from nostr.filter import Filter, Filters
from nostr.event import EventKind
from nostr.relay_manager import RelayManager
from nostr.message_type import ClientMessageType
from nostr.key import PublicKey
from nostr import bech32


with open('./common/config.yml', 'r') as yml:
  config = yaml.safe_load(yml)


def get_note_id(_id):
  converted_bits = bech32.convertbits(bytes.fromhex(_id), 8, 5)
  return bech32.bech32_encode("note", converted_bits, bech32.Encoding.BECH32)


def get_images_urls(content):
  replaced_content = content
  pattern = re.compile(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)')
  image_urls = re.findall(pattern, content)
  for image_url in image_urls:
    replaced_content = replaced_content.replace(image_url, '')

  return image_urls, replaced_content


def get_meta_data(pubkey):
  filters = Filters([
      Filter(authors=[pubkey], kinds=[EventKind.SET_METADATA], limit=1),
  ])
  subscription_id = "nostify_get_meta"
  request = [ClientMessageType.REQUEST, subscription_id]
  request.extend(filters.to_json_array())

  relay_manager = RelayManager()
  for relay_server in config["relay_servers"]:
    relay_manager.add_relay(relay_server)

  relay_manager.add_subscription_on_all_relays(subscription_id, filters)
  time.sleep(1.25)

  event_content_list = []
  give_up_count = 0
  while True:
    while relay_manager.message_pool.has_events():
      event_msg = relay_manager.message_pool.get_event()
      print(event_msg.event.content)
      content = json.loads(event_msg.event.content)
      content['timestamp'] = event_msg.event.created_at
      event_content_list.append(content)
    if len(event_content_list) > 0 or give_up_count > 10:
      break
    time.sleep(1)
    give_up_count += 1

  relay_manager.close_all_relay_connections()

  if len(event_content_list) > 0:
    result = sorted(event_content_list, key=lambda x: x['timestamp'], reverse=True)
    return result[0]
  else:
    return None
