import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import string
import unicodedata
import asyncio
from bs4 import BeautifulSoup

BASE_DIR = os.getcwd()


UZI_HTML_FILES = [
    os.path.join(BASE_DIR, "UziInfoDB", "unreleaseduzi.html"),
    os.path.join(BASE_DIR, "UziInfoDB", "releaseduzi.html"),
    os.path.join(BASE_DIR, "UziInfoDB", "unleakeduzi.html")
]

SOUP_CACHE = {}
MAX_DROPDOWN_RESULTS = 25


era_mapping = {
    
    "PRPL": "Purple Thoughtz",
    "TRU": "The Real Uzi",
    "LIR": "Luv Is Rage",
    "LIR (SC)": "LUV Is RAGE (SoundCloud Version)",
    "LUV vs. TW": "Lil Uzi Vert Vs. The World",
    "TPLT": "The Perfect LUV Tape",
    "1017 vs. TW": "1017 vs. The World",
    "LIR 1.5": "Luv Is Rage 1.5",
    "LIR2": "LUV Is Rage 2",
    "LIR2": "LUV Is Rage 2 (Deluxe)",
    "LUV vs. TW2": "Lil Uzi Vert Vs. The World 2",
    "EA": "Eternal Atake",
    "PLUTO": "Pluto x Baby Pluto",
    "PLUTO (Deluxe)": "Pluto x Baby Pluto (Deluxe)",
    "R&W": "RED & WHITE",
    "P!NK: Level 1": "Pink Tape: Level 1",
    "P!NK: Level 2": "Pink Tape: Level 2",
    "P!NK: Level 3": "Pink Tape: Level 3",
    "P!NK: Level 4": "Pink Tape: Level 4",
    "P!NK: Boss": "Pink Tape: Boss Battle",
    "P!NK": "Pink Tape",
    "B16": "Barter 16",
    "EA 2": "Eternal Atake 2",
    "AW": "All White",
    "LiveMixtapes": "LiveMixtapes",
    "YouTube": "YouTube",
    "SoundCloud": "SoundCloud",
    "Mainstream": "Mainstream",

}

era_colors = {
    "Purple Thoughtz": 0x6474fc,
    "The Real Uzi": 0xbdbdbd,
    "Luv Is Rage": 0xce64d6,
    "LUV Is RAGE (Soundcloud Version)": 0xce64d6,
    "1017 vs. The World": 0xc42e32,
    "Lil Uzi Vert Vs. The World": 0xd339e4,
    "The Perfect LUV Tape": 0x9b0de9,
    "Luv Is Rage 1.5": 0x716959,
    "LUV Is Rage 2": 0xc4f23c,
    "LUV Is Rage 2 (Deluxe)": 0xc4f23c,
    "Lil Uzi Vert Vs. The World 2": 0x6f2bf9,
    "Eternal Atake": 0xb000e9,
    "Pluto x Baby Pluto": 0x8e16e6,
    "Pluto x Baby Pluto (Deluxe)": 0x8e16e6,
    "RED & WHITE": 0xad4d7c,
    "Pink Tape": 0xf64699,
    "Pink Tape: Level 1": 0xf64699,
    "Pink Tape: Level 2": 0xf64699,
    "Pink Tape: Level 3": 0xf64699,
    "Pink Tape: Level 4": 0xf64699,
    "Pink Tape: Boss Battle": 0xf64699,
    "Barter 16": 0xf41615,
    "Eternal Atake 2": 0x4591bc,
    "All White": 0xbdbeba,
    "Mainstream": 0xab6bcc,
    "SoundCloud": 0x7ea3ce,
    "YouTube": 0x68605a
}

