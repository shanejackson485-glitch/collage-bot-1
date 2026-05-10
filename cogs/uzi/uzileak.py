import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import io
import re
import string
import asyncio
import pytz
import unicodedata
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4


UZI_LEAK_PATH = r"D:\JBDB\UziLeaks"
LEAK_CACHE_FILE = "data/Caches/uzi_leak_cache.json"
STATS_FILE = "data/Developer/uzidownload_stats.json"
COOLDOWN_FILE = 'data/Uzi/cooldown_data.json'
UZI_LEAK_ARCHIVE_CHANNEL_ID = 1455089904471117948
EASTERN_TIMEZONE = pytz.timezone('US/Eastern')


ERA_MAPPING = {
    "PRPL": "Purple Thoughtz", "TRU": "The Real Uzi", "LIR": "Luv Is Rage",
    "LIR (SC)": "LUV Is RAGE (SoundCloud Version)", "LUV vs. TW": "Lil Uzi Vert Vs. The World",
    "TPLT": "The Perfect LUV Tape", "1017 vs. TW": "1017 vs. The World", "LIR 1.5": "Luv Is Rage 1.5",
    "LIR2": "LUV Is Rage 2", "LUV vs. TW2": "Lil Uzi Vert Vs. The World 2", "EA": "Eternal Atake",
    "PLUTO": "Pluto x Baby Pluto", "R&W": "RED & WHITE", "P!NK": "Pink Tape", "B16": "Barter 16",
    "EA 2": "Eternal Atake 2", "AW": "All White"
}

ERA_COLORS = {
    "Purple Thoughtz": 0x6474fc, "The Real Uzi": 0xbdbdbd, "Luv Is Rage": 0xce64d6,
    "Lil Uzi Vert Vs. The World": 0xd339e4, "The Perfect LUV Tape": 0x9b0de9,
    "Luv Is Rage 1.5": 0x716959, "LUV Is Rage 2": 0xc4f23c, "Lil Uzi Vert Vs. The World 2": 0x6f2bf9,
    "Eternal Atake": 0xb000e9, "Pluto x Baby Pluto": 0x8e16e6, "RED & WHITE": 0xad4d7c,
    "Pink Tape": 0xf64699, "Barter 16": 0xf41615, "Eternal Atake 2": 0x4591bc
}

ERA_IMAGES = {
    "Purple Thoughtz": "https://i.ibb.co/vxMdPgv5/1-Purple-Thoughtz.jpg",
    "The Real Uzi": "https://i.ibb.co/0R2J128m/2-The-Real-Uzi.jpg",
    "Luv Is Rage": "https://i.ibb.co/mrXCQM0p/3-Luv-Is-Rage.jpg",
    "Lil Uzi Vert Vs. The World": "https://i.ibb.co/VWB3KPxd/4-Lil-Uzi-Vert-Vs-The-World.jpg",
    "The Perfect LUV Tape": "https://i.ibb.co/4RfqhWzP/5-The-Perfect-LUV-Tape.jpg",
    "LUV Is Rage 2": "https://i.ibb.co/Zp7h9cqy/6-Luv-Is-Rage-2.jpg",
    "Eternal Atake": "https://i.ibb.co/PGKRVM2R/8-Eternal-Atake.jpg",
    "Pink Tape": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Barter 16": "https://i.ibb.co/Myc9jYCn/12-Barter-16.jpg"
}



def get_clean_filename(file_path):
    base = os.path.basename(file_path)
    return os.path.splitext(base)[0]

def format_length(seconds):
    if seconds is None: return "0:00"
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

