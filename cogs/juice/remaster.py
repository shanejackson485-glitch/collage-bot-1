import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import re
import time
import asyncio
import json


from .helpers import extract_metadata, STATS_FILE, REMASTERS_PATH





class RemasterSelect(Select):
    def __init__(self, options, callback_func):
        super().__init__(options=options)
        self.placeholder = "Select the correct remaster"
        self.min_values = 1
        self.max_values = 1
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        selected_remaster = self.values[0]
        await interaction.response.defer()
        await self.callback_func(interaction, selected_remaster)


class MP3Select(Select):
    def __init__(self, options, callback_func, folder_path):
        super().__init__(options=options)
        self.placeholder = "Choose MP3 version"
        self.min_values = 1
        self.max_values = 1
        self.callback_func = callback_func
        self.folder_path = folder_path

    async def callback(self, interaction: discord.Interaction):
        selected_file = self.values[0]
        await interaction.response.defer()
        await self.callback_func(interaction, self.folder_path, selected_file)





class Remasters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.base_path = REMASTERS_PATH

    @commands.hybrid_command(name="remaster", with_app_command=True, description="Search and send a remaster file.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def remaster_command(self, ctx: commands.Context, *, query: str):

        if ctx.interaction:
            await ctx.defer()

        if not os.path.exists(self.base_path):
            await self.send_message(ctx, ":x: Remasters directory not found. Please contact admin.")
            return

        all_folders = [f for f in os.listdir(self.base_path) if os.path.isdir(os.path.join(self.base_path, f))]

        def folder_terms(folder_name: str):
            main_part = folder_name.split("(")[0].strip()
            bracketed_parts = re.findall(r"\((.*?)\)", folder_name)
            return [main_part.lower()] + [part.lower() for part in bracketed_parts]

        query_lower = query.lower()

        matches = []
        for folder in all_folders:
            terms = folder_terms(folder)
            if any(query_lower in term for term in terms):
                matches.append(folder)

        if not matches:
            await self.send_message(ctx, ":x: No matching remaster folders found.")
            return

        if len(matches) == 1:
            folder_path = os.path.join(self.base_path, matches[0])
            await self.send_remaster(ctx, folder_path, ctx.author.avatar, self.bot.user.avatar)
        else:

            matches = matches[:25]
            options = [discord.SelectOption(label=f[:100], value=f) for f in matches]

            async def folder_selected(interaction: discord.Interaction, selected_folder):
                folder_path = os.path.join(self.base_path, selected_folder)
                await self.send_remaster(interaction, folder_path, interaction.user.avatar, self.bot.user.avatar)

            view = View()
            view.add_item(RemasterSelect(options, folder_selected))

            embed = discord.Embed(
                title="Multiple Remasters Found",
                description="Please select the correct remaster from the dropdown below.",
                color=discord.Color.dark_gray()
            )

            await self.send_message(ctx, embed=embed, view=view)

    async def send_remaster(self, ctx_or_interaction, folder_path, user_avatar, bot_avatar):
        if not os.path.exists(folder_path):
            await self.send_message(ctx_or_interaction, ":x: The folder does not exist!")
            return

        try:
            mp3_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]
        except Exception as e:
            await self.send_message(ctx_or_interaction, f":x: Failed to list files: {e}")
            return

        if not mp3_files:
            await self.send_message(ctx_or_interaction, ":x: No MP3 files found.")
            return

        if len(mp3_files) > 1:
            options = [discord.SelectOption(label=f[:100], value=f) for f in mp3_files[:25]]
            view = View()
            view.add_item(MP3Select(options, self.process_remaster, folder_path))

            embed = discord.Embed(
                title="Multiple Versions Found!",
                description="Select your preferred remaster from the dropdown below.",
                color=discord.Color.dark_gray()
            )
            await self.send_message(ctx_or_interaction, embed=embed, view=view)
        else:
            await self.process_remaster(ctx_or_interaction, folder_path, mp3_files[0])

    async def process_remaster(self, ctx_or_interaction, folder_path, file_name):
        mp3_file_path = os.path.join(folder_path, file_name)

        if not os.path.exists(mp3_file_path):
            await self.send_message(ctx_or_interaction, ":x: File no longer exists.")
            return

        metadata = extract_metadata(mp3_file_path)
        if not metadata:
            await self.send_message(ctx_or_interaction, ":x: Metadata extraction failed.")
            return

        embed = discord.Embed(
            title="Remaster Found",
            description="Click the button below to download this remaster.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Song", value=f"`{metadata.get('title', 'Unknown')}`", inline=False)
        embed.add_field(name="Artist", value=f"`{metadata.get('artist', 'Unknown')}`", inline=True)
        embed.add_field(name="Album", value=f"`{metadata.get('album', 'Unknown')}`", inline=True)
        embed.add_field(name="Length", value=f"`{metadata.get('length', 'Unknown')}`", inline=True)

        file = None
        if metadata.get("cover_data"):
            with open("cover.jpg", "wb") as f:
                f.write(metadata["cover_data"])
            file = discord.File("cover.jpg", filename="cover.jpg")
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

            await interaction.response.send_message(
                "<a:GTALoading:1348124710394662995> Preparing your file...",
                ephemeral=True
            )
            await asyncio.sleep(2)

            file_size = os.path.getsize(mp3_file_path)
            file = discord.File(mp3_file_path, filename=os.path.basename(mp3_file_path))


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

            await interaction.followup.send(file=file, ephemeral=True)
            
        button.callback = button_callback 

        view = discord.ui.View()
        view.add_item(button)

        await self.send_message(ctx_or_interaction, embed=embed, view=view, file=file)
        

        if os.path.exists("cover.jpg"):
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
    await bot.add_cog(Remasters(bot))