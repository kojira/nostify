import discord
from discord.ext import commands
from discord import app_commands
from nostr.key import PublicKey


async def setup(bot):
  await bot.add_cog(Filter(bot))


class InputFilter(discord.ui.Modal, title="フィルター"):
  def __init__(self, bot) -> None:
    super().__init__()
    self.bot = bot
    self.db = bot.db

  pubkeys = discord.ui.TextInput(
      label="取得したいnoteのpubkeyを一行ずつ入力してください。※npubから始まる文字列",
      placeholder="npub",
      style=discord.TextStyle.long,
      required=False,
  )

  async def on_submit(self, interaction: discord.Interaction):
    pubkeys = self.pubkeys.value.split('\n')
    hex_pubkey_list = []
    for pubkey in pubkeys:
      if not pubkey.startswith("npub"):
        await interaction.response.send_message("npubから始まる文字列を指定してください")
        return
      else:
        hex_key = PublicKey.from_npub(pubkey).hex()
        hex_pubkey_list.append(hex_key)
    hex_pubkeys = ','.join(hex_pubkey_list)
    self.db.addFilter(interaction.guild_id, interaction.channel_id, hex_pubkeys)

    await interaction.response.send_message("フィルタを設定しました。")

  async def on_error(self, interaction: discord.Interaction, error: Exception):
    print(error)
    await interaction.response.send_message('入力をキャンセルしました')


class Filter(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db = bot.db
    self.info = {
        "name": "filter",
        "version": "0.0.2",
    }

  def get_name(self):
    return self.info["name"]

  def get_version(self):
    return self.info["version"]

  def get_plugin_info(self):
    return self.info

  def get_help(self):
    return {
        "filter": ["""チャンネルに通知するフィルタを設定。
引数:
　`引数なし`:ダイアログでフィルタする値を設定
　`clear`:チャンネルに設定されているフィルタをクリア
　`check`:設定されているフィルタを表示
　`suspend`:チャンネルへの投稿を一時停止
　`resume`:チャンネルへの投稿を再開(再開後に新規に受信したもの)
"""
                   ],
    }

  @commands.Cog.listener()
  async def on_ready(self):
    print(f"{__name__} on_ready")

  def getFilterListForDisplay(self, channel_id):
    filters = self.db.getFiltersWithChannelId(channel_id)
    message = "このチャンネルのフィルタ設定\n"
    for filter in filters:
      pubkeys = "\n　　".join(filter.pubkeys.split(","))
      message += f"状態:{filter.status}\n　pubkeys:\n　　{pubkeys}\n"

    return message

  @app_commands.command(description="filter")
  async def filter(self, interaction: discord.Integration, arg: str = None):
    if arg:
      if arg == "clear":
        self.db.clearFilters(interaction.channel_id)
        await interaction.response.send_message("チャンネルのフィルタをクリアしました。")
      elif arg == "suspend":
        self.db.suspendFilters(interaction.channel_id)
        await interaction.response.send_message("チャンネルの投稿を一時停止しました。")
      elif arg == "resume":
        self.db.resumeFilters(interaction.channel_id)
        await interaction.response.send_message("チャンネルの投稿を再開しました。")
      elif arg == "check":
        message = self.getFilterListForDisplay(interaction.channel_id)
        await interaction.response.send_message(message)
    else:
      await interaction.response.send_modal(InputFilter(self.bot))
