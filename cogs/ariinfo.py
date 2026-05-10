import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import re
import string
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
import aiohttp
from PIL import Image
from io import BytesIO
from collections import Counter
from colorsys import rgb_to_hsv
import pytz
from discord import app_commands

def _find_base_dir() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "data").is_dir() and (p / "cogs").is_dir():
            return p
        if (p / "config.py").is_file():
            return p
        if (p / "AriInfoDB").is_dir():
            return p
    return here.parents[2] if len(here.parents) > 2 else here.parent


BASE_DIR = _find_base_dir()

EASTERN_TIMEZONE = pytz.timezone('US/Eastern')
COOLDOWN_FILE = BASE_DIR / "data" / "Developer" / "ariinfo_cooldown.json"
FREE_DAILY_INFO_USES = 10


_candidates = [
    BASE_DIR / "AriInfoDB" / "unreleasedAri.html"
]
ARI_HTML_FILES = [str(p) for p in _candidates if p.exists()]

SOUP_CACHE: dict[str, BeautifulSoup] = {}
PROJECT_THUMBNAILS: dict[str, str] = {}
PROJECT_COLORS: dict[str, int] = {}
MAX_DROPDOWN_RESULTS = 25


_URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)

_PROD_RE = re.compile(
    r"\((?:\s*(?:prod\.?|producer\(s\)|producers|produced\s+by|prod\s+by)\s*[:\-]?\s*)([^\)]+?)\s*\)",
    re.IGNORECASE,
)

_OG_FILENAME_LINE_RE = re.compile(r"(?im)^\s*og\s*filename\s*:\s*(.+?)\s*$")


def load_html_files() -> dict[str, BeautifulSoup]:
    global SOUP_CACHE
    if not SOUP_CACHE:
        for html_file in ARI_HTML_FILES:
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    SOUP_CACHE[html_file] = BeautifulSoup(f.read(), "html.parser")
            except Exception as e:
                print(f"[CACHE] Failed to cache {html_file}: {e}")
    return SOUP_CACHE


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = [u.rstrip(")].,\"'" ) for u in _URL_RE.findall(text)]

    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def build_project_thumbnails() -> dict[str, str]:
    """Build a mapping of project -> thumbnail URL from the tracker header/section rows.

    The Google Sheets export includes project rows that contain <img> tags (covers).
    Track rows don't contain images, so we scan the entire table for rows that
    mention known project names and include an image.
    """
    global PROJECT_THUMBNAILS
    if PROJECT_THUMBNAILS:
        return PROJECT_THUMBNAILS

    soups = load_html_files()
    thumbs: dict[str, str] = {}

    def soup_default_image(soup: BeautifulSoup) -> str | None:
        meta = soup.find("meta", {"property": "og:image"})
        if meta and meta.get("content"):
            return str(meta.get("content"))
        return None

    for _html_file, soup in soups.items():
        table = soup.find("table", {"class": "waffle"})
        if not table:
            continue


        projects: set[str] = set()
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) != 11:
                continue

            project = clean_text(cols[1].get_text(" ", strip=True))
            if project and project.lower() != "project":
                projects.add(project)


        normalized_projects = {normalize_text(p): p for p in projects}
        for row in table.find_all("tr"):
            img = row.find("img")
            if not img or not img.get("src"):
                continue

            img_url = str(img.get("src"))
            row_text_norm = normalize_text(row.get_text(" ", strip=True))

            for proj_norm, proj in normalized_projects.items():
                if proj_norm and proj_norm in row_text_norm and proj not in thumbs:
                    thumbs[proj] = img_url

                    thumbs.setdefault(f"__norm__:{proj_norm}", img_url)

        default_img = soup_default_image(soup)
        if default_img and "__default__" not in thumbs:
            thumbs["__default__"] = default_img

    PROJECT_THUMBNAILS = thumbs
    return PROJECT_THUMBNAILS


def split_title_and_producers(raw_name: str) -> tuple[str, str | None]:
    """Return (title_without_prod, producers).

    The tracker stores producer info inside the Name cell on new lines like:
      Pink Champagne [V1]\n(prod. Pebe Sebert)
    We want producer(s) as an embed field, not part of the title.
    """
    text = clean_text(raw_name)
    if not text:
        return "Unknown", None

    producers: list[str] = []

    def _repl(m: re.Match) -> str:
        p = clean_text(m.group(1))
        if p:
            producers.append(p)
        return ""

    title = _PROD_RE.sub(_repl, text)

    title = re.sub(r"\(\s*\)", "", title)
    title = re.sub(r"[ \t]+", " ", title)

    lines = [ln.strip() for ln in title.splitlines() if ln.strip()]
    title = "\n".join(lines).strip() or "Unknown"

    if not producers:
        return title, None


    seen: set[str] = set()
    uniq: list[str] = []
    for p in producers:
        key = normalize_text(p)
        if key and key not in seen:
            seen.add(key)
            uniq.append(p)

    return title, ", ".join(uniq)


