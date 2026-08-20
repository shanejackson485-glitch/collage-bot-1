import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load secret environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up bot instances and permissions (Intents)
intents = discord.Intents.default()
intents.message_content = True  # Required to read message commands
bot = commands.Bot(command_prefix=",", intents=intents)


# --- 🚨 SYNCHRONOUS RUNNER OVERRIDE ---
# We load the files BEFORE starting the bot loop entirely 
# to bypass Python 3.14 async hook changes.
async def load_all_extensions():
    print("🔍 [STARTING SCAN] Searching for your folder files...")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ignored_folders = {'.venv', 'venv', '__pycache__', '.git', '.github'}

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for filename in files:
            if filename.endswith(".py") and filename != os.path.basename(__file__) and not filename.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, filename), root_dir)
                cog_module = rel_path[:-3].replace(os.path.sep, ".")
                try:
                    await bot.load_extension(cog_module)
                    print(f"   ✅ FORCE LOADED: {cog_module}")
                except Exception as e:
                    print(f"   ❌ Found file '{cog_module}' but it failed: {e}")


# --- THE STARTUP SYNCER ---
@bot.event
async def on_ready():
    print(f"✅ Logged in successfully as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Automatically synced {len(synced)} slash commands globally!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")


# --- THE MAIN ENTRY POINT ---
async def main():
    # 1. Force the extensions to load first
    await load_all_extensions()
    
    # 2. Run the bot
    if TOKEN:
        async with bot:
            await bot.start(TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing from the environment variables.")

if __name__ == "__main__":
    # Standard way to run async main in modern Python
    asyncio.run(main())
