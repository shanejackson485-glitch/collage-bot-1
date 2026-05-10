import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
import datetime
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

from .helpers import LEAKS_PATH





def get_mp3_metadata(file_path):
    """
    Extract metadata from an MP3 file.
    Returns a dict with: title, artist, album, length, cover (bytes)
    """
    if not os.path.exists(file_path):
        return None

    metadata = {"title": None, "artist": None, "album": None, "length": None, "cover": None}

    try:
        audio = MP3(file_path, ID3=ID3)
        metadata["length"] = str(int(audio.info.length)) + "s"

        tags = ID3(file_path)

        if "TIT2" in tags:
            metadata["title"] = tags["TIT2"].text[0]
        if "TPE1" in tags:
            metadata["artist"] = tags["TPE1"].text[0]
        if "TALB" in tags:
            metadata["album"] = tags["TALB"].text[0]


        if "APIC:" in tags:
            metadata["cover"] = tags["APIC:"].data
        else:
            for key in tags.keys():
                if key.startswith("APIC"):
                    metadata["cover"] = tags[key].data
                    break

    except Exception as e:
        print(f"[get_mp3_metadata] Error reading {file_path}: {e}")
        return None

    return metadata





class SongOfTheDay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_of_the_day = None
        self.reset_task.start()

    def cog_unload(self):
        self.reset_task.cancel()

    def pick_song(self):
        """Pick a random MP3 from leaks folder recursively."""
        if not os.path.exists(LEAKS_PATH):
            print(f"[SOTD] Leaks path not found: {LEAKS_PATH}")
            return None

        all_mp3s = []
        for root, dirs, files in os.walk(LEAKS_PATH):
            for file in files:
                if file.lower().endswith(".mp3"):
                    all_mp3s.append(os.path.join(root, file))
        
        print(f"[DEBUG] Found {len(all_mp3s)} mp3s in leaks")
        return random.choice(all_mp3s) if all_mp3s else None

    @tasks.loop(minutes=1)
    async def reset_task(self):
        """Reset SOTD at midnight."""
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute == 0:
            self.song_of_the_day = self.pick_song()
            print(f"[DEBUG] New song of the day picked: {self.song_of_the_day}")

    @reset_task.before_loop
    async def before_reset(self):
        await self.bot.wait_until_ready()
        self.song_of_the_day = self.pick_song()
        print(f"[DEBUG] Startup song of the day: {self.song_of_the_day}")

    @commands.hybrid_command(
        name="sotd",
        with_app_command=True,
        description="Send today's Song of the Day with metadata and download button."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def sotd_command(self, ctx: commands.Context):
        """Send today's Song of the Day with metadata and download button."""

        if ctx.interaction:
            await ctx.defer()

        if not self.song_of_the_day:
            self.song_of_the_day = self.pick_song()

        if not self.song_of_the_day:
            await ctx.send("❌ No song of the day available (no mp3 files found).")
            return

        file_path = self.song_of_the_day
        metadata = get_mp3_metadata(file_path)

        embed = discord.Embed(
            title="🎵 Song of the Day",
            description="Click the button below to download!",
            color=discord.Color.blue()
        )

        if metadata:
            embed.add_field(name="Title", value=f"`{metadata.get('title', 'Unknown')}`", inline=False)
            embed.add_field(name="Artist", value=f"`{metadata.get('artist', 'Unknown')}`", inline=True)
            embed.add_field(name="Album", value=f"`{metadata.get('album', 'Unknown')}`", inline=True)
            embed.add_field(name="Length", value=f"`{metadata.get('length', 'Unknown')}`", inline=True)

            if metadata.get("cover"):
                with open("cover.jpg", "wb") as f:
                    f.write(metadata["cover"])
                embed.set_thumbnail(url="attachment://cover.jpg")
                file = discord.File("cover.jpg", filename="cover.jpg")
            else:
                file = None
        else:
            embed.add_field(name="File", value=os.path.basename(file_path))
            file = None

        button = discord.ui.Button(label="Download", style=discord.ButtonStyle.green)

        async def button_callback(interaction: discord.Interaction):
            await interaction.response.send_message("<a:GTALoading:1348124710394662995> Preparing your file...", ephemeral=True)
            mp3_file = discord.File(file_path, filename=os.path.basename(file_path))
            await interaction.followup.send(file=mp3_file, ephemeral=True)

        button.callback = button_callback
        view = discord.ui.View()
        view.add_item(button)

        await ctx.send(embed=embed, view=view, file=file)


        if file and os.path.exists("cover.jpg"):
            os.remove("cover.jpg")

async def setup(bot):
    await bot.add_cog(SongOfTheDay(bot))