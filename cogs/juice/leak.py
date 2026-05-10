import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import io
import re
import string

from .helpers import (
    extract_metadata, 
    format_size, 
    update_stats_sync, 
    ERA_COLORS, 
    LEAKS_PATH, 
    LEAK_CACHE_FILE, 
    LEAK_ARCHIVE_CHANNEL_ID, 
    get_album_from_path,
    parse_folder_name,       
    get_file_download_count,
    get_juiceinfo_track,
    get_juiceinfo_shared_instrumental_titles,
    era_colors,
)






class SearchPaginationView(discord.ui.View):
    def __init__(self, matches, cog, user):
        super().__init__(timeout=60)
        self.matches = matches
        self.cog = cog
        self.user = user
        self.page = 0
        self.per_page = 25
        self.total_pages = (len(matches) - 1) // self.per_page + 1
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        self.prev_btn.disabled = (self.page == 0)
        self.next_btn.disabled = (self.page == self.total_pages - 1)
        self.add_item(self.prev_btn)
        self.add_item(self.next_btn)
        self.add_item(self.dismiss_btn)

        start = self.page * self.per_page
        end = start + self.per_page
        current_items = self.matches[start:end]

        select_options = []
        for i, path in enumerate(current_items):
            desc = "Unknown Album"
            try:
                files = [f for f in os.listdir(path) if f.lower().endswith(('.mp3', '.flac', '.m4a'))]
                if files:
                    desc = get_album_from_path(os.path.join(path, files[0]))
            except:
                pass

            select_options.append(
                discord.SelectOption(
                    label=os.path.basename(path)[:90], 
                    description=str(desc)[:100],
                    value=str(i)
                )
            )
        
        select = discord.ui.Select(placeholder="Select a leak...", options=select_options)

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                return await interaction.response.send_message("This isn't your search.", ephemeral=True)
            idx = int(select.values[0])
            folder_path = current_items[idx]
            await interaction.response.defer()
            await self.cog.send_leak(interaction, folder_path, edit_message=True)
        
        select.callback = callback
        self.add_item(select)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.page -= 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.danger)
    async def dismiss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        await interaction.message.delete()


class DownloadView(discord.ui.View):
    def __init__(self, cog, mp3_path, file_name, cache_key, user):
        super().__init__(timeout=None)
        self.cog = cog
        self.mp3_path = mp3_path
        self.file_name = file_name
        self.cache_key = cache_key
        self.user = user

    @discord.ui.button(label="Download", style=discord.ButtonStyle.success)
    async def download_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("<a:GTALoading:1348124710394662995> Preparing your file...", ephemeral=True)

        cached_id = self.cog.cache.get(self.cache_key)
        archive_channel = self.cog.bot.get_channel(LEAK_ARCHIVE_CHANNEL_ID)
        fresh_url = None

        if cached_id and archive_channel:
            try:
                msg = await archive_channel.fetch_message(cached_id)
                if msg.attachments: fresh_url = msg.attachments[0].url
            except: pass

        if not fresh_url:
            if not archive_channel:
                await interaction.followup.send("Archive channel not found.", ephemeral=True)
                return
            try:
                f = discord.File(self.mp3_path, filename=self.file_name)
                m = await archive_channel.send(content=f"Leak Archive: {self.cache_key}", file=f)
                self.cog.cache[self.cache_key] = m.id
                await self.cog._save_cache()
                fresh_url = m.attachments[0].url
            except Exception as e:
                await interaction.followup.send(f"Upload failed: {e}", ephemeral=True)
                return

        await interaction.followup.send(
            content=f"Click the link below for **{os.path.basename(self.mp3_path)}**:\n{fresh_url}",
            ephemeral=True
        )
        
        await self.cog.bot.loop.run_in_executor(
            None, 
            update_stats_sync, 
            self.mp3_path, 
            str(interaction.user.id),
            self.cache_key
        )

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user.id or interaction.user.guild_permissions.administrator:
            await interaction.message.delete()
        else:
            await interaction.response.send_message("You cannot dismiss this message.", ephemeral=True)