era_images = {
    
    "Purple Thoughtz": "https://i.ibb.co/vxMdPgv5/1-Purple-Thoughtz.jpg",
    "The Real Uzi": "https://i.ibb.co/0R2J128m/2-The-Real-Uzi.jpg",
    "Luv Is Rage": "https://i.ibb.co/mrXCQM0p/3-Luv-Is-Rage.jpg",
    "LUV Is RAGE (SoundCloud Version)": "https://i.ibb.co/mrXCQM0p/3-Luv-Is-Rage.jpg",
    "Lil Uzi Vert Vs. The World": "https://i.ibb.co/VWB3KPxd/4-Lil-Uzi-Vert-Vs-The-World.jpg",
    "The Perfect LUV Tape": "https://i.ibb.co/4RfqhWzP/5-The-Perfect-LUV-Tape.jpg",
    "1017 vs. The World": "https://i.ibb.co/W453yzBW/1017vstheworld.png",
    "Luv Is Rage 1.5": "https://i.ibb.co/B5wC3QxC/luvisrage1-5.jpg",
    "LUV Is Rage 2": "https://i.ibb.co/Zp7h9cqy/6-Luv-Is-Rage-2.jpg",
    "LUV Is Rage 2 (Deluxe)": "https://i.ibb.co/Zp7h9cqy/6-Luv-Is-Rage-2.jpg",
    "Lil Uzi Vert Vs. The World 2": "https://i.ibb.co/xqMJTnPt/7-Lil-Uzi-Vert-Vs-The-World-2.png",
    "Eternal Atake": "https://i.ibb.co/PGKRVM2R/8-Eternal-Atake.jpg",
    "Pluto x Baby Pluto": "https://i.ibb.co/MxxZx84X/9-Pluto-x-Baby-Pluto.jpg",
    "Pluto x Baby Pluto (Deluxe)": "https://i.ibb.co/MxxZx84X/9-Pluto-x-Baby-Pluto.jpg",
    "RED & WHITE": "https://i.ibb.co/b5xm7wQw/https-images-genius-com-9aba096075f365de6eeaa63659a96963-1000x1000x1.jpg",
    "Pink Tape": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Pink Tape: Level 1": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Pink Tape: Level 2": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Pink Tape: Level 3": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Pink Tape: Level 4": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Pink Tape: Boss Battle": "https://i.ibb.co/prhMG81j/11-Pink-Tape.jpg",
    "Barter 16": "https://i.ibb.co/Myc9jYCn/12-Barter-16.jpg",
    "Eternal Atake 2": "https://i.ibb.co/qYZDj1Jw/13-Eternal-Atake-2.jpg",
    "All White": "https://i.ibb.co/RpLkZr9B/14-allwhite.jpg",
    "Mainstream": "https://i.ibb.co/JjY5ZrXV/mainstream.jpg",
    "SoundCloud": "https://i.ibb.co/2YR7K7mq/soundcloud.jpg",
    "YouTube": "https://i.ibb.co/Y4JQp0Tj/youtube.jpg"
}





def load_html_files():
    global SOUP_CACHE
    if not SOUP_CACHE: 
        for html_file in UZI_HTML_FILES:
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read()
                SOUP_CACHE[html_file] = BeautifulSoup(content, "html.parser")
            except Exception as e:
                print(f"[CACHE] Failed to cache {html_file}: {e}")
    return SOUP_CACHE

