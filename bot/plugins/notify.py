import os
import sys
import time
import datetime
import asyncio
import traceback
import discord
from discord.ext import commands, tasks
import pytz

sys.path.append('./common')

from common.models import QueueStatus
import common.util as util

async def setup(bot):
    await bot.add_cog(Notify(bot))


def create_embed(author, date_time_str, note_id, content, icon_url=None, imageUrl=None):

  _embed: dict = {
      "title": "Nostr",
      "description": content[:4096],
      "fields": [
          {
              "name": "snort",
              "value": f"[open with snort](https://snort.social/e/{note_id})",
              "inline": True
          },
          {
              "name": "iris",
              "value": f"[open with iris](https://iris.to/post/{note_id})",
              "inline": True
          },
          {
              "name": "datetime",
              "value": date_time_str,
              "inline": True
          }
      ]
  }
  if imageUrl:
    _embed["image"] = {
        "url": imageUrl
    }
  if author:
    _embed["author"] = {
        "name": author,
        "icon_url": icon_url
    }
  return _embed


class Notify(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db = bot.db
    self.info = {
        "name": "notify",
        "version": "0.0.1"
    }
    self.notify.start()

  def get_name(self):
    return self.info["name"]

  def get_version(self):
    return self.info["version"]

  def get_plugin_info(self):
    return self.info

  @commands.Cog.listener()
  async def on_ready(self):
      print(f"{__name__} on_ready")

  def cog_unload(self):
      self.notify.cancel()

  @tasks.loop(seconds=30.0)
  async def notify(self):
      await self.async_notify()

  async def async_notify(self):
    loop = asyncio.get_running_loop()

    def do_task():
      return self.db.getNotifyQueues()

    notifyQueues = await loop.run_in_executor(None, do_task)

    for notifyQueue in notifyQueues:
      channel_id = notifyQueue.target_channel_id
      try:
        channel = self.bot.get_channel(channel_id)
        if channel:
          event = self.db.getEvent(notifyQueue.event_id)
          if event:
            image_urls, content = util.get_images_urls(event.content)
            image_url = None if image_urls is None or len(image_urls) < 1 else image_urls[0]
            user_meta = util.get_meta_data(event.pubkey)
            jst = pytz.timezone('Asia/Tokyo')
            date_time_str = event.event_created_at.astimezone(jst).strftime("%Y-%m-%d %H:%M:%S %z")
            if user_meta:
              _embed = create_embed(user_meta['display_name'], date_time_str, util.get_note_id(event.hex_event_id), content, icon_url=user_meta['picture'], imageUrl=image_url)
            else:
              icon_url = "https://www.gravatar.com/avatar/{event.pubkey}"
              _embed = create_embed(event.pubkey, date_time_str, util.get_note_id(event.hex_event_id), content, icon_url=icon_url, imageUrl=image_url)
            
            await channel.send(
                content="",
                embed=discord.Embed.from_dict(_embed),
            )
            self.db.updateNotifyQueue(notifyQueue.id, QueueStatus.DONE, notifyQueue.error_count)
          else:
            self.db.updateNotifyQueue(notifyQueue.id, QueueStatus.EVENT_NOT_FOUND, notifyQueue.error_count+1)
        else:
          self.db.updateNotifyQueue(notifyQueue.id, QueueStatus.NOT_FOUND, notifyQueue.error_count+1)
          print("channel not found. channel_id: {}, queue_id: {}".format(channel_id, notifyQueue.id))

      except discord.errors.Forbidden as e:
        self.db.updateNotifyQueue(notifyQueue.id, QueueStatus.FORBIDDEN, notifyQueue.error_count+1)
        print("channel permission error channel_id: {}, queue_id: {}".format(channel_id, notifyQueue.id))
        trace = traceback.format_exc()
        if e.code == 50013:
          # missing permissions
          print(e.text, channel_id)
        else:
          print(trace)
      except Exception:
        self.db.updateNotifyQueue(notifyQueue.id, QueueStatus.NOT_YET, notifyQueue.error_count+1)
        print("channel error channel_id: {}, queue_id: {}".format(channel_id, notifyQueue.id))
        trace = traceback.format_exc()
        print(trace)

  @notify.before_loop
  async def befor_notify(self):
      await self.bot.wait_until_ready()

