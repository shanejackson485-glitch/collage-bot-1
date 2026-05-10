import os
import asyncio
import json
import logging
import time
import discord
from discord.ext import commands
from patched_gateway import PatchedWebSocket

discord.gateway.DiscordWebSocket = PatchedWebSocket
discord.client.DiscordWebSocket = PatchedWebSocket
discord.state.DiscordWebSocket = PatchedWebSocket


handler = logging.FileHandler(filename='logs/collage.log', encoding='utf-8', mode='a')

try:
    with open("data/Developer/config.json", "r") as config_file:
        config = json.load(config_file)
    TOKEN = config["token"]
    PREFIX = config["prefix"]
except FileNotFoundError:
    print("ERROR: config.json not found. Please create it.")
    exit()
except KeyError as e:
    print(f"ERROR: Missing key {e} in config.json.")
    exit()



class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.start_time = time.time()

    async def setup_hook(self):
        """This is called once when the bot logs in to load cogs recursively."""
        print("Loading cogs...")
        

        for root, dirs, files in os.walk("./cogs"):
            for filename in files:

                if filename.endswith(".py") and not filename.startswith("__") and filename not in ["config.py", "helpers.py"]:
                    

                    file_path = os.path.join(root, filename)
                    




                    module_name = os.path.relpath(file_path, ".").replace(os.path.sep, ".")[:-3]

                    try:
                        await self.load_extension(module_name)
                        print(f"-> Loaded cog: {module_name}")
                    except Exception as e:

                        print(f"-> Failed to load cog {module_name}: {e}")
                        
        print("Cog loading complete.")

    async def on_message(self, message):
        """
        override for default on_message event
        """
        pass


intents = discord.Intents.default()

intents.message_content = False
intents.members = True





def get_prefix(bot, message):

    mentions = commands.when_mentioned(bot, message)


    spaced_mentions = [m + " " for m in mentions]


    return spaced_mentions + list(mentions) + [PREFIX]





bot = Bot(command_prefix=get_prefix, intents=intents, help_command=None)


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown requested.")