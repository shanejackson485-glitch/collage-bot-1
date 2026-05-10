import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import re
import urllib.parse
from datetime import datetime, timedelta


from .helpers import api_client, EASTERN_TIMEZONE





class ProToolsSelectView(discord.ui.View):
    """Dropdown view for selecting a song when multiple results are found."""
    def __init__(self, cog, ctx, results):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        
        options = []

        for i, song in enumerate(results[:25]):
            description_text = f"Type: {song.get('type', 'N/A')}"
            era_raw = song.get('era')
            
            if era_raw:
                era_code = era_raw.get('name') if isinstance(era_raw, dict) else era_raw
                if era_code:
                    clean_code = str(era_code).strip().upper()
                    if clean_code in self.cog.ERA_MAPPING:
                        description_text = f"Era: {self.cog.ERA_MAPPING[clean_code]['name_long']}"
                    else:
                        description_text = f"Era: {clean_code}"

            alt_titles_part = ""
            if song.get('track_titles') and len(song['track_titles']) > 1:
                alt_titles_part = f" [{', '.join(song['track_titles'][1:])}]"

            label_str = f"{i+1}. {song['name']}{alt_titles_part}"

            options.append(
                discord.SelectOption(
                    label=label_str[:100],
                    value=str(song['public_id']),
                    description=description_text
                )
            )

        select = discord.ui.Select(
            placeholder="Select a song to find sessions...",
            options=options 
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return

        try:
            self.cog._check_rate_limit(interaction.user.id)
        except commands.CommandOnCooldown as e:
            await interaction.response.send_message(f"⏳ Premium Limit Reached. Try again later.", ephemeral=True)
            return

        await interaction.response.defer()
        
        selected_id = interaction.data['values'][0]
        
        try: await interaction.message.delete()
        except: pass


        full_song = await self.cog.api.get_song_by_id(selected_id)
        session_paths = await self.cog.resolve_session_path(full_song)
        
        await self.cog.send_protools_embed(self.ctx, full_song, session_paths)
        self.stop()



class ProToolsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = api_client
        self.cooldown_file = 'data/JuiceWRLD/cooldown_data.json'
        self.cooldown_data = self._load_cooldown_data()
        self.ERA_MAPPING = {
            "GB&GR": {"name_long": "Goodbye & Good Riddance", "color": discord.Color.from_rgb(0, 100, 150), "cover_url": r"https://i.ibb.co/Nds1hHVW/goodbyegoodriddance.jpg"},
            "WOD": {"name_long": "WRLD On Drugs", "color": discord.Color.from_rgb(7, 33, 202), "cover_url": r"https://i.ibb.co/gbzZsCPN/wod.jpg"},
            "DRFL": {"name_long": "Death Race for Love", "color": discord.Color.from_rgb(184, 61, 17), "cover_url": r"https://i.ibb.co/20cC9BTC/deathraceforlove.png"},
            "OUT": {"name_long": "Outsiders", "color": discord.Color.from_rgb(22, 18, 19), "cover_url": r"https://i.ibb.co/93hFgB16/jw3-cover.jpg"},
            "AFFLICTIONS": {"name_long": "Affliction", "color": discord.Color.from_rgb(0, 0, 0), "cover_url": r"https://i.ibb.co/Dg78D9SL/affliction2.jpg"},
            "BDM": {"name_long": "BINGEDRINKINGMUSIC", "color": discord.Color.from_rgb(0, 0, 0), "cover_url": r"https://i.ibb.co/HLXqCLg9/BINGEDRINKINGMUSIC.jpg"},
            "ND": {"name_long": "NOTHINGS DIFFERENT </3", "color": discord.Color.from_rgb(204, 84, 55), "cover_url": r"https://i.ibb.co/YBFQJX8s/nothingsdifferent.jpg"},
            "JW 999": {"name_long": "Juice WRLD 999", "color": discord.Color.from_rgb(27, 7, 6), "cover_url": r"https://i.ibb.co/spskD3Qj/999.jpg"},
            "HIH 999": {"name_long": "HEARTBROKEN IN HOLLYWOOD 999", "color": discord.Color.from_rgb(71, 20, 34), "cover_url": r"https://i.ibb.co/wNyGCZB7/heartbrokeninhollywood2.jpg"},
            "POST": {"name_long": "Posthumous", "color": discord.Color.from_rgb(19, 19, 19), "cover_url": r"https://i.ibb.co/QF7dCqWY/posthumous.webp"},
            "JUTE": {"name_long": "JUICED UP THE EP", "color": discord.Color.from_rgb(87, 141, 207), "cover_url": r"https://i.ibb.co/20bWyHmg/juiceduptheep.jpg"}
        }


    def _load_cooldown_data(self):
        if os.path.exists(self.cooldown_file):
            try:
                with open(self.cooldown_file, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def _save_cooldown_data(self):
        try:
            os.makedirs(os.path.dirname(self.cooldown_file), exist_ok=True)
            with open(self.cooldown_file, 'w') as f: json.dump(self.cooldown_data, f, indent=4)
        except: pass

    def is_premium_user(self, user_id):
        for file in ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]:
            try:
                if os.path.exists(file):
                    with open(file, "r", encoding="utf-8") as f:
                        if str(user_id) in json.load(f).get("whitelisted_ids", []): return True
            except: continue
        return False

    def _check_rate_limit(self, user_id):
        if self.is_premium_user(user_id): return True
        user_id_str = str(user_id)
        if user_id_str not in self.cooldown_data:
            self.cooldown_data[user_id_str] = {'uses': 0, 'last_reset': 0}
        user_data = self.cooldown_data[user_id_str]
        now_est = datetime.now(EASTERN_TIMEZONE)
        today_midnight = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if user_data['last_reset'] < today_midnight.timestamp():
            user_data['uses'] = 0
            user_data['last_reset'] = today_midnight.timestamp()
        if user_data['uses'] < 10:
            user_data['uses'] += 1
            self._save_cooldown_data()
            return True
        else:
            next_reset = today_midnight + timedelta(days=1)
            self._save_cooldown_data()
            raise commands.CommandOnCooldown(commands.Cooldown(10, 86400), (next_reset - now_est).total_seconds(), commands.BucketType.user)


    def get_stream_url(self, path):
        if not path: return None
        return f"https://juicewrldapi.com/juicewrld/files/download/?path={urllib.parse.quote(path)}"

    def format_record_date(self, text):
        if not text: return None
        clean = text.replace('\r\n', ' ').replace('\n', ' ').strip()
        date = re.sub(r'^Recorded\s*', '', clean, flags=re.IGNORECASE).strip('.').strip()
        return f"Recorded: **{date}**" if date else None

    def _clean_multiline_text(self, text, remove_prefix=None):
        if not text: return None
        clean = text.replace('\r\n', ' ').replace('\n', ' ').strip()
        if remove_prefix:
            clean = re.sub(rf'^{re.escape(remove_prefix)}\s*', '', clean, flags=re.IGNORECASE).strip('.').strip()
        return clean

    def _format_size(self, size_in_bytes):
        if not size_in_bytes: return "Unknown Size"
        try:
            size = float(size_in_bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0: return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} PB"
        except ValueError: return "Unknown Size"

    def _get_session_type(self, filename):
        name = filename.lower()
        if any(x in name for x in ['logic', '.logic', 'lx4']): return "Logic Pro Session"
        elif any(x in name for x in ['protools', 'pro tools', '.ptx', '.ptf']): return "Pro Tools Session"
        elif any(x in name for x in ['fl studio', '.flp']): return "FL Studio Project"
        elif any(x in name for x in ['ableton', '.als']): return "Ableton Live Set"
        elif any(x in name for x in ['stems', 'multitrack', 'multi-track', 'trackout']): return "Multi-Track / Stems"
        else: return "Studio Session"


    async def _smart_search(self, query):
        data = await self.api.search_songs(query)
        results = data.get('results', []) if isinstance(data, dict) else (data if data else [])
        if results: return results
        

        replacements = { "cant": "can't", "dont": "don't", "wont": "won't", "im": "i'm", "em": "'em", "aint": "ain't" }
        words = query.lower().split()
        fixed_words = [replacements.get(w, w) for w in words]
        fixed_query = " ".join(fixed_words)
        if fixed_query != query.lower():
            data = await self.api.search_songs(fixed_query)
            results = data.get('results', []) if isinstance(data, dict) else (data if data else [])
            if results: return results
            

        clean_query = re.sub(r"[^a-zA-Z0-9\s]", "", query)
        long_words = sorted([w for w in clean_query.split() if len(w) > 2], key=len, reverse=True)
        norm_query = re.sub(r"[^a-z0-9]", "", query.lower())

        for word in long_words:
            try:
                data = await self.api.search_songs(word)
                candidates = data.get('results', []) if isinstance(data, dict) else (data if data else [])
                filtered = []
                for s in candidates:
                    norm_name = re.sub(r"[^a-z0-9]", "", s.get('name', '').lower())
                    titles = s.get('track_titles', []) or []
                    norm_titles = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in titles]
                    if (norm_query in norm_name or norm_name in norm_query or any(norm_query in t for t in norm_titles)):
                        filtered.append(s)
                if filtered: return filtered
            except: continue
        return []


    async def resolve_session_path(self, song):
        if not song: return []
        STRICT_SESSION_PREFIX = "Studio Sessions"


        def clean_for_match(text):
            if not text: return ""
            return re.sub(r"[^a-zA-Z0-9]", "", str(text)).lower()

        search_candidates = []
        seen = set()

        def add_candidate(val):
            if val:
                s = str(val).strip()
                if s and s.lower() not in seen:
                    search_candidates.append(s)
                    seen.add(s.lower())



        if session_raw := song.get("session_titles"):
            if isinstance(session_raw, str) and session_raw != "N/A":
                for line in session_raw.split('\n'):
                    clean = re.sub(r'^(Session|Project)\s*Title(\(s\))?(\s*\(\d+\))?\s*:\s*', '', line, flags=re.IGNORECASE)
                    clean = re.sub(r'\.(ptx|logic|flp|als|zip|rar|7z)$', '', clean, flags=re.IGNORECASE).strip()
                    add_candidate(clean)


        if file_names := song.get("file_names"):
            raw_files = file_names if isinstance(file_names, list) else str(file_names).split('\n')
            for line in raw_files:
                clean_line = re.sub(r'^File\s*Name(\(s\))?\s*:\s*', '', line, flags=re.IGNORECASE).strip()
                add_candidate(clean_line)
                if match := re.search(r'\((.*?)\)', clean_line):
                    add_candidate(match.group(1))
                no_artist = re.sub(r'^juice\s*wrld\s*-\s*', '', clean_line, flags=re.IGNORECASE)
                simple_name = re.split(r'\s+(v\d|[\(\[])', no_artist)[0].strip()
                if len(simple_name) > 3:
                    add_candidate(simple_name)


        if track_titles := song.get("track_titles"):
            if isinstance(track_titles, list):
                for title in track_titles: add_candidate(title)


        add_candidate(song.get("name"))


        for candidate in search_candidates:

            base_queries = [candidate]
            


            clean_ver = re.sub(r"['\"’]", "", candidate)
            clean_ver = re.sub(r"[^a-zA-Z0-9\.\-\s]", " ", clean_ver).strip()
            clean_ver = re.sub(r"\s+", " ", clean_ver)
            if clean_ver != candidate: base_queries.append(clean_ver)



            final_queries = []
            extensions = [" zip", " rar", " 7z", " session", " protools"]
            
            for base in base_queries:

                for ext in extensions:
                    final_queries.append(f"{base}{ext}")

                final_queries.append(base)

            match_clean = clean_for_match(candidate)

            for q in final_queries:
                if len(q) < 2: continue

                data = None
                try:
                    data = await self.api.get("files/browse", params={'search': q})
                except: pass

                if not data or "items" not in data: continue

                matches = []
                for item in data["items"]:
                    if item.get("type") != "file": continue
                    path = item.get("path", "")
                    

                    if STRICT_SESSION_PREFIX not in path.lstrip('/'): continue
                    

                    if not re.search(r'\.(zip|rar|7z)$', path, re.IGNORECASE): continue

                    filename = path.rsplit("/", 1)[-1] 
                    filename_clean = clean_for_match(filename)
                    


                    if match_clean in filename_clean:
                        matches.append({
                            "path": path,
                            "name": filename,
                            "size": item.get("size", 0),
                            "type": self._get_session_type(filename)
                        })
                
                if matches: return matches

        return []

    async def send_protools_embed(self, ctx, full_song, session_files):
        track_titles = full_song.get('track_titles', [])
        main_title = track_titles[0] if track_titles else full_song.get('name', 'Unknown Title')
        
        era_display = None
        embed_color = discord.Color.from_rgb(44, 47, 51)
        era_cover_url = None
        
        era_raw = full_song.get('era')
        if era_raw:
            era_code = era_raw.get('name') if isinstance(era_raw, dict) else era_raw
            if era_code:
                clean_code = str(era_code).strip().upper()
                if clean_code in self.ERA_MAPPING:
                    d = self.ERA_MAPPING[clean_code]
                    era_display = d['name_long']
                    embed_color = d['color']
                    era_cover_url = d['cover_url']
                else:
                    era_display = clean_code

        if session_files:
            main_type_label = session_files[0]['type'] 
            if len(set(f['type'] for f in session_files)) > 1:
                main_type_label = "Studio Sessions"
        else:
            main_type_label = "Studio Sessions"

        embed = discord.Embed(
            title=f"{main_title} ({main_type_label})",
            description="Use the buttons below to download the session files." if session_files else "❌ No session files found matching this song.",
            color=embed_color if session_files else discord.Color.red()
        )

        if era_display: embed.add_field(name="Era", value=era_display, inline=True)
        if full_song.get('length'): embed.add_field(name="Length", value=full_song['length'], inline=True)
        
        if session_files and len(session_files) == 1:
            size_str = self._format_size(session_files[0]['size'])
            embed.add_field(name="File Size", value=size_str, inline=True)
        
        if full_song.get('producers'): embed.add_field(name="Producers", value=full_song['producers'], inline=True)

        if full_song.get('engineers'):
            embed.add_field(name="Engineers", value=full_song['engineers'], inline=True)

        leak_raw = full_song.get('date_leaked')
        if leak_raw:
            clean_leak = self._clean_multiline_text(leak_raw, remove_prefix="Surfaced")
            embed.add_field(name="Date Leaked", value=clean_leak, inline=True)

        if full_song.get('session_titles'):
            titles = full_song['session_titles']
            if isinstance(titles, list): titles = ", ".join(titles)
            embed.add_field(name="Session Titles", value=str(titles), inline=False)

        if full_song.get('session_tracking'):
            tracking_info = full_song['session_tracking'].strip()
            embed.add_field(name="Session Tracking", value=tracking_info, inline=False)

        rec_date = self.format_record_date(full_song.get('record_dates'))
        if rec_date: embed.add_field(name="Record Date", value=rec_date, inline=False)

        view = discord.ui.View()
        found_files = False

        if session_files:
            for file_data in session_files:
                url = self.get_stream_url(file_data['path'])
                fname = file_data['name']
                fsize = self._format_size(file_data['size'])
                
                max_len = 75 - len(fsize)
                display_name = fname[:max_len] + "..." if len(fname) > max_len else fname
                
                button_label = f"📥 {display_name} ({fsize})"
                
                view.add_item(discord.ui.Button(label=button_label, url=url, style=discord.ButtonStyle.link))
                found_files = True
            
            if len(session_files) > 1:
                types_list = "\n".join([f"- {f['name']}: **{f['type']}**" for f in session_files])
                embed.add_field(name="Files Found", value=types_list[:1000], inline=False)
            elif len(session_files) == 1:
                 embed.add_field(name="Session Type", value=session_files[0]['type'], inline=False)

        if era_cover_url: embed.set_thumbnail(url=era_cover_url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed, view=view if found_files else None)

    @commands.hybrid_command(name="protools", description="Search for and download leaked Studio Sessions (Premium).")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def juiceprotools(self, ctx, *, query: str):
        try:
            self._check_rate_limit(ctx.author.id) 
        except commands.CommandOnCooldown as e:
            time_left = str(timedelta(seconds=int(e.retry_after)))
            embed = discord.Embed(
                title="⭐ Premium Feature Limit Reached",
                description=f"You have used your 10 free requests today.\nResets in: `{time_left}`.\nUse `@collage premium` to unlock unlimited access.",
                color=discord.Color.gold()
            )
            await ctx.reply(embed=embed, ephemeral=True)
            return

        await ctx.defer()
        
        song_list = await self._smart_search(query)
        if not song_list:
            await ctx.send(f"❌ No songs found for '{query}'.")
            return

        recording_sessions = [s for s in song_list if s.get('category') == 'recording_session']
        if not recording_sessions:
            await ctx.send(f"❌ No recording sessions found for '{query}' (Found {len(song_list)} other results).")
            return

        if len(recording_sessions) > 1:
            view = ProToolsSelectView(self, ctx, recording_sessions)
            await ctx.send(f"Found {len(recording_sessions)} recording sessions. Please select one:", view=view)
        else:
            full_song = recording_sessions[0]
            sessions = await self.resolve_session_path(full_song)
            await self.send_protools_embed(ctx, full_song, sessions)

async def setup(bot):
    await bot.add_cog(ProToolsCog(bot))