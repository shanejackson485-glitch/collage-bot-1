import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import io
import re
import string
import asyncio


from .helpers import (
    extract_metadata, 
    format_size, 
    update_stats_sync, 
    SESSION_ERA_COLORS, 
    SESSIONS_PATH, 
    SESSION_ARCHIVE_CHANNEL_ID, 
    get_album_from_path,
    parse_folder_name,       
    get_file_download_count  
)


SESSION_CACHE_FILE = "data/JuiceWRLD/session_cache.json"



class SessionPaginationView(discord.ui.View):
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
            desc = "Session"
            try:

                files = [f for f in os.listdir(path) if f.lower().endswith(('.mp3', '.flac', '.m4a'))]
                if files:

                    desc = f"{len(files)} files"
            except:
                pass

            select_options.append(
                discord.SelectOption(
                    label=os.path.basename(path)[:90], 
                    description=str(desc)[:100],
                    value=str(i)
                )
            )
        
        select = discord.ui.Select(placeholder="Select a session...", options=select_options)

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                return await interaction.response.send_message("This isn't your search.", ephemeral=True)
            idx = int(select.values[0])
            folder_path = current_items[idx]
            await self.cog.send_session(interaction, folder_path)
        
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


class SessionDownloadView(discord.ui.View):
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
        archive_channel = self.cog.bot.get_channel(SESSION_ARCHIVE_CHANNEL_ID)
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
                m = await archive_channel.send(content=f"Session Archive: {self.cache_key}", file=f)
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




