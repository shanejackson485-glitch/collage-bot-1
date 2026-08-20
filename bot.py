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


# --- 🚨 EXTREME OVERRIDE AUTO-LOADER ---
# This looks through EVERY folder in your project automatically
@bot.event
async def setup_hook():
    print("🔍 Beginning absolute scan of your project files...")
    
    # Get the root location of your running application on Render
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # We ignore virtual environments and hidden setup files
    ignored_folders = {'.venv', 'venv', '__pycache__', '.git', '.github'}

    for root, dirs, files in os.walk(root_dir):
        # Skip internal system folders entirely
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        
        for filename in files:
            if filename.endswith(".py") and filename != os.path.basename(__file__) and not filename.startswith("__"):
                # Find the relative path from your main script to the command file
                rel_path = os.path.relpath(os.path.join(root, filename), root_dir)
                # Convert standard paths like 'cogs/heist/file.py' into python modules 'cogs.heist.file'
                cog_module = rel_path[:-3].replace(os.path.sep, ".")
                
                try:
                    await bot.load_extension(cog_module)
                    print(f"   ✅ FORCE LOADED: {cog_module}")
                except Exception as e:
                    print(f"   ❌ Found file '{cog_module}' but it failed to load: {e}")


# --- THE STARTUP SYNCER ---
@bot.event
async def on_ready():
    print(f"✅ Logged in successfully as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Automatically synced {len(synced)} slash commands globally!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")


# --- START THE BOT ---
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing from the environment variables.")
