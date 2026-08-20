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


# --- 1. THE FOLDER LOADER ---
# This special function runs BEFORE the bot logs in. 
# It loops through your folders and loads all your python command files.
@bot.event
async def setup_hook():
    # List of all the folders you store your command files in
    folders_to_load = ["cogs", "heist", "data"]
    
    for folder in folders_to_load:
        if os.path.exists(folder):
            print(f"📁 Scanning folder: {folder}...")
            for filename in os.listdir(folder):
                if filename.endswith(".py") and not filename.startswith("__"):
                    try:
                        # Converts 'cogs/heist_command.py' into 'cogs.heist_command'
                        cog_path = f"{folder}.{filename[:-3]}"
                        await bot.load_extension(cog_path)
                        print(f"   ✅ Loaded: {cog_path}")
                    except Exception as e:
                        print(f"   ❌ Failed to load {filename}: {e}")
        else:
            print(f"⚠️ Warning: Folder '{folder}' was not found in your project directory.")


# --- 2. THE STARTUP SYNCER ---
@bot.event
async def on_ready():
    print(f"✅ Logged in successfully as {bot.user.name}")
    try:
        # This registers all the loaded slash commands with Discord globally
        synced = await bot.tree.sync()
        print(f"🔄 Automatically synced {len(synced)} slash commands globally!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")


# --- 3. START THE BOT ---
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing from the environment variables.")
