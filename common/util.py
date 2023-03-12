
import time
import yaml
import json
import re
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.relay_manager import RelayManager
from pynostr import bech32

import requests
import asyncio

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


def get_mention(content):
  pattern = re.compile(r"<@\d{18}>")
  return pattern.findall(content)