class Leak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}      
        self.leak_map = {}   
        self.is_indexing = True
        
        self.bot.loop.create_task(self._load_cache())
        self.bot.loop.create_task(self.build_leak_map())

    async def _load_cache(self):
        if os.path.exists(LEAK_CACHE_FILE):
            try:
                with open(LEAK_CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    async def _save_cache(self):
        def write():
            with open(LEAK_CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=4)
        await self.bot.loop.run_in_executor(None, write)

    async def build_leak_map(self):
        self.is_indexing = True
        print(f"[Leak Cog] Indexing {LEAKS_PATH}...")
        
        def scan_disk():
            cache = {}
            if os.path.exists(LEAKS_PATH):
                for root, dirs, files in os.walk(LEAKS_PATH):
                    for folder in dirs:
                        cache[folder.lower()] = os.path.join(root, folder)
            return cache
        
        self.leak_map = await self.bot.loop.run_in_executor(None, scan_disk)
        self.is_indexing = False
        print(f"[Leak Cog] Index complete. Count: {len(self.leak_map)}")

    async def send_message(self, ctx_or_int, *args, edit=False, **kwargs):

        if edit and "file" in kwargs:
            kwargs["attachments"] = [kwargs.pop("file")]

        if isinstance(ctx_or_int, discord.Interaction):
            if edit and ctx_or_int.message:
                return await ctx_or_int.message.edit(*args, **kwargs)
            elif ctx_or_int.response.is_done():
                return await ctx_or_int.followup.send(*args, **kwargs)
            else:
                return await ctx_or_int.response.send_message(*args, **kwargs)
        else:
            return await ctx_or_int.reply(*args, mention_author=False, **kwargs)

    @commands.hybrid_command(name="leak", description="Search for Juice WRLD leaks by name.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(query="The song name to search for.")
    async def leak_command(self, ctx: commands.Context, *, query: str = None):
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx. interaction.response.defer()
            
        if self.is_indexing:
            await self.send_message(ctx, content="The bot is currently indexing files. Please wait.", ephemeral=True)
            return

        if not self.leak_map:
            await self.build_leak_map()
            if not self.leak_map:
                await self.send_message(ctx, content="Error: No leaks found in database.", ephemeral=True)
                return

        if not query:
            embed = discord.Embed(
                title="Missing Song Name",
                description="Please provide a song name.\nExample: `/leak biscotti`",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed)
            return

        def normalize(text):
            text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            return re.sub(rf"[{re.escape(string.punctuation)}]", "", text.lower())

        normalized_query = normalize(query)
        matching_folders = []

        for folder_name_lower, full_path in self.leak_map.items():
            if normalized_query in normalize(folder_name_lower):
                matching_folders.append(full_path)
        
        if not matching_folders:
            embed = discord.Embed(
                title="No Leaks Found",
                description=f"No leaks matching '{query}' found.",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed)
            return

        matching_folders.sort(key=lambda p: os.path.basename(p))

        if len(matching_folders) == 1:
            await self.send_leak(ctx, matching_folders[0])
            return

        if len(matching_folders) > 25:
            view = SearchPaginationView(matching_folders, self, ctx.author)
            embed = discord.Embed(
                description=f"**{len(matching_folders)} Leaks Found**\nSelect one from the dropdown below.",
                color=discord.Color.blurple()
            )
            await self.send_message(ctx, embed=embed, view=view)
        else:
            options = []
            for i, f in enumerate(matching_folders):
                desc = "Unknown Album"
                try:
                    files = [fl for fl in os.listdir(f) if fl.lower().endswith(('.mp3', '.flac', '.m4a'))]
                    if files:
                        desc = get_album_from_path(os.path.join(f, files[0]))
                except:
                    pass

                options.append(discord.SelectOption(
                    label=os.path.basename(f)[:90], 
                    description=str(desc)[:100],
                    value=str(i)
                ))
            
            class SimpleDropdown(discord.ui.View):
                def __init__(self, cog, folders, options):
                    super().__init__(timeout=30)
                    self.cog = cog
                    self.folders = folders
                    
                    select = discord.ui.Select(placeholder="Select a leak", options=options)
                    
                    async def callback(interaction: discord.Interaction):
                        idx = int(select.values[0])
                        await self.cog.send_leak(interaction, self.folders[idx])
                    
                    select.callback = callback
                    self.add_item(select)

            embed = discord.Embed(
                description=f"**{len(matching_folders)} Leaks Found**\nSelect one from the dropdown below.",
                color=discord.Color.blurple()
            )
            await self.send_message(ctx, embed=embed, view=SimpleDropdown(self, matching_folders, options))

    async def send_leak(self, ctx_or_int, folder_path, edit_message=False):
        if isinstance(ctx_or_int, discord.Interaction) and not ctx_or_int.response.is_done():
            await ctx_or_int.response.defer()

        if not os.path.exists(folder_path):
            await self.send_message(ctx_or_int, content="Folder does not exist.", edit=edit_message)
            return

        try:
            audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith((".mp3", ".m4a"))]
        except Exception:
            await self.send_message(ctx_or_int, content="Failed to read folder.", edit=edit_message)
            return

        if not audio_files:
            await self.send_message(ctx_or_int, content="No MP3 or M4A files in this folder.")
            return

        if len(audio_files) > 1:
            options = []
            files_subset = audio_files[:25]
            
            for i, f in enumerate(files_subset):
                try:
                    full_p = os.path.join(folder_path, f)
                    desc = get_album_from_path(full_p)
                except:
                    desc = "Unknown"
                
                options.append(discord.SelectOption(
                    label=f[:90], 
                    description=str(desc)[:100], 
                    value=str(i)
                ))
            
            class VersionSelect(discord.ui.View):
                def __init__(self, cog, f_path, files, options):
                    super().__init__(timeout=30)
                    self.cog = cog
                    self.f_path = f_path
                    self.files = files
                    
                    select = discord.ui.Select(placeholder="Choose a version", options=options)
                    
                    async def select_callback(interaction: discord.Interaction):
                        idx = int(select.values[0])
                        await self.cog.process_leak(interaction, self.f_path, self.files[idx])
                    
                    select.callback = select_callback
                    self.add_item(select)
                    
            embed = discord.Embed(
                title="Multiple Versions Found",
                description="Select the desired version below.",
                color=discord.Color.dark_gray()
            )
            await self.send_message(ctx_or_int, embed=embed, view=VersionSelect(self, folder_path, files_subset, options))
        else:
            await self.process_leak(ctx_or_int, folder_path, audio_files[0], edit_message=edit_message)

    async def process_leak(self, ctx_or_int, folder_path, file_name, edit_message=False):
        user = ctx_or_int.user if isinstance(ctx_or_int, discord.Interaction) else ctx_or_int.author
        
        mp3_file_path = os.path.join(folder_path, file_name)
        cache_key = f"{os.path.basename(folder_path)}_{file_name}"
        
        folder_name = os.path.basename(folder_path)
        main_title, aliases = parse_folder_name(folder_name)

        db_info = await self.bot.loop.run_in_executor(
            None,
            get_juiceinfo_track,
            main_title,
            aliases,
            file_name,
            folder_name,
        )
        
        metadata = await self.bot.loop.run_in_executor(None, extract_metadata, mp3_file_path)
        
        if not metadata:
            await self.send_message(ctx_or_int, content="Metadata extraction failed.", edit=edit_message)
            return

        embed_color = discord.Color.green()


        if db_info and db_info.get("Era"):
            embed_color = discord.Color(era_colors.get(db_info["Era"], embed_color.value))
        elif metadata.get("album"):
            album_tag = metadata["album"]
            found_color = ERA_COLORS.get(album_tag)
            if not found_color and isinstance(album_tag, str) and album_tag.lower().endswith(" era"):

                base_era = album_tag[:-4].strip()
                found_color = era_colors.get(base_era)
            if found_color:
                embed_color = discord.Color(found_color)

        download_count = await self.bot.loop.run_in_executor(None, get_file_download_count, cache_key)


        embed = discord.Embed(title=main_title, color=embed_color)
        
        if aliases:
            embed.description = f"-# {aliases}"
        
        embed.set_author(name=metadata['artist'])


        if metadata.get("album"):
            embed.add_field(name="Album", value=metadata["album"], inline=True)
        if metadata.get("length"):
            embed.add_field(name="Duration", value=metadata["length"], inline=True)


        if db_info:
            producer = db_info.get("Producer")
            if producer and producer not in ["N/A", "-"]:
                embed.add_field(name="Producer", value=producer, inline=False)

            shared_titles = await self.bot.loop.run_in_executor(
                None,
                get_juiceinfo_shared_instrumental_titles,
                db_info,
                main_title,
            )
            if shared_titles:
                max_titles = 10
                shown = shared_titles[:max_titles]
                extra = len(shared_titles) - len(shown)
                value = "\n".join(shown)
                if extra > 0:
                    value += f"\n… (+{extra} more)"
                embed.add_field(name="Shares same instrumental as", value=value, inline=False)
        
        embed.set_footer(text=f"{metadata['size_str']}  •  {download_count} Downloads")
        
        view = DownloadView(self, mp3_file_path, file_name, cache_key, user)

        try:
            if metadata.get("cover_data"):
                with io.BytesIO(metadata["cover_data"]) as image_binary:
                    cover_file = discord.File(image_binary, filename="cover.jpg")
                    embed.set_thumbnail(url="attachment://cover.jpg")
                    await self.send_message(ctx_or_int, embed=embed, view=view, file=cover_file, edit=edit_message)
            else:
                await self.send_message(ctx_or_int, embed=embed, view=view, edit=edit_message)
        except Exception:
            await self.send_message(ctx_or_int, content="Error displaying leak.", edit=edit_message)


async def setup(bot):
    await bot.add_cog(Leak(bot))