def normalize_text(text: str) -> str:
    text = text.lower()
    replacements = { "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "\xa0": " " }
    for k, v in replacements.items(): text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(rf"[{re.escape(string.punctuation)}]", "", text)
    text = re.sub(r'\s+', '', text)
    return text.strip()

def clean_text(text, filter_out_words=None, add_spaces=False):
    text = text.replace("\xa0", " ")
    if filter_out_words:
        for word in filter_out_words:
            text = re.sub(re.escape(word), "", text, flags=re.IGNORECASE).strip()
    return text.strip()

def format_title(title: str) -> str:
    if "*" in title:
        parts = title.split("*", 1)
        return f"{parts[0]}*\n{parts[1].strip()}"
    if ")" in title:
        parts = title.split(")", 1)
        return f"{parts[0]})\n{parts[1].strip()}"
    return title

def clean_instrumental_text(text: str) -> str:
    if not text: return ""
    text = text.replace("\xa0", " ").strip()
    if text.lower() in ["n/a", "-", "none", "", "unknown"]: return ""
    return text

def parse_instrumental_field(text: str) -> dict:
    if not text: return {}
    return {"Instrumental Name(s)": text}

def build_embed(info, era_colors):
    era = info.get("Era", "Unknown Era")
    formatted_title = format_title(info.get("Track Title", "Unknown Track"))
    embed = discord.Embed(
        title=formatted_title,
        description="Track Info",
        color=era_colors.get(era, discord.Color.blue().value)
    )

    def add_field(name, value):
        if value and value not in ["N/A", "-", ""]:
            embed.add_field(name=name, value=value, inline=False)

    add_field("Era", era)
    add_field("Produced by:", info.get("Producer"))
    add_field("Engineered by:", info.get("Engineer"))
    add_field("Additional Info", info.get("Additional Info"))
    add_field("File Name(s):", info.get("File Name"))

    inst_fields = info.get("Instrumental Fields", {})
    for k, v in inst_fields.items():
        add_field(k, v)

    add_field("Recording Location(s):", info.get("Recording Location"))
    add_field("Recording Date(s):", info.get("Recording Date"))
    add_field("Preview Date", info.get("Preview Date"))
    add_field("Date(s)", info.get("Surfaced"))
    add_field("Duration", info.get("Duration"))
    add_field("Category", info.get("Category"))
    add_field("Properties", info.get("Properties"))
    
    embed.set_thumbnail(url=era_images.get(era, ""))
    return embed

def build_quick_embed(info):
    era = info.get("Era", "Unknown Era")
    formatted_title = format_title(info.get("Track Title", "Unknown Track"))
    embed = discord.Embed(
        title=f"Quick Info:\n{formatted_title}",
        description=f"**Era:** {era}",
        color=era_colors.get(era, discord.Color.blue().value)
    )
    embed.add_field(name="Engineered by:", value=info.get("Engineer", "N/A"), inline=True)
    embed.add_field(name="Produced by:", value=info.get("Producer", "N/A"), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True) 
    embed.add_field(name="Recording Date(s):", value=info.get("Recording Date", "N/A"), inline=True)
    embed.add_field(name="Location(s):", value=info.get("Recording Location", "N/A"), inline=True)
    embed.add_field(name="Preview Date:", value=info.get("Preview Date", "N/A"), inline=True)
    return embed





def search_tracks_by_field(query_term: str, field_name: str):
    results = []
    query = normalize_text(query_term)
    soups = load_html_files()
    
    field_config = {
        "Track Title": (2, 2, None), 
        "Producer": (4, 4, None),
        "Engineer": (5, 5, None),
        "Recording Location": (9, 9, None), 
        "Recording Date": (10, 10, ["recorded"]),
        "Preview Date": (11, 11, ["first previewed"]), 
    }
    
    u_idx, o_idx, filter_words = field_config[field_name]

    for html_file, soup in soups.items():

        is_unsurfaced = "unleaked" in html_file.lower()
        
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if not cols: continue


            def get_col(idx):
                if idx >= len(cols): return ""
                c = cols[idx]
                for br in c.find_all("br"): br.replace_with("||BR||")
                text = c.get_text(strip=True)
                return text.replace("||BR||", "\n")


            min_cols = 13 if is_unsurfaced else 16
            if len(cols) < min_cols: continue

            match_found = False
            if field_name == "Track Title":
                main_title = clean_text(get_col(2))
                alt_titles = clean_text(get_col(3))
                all_titles = [main_title] + [t.strip() for t in alt_titles.split("|") if t.strip()]
                if any(query in normalize_text(t) for t in all_titles): match_found = True
            else:
                col_idx = u_idx if is_unsurfaced else o_idx
                target_text = clean_text(get_col(col_idx), filter_out_words=filter_words)
                if query in normalize_text(target_text): match_found = True

            if not match_found: continue


            res = {
                "Era": era_mapping.get(clean_text(get_col(0)), clean_text(get_col(0))),
                "Track Title": clean_text(get_col(2)),
                "Producer": clean_text(get_col(4)),
                "Engineer": clean_text(get_col(5)),
                "Additional Info": clean_text(get_col(6)),
                "File Name": clean_text(get_col(7)),
                "Instrumental Fields": parse_instrumental_field(clean_instrumental_text(get_col(8))),
                "Recording Location": clean_text(get_col(9)),
                "Recording Date": clean_text(get_col(10), filter_out_words=["recorded"]),
                "Preview Date": clean_text(get_col(11), filter_out_words=["first previewed"]),
            }

            if is_unsurfaced:
                res.update({"Surfaced": "Not Surfaced", "Duration": "", "Category": clean_text(get_col(12)), "Properties": ""})
            else:
                res.update({
                    "Surfaced": clean_text(get_col(12)),
                    "Duration": clean_text(get_col(13)),
                    "Category": clean_text(get_col(14)),
                    "Properties": clean_text(get_col(15))
                })
            results.append(res)
    return results





class UziInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.era_colors = era_colors

    async def is_premium_user(self, user_id):
        whitelists = ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]
        for f in whitelists:
            if os.path.exists(f):
                with open(f, "r", encoding="utf-8") as file:
                    if str(user_id) in json.load(file).get("whitelisted_ids", []): return True
        return False



    class TrackDropdown(discord.ui.Select):
        def __init__(self, results_page, era_colors):
            self.results = results_page
            self.era_colors = era_colors
            options = [
                discord.SelectOption(
                    label=f"{track['index']}. {track['Track Title']} ({track['Era']})"[:100],
                    value=str(track['absolute_index'])
                ) for track in self.results
            ]
            super().__init__(placeholder="Select a track for full details", options=options)

        async def callback(self, interaction: discord.Interaction):
            absolute_index = int(self.values[0])
            full_results = self.view.full_results
            info = full_results[absolute_index]
            embed = build_embed(info, self.era_colors)
            await interaction.response.send_message(embed=embed)

    class PaginationDropdown(discord.ui.Select):
        def __init__(self, num_pages, current_page):

            display_pages = min(num_pages, 25)
            options = [
                discord.SelectOption(
                    label=f"Page {i+1} ({(i*MAX_DROPDOWN_RESULTS)+1}-{(i+1)*MAX_DROPDOWN_RESULTS})", 
                    value=str(i), 
                    default=(i == current_page)
                ) for i in range(display_pages)
            ]
            super().__init__(placeholder="Select a page", options=options)

        async def callback(self, it: discord.Interaction):
            await it.response.defer()
            await self.view.update_view_page(int(self.values[0]), it)

    class PreviousQuickInfoButton(discord.ui.Button):
        def __init__(self, results):
            super().__init__(label="⬅️ Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
            self.results = results
        async def callback(self, it: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index - 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}.")
            await it.response.edit_message(embed=embed, view=view)

    class QuickInfoButton(discord.ui.Button):
        def __init__(self, results):
            super().__init__(label="➡️ Next Quick Info", style=discord.ButtonStyle.secondary, emoji="➡️")
            self.results = results
        async def callback(self, it: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index + 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}.")
            await it.response.edit_message(embed=embed, view=view)

    class PaginatedSearchView(discord.ui.View):
        def __init__(self, full_results, era_colors, parent_cog, is_quick):
            super().__init__(timeout=180)

            self.full_results = full_results[:625]
            self.era_colors = era_colors
            self.parent_cog = parent_cog
            self.is_quick = is_quick
            
            for i, r in enumerate(self.full_results): 
                r['absolute_index'] = i
                r['index'] = i + 1
                
            self.num_pages = (len(self.full_results) + MAX_DROPDOWN_RESULTS - 1) // MAX_DROPDOWN_RESULTS
            self.current_page = 0
            self.current_quick_index = 0
            
            if self.is_quick: 
                self._add_quick_info_buttons()
            self._update_dropdowns()

        def _add_quick_info_buttons(self):

            self.add_item(self.parent_cog.PreviousQuickInfoButton(self.full_results))
            self.add_item(self.parent_cog.QuickInfoButton(self.full_results))
        
        def _update_dropdowns(self):
            for item in list(self.children):
                if isinstance(item, (self.parent_cog.TrackDropdown, self.parent_cog.PaginationDropdown)):
                    self.remove_item(item)
            
            start = self.current_page * MAX_DROPDOWN_RESULTS
            new_children = []
            
            if self.num_pages > 1:
                new_children.append(self.parent_cog.PaginationDropdown(self.num_pages, self.current_page))
            
            new_children.append(self.parent_cog.TrackDropdown(self.full_results[start:start+MAX_DROPDOWN_RESULTS], self.era_colors))
            
            for item in reversed(new_children):
                self.add_item(item)
            
        async def update_view_page(self, new_idx, it):
            self.current_page = new_idx
            self._update_dropdowns()
            await it.edit_original_response(view=self)

        def get_initial_embed(self):
            info = self.full_results[0]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result 1 of {len(self.full_results)}.")

    async def _handle_search(self, ctx, term, field, desc, quick):
        if ctx.command.name != "uziinfo" and not await self.is_premium_user(ctx.author.id):
            return await ctx.send(embed=discord.Embed(title="⭐ Premium Feature!", description="This is for Premium users.\n Visit [Our Website](https://collagebot.info/premium) to purchase premium.", color=0xD4AF37))
        
        if ctx.interaction: await ctx.defer()
        if not term: return await ctx.send(f"❌ Missing {desc}.")

        results = search_tracks_by_field(term, field)
        if not results: return await ctx.send(f":x: No Tracks Found for **{term}**.")
        
        if len(results) == 1:
            await ctx.send(embed=build_embed(results[0], self.era_colors))
        else: 
            view = self.PaginatedSearchView(results, self.era_colors, self, quick)
            if quick:
                embed = build_quick_embed(results[0])
                embed.set_footer(text=f"Showing result 1 of {len(results)}.")
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.send(content="Multiple results found!", view=view)

    @commands.hybrid_command(name="uziinfo", description="Get detailed information on any Lil Uzi Vert track.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uziinfo(self, ctx, *, track_title: str = None):
        await self._handle_search(ctx, track_title, "Track Title", "Track Name", False)

    @commands.hybrid_command(name="uziproducer", description="Search for tracks created by a specific producer for Lil Uzi Vert.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uziproducer(self, ctx, *, producer: str = None):
        await self._handle_search(ctx, producer, "Producer", "Producer", True)

    @commands.hybrid_command(name="uziengineer", description="Search for tracks produced by a specific engineer for Lil Uzi Vert.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uziengineer(self, ctx, *, engineer: str = None):
        await self._handle_search(ctx, engineer, "Engineer", "Engineer", True)

    @commands.hybrid_command(name="uziloc", description="Search for tracks recorded at a specific location for Lil Uzi Vert.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uziloc(self, ctx, *, location: str = None):
        await self._handle_search(ctx, location, "Recording Location", "Location", True)

    @commands.hybrid_command(name="uzipreview", description="Search for tracks previewed on a specific date for Lil Uzi Vert.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uzipreview(self, ctx, *, date: str = None):
        await self._handle_search(ctx, date, "Preview Date", "Preview Date", True)

async def setup(bot):
    await bot.add_cog(UziInfo(bot))