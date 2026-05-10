import discord
from discord.ext import commands
from discord import app_commands
import json
import io


from .helpers import api_client


EMBED_COLOR = discord.Color.from_rgb(44, 47, 51)





def create_song_embed(data):
    if not data:
        return discord.Embed(title="Error", description="No data returned.", color=discord.Color.red())

    title = data.get('name', 'Unknown Title')
    category = str(data.get('category', 'N/A')).replace('_', ' ').title()
    

    era_obj = data.get('era')
    era_name = "Unknown"
    if isinstance(era_obj, dict):
        era_name = era_obj.get('name', 'Unknown')
    elif isinstance(era_obj, str):
        era_name = era_obj

    embed = discord.Embed(title=title, color=EMBED_COLOR)
    embed.add_field(name="Category", value=category, inline=True)
    embed.add_field(name="Era", value=era_name, inline=True)

    if artists := data.get('credited_artists'):
        if isinstance(artists, list): artists = ", ".join(artists)
        embed.add_field(name="Artists", value=str(artists), inline=False)

    date = data.get('date_leaked') or data.get('release_date') or data.get('preview_date')
    if date:
        clean_date = str(date).replace('\n', ' ').strip()
        embed.add_field(name="Date", value=clean_date, inline=True)

    pub_id = data.get('public_id') or data.get('id')
    embed.set_footer(text=f"ID: {pub_id}")

    if img := data.get('image_url'):
        clean_img = img.lstrip('/')
        embed.set_thumbnail(url=f"https://juicewrldapi.com/{clean_img}")

    return embed





class FileBrowserView(discord.ui.View):
    def __init__(self, current_path, items):
        super().__init__(timeout=180)
        self.current_path = current_path
        self.items = items
        
        self.add_item(FileSelect(items, current_path))
        

        self.add_home_button()
        if current_path:
            btn = discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, row=1)
            btn.callback = self.go_back
            self.add_item(btn)

    def add_home_button(self):
        btn = discord.ui.Button(label="🏠 Home", style=discord.ButtonStyle.secondary, row=1)
        btn.callback = self.go_home
        self.add_item(btn)

    async def go_home(self, interaction: discord.Interaction):
        await self.refresh_view(interaction, "")

    async def go_back(self, interaction: discord.Interaction):
        if "/" not in self.current_path:
            parent = ""
        else:
            parent = "/".join(self.current_path.split("/")[:-1])
        await self.refresh_view(interaction, parent)

    async def refresh_view(self, interaction, path):
        await interaction.response.defer()
        params = {'path': path} if path else {}
        data = await api_client.browse_files(params=params)
        
        if not data or 'items' not in data:
            return await interaction.followup.send("❌ Failed to load folder.", ephemeral=True)
            
        embed = discord.Embed(title="🗂️ File Browser", description=f"Path: `/{path}`", color=EMBED_COLOR)
        

        items = sorted(data['items'], key=lambda x: (x['type'] != 'directory', x['name']))
        
        content_lines = []
        for item in items[:15]:
            emoji = "📁" if item['type'] == 'directory' else "🎵"
            content_lines.append(f"{emoji} **{item['name']}**")
        
        if len(items) > 15: content_lines.append(f"...and {len(items)-15} more.")
        
        embed.add_field(name="Contents", value="\n".join(content_lines) or "*(Empty Folder)*")
        
        view = FileBrowserView(path, items)
        await interaction.edit_original_response(embed=embed, view=view)

class FileSelect(discord.ui.Select):
    def __init__(self, items, parent_path):
        options = []
        for item in items[:25]:
            emoji = "📁" if item['type'] == 'directory' else "🎵"
            label = item['name'][:99]
            val = item['path'] 
            
            desc = "Folder"
            if item['type'] != 'directory':
                size_raw = item.get('size', 0)
                try:
                    mb = int(size_raw) / (1024 * 1024)
                    desc = f"{mb:.2f} MB"
                except: desc = "File"

            options.append(discord.SelectOption(label=label, value=val, emoji=emoji, description=desc))

        if not options:
            options.append(discord.SelectOption(label="Empty", value="none", description="No items"))

        super().__init__(placeholder="📂 Open folder or download file...", min_values=1, max_values=1, options=options, disabled=len(options)==0)
        self.items = items

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "none": return await interaction.response.send_message("Empty folder.", ephemeral=True)

        selected_item = next((i for i in self.items if i['path'] == val), None)
        if not selected_item: return await interaction.response.send_message("Item not found.", ephemeral=True)

        if selected_item['type'] == 'directory':
            await self.view.refresh_view(interaction, val)
        else:
            url = api_client.get_download_url(val)
            await interaction.response.send_message(
                f"✅ **Selected File:** `{selected_item['name']}`\n🔗 [Click to Download]({url})", 
                ephemeral=True
            )





