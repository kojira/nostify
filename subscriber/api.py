
import time
import yaml
import json
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.relay_manager import RelayManager

from flask import Flask, jsonify, request
import asyncio
from multiprocessing import Pool

with open('./common/config.yml', 'r') as yml:
  config = yaml.safe_load(yml)

app = Flask(__name__)


def get_meta_data(pubkey):
  filters = FiltersList([
      Filters(authors=[pubkey], kinds=[EventKind.SET_METADATA], limit=1),
  ])
  subscription_id = "get_meta"

  relay_manager = RelayManager()
  for relay_server in config["relay_servers"]:
    relay_manager.add_relay(relay_server)

  relay_manager.add_subscription_on_all_relays(subscription_id, filters)
  relay_manager.run_sync()

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


def run_asyncio(loop):
  asyncio.set_event_loop(loop)
  loop.run_forever()


@app.route('/meta', methods=['GET'])
def get_meta():
  print("get_meta")
  pubkey = request.args.get('pubkey')
  pool = Pool(1)
  result = pool.apply_async(get_meta_data, (pubkey,))
  user_meta = result.get()
  pool.close()
  pool.join()
  if user_meta:
    user_meta_dict = {
        'result': True,
        'display_name': user_meta['display_name'],
        'name': user_meta['name'],
        'picture': user_meta['picture'],
    }
  else:
    user_meta_dict = {
        'result': False
    }

  return jsonify(user_meta_dict)


if __name__ == '__main__':
  app.run(host='0.0.0.0')
