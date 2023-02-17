import os
import sys
import traceback
import importlib
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

sys.path.append('./common')

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_APPLICATION_ID = os.environ.get("BOT_APPLICATION_ID")
ADMIN_GUILD = os.environ.get("ADMIN_GUILD", None)


class MyClient(commands.Bot):
  def __init__(self, *, intents: discord.Intents, application_id: int):
    super().__init__(command_prefix="!", help_command=None, intents=intents, application_id=application_id)
    print("client init")

  async def setup_hook(self):
    print("setup_hook start")
    self.db = None
    self.load_db()

    await self.load_cog_plugins()
    print("setup_hook end")

  def load_db(self):
    print("load_db start")
    if self.db:
      importlib.reload(self.db)
    else:
      import db as db
      self.db = db
    print("load db")

  async def load_cog_plugins(self):
    plugin_dir = "plugins"

    old_items = set(self.extensions)
    new_items = set(map(
        lambda x: f'{plugin_dir}.{x[:-3]}',
        filter(
            lambda x: x.endswith('.py'),
            os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), plugin_dir)))
    ))
    if old_items == new_items:
      print("reload extensions")
      for p in old_items:
        await self.reload_extension(p)
    else:
      print("unload extensions")
      for p in old_items:
        await self.unload_extension(p)
      print("load extensions")
      for p in new_items:
        print("loading: ", p)
        await self.load_extension(p)
    print("load_cog_plugins success")

  async def on_ready(self):
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    await self.change_presence(activity=discord.Game("Nostr"))

    print("global sync")
    await self.tree.sync()
    print("global sync done")

    if ADMIN_GUILD:
      try:
        print("admin guild sync")
        await self.tree.sync(guild=discord.Object(id=ADMIN_GUILD))
        print("admin guild sync done")
      except Exception as e:
        traceback.format_exc()
        print("admin guild sync: \"(id={})\" sync faild".format(ADMIN_GUILD))


def cog_versions(client) -> str:
  cogs = client.cogs
  cog_instans = []

  for cog_name in cogs:
    cog = client.get_cog(cog_name)
    name = None
    if cog is None:
      continue
    name = cog_name
    if cog.info:
      name += "(" + cog.info["name"] + ", " + cog.info["version"] + ")"
    cog_instans.append(name)

  return ", ".join(cog_instans)


if __name__ == "__main__":
  intents = discord.Intents.default()
  client = MyClient(intents=intents, application_id=BOT_APPLICATION_ID)

  @client.tree.command(description="[Admin] reload plugin")
  @app_commands.default_permissions()
  @app_commands.guilds(discord.Object(ADMIN_GUILD))
  async def reload(interaction: discord.Integration):
    print("reload start")
    commands = client.commands
    tree = client.tree.get_commands()

    old_cogs_str = cog_versions(client)
    old_commands_str = ", ".join(commands)
    old_tree_str = ", ".join(map(lambda x: x.name, tree))

    await client.load_cog_plugins()

    commands = client.commands
    tree = client.tree.get_commands()

    cogs_str = cog_versions(client)
    commands_str = ", ".join(commands)
    tree_str = ", ".join(map(lambda x: x.name, tree))

    message = [
        "reloaded.",
        "before",
        f"  cogs: {old_cogs_str}",
        f"  commands: {old_commands_str}",
        f"  tree: {old_tree_str}",
        "now",
        f"  cogs: {cogs_str}",
        f"  commands: {commands_str}",
        f"  tree: {tree_str}"
    ]
    await interaction.response.send_message("\n".join(message))
    print("reload done.")

  try:
    client.run(BOT_TOKEN)
  except KeyboardInterrupt:
    print("exit")
  except Exception:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    trace = traceback.format_exc()
    print(trace)
