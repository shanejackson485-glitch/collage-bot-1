import os
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

@bot.event
async def on_ready():
    print(f"✅ Logged in successfully as {bot.user.name}")

@bot.command()
async def ping(ctx):
    """Simple test command to verify the bot workflow is alive."""
    await ctx.send("🏓 Pong! The workflow bot is active and running.")

# Start the bot
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing from the environment variables.")