class SongActionView(discord.ui.View):
    def __init__(self, song_data):
        super().__init__(timeout=None)
        self.song_data = song_data
        

        self.file_paths = []
        raw = song_data.get('file_names')
        
        if isinstance(raw, list):
            self.file_paths = [str(x) for x in raw]
        elif isinstance(raw, str) and raw not in ["N/A", ""]:
            self.file_paths = [raw]

        if not self.file_paths:
            self.get_audio.disabled = True
            self.get_audio.label = "No Audio Available"
            self.get_audio.style = discord.ButtonStyle.gray

    @discord.ui.button(label="Download / Stream", style=discord.ButtonStyle.success, emoji="🔊")
    async def get_audio(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = "**Audio Links:**\n"
        count = 0
        view = discord.ui.View()
        
        for p in self.file_paths[:5]:
            url = api_client.get_download_url(p)
            fname = p.rsplit('/', 1)[-1]
            view.add_item(discord.ui.Button(label=f"📥 {fname[:25]}", url=url, style=discord.ButtonStyle.link))
            count += 1
            
        if count == 0:
            await interaction.response.send_message("❌ Error generating links.", ephemeral=True)
        else:
            await interaction.response.send_message("Click below to download:", view=view, ephemeral=True)

    @discord.ui.button(label="Raw JSON", style=discord.ButtonStyle.secondary, emoji="📄")
    async def get_json(self, interaction: discord.Interaction, button: discord.ui.Button):
        data_str = json.dumps(self.song_data, indent=4)
        if len(data_str) > 1900:
            file = discord.File(io.StringIO(data_str), filename="song_data.json")
            await interaction.response.send_message(file=file, ephemeral=True)
        else:
            await interaction.response.send_message(f"```json\n{data_str}\n```", ephemeral=True)

class SearchResultView(discord.ui.View):
    def __init__(self, songs):
        super().__init__(timeout=60)
        self.add_item(SongSelect(songs))

class SongSelect(discord.ui.Select):
    def __init__(self, songs):
        options = []
        for s in songs[:25]:
            lbl = s.get('name', 'Unknown')[:99]
            cat = str(s.get('category', 'N/A')).replace('_', ' ').title()
            pid = str(s.get('public_id') or s.get('id'))
            options.append(discord.SelectOption(label=lbl, description=cat, value=pid))
        super().__init__(placeholder="Select a result...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        song = await api_client.get_song_by_id(self.values[0])
        if song:
            embed = create_song_embed(song)
            view = SongActionView(song)
            await interaction.edit_original_response(embed=embed, view=view)





class JuiceCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="browse", description="File Browser (DEBUG TOOL)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def browse(self, ctx):
        await ctx.defer()

        data = await api_client.browse_files()
        
        if not data or 'items' not in data:
            await ctx.send("❌ Could not connect to File Server.")
            return

        items = sorted(data['items'], key=lambda x: (x['type'] != 'directory', x['name']))
        
        embed = discord.Embed(title="🗂️ File Browser", description="Path: `/` (Root)", color=EMBED_COLOR)
        
        content_lines = []
        for item in items[:15]:
            emoji = "📁" if item['type'] == 'directory' else "🎵"
            content_lines.append(f"{emoji} **{item['name']}**")
            
        embed.add_field(name="Contents", value="\n".join(content_lines) or "Empty")
        
        view = FileBrowserView("", items)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="find", aliases=["searchhh"], description="DEBUG TOOL")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def juicesearch(self, ctx, query: str):
        await ctx.defer()
        data = await api_client.search_songs(query)
        
        results = []
        if isinstance(data, dict):
            results = data.get('results', [])
        elif isinstance(data, list):
            results = data

        if not results:
            await ctx.send(f"❌ No songs found for `{query}`.")
            return

        if len(results) == 1:

            song = results[0]

            full_song = await api_client.get_song_by_id(song.get('public_id'))
            embed = create_song_embed(full_song or song)
            view = SongActionView(full_song or song)
            await ctx.send(embed=embed, view=view)
        else:

            embed = discord.Embed(title=f"Found {len(results)} results", description="Select a track below.", color=EMBED_COLOR)
            view = SearchResultView(results)
            await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(JuiceCommands(bot))