def format_size(size_bytes):
    if not size_bytes: return "Unknown"
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def extract_metadata(file_path):
    if not file_path or not os.path.exists(file_path): return None
    file_size = os.path.getsize(file_path)
    clean_name = get_clean_filename(file_path)
    metadata = {"title": clean_name, "artist": "Lil Uzi Vert", "album": "Unknown Album", "length": "0:00", "size_str": format_size(file_size), "cover_data": None}
    try:
        ext = file_path.lower().split('.')[-1]
        if ext == "mp3":
            audio = MP3(file_path); metadata["length"] = format_length(audio.info.length)
            tags = ID3(file_path)
            if 'TIT2' in tags: metadata["title"] = str(tags['TIT2'].text[0])
            if 'TPE1' in tags: metadata["artist"] = str(tags['TPE1'].text[0])
            if 'TALB' in tags: metadata["album"] = str(tags['TALB'].text[0])
            for key in tags.keys():
                if key.startswith("APIC"): metadata["cover_data"] = tags[key].data; break
        elif ext == "flac":
            audio = FLAC(file_path); metadata["length"] = format_length(audio.info.length)
            metadata["title"] = audio.get("title", [clean_name])[0]
            metadata["artist"] = audio.get("artist", ["Lil Uzi Vert"])[0]
            metadata["album"] = audio.get("album", ["Unknown Album"])[0]
            if audio.pictures: metadata["cover_data"] = audio.pictures[0].data
        elif ext in ["m4a", "mp4"]:
            audio = MP4(file_path); metadata["length"] = format_length(audio.info.length)
            metadata["title"] = audio.get("\xa9nam", [clean_name])[0]
            metadata["artist"] = audio.get("\xa9ART", ["Lil Uzi Vert"])[0]
            metadata["album"] = audio.get("\xa9alb", ["Unknown Album"])[0]
            if "covr" in audio: metadata["cover_data"] = audio["covr"][0]
    except: pass 
    return metadata

def update_stats_sync(f_path, u_id, cache_key):
    try:
        f_size = os.path.getsize(f_path)
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f: stats = json.load(f)
        else: stats = {"total_downloads": 0, "total_size_bytes": 0, "users": {}, "files": {}}
        stats["total_downloads"] += 1; stats["total_size_bytes"] += f_size
        u_id_str = str(u_id)
        if u_id_str not in stats["users"]: stats["users"][u_id_str] = {"downloads": 0, "size_bytes": 0}
        stats["users"][u_id_str]["downloads"] += 1; stats["users"][u_id_str]["size_bytes"] += f_size
        if "files" not in stats: stats["files"] = {}
        stats["files"][cache_key] = stats["files"].get(cache_key, 0) + 1
        with open(STATS_FILE, "w") as f: json.dump(stats, f, indent=4)
    except: pass



class SearchPaginationView(discord.ui.View):
    def __init__(self, matches, cog, user):
        super().__init__(timeout=60)
        self.matches = matches
        self.cog = cog
        self.user = user
        self.page = 0
        self.per_page = 25
        self.total_pages = (len(matches) - 1) // self.per_page + 1


        self.prev_btn = discord.ui.Button(label="Previous", style=discord.ButtonStyle.secondary)
        self.next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary)
        self.dismiss_btn = discord.ui.Button(label="Dismiss", style=discord.ButtonStyle.danger)
        self.select = discord.ui.Select(placeholder="Select a leak...")


        self.prev_btn.callback = self.go_prev
        self.next_btn.callback = self.go_next
        self.dismiss_btn.callback = self.go_dismiss
        self.select.callback = self.select_callback


        self.add_item(self.prev_btn)
        self.add_item(self.next_btn)
        self.add_item(self.dismiss_btn)
        self.add_item(self.select)

        self.refresh()

    def refresh(self):
        """Updates the state of existing components without recreating them."""
        self.prev_btn.disabled = (self.page == 0)
        self.next_btn.disabled = (self.page == self.total_pages - 1)

        start = self.page * self.per_page
        current_items = self.matches[start:start + self.per_page]

        options = []
        for i, path in enumerate(current_items):

            desc = "Unknown Album"
            if path in self.cog.db_info_cache:
                desc = self.cog.db_info_cache[path].get("era", "Unknown")
            
            options.append(
                discord.SelectOption(
                    label=get_clean_filename(path)[:90],
                    description=str(desc)[:100],
                    value=str(start + i)
                )
            )
        
        self.select.options = options
        self.select.placeholder = f"Page {self.page + 1} of {self.total_pages}"

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your search.", ephemeral=True)

        idx = int(self.select.values[0])

        self.select.disabled = True
        await interaction.response.edit_message(view=self)
        
        await self.cog.send_leak(interaction, self.matches[idx])

    async def go_prev(self, interaction: discord.Interaction):
        if interaction.user != self.user: return
        self.page -= 1
        self.refresh()
        await interaction.response.edit_message(view=self)

    async def go_next(self, interaction: discord.Interaction):
        if interaction.user != self.user: return
        self.page += 1
        self.refresh()
        await interaction.response.edit_message(view=self)

    async def go_dismiss(self, interaction: discord.Interaction):
        if interaction.user != self.user: return
        await interaction.message.delete()

