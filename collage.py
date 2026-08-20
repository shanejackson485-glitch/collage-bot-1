import os
import asyncio
import json
import logging
import time
import discord
from discord.ext import commands
from patched_gateway import PatchedWebSocket

# Hot-patching the gateway as required by your architecture
discord.gateway.DiscordWebSocket = PatchedWebSocket
discord.client.DiscordWebSocket = PatchedWebSocket
discord.state.DiscordWebSocket = PatchedWebSocket

# Create the logs folder automatically if it does not exist on Render
os.makedirs('logs', exist_ok=True)

# Define your file handler
handler = logging.FileHandler(filename='logs/collage.log', encoding='utf-8', mode='a')

# Load Configuration
try:
    with open("data/Developer/config.json", "r") as config_file:
        config = json.load(config_file)
    TOKEN = config["token"].strip()  # .strip() sanitizes hidden spacing/newlines
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
        """Override for default on_message event"""
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
    # Setup clean manual logging without using default root loggers
    discord.utils.setup_logging(handler=handler, root=False)
    
    # Pre-flight check: Make sure your script actually loaded a token string
    if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
        print("CRITICAL ERROR: The bot token is empty or placeholder in config.json.")
        return

    async with bot:
        try:
            await bot.start(TOKEN)
        except discord.errors.LoginFailure:
            print("\n" + "="*60)
            print("CRITICAL CONFIGURATION ERROR: 401 UNAUTHORIZED")
            print("Discord completely rejected this token. Please:")
            print("1. Go to the Discord Developer Portal.")
            print("2. Re-generate a fresh token from the 'Bot' tab.")
            print("3. Ensure you copied the Bot Token, NOT your Client ID/Public Key.")
            print("="*60 + "\n")
        except Exception as e:
            print(f"An unexpected startup error occurred: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown requested.")
