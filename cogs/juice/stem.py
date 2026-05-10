import discord
from discord.ext import commands
from discord import app_commands, ui
from discord.ui import View, Button
import os
import time
import asyncio
import json
import eyed3

from .helpers import STATS_FILE, STEMS_PATH






class StemSelect(ui.Select):
    def __init__(self, options, callback_func):
        super().__init__(options=options)
        self.placeholder = "Select the correct stem"
        self.min_values = 1
        self.max_values = 1
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        selected_file = self.values[0]
        await interaction.response.defer()

        await self.callback_func(interaction, selected_file) 

class StemView(View):
    def __init__(self, select_options, callback_func, *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(StemSelect(select_options, callback_func))





class StemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    @commands.hybrid_command(
        name="stem",
        description="Search for and send a song stem by name."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def stem(self, ctx: commands.Context, *, query: str = None):
        """Find and send stems matching the query."""

        if ctx.interaction:
            await ctx.defer()

        if not query:
            embed = discord.Embed(
                title="Missing Song Name",
                description="Please provide a song name to search for a stem.\nExample: `/stem lucid dreams`",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed, ephemeral=True)
            return

        matches = []

        if os.path.exists(STEMS_PATH):
            for root, _, files in os.walk(STEMS_PATH):
                for file in files:
                    if query.lower() in file.lower() and file.lower().endswith('.mp3'):
                        matches.append(os.path.join(root, file))
        
        if not matches:
            embed = discord.Embed(
                title=":x: No Stems Found",
                description=f"No stems matching '{query}' found!",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed, ephemeral=True)
            return


        if len(matches) == 1:
            await self.send_stem(ctx, matches[0])
            return


        options = [
            discord.SelectOption(label=os.path.basename(f)[:100], value=f)
            for f in matches[:25]
        ]
        view = StemView(options, self.send_stem)

        embed = discord.Embed(
            title="Multiple Stems Found",
            description="Select the correct stem from the dropdown below.",
            color=discord.Color.dark_gray()
        )
        await self.send_message(ctx, embed=embed, view=view)

    async def send_stem(self, ctx_or_interaction, file_path: str):
        if not os.path.exists(file_path):
            await self.send_message(ctx_or_interaction, ":x: File no longer exists.")
            return


        try:
            audiofile = eyed3.load(file_path)
        except Exception:
            audiofile = None

        if not audiofile:
            await self.send_message(ctx_or_interaction, ":x: Could not read MP3 metadata.")
            return

        title = audiofile.tag.title or "Unknown"
        artist = audiofile.tag.artist or "Unknown"
        album = audiofile.tag.album or "Unknown"
        duration = int(audiofile.info.time_secs)
        formatted_length = f"{duration // 60}:{duration % 60:02d}"

        embed = discord.Embed(
            title=title,
            description=f"**Artist**: `{artist}`\n**Album**: `{album}`\n**Length**: `{formatted_length}`",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click the button below to download this file.")

        cover_file = None

        if audiofile.tag.frame_set.get(b'APIC'):
            image_data = audiofile.tag.frame_set.get(b'APIC')[0].image_data
            with open("cover.jpg", "wb") as f:
                f.write(image_data)
            cover_file = discord.File("cover.jpg", filename="cover.jpg")
            embed.set_thumbnail(url="attachment://cover.jpg")

        user_id = (
            ctx_or_interaction.user.id
            if isinstance(ctx_or_interaction, discord.Interaction)
            else ctx_or_interaction.author.id
        )

        button = Button(label="Download", style=discord.ButtonStyle.green)

        async def button_callback(interaction: discord.Interaction):
            now = time.time()
            last_used = self.cooldowns.get(interaction.user.id, 0)

            if now - last_used < 30:
                remaining = int(30 - (now - last_used))
                await interaction.response.send_message(
                    f"⏳ Please wait {remaining}s before downloading again.",
                    ephemeral=True
                )
                return

            self.cooldowns[interaction.user.id] = now

            await interaction.response.send_message("<a:GTALoading:1348124710394662995> Preparing your file...", ephemeral=True)
            await asyncio.sleep(2)

            file_size = os.path.getsize(file_path)
            mp3_file = discord.File(file_path, filename=os.path.basename(file_path))


            if os.path.exists(STATS_FILE):
                try:
                    with open(STATS_FILE, "r") as f:
                        stats = json.load(f)
                except:
                    stats = {"total_downloads": 0, "total_size_bytes": 0, "users": {}}
            else:
                stats = {"total_downloads": 0, "total_size_bytes": 0, "users": {}}

            stats["total_downloads"] += 1
            stats["total_size_bytes"] += file_size

            uid = str(interaction.user.id)
            if uid not in stats["users"]:
                stats["users"][uid] = {"downloads": 0, "size_bytes": 0}
            stats["users"][uid]["downloads"] += 1
            stats["users"][uid]["size_bytes"] += file_size

            with open(STATS_FILE, "w") as f:
                json.dump(stats, f, indent=4)

            await interaction.followup.send(file=mp3_file, ephemeral=True)

        button.callback = button_callback
        view = View()
        view.add_item(button)

        await self.send_message(ctx_or_interaction, embed=embed, view=view, file=cover_file)


        if cover_file and os.path.exists("cover.jpg"):
            os.remove("cover.jpg")

    async def send_message(self, ctx_or_interaction, *args, **kwargs):

        ephemeral = kwargs.pop('ephemeral', False)
        if isinstance(ctx_or_interaction, discord.Interaction):
            if ctx_or_interaction.response.is_done():
                return await ctx_or_interaction.followup.send(*args, ephemeral=ephemeral, **kwargs)
            else:
                return await ctx_or_interaction.response.send_message(*args, ephemeral=ephemeral, **kwargs)
        else:
            return await ctx_or_interaction.send(*args, **kwargs)

async def setup(bot):
    await bot.add_cog(StemCog(bot))