class DownloadView(discord.ui.View):
    def __init__(self, cog, mp3_path, cache_key, user):
        super().__init__(timeout=None)
        self.cog, self.mp3_path, self.cache_key, self.user = cog, mp3_path, cache_key, user

    @discord.ui.button(label="Download", style=discord.ButtonStyle.success)
    async def download_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("<a:GTALoading:1348124710394662995> Preparing your file...", ephemeral=True)
        cached_id, archive_channel, fresh_url = self.cog.cache.get(self.cache_key), self.cog.bot.get_channel(UZI_LEAK_ARCHIVE_CHANNEL_ID), None
        if cached_id and archive_channel:
            try:
                msg = await archive_channel.fetch_message(cached_id)
                if msg.attachments: fresh_url = msg.attachments[0].url
            except: pass
        if not fresh_url:
            if not archive_channel: return await interaction.followup.send("Archive error.", ephemeral=True)
            try:
                f = discord.File(self.mp3_path, filename=os.path.basename(self.mp3_path))
                m = await archive_channel.send(content=f"Uzi Archive: `{self.cache_key}`", file=f)
                self.cog.cache[self.cache_key] = m.id; await self.cog._save_cache()
                if m.attachments: fresh_url = m.attachments[0].url
            except Exception as e: return await interaction.followup.send(f"Upload failed: {e}", ephemeral=True)
        if fresh_url:
            await interaction.followup.send(content=f"Click link: {fresh_url}", ephemeral=True)
            await self.cog.bot.loop.run_in_executor(None, update_stats_sync, self.mp3_path, interaction.user.id, self.cache_key)

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user.id or interaction.user.guild_permissions.administrator: await interaction.message.delete()
        else: await interaction.response.send_message("You cannot dismiss this message.", ephemeral=True)



