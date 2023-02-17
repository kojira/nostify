import discord
from discord.ext import commands
from discord import app_commands


async def setup(bot):
  await bot.add_cog(Help(bot))


class Help(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db = bot.db
    self.info = {
        "name": "help",
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
        "help": ["ヘルプを表示します。"]
    }

  @commands.Cog.listener()
  async def on_ready(self):
    print(f"{__name__} on_ready")

  @app_commands.command(description="help")
  async def help(self, interaction: discord.Integration):
    cogs = self.bot.cogs
    tree = self.bot.tree.get_commands(type=discord.AppCommandType.chat_input)
    tree.sort(key=lambda x: x.name)

    message = []

    for command in tree:
      message.append(f"**/{command.name}**")
      for cog_name in cogs:
        cog = self.bot.get_cog(cog_name)
        if hasattr(cog, "get_help"):
          for key, val in cog.get_help().items():
            if key == command.name:
              if isinstance(val, str):
                message.append(" " + val)
              elif isinstance(val, list):
                strs = []
                for k in val:
                  strs.append("  " + k)
                message.append("\n".join(strs))
              else:
                print("warning help! ", key, val)

      await interaction.response.send_message("\n".join(message))
