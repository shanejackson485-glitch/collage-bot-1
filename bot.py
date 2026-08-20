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


# --- 1. RENDER-PROOF FOLDER LOADER ---
# This function automatically scans and loads all your folder files before logging in.
@bot.event
async def setup_hook():
    # Gets the exact directory where this main file lives on Render's server
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    folders_to_load = ["cogs", "heist", "data"]
    
    for folder in folders_to_load:
        full_folder_path = os.path.join(BASE_DIR, folder)
        
        if os.path.exists(full_folder_path):
            print(f"📁 Scanning folder: {folder}...")
            for filename in os.listdir(full_folder_path):
                if filename.endswith(".py") and not filename.startswith("__"):
                    try:
                        # Format needed for discord.py: "foldername.filename"
                        cog_path = f"{folder}.{filename[:-3]}"
                        await bot.load_extension(cog_path)
                        print(f"   ✅ Loaded: {cog_path}")
                    except Exception as e:
                        print(f"   ❌ Failed to load {filename}: {e}")
        else:
            print(f"⚠️ Warning: Folder '{folder}' not found at {full_folder_path}")


# --- 2. THE STARTUP SYNCER ---
@bot.event
async def on_ready():
    print(f"✅ Logged in successfully as {bot.user.name}")
    try:
        # Registers your slash commands globally
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
