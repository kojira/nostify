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
            "version": "0.0.1",
        }

    def get_name(self):
        return self.info["name"]

    def get_version(self):
        return self.info["version"]

    def get_plugin_info(self):
        return self.info

    def get_help(self):
        return {
            "filter": ["チャンネルに通知するフィルタを設定します。"]
        }

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} on_ready")

    @app_commands.command(description="filter")
    async def filter(self, interaction: discord.Integration):
        await interaction.response.send_modal(InputFilter(self.bot))
