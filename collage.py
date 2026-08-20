import os
import asyncio
import logging
import time
import discord
from discord.ext import commands

# Automatically set up logs folder in your workspace
os.makedirs('logs', exist_ok=True)
handler = logging.FileHandler(filename='logs/collage.log', encoding='utf-8', mode='a')

# FETCH FROM RENDER ENVIRONMENT VARIABLES INSTEAD OF CONFIG.JSON
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("DISCORD_PREFIX", "!")  # Defaults to ! if not provided

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    async def setup_hook(self):
        """Loads your extension cogs dynamically at execution setup."""
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
        pass

# Gateway Intent Declarations
intents = discord.Intents.default()
intents.message_content = False
intents.members = True

def get_prefix(bot, message):
    mentions = commands.when_mentioned(bot, message)
    spaced_mentions = [m + " " for m in mentions]
    return spaced_mentions + list(mentions) + [PREFIX]

bot = Bot(command_prefix=get_prefix, intents=intents, help_command=None)

async def main():
    discord.utils.setup_logging(handler=handler, root=False)
    
    # Validation step to ensure your hosting parameters were saved correctly
    if not TOKEN:
        print("\n" + "="*60)
        print("CRITICAL DEPLOYMENT ERROR: 'DISCORD_TOKEN' IS NOT SET!")
        print("Please log into Render, navigate to Environment Variables,")
        print("and add a variable named 'DISCORD_TOKEN' with your bot secret.")
        print("="*60 + "\n")
        return

    async with bot:
        try:
            await bot.start(TOKEN)
        except discord.errors.LoginFailure:
            print("\nCRITICAL AUTHENTICATION ERROR: 401 UNAUTHORIZED")
            print("The token stored inside your Render environment dashboard was rejected.")
        except Exception as e:
            print(f"An unexpected startup error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown requested.")
