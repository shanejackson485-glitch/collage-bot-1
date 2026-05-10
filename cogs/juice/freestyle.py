import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import eyed3
import time
import asyncio

from .helpers import FREESTYLES_PATH


class FreestyleSelect(Select):
    def __init__(self, options, callback_func):
        super().__init__(options=options)
        self.placeholder = "Select the correct freestyle"
        self.min_values = 1
        self.max_values = 1
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        selected_file = self.values[0]

        await interaction.response.defer() 
        await self.callback_func(interaction, selected_file)

class Freestyle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    @commands.hybrid_command(
        name="freestyle",
        with_app_command=True,
        description="Search for and send a freestyle."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def freestyle(self, ctx: commands.Context, *, query: str = None):
        
        if ctx.interaction:
            await ctx.defer()
            
        if not query:
            embed = discord.Embed(
                title="Missing Song Name",
                description="Please provide a song name to search for a freestyle.\nExample: `/freestyle stan`",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed) 
            return

        matches = []
        if os.path.exists(FREESTYLES_PATH):
            for root, _, files in os.walk(FREESTYLES_PATH):
                for file in files:
                    if query.lower() in file.lower() and file.lower().endswith('.mp3'):
                        if len(matches) < 25: 
                            matches.append(os.path.join(root, file))

        if not matches:
            await self.send_message(ctx, embed=discord.Embed(
                title=":x: No Freestyles Found",
                description=f"No freestyles matching `'{query}'` found!",
                color=discord.Color.red()
            ))
            return

        if len(matches) == 1:
            await self.send_freestyle(ctx, matches[0]) 
        else:
            options = [discord.SelectOption(label=os.path.basename(f)[:100], value=f) for f in matches]
            view = View()
            view.add_item(FreestyleSelect(options, self.send_freestyle))

            embed = discord.Embed(
                title="Multiple Freestyles Found",
                description="Select the correct freestyle from the dropdown below.",
                color=discord.Color.dark_gray()
            )
            await self.send_message(ctx, embed=embed, view=view)

    async def send_freestyle(self, ctx_or_interaction, file_path: str):
        if not os.path.exists(file_path):
            await self.send_message(ctx_or_interaction, ":x: File no longer exists.")
            return

        await self.process_freestyle(ctx_or_interaction, file_path)

    async def process_freestyle(self, ctx_or_interaction, file_path: str):



        try:
            audiofile = eyed3.load(file_path)
        except Exception:
            audiofile = None

        if not audiofile:
            await self.send_message(ctx_or_interaction, ":x: Failed to load MP3 metadata.")
            return

        title = audiofile.tag.title or "Unknown"
        artist = audiofile.tag.artist or "Unknown"
        album = audiofile.tag.album or "Unknown"
        duration = int(audiofile.info.time_secs)
        formatted_length = f"{duration // 60}:{duration % 60:02d}"

        embed = discord.Embed(
            title=f"{title}",
            description=f"**Artist**\n `{artist}`\n**Album**\n `{album}`\n**Length**\n `{formatted_length}`",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="File will be deleted after 60 seconds.")

        file = None
        if audiofile.tag.frame_set.get(b'APIC'):
            image_data = audiofile.tag.frame_set.get(b'APIC')[0].image_data
            with open("cover.jpg", "wb") as f:
                f.write(image_data)
            file = discord.File("cover.jpg", filename="cover.jpg")
            embed.set_thumbnail(url="attachment://cover.jpg")

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

            mp3_file = discord.File(file_path, filename=os.path.basename(file_path))

            await interaction.followup.send(file=mp3_file, ephemeral=True)

        button.callback = button_callback
        view = View()
        view.add_item(button)

        await self.send_message(ctx_or_interaction, embed=embed, view=view, file=file)
        
        if file and os.path.exists("cover.jpg"):
            os.remove("cover.jpg")

    async def send_message(self, ctx_or_interaction, *args, **kwargs):
        if isinstance(ctx_or_interaction, discord.Interaction):
            if ctx_or_interaction.response.is_done():
                return await ctx_or_interaction.followup.send(*args, **kwargs)
            else:
                return await ctx_or_interaction.response.send_message(*args, **kwargs)
        else:
            return await ctx_or_interaction.send(*args, **kwargs)

async def setup(bot):
    await bot.add_cog(Freestyle(bot))