def split_notes_and_og_filename(raw_notes: str) -> tuple[str | None, str | None]:
    """Return (og_filename, remaining_notes)."""
    notes = clean_text(raw_notes)
    if not notes:
        return None, None

    og_matches = _OG_FILENAME_LINE_RE.findall(notes)
    og = "; ".join([clean_text(x) for x in og_matches if clean_text(x)]) if og_matches else None


    lines = []
    for line in notes.splitlines():
        if _OG_FILENAME_LINE_RE.match(line):
            continue
        lines.append(line)
    remaining = "\n".join([ln.rstrip() for ln in lines]).strip() or None

    return og, remaining


def _rgb_to_int(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return (r << 16) + (g << 8) + b


def _pick_dominant_color(image: Image.Image) -> tuple[int, int, int] | None:
    img = image.convert("RGB")
    img = img.resize((64, 64))
    pixels = list(img.getdata())
    if not pixels:
        return None

    counts = Counter(pixels)

    def score(rgb: tuple[int, int, int], freq: int) -> float:
        r, g, b = rgb
        h, s, v = rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

        if v > 0.97 and s < 0.12:
            return freq * 0.05
        if v < 0.08:
            return freq * 0.10
        return freq * (0.6 + s) * (0.7 + v)

    best_rgb, best_score = None, -1.0
    for rgb, freq in counts.most_common(50):
        sc = score(rgb, freq)
        if sc > best_score:
            best_rgb, best_score = rgb, sc

    return best_rgb


async def get_project_color(project: str, thumb_url: str | None) -> int:
    proj_norm = normalize_text(project)
    cache_key = proj_norm or project
    if cache_key in PROJECT_COLORS:
        return PROJECT_COLORS[cache_key]

    fallback = _embed_color_for_project(project)
    if not thumb_url:
        PROJECT_COLORS[cache_key] = fallback
        return fallback

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(thumb_url) as resp:
                if resp.status != 200:
                    PROJECT_COLORS[cache_key] = fallback
                    return fallback
                data = await resp.read()

        img = Image.open(BytesIO(data))
        rgb = _pick_dominant_color(img)
        if not rgb:
            PROJECT_COLORS[cache_key] = fallback
            return fallback

        color_int = _rgb_to_int(rgb)
        PROJECT_COLORS[cache_key] = color_int
        return color_int
    except Exception:
        PROJECT_COLORS[cache_key] = fallback
        return fallback


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "\xa0": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(rf"[{re.escape(string.punctuation)}]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def clean_text(text: str) -> str:
    return (text or "").replace("\xa0", " ").strip()


def format_title(title: str) -> str:
    if not title:
        return "Unknown"
    if "*" in title:
        left, right = title.split("*", 1)
        return f"{left}*\n{right.strip()}"
    if ")" in title:
        left, right = title.split(")", 1)
        return f"{left})\n{right.strip()}"
    return title


def _embed_color_for_project(project: str) -> int:
    project = (project or "").lower()
    if "yours truly" in project:
        return 0xF4B7C5
    if "my everything" in project:
        return 0xE5DCCB
    if "dangerous woman" in project:
        return 0x111111
    if "sweetener" in project:
        return 0xF2D16B
    if "thank u" in project or "thank u, next" in project:
        return 0xF2A8B5
    if "positions" in project:
        return 0x6F4B37
    return discord.Color.blurple().value


async def build_embed(info: dict) -> discord.Embed:
    project = info.get("Project", "Unknown")
    raw_name = info.get("Name", "Unknown")
    title_wo_prod, producers = split_title_and_producers(raw_name)
    title = format_title(title_wo_prod)

    thumbs = build_project_thumbnails()
    proj_norm = normalize_text(project)
    thumb = thumbs.get(project) or thumbs.get(f"__norm__:{proj_norm}") or thumbs.get("__default__")

    embed = discord.Embed(
        title=title,
        description="Track Info",
        color=await get_project_color(project, thumb),
    )

    def add_field(name: str, value: str):
        value = clean_text(value)
        if value and value not in {"N/A", "-"}:
            embed.add_field(name=name, value=value, inline=False)

    add_field("Era", project)
    if producers:
        add_field("Producer(s)", producers)
    add_field("Type", info.get("Type", ""))
    add_field("Track Length", info.get("Track Length", ""))
    add_field("Available Length", info.get("Available Length", ""))
    add_field("Quality", info.get("Quality", ""))
    add_field("File Date", info.get("File Date", ""))
    add_field("Leak Date", info.get("Leak Date", ""))

    og_filename, notes = split_notes_and_og_filename(info.get("Notes", ""))
    if og_filename:
        if len(og_filename) > 1024:
            og_filename = og_filename[:1018] + "..."
        embed.add_field(name="OG Filename", value=og_filename, inline=False)

    if notes:
        if len(notes) > 1024:
            notes = notes[:1018] + "..."
        embed.add_field(name="Notes", value=notes, inline=False)

    if thumb:
        embed.set_thumbnail(url=thumb)

    return embed


async def build_quick_embed(info: dict) -> discord.Embed:
    project = info.get("Project", "Unknown")
    raw_name = info.get("Name", "Unknown")
    title_wo_prod, producers = split_title_and_producers(raw_name)
    title = format_title(title_wo_prod)

    thumbs = build_project_thumbnails()
    proj_norm = normalize_text(project)
    thumb = thumbs.get(project) or thumbs.get(f"__norm__:{proj_norm}") or thumbs.get("__default__")

    embed = discord.Embed(
        title=f"Quick Info:\n{title}",
        description=f"**Project:** {project}",
        color=await get_project_color(project, thumb),
    )

    def f(name: str, key: str):
        v = clean_text(info.get(key, "")) or "N/A"
        embed.add_field(name=name, value=v, inline=True)

    f("Type", "Type")
    f("Length", "Track Length")
    f("Quality", "Quality")
    f("File Date", "File Date")
    f("Leak Date", "Leak Date")
    f("Avail. Length", "Available Length")

    if producers:

        embed.add_field(name="Producer(s)", value=producers[:1024], inline=False)

    if thumb:
        embed.set_thumbnail(url=thumb)

    return embed


def search_tracks_by_field(query_term: str, field_name: str) -> list[dict]:
    results: list[dict] = []
    query = normalize_text(query_term)

    soups = load_html_files()













    field_to_idx = {
        "Name": 2,
        "Project": 1,
        "Type": 7,
        "Quality": 9,
        "File Date": 5,
        "Leak Date": 6,
    }

    if field_name not in field_to_idx:
        return []

    idx = field_to_idx[field_name]

    for html_file, soup in soups.items():
        table = soup.find("table", {"class": "waffle"})
        if not table:
            continue

        for row in table.find_all("tr"):

            cols = row.find_all(["td", "th"])

            if len(cols) != 11:
                continue

            def get_col(i: int) -> str:
                if i >= len(cols):
                    return ""
                c = cols[i]
                return c.get_text("\n", strip=True)


            if clean_text(get_col(2)).lower() == "name":
                continue


            project = clean_text(get_col(1))
            name = clean_text(get_col(2))
            if not name:
                continue

            target = normalize_text(get_col(idx))
            if query not in target:
                continue

            results.append(
                {
                    "Project": project,
                    "Name": name,
                    "Notes": clean_text(get_col(3)),
                    "Track Length": clean_text(get_col(4)),
                    "File Date": clean_text(get_col(5)),
                    "Leak Date": clean_text(get_col(6)),
                    "Type": clean_text(get_col(7)),
                    "Available Length": clean_text(get_col(8)),
                    "Quality": clean_text(get_col(9)),
                    "Links": clean_text(get_col(10)),
                    "_source": os.path.basename(html_file),
                }
            )

    return results


class AriInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldown_data = self._load_cooldown_data()

    def _load_cooldown_data(self) -> dict:
        try:
            if COOLDOWN_FILE.exists():
                with open(COOLDOWN_FILE, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def _save_cooldown_data(self) -> None:
        try:
            COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(COOLDOWN_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cooldown_data, f, indent=4)
        except Exception:
            pass

    async def _enforce_info_daily_limit(self, ctx: commands.Context) -> bool:
        """Enforce the free-user daily cap for the base info command only."""
        if await self.is_premium_user(ctx.author.id):
            return True

        uid = str(ctx.author.id)
        now = datetime.now(EASTERN_TIMEZONE)
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        data = self.cooldown_data.get(uid, {"uses": 0, "last_reset": 0})
        if data.get("last_reset", 0) < today_midnight.timestamp():
            data["uses"] = 0
            data["last_reset"] = today_midnight.timestamp()

        used = int(data.get("uses", 0) or 0)
        if used < FREE_DAILY_INFO_USES:
            data["uses"] = used + 1
            self.cooldown_data[uid] = data
            self._save_cooldown_data()
            return True

        tomorrow_midnight = today_midnight + timedelta(days=1)
        retry_seconds = int((tomorrow_midnight - now).total_seconds())
        h = retry_seconds // 3600
        m = (retry_seconds % 3600) // 60
        s = retry_seconds % 60
        limit_embed = discord.Embed(
            title="⭐ Premium Feature Limit Reached",
            color=discord.Color.gold(),
            description=(
                f"Used your {FREE_DAILY_INFO_USES} free searches today.\n"
                f"**Resets in:** `{h}h {m}m {s}s`\n"
                "Visit [Our Website](https://collagebot.info/premium) to purchase premium access for unlimited searches."
            ),
        )

        try:
            await ctx.reply(embed=limit_embed, ephemeral=True)
        except Exception:
            await ctx.send(embed=limit_embed)
        return False

    async def is_premium_user(self, user_id: int) -> bool:
        whitelists = [
            BASE_DIR / "data" / "Developer" / "premium_whitelist.json",
            BASE_DIR / "data" / "Developer" / "manual_whitelist.json",
        ]
        for f in whitelists:
            if f.exists():
                with open(f, "r", encoding="utf-8") as file:
                    if str(user_id) in (json.load(file) or {}).get("whitelisted_ids", []):
                        return True
        return False

    class TrackDropdown(discord.ui.Select):
        def __init__(self, results_page: list[dict]):
            self.results = results_page
            options = [
                discord.SelectOption(
                    label=f"{track['index']}. {track['Name']} ({track.get('Project','Unknown')})"[:100],
                    value=str(track["absolute_index"]),
                )
                for track in self.results
            ]
            super().__init__(placeholder="Select a track for full details", options=options)

        async def callback(self, interaction: discord.Interaction):
            absolute_index = int(self.values[0])
            info = self.view.full_results[absolute_index]
            view = AriInfo.LinksView.from_info(info)
            await interaction.response.send_message(embed=await build_embed(info), view=view)

    class LinksView(discord.ui.View):
        def __init__(self, urls: list[str]):
            super().__init__(timeout=180)
            for i, url in enumerate(urls[:5]):
                label = "Download" if i == 0 else f"Link {i+1}"
                self.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.link, url=url))

        @classmethod
        def from_info(cls, info: dict) -> "AriInfo.LinksView | None":
            urls = extract_urls(clean_text(info.get("Links", "")))
            if not urls:
                return None
            return cls(urls)

    class PaginationDropdown(discord.ui.Select):
        def __init__(self, num_pages: int, current_page: int):
            display_pages = min(num_pages, 25)
            options = [
                discord.SelectOption(
                    label=f"Page {i+1} ({(i*MAX_DROPDOWN_RESULTS)+1}-{(i+1)*MAX_DROPDOWN_RESULTS})",
                    value=str(i),
                    default=(i == current_page),
                )
                for i in range(display_pages)
            ]
            super().__init__(placeholder="Select a page", options=options)

        async def callback(self, it: discord.Interaction):
            await it.response.defer()
            await self.view.update_view_page(int(self.values[0]), it)

    class PreviousQuickInfoButton(discord.ui.Button):
        def __init__(self, results: list[dict]):
            super().__init__(label="⬅️ Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
            self.results = results

        async def callback(self, it: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index - 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = await build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}.")
            view.update_link_buttons(info)
            await it.response.edit_message(embed=embed, view=view)

    class QuickInfoButton(discord.ui.Button):
        def __init__(self, results: list[dict]):
            super().__init__(label="➡️ Next Quick Info", style=discord.ButtonStyle.secondary, emoji="➡️")
            self.results = results

        async def callback(self, it: discord.Interaction):
            view = self.view
            view.current_quick_index = (view.current_quick_index + 1) % len(self.results)
            info = self.results[view.current_quick_index]
            embed = await build_quick_embed(info)
            embed.set_footer(text=f"Showing result {view.current_quick_index + 1} of {len(self.results)}.")
            view.update_link_buttons(info)
            await it.response.edit_message(embed=embed, view=view)

    class PaginatedSearchView(discord.ui.View):
        def __init__(self, full_results: list[dict], parent_cog: "AriInfo", is_quick: bool):
            super().__init__(timeout=180)
            self.full_results = full_results[:625]
            self.parent_cog = parent_cog
            self.is_quick = is_quick
            self._link_button_count = 0

            for i, r in enumerate(self.full_results):
                r["absolute_index"] = i
                r["index"] = i + 1

            self.num_pages = (len(self.full_results) + MAX_DROPDOWN_RESULTS - 1) // MAX_DROPDOWN_RESULTS
            self.current_page = 0
            self.current_quick_index = 0

            if self.is_quick:
                self._add_quick_info_buttons()
            self._update_dropdowns()

            if self.is_quick and self.full_results:
                self.update_link_buttons(self.full_results[self.current_quick_index])

        def _add_quick_info_buttons(self):
            self.add_item(self.parent_cog.PreviousQuickInfoButton(self.full_results))
            self.add_item(self.parent_cog.QuickInfoButton(self.full_results))

        def _update_dropdowns(self):
            for item in list(self.children):
                if isinstance(item, (self.parent_cog.TrackDropdown, self.parent_cog.PaginationDropdown)):
                    self.remove_item(item)

            start = self.current_page * MAX_DROPDOWN_RESULTS
            new_children: list[discord.ui.Item] = []

            if self.num_pages > 1:
                new_children.append(self.parent_cog.PaginationDropdown(self.num_pages, self.current_page))

            new_children.append(self.parent_cog.TrackDropdown(self.full_results[start : start + MAX_DROPDOWN_RESULTS]))

            for item in reversed(new_children):
                self.add_item(item)

        def update_link_buttons(self, info: dict):

            for item in list(self.children):
                if isinstance(item, discord.ui.Button) and getattr(item, "_ari_link", False):
                    self.remove_item(item)

            urls = extract_urls(clean_text(info.get("Links", "")))
            if not urls:
                self._link_button_count = 0
                return

            self._link_button_count = min(len(urls), 5)
            for i, url in enumerate(urls[:5]):
                label = "Download" if i == 0 else f"Link {i+1}"
                b = discord.ui.Button(label=label, style=discord.ButtonStyle.link, url=url)
                setattr(b, "_ari_link", True)
                self.add_item(b)

        async def update_view_page(self, new_idx: int, it: discord.Interaction):
            self.current_page = new_idx
            self._update_dropdowns()
            await it.edit_original_response(view=self)

    async def _handle_search(self, ctx: commands.Context, term: str | None, field: str, desc: str, quick: bool):



        if ctx.command.name != "ariinfo" and not await self.is_premium_user(ctx.author.id):
            return await ctx.send(
                embed=discord.Embed(
                    title="⭐ Premium Feature!",
                    description="This is for Premium users.",
                    color=0xD4AF37,
                )
            )

        if ctx.interaction:
            await ctx.defer()

        if not term:
            return await ctx.send(f"❌ Missing {desc}.")

        results = search_tracks_by_field(term, field)
        if not results:
            return await ctx.send(f":x: No Tracks Found for **{term}**.")

        if len(results) == 1:
            view = self.LinksView.from_info(results[0])
            await ctx.send(embed=await build_embed(results[0]), view=view)
            return

        view = self.PaginatedSearchView(results, self, quick)
        if quick:
            embed = await build_quick_embed(results[0])
            embed.set_footer(text=f"Showing result 1 of {len(results)}.")
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(content="Multiple results found!", view=view)



    @commands.hybrid_command(name="ariinfo", description="Get detailed information on Ariana Grande tracks from AriInfoDB.", aliases=["arileak"])
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ariinfo(self, ctx: commands.Context, *, track_name: str | None = None):
        if not await self._enforce_info_daily_limit(ctx):
            return
        await self._handle_search(ctx, track_name, "Name", "Track Name", False)

    @commands.hybrid_command(name="ariproject", description="(Premium) Search Ariana Grande tracks by project/era name.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ariproject(self, ctx: commands.Context, *, project: str | None = None):
        await self._handle_search(ctx, project, "Project", "Project", True)

    @commands.hybrid_command(name="aritype", description="(Premium) Search Ariana Grande tracks by type (Demo, Throwaway, etc.).")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def aritype(self, ctx: commands.Context, *, type_name: str | None = None):
        await self._handle_search(ctx, type_name, "Type", "Type", True)

    @commands.hybrid_command(name="arileakdate", description="(Premium) Search Ariana Grande tracks by leak date/year.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def arileakdate(self, ctx: commands.Context, *, leak_date: str | None = None):
        await self._handle_search(ctx, leak_date, "Leak Date", "Leak Date", True)

    @commands.hybrid_command(name="arifiledate", description="(Premium) Search Ariana Grande tracks by file date/year.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def arifiledate(self, ctx: commands.Context, *, file_date: str | None = None):
        await self._handle_search(ctx, file_date, "File Date", "File Date", True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AriInfo(bot))