class Uzileak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.leak_map = {}
        self.db_records = [] 
        self.db_info_cache = {} 
        self.is_indexing = True
        self.premium_ids = set()
        self.cooldown_data = self._load_cooldown_data()
        self.bot.loop.create_task(self._initialize())

    def normalize_text(self, text: str) -> str:
        if not text: return ""
        text = text.lower()
        

        replacements = { "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "\xa0": " " }
        for k, v in replacements.items(): 
            text = text.replace(k, v)
        


        text = text.replace("'", "")
        

        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        


        text = re.sub(rf"[{re.escape(string.punctuation)}]", " ", text)
        

        return " ".join(text.split())
    async def _initialize(self):
        await self._reload_whitelists()
        if os.path.exists(LEAK_CACHE_FILE):
            try:
                with open(LEAK_CACHE_FILE, "r") as f: self.cache = json.load(f)
            except: self.cache = {}
        
        await self.bot.loop.run_in_executor(None, self._parse_html_database)
        await self.build_leak_map_fast()

    def _parse_html_database(self):
        """Parses HTML files into memory with defensive error handling."""
        print("[UziLeak] Parsing HTML Database...")
        html_files = [
            os.path.join(os.getcwd(), "UziInfoDB", "unreleaseduzi.html"), 
            os.path.join(os.getcwd(), "UziInfoDB", "releaseduzi.html"), 
            os.path.join(os.getcwd(), "UziInfoDB", "unleakeduzi.html")
        ]
        
        new_records = []
        for file_path in html_files:
            if not os.path.exists(file_path): continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:

                    soup = BeautifulSoup(f.read(), "lxml" if "lxml" in str(BeautifulSoup) else "html.parser")
                
                for row in soup.find_all("tr"):
                    cols = row.find_all("td")

                    if len(cols) < 8: 
                        continue

                    def get_split_text(idx):
                        if idx >= len(cols): return []
                        cell = cols[idx]
                        return [line.strip() for line in cell.get_text(separator="\n").split('\n') if line.strip()]

                    try:
                        era_code = cols[0].get_text(strip=True)
                        names_col2 = get_split_text(2) 
                        names_col3 = get_split_text(3) 
                        

                        if not names_col2:
                            continue

                        producers = cols[4].get_text(strip=True) if len(cols) > 4 else "N/A"
                        engineers = cols[5].get_text(strip=True) if len(cols) > 5 else "N/A"
                        info = cols[6].get_text(strip=True) if len(cols) > 6 else "N/A"
                        db_filename_raw = cols[7].get_text(strip=True) if len(cols) > 7 else "N/A"

                        new_records.append({
                            "main_title": names_col2[0],
                            "all_titles": [self.normalize_text(n) for n in (names_col2 + names_col3)],
                            "db_filename": db_filename_raw if db_filename_raw != "N/A" else None,
                            "era": ERA_MAPPING.get(era_code, era_code),
                            "producers": producers,
                            "engineers": engineers,
                            "info": info
                        })
                    except Exception:

                        continue

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                
        self.db_records = new_records
        print(f"[UziLeak] DB Parse Complete. {len(self.db_records)} tracks loaded.")

    def get_db_track_data(self, query):
        norm_query = self.normalize_text(query)
        query_pattern = rf"\b{re.escape(norm_query)}\b"
        return [
            rec for rec in self.db_records 
            if any(re.search(query_pattern, title) for title in rec['all_titles'])
        ]

    async def build_leak_map_fast(self):
        self.is_indexing = True
        def scan():
            mapping = {}
            if os.path.exists(UZI_LEAK_PATH):
                for root, _, files in os.walk(UZI_LEAK_PATH):
                    for f in files:
                        if f.lower().endswith((".mp3", ".flac", ".m4a")):
                            clean_name = get_clean_filename(f)
                            mapping[self.normalize_text(clean_name)] = os.path.join(root, f)
            return mapping
        self.leak_map = await self.bot.loop.run_in_executor(None, scan)
        self.is_indexing = False
        print(f"[UziLeak] File Index Complete. {len(self.leak_map)} files.")

    async def _reload_whitelists(self):
        new_ids = set()
        for p in ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        new_ids.update([str(i) for i in json.load(f).get("whitelisted_ids", [])])
                except: pass
        self.premium_ids = new_ids

    def _load_cooldown_data(self):
        if os.path.exists(COOLDOWN_FILE):
            try:
                with open(COOLDOWN_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def _save_cooldown_data(self):
        try:
            os.makedirs(os.path.dirname(COOLDOWN_FILE), exist_ok=True)
            with open(COOLDOWN_FILE, 'w') as f: json.dump(self.cooldown_data, f, indent=4)
        except: pass

    async def _save_cache(self):
        def save():
            os.makedirs(os.path.dirname(LEAK_CACHE_FILE), exist_ok=True)
            with open(LEAK_CACHE_FILE, "w") as f: json.dump(self.cache, f, indent=4)
        await self.bot.loop.run_in_executor(None, save)

    def _check_rate_limit(self, user_id):
        if str(user_id) in self.premium_ids: return True
        user_id_str, now = str(user_id), datetime.now(EASTERN_TIMEZONE)
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        data = self.cooldown_data.get(user_id_str, {'uses': 0, 'last_reset': 0})
        if data['last_reset'] < today_midnight.timestamp():
            data['uses'] = 0; data['last_reset'] = today_midnight.timestamp()
        if data['uses'] < 10:
            data['uses'] += 1; self.cooldown_data[user_id_str] = data; self._save_cooldown_data(); return True
        tomorrow_midnight = today_midnight + timedelta(days=1)
        seconds_until_reset = (tomorrow_midnight - now).total_seconds()
        raise commands.CommandOnCooldown(commands.Cooldown(1, 86400), seconds_until_reset, commands.BucketType.user)

    @commands.hybrid_command(name="uzileak", description="Search for any leaked track from Lil Uzi Vert.")
    @app_commands.describe(query="The name of the song to search for")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uzileak(self, ctx: commands.Context, *, query: str = None):
            
        try: self._check_rate_limit(ctx.author.id)
        except commands.CommandOnCooldown as e:
            retry_seconds = int(e.retry_after)
            h = retry_seconds // 3600
            m = (retry_seconds % 3600) // 60
            s = retry_seconds % 60
            limit_embed = discord.Embed(title="⭐ Premium Feature Limit Reached", color=discord.Color.gold(), 
                description=f"Used your 10 free searches today.\n**Resets in:** `{h}h {m}m {s}s`\nUse `@collage premium` for unlimited access.")
            return await ctx.reply(embed=limit_embed, ephemeral=True)

        if self.is_indexing: return await ctx.send("Bot is indexing...", ephemeral=True)
        if not query: return await ctx.send("Missing query.", ephemeral=True)
        if ctx.interaction: await ctx.interaction.response.defer()


        db_records = self.get_db_track_data(query)
        

        search_net = {self.normalize_text(query)}
        for rec in db_records:
            search_net.add(self.normalize_text(rec['main_title']))
            if rec['db_filename']: search_net.add(self.normalize_text(rec['db_filename']))


        matches = []
        for norm_indexed_name, path in self.leak_map.items():
            for target in search_net:
                if target and (target in norm_indexed_name):
                    matches.append(path)
                    break

        if not matches: return await self.send_msg(ctx, embed=discord.Embed(title="❌ No Leaks Found", color=discord.Color.red()))
        matches.sort(key=lambda x: os.path.basename(x))


        for path in matches:
            norm_path = self.normalize_text(get_clean_filename(path))
            best_rec, best_score = None, 0
            for rec in db_records:
                score = 0
                norm_main = self.normalize_text(rec['main_title'])
                if rec['db_filename'] and self.normalize_text(rec['db_filename']) in norm_path: score = 3
                elif norm_main == norm_path: score = 2
                elif norm_main in norm_path: score = 1
                
                if score > best_score:
                    best_score, best_rec = score, rec
                elif score == best_score and best_rec:
                    if len(norm_main) > len(self.normalize_text(best_rec['main_title'])):
                        best_rec = rec
            if best_rec: self.db_info_cache[path] = best_rec

        if len(matches) == 1:
            await self.send_leak(ctx, matches[0])
        else:
            subset = matches[:25]
            tasks = [self.bot.loop.run_in_executor(None, extract_metadata, p) for p in subset]
            metadata_results = await asyncio.gather(*tasks)
            
            options = [
                discord.SelectOption(
                    label=get_clean_filename(path)[:90], 
                    description=metadata_results[i].get("album", "Unknown")[:100], 
                    value=str(i)
                ) for i, path in enumerate(subset)
            ]

            class QuickSelect(discord.ui.View):
                def __init__(self, cog, m): 
                    super().__init__(timeout=60); self.cog = cog; self.m = m
                @discord.ui.select(options=options, placeholder=f"{len(matches)} results found...")
                async def cb(self, it, select):
                    await it.response.defer(); await self.cog.send_leak(it, self.m[int(select.values[0])])
            
            await self.send_msg(ctx, content=f"**{len(matches)} Results Found**", view=QuickSelect(self, subset))

    async def send_leak(self, ctx_or_int, file_path):
        if isinstance(ctx_or_int, discord.Interaction) and not ctx_or_int.response.is_done(): await ctx_or_int.response.defer()
        metadata = await self.bot.loop.run_in_executor(None, extract_metadata, file_path)
        db_info = self.db_info_cache.get(file_path, {})

        title = db_info.get("main_title", metadata['title'])
        era = db_info.get("era", "Unknown Era")
        
        embed = discord.Embed(title=title, color=ERA_COLORS.get(era, 0x2f3136))
        embed.set_author(name=metadata['artist'])
        embed.set_thumbnail(url=ERA_IMAGES.get(era, ""))
        
        embed.add_field(name="Era / Album", value=f"`{db_info.get('era', metadata['album'])}`", inline=True)
        embed.add_field(name="Duration", value=f"`{metadata['length']}`", inline=True)
        
        if db_info.get("producers") and db_info["producers"] not in ["N/A", "-", "Unknown"]:
            embed.add_field(name="Produced by", value=db_info["producers"], inline=False)
        
        if db_info.get("info") and db_info["info"] not in ["-", "N/A"]:
            embed.add_field(name="Additional Info", value=f"*{db_info['info']}*", inline=False)

        cache_key = f"{os.path.basename(file_path)}_{os.path.getsize(file_path)}"
        dl_count = 0
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f: dl_count = json.load(f).get("files", {}).get(cache_key, 0)
            except: pass
            
        embed.set_footer(text=f"{metadata['size_str']}   •  {dl_count} Downloads")
        user = ctx_or_int.user if isinstance(ctx_or_int, discord.Interaction) else ctx_or_int.author
        view = DownloadView(self, file_path, cache_key, user)
        
        if metadata["cover_data"]:
            file = discord.File(io.BytesIO(metadata["cover_data"]), filename="cover.jpg")
            embed.set_thumbnail(url="attachment://cover.jpg")
            await self.send_msg(ctx_or_int, embed=embed, view=view, file=file)
        else: await self.send_msg(ctx_or_int, embed=embed, view=view)

    async def send_msg(self, ctx_or_int, **kwargs):
        if isinstance(ctx_or_int, discord.Interaction): return await ctx_or_int.followup.send(**kwargs)
        if hasattr(ctx_or_int, 'interaction') and ctx_or_int.interaction: return await ctx_or_int.interaction.followup.send(**kwargs)
        return await ctx_or_int.send(**kwargs)

async def setup(bot):
    await bot.add_cog(Uzileak(bot))