class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}      
        self.session_map = {}   
        self.is_indexing = True
        
        self.bot.loop.create_task(self._load_cache())
        self.bot.loop.create_task(self.build_session_map())

    async def _load_cache(self):
        if os.path.exists(SESSION_CACHE_FILE):
            try:
                with open(SESSION_CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    async def _save_cache(self):
        def write():

            os.makedirs(os.path.dirname(SESSION_CACHE_FILE), exist_ok=True)
            with open(SESSION_CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=4)
        await self.bot.loop.run_in_executor(None, write)

    async def build_session_map(self):
        self.is_indexing = True
        print(f"[Session Cog] Indexing {SESSIONS_PATH}...")
        
        def scan_disk():
            cache = {}
            if os.path.exists(SESSIONS_PATH):
                for root, dirs, files in os.walk(SESSIONS_PATH):
                    for folder in dirs:
                        cache[folder.lower()] = os.path.join(root, folder)
            return cache
        
        self.session_map = await self.bot.loop.run_in_executor(None, scan_disk)
        self.is_indexing = False
        print(f"[Session Cog] Index complete. Count: {len(self.session_map)}")

    async def send_message(self, ctx_or_int, *args, **kwargs):
        if isinstance(ctx_or_int, discord.Interaction):
            if ctx_or_int.response.is_done():
                return await ctx_or_int.followup.send(*args, **kwargs)
            else:
                return await ctx_or_int.response.send_message(*args, **kwargs)
        else:
            return await ctx_or_int.reply(*args, mention_author=False, **kwargs)

    @commands.hybrid_command(name='session', description="Search for a session by song name.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(query="The session/song name to search for.")
    async def session_command(self, ctx: commands.Context, *, query: str = None):
        if self.is_indexing:
            await self.send_message(ctx, content="⚠️ The bot is currently indexing sessions. Please wait.", ephemeral=True)
            return

        if not self.session_map:
            await self.build_session_map()
            if not self.session_map:
                await self.send_message(ctx, content="Error: No sessions found in database.", ephemeral=True)
                return

        if not query:
            embed = discord.Embed(
                title="Missing Session Name",
                description="Please provide a session name.\nExample: `/session rental`",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed)
            return

        def normalize(text):
            text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            return re.sub(rf"[{re.escape(string.punctuation)}]", "", text.lower())

        normalized_query = normalize(query)
        matching_folders = []

        for folder_name_lower, full_path in self.session_map.items():
            if normalized_query in normalize(folder_name_lower):
                matching_folders.append(full_path)
        
        if not matching_folders:
            embed = discord.Embed(
                title="No Sessions Found",
                description=f"No sessions matching '{query}' found.",
                color=discord.Color.red()
            )
            await self.send_message(ctx, embed=embed)
            return

        matching_folders.sort(key=lambda p: os.path.basename(p))

        if len(matching_folders) == 1:
            await self.send_session(ctx, matching_folders[0])
            return

        if len(matching_folders) > 25:
            view = SessionPaginationView(matching_folders, self, ctx.author)
            embed = discord.Embed(
                description=f"**{len(matching_folders)} Sessions Found**\nSelect one from the dropdown below.",
                color=discord.Color.blurple()
            )
            await self.send_message(ctx, embed=embed, view=view)
        else:
            options = []
            for i, f in enumerate(matching_folders):
                desc = "Session"
                try:
                    files = [fl for fl in os.listdir(f) if fl.lower().endswith(('.mp3', '.flac', '.m4a'))]
                    if files:
                        desc = f"{len(files)} files"
                except:
                    pass

                options.append(discord.SelectOption(
                    label=os.path.basename(f)[:90], 
                    description=str(desc)[:100],
                    value=str(i)
                ))
            
            class SimpleSessionDropdown(discord.ui.View):
                def __init__(self, cog, folders):
                    super().__init__(timeout=30)
                    self.cog = cog
                    self.folders = folders

                @discord.ui.select(placeholder="Select a session...", options=options)
                async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                    idx = int(select.values[0])
                    await self.cog.send_session(interaction, self.folders[idx])

            embed = discord.Embed(
                description=f"**{len(matching_folders)} Sessions Found**\nSelect one from the dropdown below.",
                color=discord.Color.blurple()
            )
            await self.send_message(ctx, embed=embed, view=SimpleSessionDropdown(self, matching_folders))

    async def send_session(self, ctx_or_int, folder_path):
        if isinstance(ctx_or_int, discord.Interaction) and not ctx_or_int.response.is_done():
            await ctx_or_int.response.defer()

        if not os.path.exists(folder_path):
            await self.send_message(ctx_or_int, content="Folder does not exist.")
            return

        try:
            mp3_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]
        except Exception:
            await self.send_message(ctx_or_int, content="Failed to read folder.")
            return

        if not mp3_files:
            await self.send_message(ctx_or_int, content="No MP3 files in this session folder.")
            return

        if len(mp3_files) > 1:
            options = []
            files_subset = mp3_files[:25]
            
            for i, f in enumerate(files_subset):

                try:
                    full_p = os.path.join(folder_path, f)
                    size_mb = os.path.getsize(full_p) / (1024 * 1024)
                    desc = f"{size_mb:.2f} MB"
                except:
                    desc = "Unknown Size"
                
                options.append(discord.SelectOption(
                    label=f[:90], 
                    description=desc, 
                    value=str(i)
                ))
            
            class SessionVersionSelect(discord.ui.View):
                def __init__(self, cog, f_path, files):
                    super().__init__(timeout=30)
                    self.cog = cog
                    self.f_path = f_path
                    self.files = files

                @discord.ui.select(placeholder="Choose an MP3 version", options=options)
                async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                    idx = int(select.values[0])
                    await interaction.response.defer()
                    await self.cog.process_session(interaction, self.f_path, self.files[idx])
                    
            embed = discord.Embed(
                title="Multiple Files Found",
                description="Select the desired session file below.",
                color=discord.Color.dark_gray()
            )
            await self.send_message(ctx_or_int, embed=embed, view=SessionVersionSelect(self, folder_path, files_subset))
        else:
            await self.process_session(ctx_or_int, folder_path, mp3_files[0])

    async def process_session(self, ctx_or_int, folder_path, file_name):
        user = ctx_or_int.user if isinstance(ctx_or_int, discord.Interaction) else ctx_or_int.author
        
        mp3_file_path = os.path.join(folder_path, file_name)

        cache_key = f"SESSION_{os.path.basename(folder_path)}_{file_name}"
        
        folder_name = os.path.basename(folder_path)
        main_title, aliases = parse_folder_name(folder_name)
        
        metadata = await self.bot.loop.run_in_executor(None, extract_metadata, mp3_file_path)
        
        if not metadata:

            metadata = {
                'artist': 'Juice WRLD',
                'album': 'Session',
                'length': 'Unknown',
                'size_str': format_size(os.path.getsize(mp3_file_path)) if os.path.exists(mp3_file_path) else "0MB"
            }


        embed_color = discord.Color.green()
        if metadata.get("album"):
            found_color = SESSION_ERA_COLORS.get(metadata["album"])
            if found_color:
                embed_color = discord.Color(found_color)

        download_count = await self.bot.loop.run_in_executor(None, get_file_download_count, cache_key)


        embed = discord.Embed(title=main_title, color=embed_color)
        
        if aliases:
            embed.description = f"-# {aliases}"
        

        artist = metadata.get('artist', 'Unknown Artist')
        album = metadata.get('album', 'Session')
        duration = metadata.get('length', 'Unknown')
        size_str = metadata.get('size_str', 'Unknown Size')
        
        embed.set_author(name=artist)
        embed.add_field(name="Type", value=album, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        
        embed.set_footer(text=f"{size_str}  •  {download_count} Downloads")
        
        view = SessionDownloadView(self, mp3_file_path, file_name, cache_key, user)

        try:

            cover_data = metadata.get("cover_data") or metadata.get("cover")
            if cover_data:
                with io.BytesIO(cover_data) as image_binary:
                    cover_file = discord.File(image_binary, filename="cover.jpg")
                    embed.set_thumbnail(url="attachment://cover.jpg")
                    await self.send_message(ctx_or_int, embed=embed, view=view, file=cover_file)
            else:
                await self.send_message(ctx_or_int, embed=embed, view=view)
        except Exception as e:
            print(f"Session Embed Error: {e}")
            await self.send_message(ctx_or_int, content="Error displaying session.", ephemeral=True)

    @commands.command(name="listallsessions")
    async def list_all_sessions(self, ctx):
        sessions = []
        if os.path.exists(SESSIONS_PATH):
            for root, dirs, files in os.walk(SESSIONS_PATH):
                for folder in dirs:
                    sessions.append(folder)

        if not sessions:
            await ctx.author.send(":x: No sessions found!")
            return

        sessions.sort()
        chunks = [sessions[i:i+70] for i in range(0, len(sessions), 70)]

        for idx, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title=f"🎶 All Sessions (Page {idx}/{len(chunks)})",
                description="\n".join(f"`{s}`" for s in chunk),
                color=discord.Color.blurple()
            )
            await ctx.author.send(embed=embed)

        await ctx.send("<a:checkdone:1353058188877889647> check your DM's.")

async def setup(bot):
    await bot.add_cog(Session(bot))