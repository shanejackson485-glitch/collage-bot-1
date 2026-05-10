import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import string
import unicodedata
from bs4 import BeautifulSoup


from .helpers import era_colors, era_images, era_mapping





BASE_DIR = os.getcwd()

HTML_FILES = [
    os.path.join(BASE_DIR, "JuiceInfoDB", "New", "released.html"),
    os.path.join(BASE_DIR, "JuiceInfoDB", "New", "unreleased.html"),
    os.path.join(BASE_DIR, "JuiceInfoDB", "New", "unsurfaced.html"),
]

SOUP_CACHE = {}
MAX_DROPDOWN_RESULTS = 25





def load_html_files():
    """Parse all HTML files once and store them in SOUP_CACHE."""
    global SOUP_CACHE
    if not SOUP_CACHE:
        for html_file in HTML_FILES:
            if not os.path.exists(html_file):
                continue
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read()
                SOUP_CACHE[html_file] = BeautifulSoup(content, "html.parser")
            except Exception as e:
                print(f"[CACHE] Failed to cache {html_file}: {e}")
    return SOUP_CACHE

def normalize_text(text: str) -> str:
    """Normalizes text for consistent searching (removes punctuation, spaces, converts to lower case)."""
    text = text.lower()
    replacements = { "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "\xa0": " " }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(rf"[{re.escape(string.punctuation)}]", "", text)
    text = re.sub(r'\s+', '', text)
    return text.strip()

def fix_missing_spaces(text: str) -> str:
    """Best-effort spacing fixes for tracker exports where anchor removal collapsed spaces."""
    if not text:
        return text

    patterns = [
        (r"(?i)on(?=SoundCloud)", "on "),
        (r"(?i)SoundCloud(?=[A-Za-z])", "SoundCloud "),
        (r"(?i)(First\s+Previewed|First\s+Teased)(?=[A-Z])", r"\1 "),
        (r"(?i)(Released|Recorded|Previewed|Teased)(?=[A-Z])", r"\1 "),
        (r"(?<=[A-Za-z0-9])\(", " ("),
        (r"(?<=\d)(?=[A-Za-z])", " "),
        (r"(?<=[A-Za-z])(?=[A-Z][a-z])", " "),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def clean_text(text, filter_out_words=None, add_spaces=False, fix_spacing=False):
    """Cleans text for display or pre-normalization filtering."""
    text = text.replace("\xa0", " ")

    if filter_out_words:
        for word in filter_out_words:
            text = re.sub(re.escape(word), "", text, flags=re.IGNORECASE).strip()

    if add_spaces:
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    if fix_spacing:
        text = fix_missing_spaces(text)
        text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def format_title(title: str) -> str:
    """Returns titles untouched aside from basic trimming/spacing."""
    return fix_missing_spaces(title.strip())


def split_title_and_notes(raw_title: str):
    """Splits multi-line title cells into main title, alt titles, and note lines."""
    if not raw_title:
        return "", [], []
    parts = [p.strip() for p in raw_title.split("\n") if p.strip()]
    if not parts:
        return "", [], []
    main = fix_missing_spaces(parts[0])
    alt_titles = []
    note_lines = []
    for segment in parts[1:]:
        cleaned = fix_missing_spaces(segment)
        if re.search(r"(?i)song\s+is\s+titled|song\s+was\s+originally\s+called", cleaned):
            note_lines.append(cleaned)
        else:
            alt_titles.append(cleaned)
    return main, alt_titles, note_lines
    
def clean_instrumental_text(text: str) -> str:
    """Cleans the raw HTML text from the instrumental column."""
    if not text:
        return ""

    text = text.replace("\xa0", " ").strip()

    if text.lower() in ["n/a", "-", "none", "", "unknown"]:
        return ""
    return text

def parse_instrumental_field(text: str) -> dict:
    """Converts the cleaned text into a dictionary for the embed."""
    if not text:
        return {}
    return {"Instrumental Name(s)": text}



DATASET_SCHEMAS = {
    "released": {
        "min_cols": 16,
        "title_idx": 2,
        "credited_idx": 3,
        "producer_idx": 4,
        "engineer_idx": 5,
        "info_idx": 6,
        "file_idx": 7,
        "inst_idx": 8,
        "location_idx": 9,
        "record_idx": 10,
        "preview_idx": 11,
        "surfaced_idx": 12,
        "duration_idx": 13,
        "category_idx": 14,
        "properties_idx": None,
        "available_idx": None,
    },
    "unreleased": {
        "min_cols": 17,
        "title_idx": 2,
        "credited_idx": 3,
        "producer_idx": 4,
        "engineer_idx": 5,
        "info_idx": 6,
        "file_idx": 7,
        "inst_idx": 8,
        "location_idx": 9,
        "record_idx": 10,
        "preview_idx": 11,
        "surfaced_idx": 12,
        "duration_idx": 13,
        "category_idx": 14,
        "properties_idx": None,
        "available_idx": 15,
    },
    "unsurfaced": {
        "min_cols": 14,
        "title_idx": 2,
        "credited_idx": 3,
        "producer_idx": 4,
        "engineer_idx": 5,
        "info_idx": 6,
        "file_idx": 7,
        "inst_idx": 8,
        "location_idx": 9,
        "record_idx": 10,
        "preview_idx": 11,
        "surfaced_idx": None,
        "duration_idx": None,
        "category_idx": 12,
        "properties_idx": None,
        "available_idx": None,
    },
}


def detect_dataset(html_file: str) -> str:
    name = os.path.basename(html_file).lower()
    if "unsurfaced" in name:
        return "unsurfaced"
    if "unreleased" in name:
        return "unreleased"
    return "released"

def build_embed(info, era_colors):
    """Builds the full, detailed discord.Embed."""
    era = info.get("Era", "Unknown Era")
    formatted_title = format_title(info.get("Track Title", "Unknown Track"))

    alt_titles = info.get("Alternate Titles") or []
    title_notes = info.get("Title Notes") or []
    desc_blocks = []
    if alt_titles:
        desc_blocks.append("**Alternate Titles:**\n" + "\n".join(alt_titles))
    if title_notes:
        desc_blocks.append("**Title Notes:**\n" + "\n".join(title_notes))
    description_text = "\n\n".join(desc_blocks) if desc_blocks else "Track Info"

    embed = discord.Embed(
        title=formatted_title,
        description=description_text,
        color=era_colors.get(era, discord.Color.blue().value)
    )

    def add_field(name, value):
        if value and value not in ["N/A", "-", ""]:
            embed.add_field(name=name, value=value, inline=False)

    add_field("Era", era)
    add_field("Credited Artist(s):", info.get("Credited Artists"))
    add_field("Produced by:", info.get("Producer"))
    add_field("Engineered by:", info.get("Engineer"))
    add_field("Additional Info", info.get("Additional Info"))
    add_field("File Name(s):", info.get("File Name"))
    add_field("Folder Title", info.get("Folder Title"))
    add_field("Session Title", info.get("Session Title"))

    inst_fields = info.get("Instrumental Fields", {})
    for k, v in inst_fields.items():
        add_field(k, v)

    add_field("Recording Location(s):", info.get("Recording Location"))
    add_field("Recording Date(s):", info.get("Recording Date"))
    add_field("File Exported", info.get("File Exported"))
    add_field("Acapella File Exported", info.get("Acapella Exported"))
    add_field("Preview Date", info.get("Preview Date"))
    add_field("Leaked", info.get("Surfaced"))
    add_field("Session Surfaced", info.get("Session Surfaced"))
    add_field("Duration", info.get("Duration"))
    add_field("Category", info.get("Category"))
    add_field("Available Files", info.get("Available Files"))
    add_field("Properties", info.get("Properties"))
    

    embed.set_thumbnail(url=era_images.get(era, era_images.get("Posthumous", "")))
    return embed

def build_quick_embed(info):
    """Builds a concise embed for the quick menu."""
    era = info.get("Era", "Unknown Era")
    formatted_title = format_title(info.get("Track Title", "Unknown Track"))
    
    embed = discord.Embed(
        title=f"Quick Info:\n{formatted_title}",
        description=f"**Era:** {era}",
        color=era_colors.get(era, discord.Color.blue().value)
    )

    embed.add_field(name="Engineered by:", value=info.get("Engineer", "N/A"), inline=True)
    embed.add_field(name="Produced by:", value=info.get("Producer", "N/A"), inline=True)
    embed.add_field(name="Credited Artist(s):", value=info.get("Credited Artists", "N/A"), inline=True)
    embed.add_field(name="Recording Date(s):", value=info.get("Recording Date", "N/A"), inline=True)
    embed.add_field(name="Location(s):", value=info.get("Recording Location", "N/A"), inline=True)
    embed.add_field(name="Preview Date:", value=info.get("Preview Date", "N/A"), inline=True)
    
    return embed

def search_tracks_by_field(query: str, field_name: str):
    """
    Generalized search function with conditional word boundary matching.
    """
    results = []
    normalized_query = normalize_text(query)
    soups = load_html_files()
    
    field_config = {
        "Track Title": "title_idx",
        "Producer": "producer_idx",
        "Engineer": "engineer_idx",
        "Recording Location": "location_idx",
        "Recording Date": "record_idx",
        "Preview Date": "preview_idx",
    }

    strict_fields = ["Producer", "Engineer"]

    if field_name not in field_config:
        return []

    for html_file, soup in soups.items():
        dataset = detect_dataset(html_file)
        schema = DATASET_SCHEMAS.get(dataset, DATASET_SCHEMAS["released"])

        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue

            if len(cols) < schema["min_cols"]:
                continue

            def get_col(idx):
                c = cols[idx]
                for br in c.find_all("br"):
                    br.replace_with("||BR||")
                text = c.get_text(strip=True) if hasattr(c, "get_text") else str(c).strip()
                return text.replace("||BR||", "\n")

            match_found = False

            if field_name == "Track Title":
                title_raw = get_col(schema["title_idx"])
                title_clean = clean_text(title_raw, fix_spacing=True, add_spaces=True)
                title_options = [t.strip() for t in title_clean.split("|") if t.strip()]
                if any(normalized_query in normalize_text(t) for t in title_options):
                    match_found = True
            else:
                col_name = field_config[field_name]
                col_idx = schema.get(col_name)
                if col_idx is None or col_idx >= len(cols):
                    continue

                target_text_raw = get_col(col_idx)
                target_text_clean = clean_text(
                    target_text_raw,
                    filter_out_words=["Recorded"] if field_name == "Recording Date" else ["First Previewed"] if field_name == "Preview Date" else None,
                    fix_spacing=True,
                )
                normalized_target = normalize_text(target_text_clean)

                if field_name in strict_fields:
                    pattern = r"\b" + re.escape(normalized_query) + r"\b"
                else:
                    pattern = r"\b" + re.escape(normalized_query)

                if re.search(pattern, normalized_target):
                    match_found = True

            if not match_found:
                continue

            inst_fields = parse_instrumental_field(clean_instrumental_text(get_col(schema["inst_idx"])))

            title_main, alt_titles, title_notes = split_title_and_notes(get_col(schema["title_idx"]))

            credited_raw = clean_text(get_col(schema["credited_idx"]), fix_spacing=True, add_spaces=True)
            hide_credited = credited_raw.lower().strip() in ["juice wrld", "juicethekidd", "juice wrld & juicethekidd", "juicethekidd & juice wrld"]
            credited_value = "" if hide_credited else credited_raw

            file_col_raw = get_col(schema["file_idx"])
            session_title = ""
            folder_title = ""

            m_session = re.search(r"(?i)session\s*title\s*:?[\s]*([^\n]+)", file_col_raw)
            if m_session:
                session_title = clean_text(m_session.group(1), fix_spacing=True)

            m_folder = re.search(r"(?i)folder\s*title\s*:?[\s]*([^\n]+)", file_col_raw)
            if m_folder:
                folder_title = clean_text(m_folder.group(1), fix_spacing=True)


            cleaned_file_col = re.sub(r"(?i)session\s*title\s*:?[\s]*[^\n]+", "", file_col_raw)
            cleaned_file_col = re.sub(r"(?i)folder\s*title\s*:?[\s]*[^\n]+", "", cleaned_file_col)
            file_raw = clean_text(cleaned_file_col.replace("File Name:", ""), fix_spacing=True)

            recording_date_full = clean_text(get_col(schema["record_idx"]), fix_spacing=True)
            file_exported = ""
            m_file = re.search(r"(?i)file\s+exported\s*:?\s*(.*)", recording_date_full)
            if m_file:
                file_exported = m_file.group(1).strip()
                recording_date_full = recording_date_full.replace(m_file.group(0), "").strip()

            recording_date_raw = clean_text(recording_date_full, filter_out_words=["Recorded"], fix_spacing=True)
            acapella_exported = ""
            if "acapella" in recording_date_raw.lower():
                match = re.search(r"(?i)acapella file exported\s*(.*)", recording_date_raw)
                if match:
                    acapella_exported = match.group(1).strip()
                recording_date_raw = recording_date_raw.replace(match.group(0), "").strip() if match else recording_date_raw

            surfaced_raw = ""
            session_surfaced = ""
            if schema.get("surfaced_idx") is not None:
                surfaced_raw = clean_text(get_col(schema["surfaced_idx"]), fix_spacing=True)
                surfaced_raw = re.sub(r"(?i)^surfaced\s*:?[\s\-]*", "", surfaced_raw).strip()
                match = re.search(r"(?i)session surfaced\s*(.*)", surfaced_raw)
                if match:
                    session_surfaced = match.group(1).strip()
                    surfaced_raw = surfaced_raw.replace(match.group(0), "").strip()

            result_data = {
                "Era": era_mapping.get(clean_text(get_col(0)), clean_text(get_col(0))),
                "Track Title": title_main or clean_text(get_col(schema["title_idx"]), fix_spacing=True, add_spaces=True),
                "Alternate Titles": alt_titles,
                "Title Notes": title_notes,
                "Credited Artists": credited_value,
                "Producer": clean_text(get_col(schema["producer_idx"])),
                "Engineer": clean_text(get_col(schema["engineer_idx"])),
                "Additional Info": clean_text(get_col(schema["info_idx"]), fix_spacing=True),
                "File Name": file_raw,
                "Folder Title": folder_title,
                "Session Title": session_title,
                "Instrumental Fields": inst_fields,
                "Recording Location": clean_text(get_col(schema["location_idx"]), fix_spacing=True),
                "Recording Date": recording_date_raw,
                "File Exported": file_exported,
                "Acapella Exported": acapella_exported,
                "Preview Date": clean_text(get_col(schema["preview_idx"]), filter_out_words=["First Previewed"], fix_spacing=True),
                "Session Surfaced": session_surfaced,
            }

            if dataset == "unsurfaced":
                result_data.update({
                    "Surfaced": "Not Surfaced",
                    "Duration": "",
                    "Category": clean_text(get_col(schema["category_idx"]), fix_spacing=True),
                    "Available Files": "",
                    "Properties": "",
                })
            elif dataset == "unreleased":
                result_data.update({
                    "Surfaced": surfaced_raw,
                    "Duration": clean_text(get_col(schema["duration_idx"])),
                    "Category": clean_text(get_col(schema["category_idx"]), fix_spacing=True),
                    "Available Files": clean_text(get_col(schema["available_idx"]), fix_spacing=True) if schema.get("available_idx") is not None else "",
                    "Properties": "",
                })
            else:
                result_data.update({
                    "Surfaced": surfaced_raw,
                    "Duration": clean_text(get_col(schema["duration_idx"])),
                    "Category": clean_text(get_col(schema["category_idx"]), fix_spacing=True),
                    "Available Files": "",
                    "Properties": "",
                })
            results.append(result_data)

    return results





class JuiceInfo(commands.Cog):
    """Hybrid command to get info about Juice WRLD tracks."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.era_colors = era_colors


    async def is_premium_user(self, user_id):
        """Check if the user is in either premium_whitelist.json or manual_whitelist.json."""
        whitelists = ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]
        for file in whitelists:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if str(user_id) in data.get("whitelisted_ids", []):
                        return True
            except FileNotFoundError:
                continue
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
            try:
                await interaction.response.send_message(embed=embed)
            except discord.HTTPException:
                await interaction.followup.send("❌ Error: Service is busy. Try again later.", ephemeral=True)

    class PaginationDropdown(discord.ui.Select):
        def __init__(self, num_pages, current_page):
            self.num_pages = num_pages
            options = [
                discord.SelectOption(
                    label=f"Page {i+1} ({i*MAX_DROPDOWN_RESULTS + 1} - {(i+1)*MAX_DROPDOWN_RESULTS})",
                    value=str(i),
                    default=(i == current_page)
                ) for i in range(num_pages)
            ]
            super().__init__(placeholder="Select a page", options=options)

        async def callback(self, interaction: discord.Interaction):
            new_page_index = int(self.values[0])
            await interaction.response.defer() 
            await self.view.update_view_page(new_page_index, interaction)

    class PreviousQuickInfoButton(discord.ui.Button):
        def __init__(self, results):
            super().__init__(label="⬅️ Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
            self.results = results

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index - 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}. Use the menu for full details. Change results using page number menu.")
            await interaction.response.edit_message(embed=embed, view=view)

    class QuickInfoButton(discord.ui.Button):
        def __init__(self, results):
            super().__init__(label="➡️ Next Quick Info", style=discord.ButtonStyle.secondary, emoji="➡️")
            self.results = results

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index + 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}. Use the menu for full details.")
            await interaction.response.edit_message(embed=embed, view=view)
            
    class PaginatedSearchView(discord.ui.View):
        def __init__(self, full_results, era_colors, parent_cog, is_quick_info_view):
            super().__init__(timeout=180) 
            self.full_results = full_results
            self.era_colors = era_colors
            self.parent_cog = parent_cog
            self.is_quick_info_view = is_quick_info_view
            self.num_results = len(full_results)
            self.num_pages = (self.num_results + MAX_DROPDOWN_RESULTS - 1) // MAX_DROPDOWN_RESULTS
            self.current_page = 0
            self.current_quick_index = 0

            for i, result in enumerate(self.full_results):
                result['absolute_index'] = i
                result['index'] = i + 1

            if self.is_quick_info_view:
                self._add_quick_info_buttons()
            
            self._update_dropdowns()

        def _add_quick_info_buttons(self):
            self.add_item(self.parent_cog.PreviousQuickInfoButton(self.full_results))
            self.add_item(self.parent_cog.QuickInfoButton(self.full_results))
        
        def _update_dropdowns(self):
            for item in list(self.children):
                if isinstance(item, (self.parent_cog.TrackDropdown, self.parent_cog.PaginationDropdown)):
                    self.remove_item(item)

            start_index = self.current_page * MAX_DROPDOWN_RESULTS
            end_index = min(start_index + MAX_DROPDOWN_RESULTS, self.num_results)
            results_page = self.full_results[start_index:end_index]

            new_children = []
            

            if self.num_pages > 1:
                pagination_dropdown = self.parent_cog.PaginationDropdown(self.num_pages, self.current_page)
                new_children.append(pagination_dropdown)


            track_dropdown = self.parent_cog.TrackDropdown(results_page, self.era_colors)
            new_children.append(track_dropdown)


            for item in reversed(new_children):
                self.add_item(item)
            
        async def update_view_page(self, new_page_index, interaction):
            self.current_page = new_page_index
            self._update_dropdowns()
            
            if self.is_quick_info_view:
                await interaction.edit_original_response(view=self)
            else:
                await interaction.edit_original_response(content="Multiple results found! Please select one:", view=self)
            
        def get_initial_embed(self):
            info = self.full_results[0]
            embed = build_quick_embed(info)
            embed.set_footer(text=f"Showing result 1 of {self.num_results}. Use the menu for full details or the buttons to cycle quick info.")
            return embed
        
        def get_initial_message(self):
            return "Multiple results found! Please select one:"



    async def _handle_search(self, ctx: commands.Context, search_term: str, field_name: str, desc_name: str, use_interactive_menu: bool):
        


        if ctx.command.name != "juiceinfo":
            if not await self.is_premium_user(ctx.author.id):
                embed = discord.Embed(
                    title="⭐ Premium Feature!",
                    description=f"The **`/{ctx.command.name}`** command is available to **Premium** users.\nUse `@collage premium` to learn more.",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
                return

        
        if ctx.interaction:
            await ctx.defer()
            
        if not search_term:
            embed = discord.Embed(
                title=f"❌ Missing {desc_name}",
                description=f"Please provide a search term for the {desc_name} field.\nExample: `/{ctx.command.name} 'query'`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        results = search_tracks_by_field(search_term, field_name)

        if not results:
            embed = discord.Embed(
                title=":x: No Tracks Found",
                description=f"No tracks matching **{search_term}** in the **{desc_name}** field found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            if len(results) == 1:
                embed = build_embed(results[0], self.era_colors)
                await ctx.send(embed=embed)
            
            else: 
                paginated_view = self.PaginatedSearchView(results, self.era_colors, self, use_interactive_menu)
                
                if use_interactive_menu:
                    initial_embed = paginated_view.get_initial_embed()
                    await ctx.send(embed=initial_embed, view=paginated_view)
                else:
                    initial_message = paginated_view.get_initial_message()
                    await ctx.send(content=initial_message, view=paginated_view)
                
        except discord.HTTPException:
            try:
                await ctx.send("❌ Error: Bot is temporarily rate-limited. Please try your command again in a few seconds.", delete_after=10)
            except Exception:
                pass





    @commands.hybrid_command(name="juiceinfo", with_app_command=True, description="Get detailed info about a Juice WRLD track by title")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(track_title="The name of the track to search for")
    async def juiceinfo(self, ctx: commands.Context, *, track_title: str = None):
        """Free command for track info."""
        await self._handle_search(ctx, track_title, "Track Title", "Track Name", use_interactive_menu=False)


    @commands.hybrid_command(name="juiceproducer", with_app_command=True, description="Search for tracks by producer name")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(producer="The name of the producer")
    async def juiceproducer(self, ctx: commands.Context, *, producer: str = None):
        """Premium command for producer search."""
        await self._handle_search(ctx, producer, "Producer", "Producer", use_interactive_menu=True)
    

    @commands.hybrid_command(name="juiceengineer", with_app_command=True, description="Search for tracks by engineer name")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(engineer="The name of the engineer")
    async def juiceengineer(self, ctx: commands.Context, *, engineer: str = None):
        """Premium command for engineer search."""
        await self._handle_search(ctx, engineer, "Engineer", "Engineer", use_interactive_menu=True)


    @commands.hybrid_command(name="juiceloc", with_app_command=True, description="Search for tracks by recording location")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(location="The name of the recording location")
    async def juiceloc(self, ctx: commands.Context, *, location: str = None):
        """Premium command for location search."""
        await self._handle_search(ctx, location, "Recording Location", "Recording Location", use_interactive_menu=True)
        

    @commands.hybrid_command(name="juicepreview", with_app_command=True, description="Search for tracks by preview date (e.g., '2020')")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(date="The preview date or year")
    async def juicepreview(self, ctx: commands.Context, *, date: str = None):
        """Premium command for preview date search."""
        await self._handle_search(ctx, date, "Preview Date", "Preview Date", use_interactive_menu=True)

async def setup(bot):
    await bot.add_cog(JuiceInfo(bot))