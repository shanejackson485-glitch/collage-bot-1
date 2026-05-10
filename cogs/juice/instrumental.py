import os
import re
import string
import unicodedata
import asyncio
import json
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple

import discord
from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup
import pytz

from .helpers import era_colors, era_images, era_mapping

try:
    from config import (
        INSTRUMENTALS_PATH,
        INSTRUMENTAL_ARCHIVE_CHANNEL_ID,
        INSTRUMENTAL_CACHE_FILE,
        ARCHIVE_CHANNEL_ID,
    )
except Exception:
    INSTRUMENTALS_PATH = r"D:\JBDB\Official Instrumentals"
    INSTRUMENTAL_ARCHIVE_CHANNEL_ID = 1462227287306014935
    INSTRUMENTAL_CACHE_FILE = "data/Caches/instrumental_cache.json"
    ARCHIVE_CHANNEL_ID = 1462227287306014935


BASE_DIR = os.getcwd()

HTML_FILES = [
    os.path.join(BASE_DIR, "JuiceInfoDB", "modified_document.html"),
    os.path.join(BASE_DIR, "JuiceInfoDB", "released.html"),
    os.path.join(BASE_DIR, "JuiceInfoDB", "unsurfaced.html"),
]

SOUP_CACHE = {}
MAX_DROPDOWN_RESULTS = 25

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
MIN_MATCH_SCORE = 40

def _normalize_search_dirs(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [value]
    return []





DEFAULT_SEARCH_DIRS: List[str] = _normalize_search_dirs(INSTRUMENTALS_PATH)


_local_fallback = os.path.join(BASE_DIR, "Instrumentals")
if os.path.isdir(_local_fallback) and _local_fallback not in DEFAULT_SEARCH_DIRS:
    DEFAULT_SEARCH_DIRS.append(_local_fallback)


_official_fallback = os.path.join(BASE_DIR, "Official Instrumentals")
_has_valid_configured_dir = any(os.path.isdir(d) for d in DEFAULT_SEARCH_DIRS if isinstance(d, str) and d)
if (not _has_valid_configured_dir) and os.path.isdir(_official_fallback) and _official_fallback not in DEFAULT_SEARCH_DIRS:
    DEFAULT_SEARCH_DIRS.append(_official_fallback)


def load_html_files():
    global SOUP_CACHE
    if not SOUP_CACHE:
        for html_file in HTML_FILES:
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read()
                SOUP_CACHE[html_file] = BeautifulSoup(content, "html.parser")
            except Exception as e:
                print(f"[CACHE] Failed to cache {html_file}: {e}")
    return SOUP_CACHE


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


def clean_text(text: str, filter_out_words: Optional[List[str]] = None) -> str:
    text = (text or "").replace("\xa0", " ")
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
    if not text:
        return ""
    text = text.replace("\xa0", " ").strip()
    if text.lower() in ["n/a", "-", "none", "", "unknown"]:
        return ""
    return text


def split_alt_titles(alt_titles_raw: str) -> List[str]:
    if not alt_titles_raw:
        return []
    return [t.strip() for t in alt_titles_raw.split("|") if t.strip()]


def split_instrumental_names(inst_raw: str) -> List[str]:
    inst_raw = clean_instrumental_text(inst_raw)
    if not inst_raw:
        return []


    parts: List[str] = []
    for chunk in inst_raw.split("\n"):
        parts.extend([p.strip() for p in chunk.split("|") if p.strip()])
    return [p for p in parts if p]


def _parse_title_and_alts(title_cell: str) -> Tuple[str, List[str]]:
    """JuiceInfoDB puts alt titles in the title cell (after <br>), not a separate column."""
    text = (title_cell or "").replace("\xa0", " ").strip()
    if not text:
        return "", []

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    main = lines[0] if lines else text
    alts: List[str] = []


    for rest in lines[1:]:
        for part in rest.split("|"):
            part = part.strip()
            if part:
                alts.append(part)


    seen = set()
    out: List[str] = []
    for t in alts:
        tn = normalize_text(t)
        if not tn or tn in seen:
            continue
        seen.add(tn)
        out.append(t)
    return main, out


def _extract_inst_tokens(inst_list: List[str]) -> List[str]:
    tokens: List[str] = []
    for raw in inst_list or []:
        if not raw:
            continue


        pieces = [p.strip() for p in str(raw).split(":", 1)]
        if len(pieces) == 2:
            left, right = pieces[0].strip().lower(), pieces[1].strip()
            if left in {"instrumental", "inst", "loop"} and right:
                raw = right


        cleaned = re.sub(r"[\"'()\[\]]", " ", raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue



        if len(cleaned) <= 80 and len(cleaned.split()) >= 2:
            tokens.append(cleaned)



        alpha_numish = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", cleaned)
        numeric_ids = re.findall(r"\b\d{3,4}\b", cleaned)
        candidates = numeric_ids + alpha_numish

        if candidates:

            digit_first = sorted(candidates, key=lambda s: (0 if any(ch.isdigit() for ch in s) else 1))
            tokens.extend(digit_first[:4])
        else:

            if len(cleaned) <= 80:
                tokens.append(cleaned)


    seen = set()
    out: List[str] = []
    for t in tokens:
        tn = normalize_text(t)
        if not tn or tn in seen:
            continue
        seen.add(tn)
        out.append(t)
    return out


def build_instrumental_embed(
    info: dict,
    found_path: Optional[str],
    search_dirs: Optional[List[str]] = None,
    matched_files: Optional[List[str]] = None,
) -> discord.Embed:
    era = info.get("Era", "Unknown Era")
    title = format_title(info.get("Track Title", "Unknown Track"))

    embed = discord.Embed(
        title=f"Instrumental: {title}",
        description=None,
        color=era_colors.get(era, discord.Color.blue().value),
    )

    def add_field(name: str, value: str, inline: bool = False):
        if value and value not in ["N/A", "-", "None", ""]:
            embed.add_field(name=name, value=value, inline=inline)

    add_field("Era", era, inline=True)
    add_field("Produced by", info.get("Producer", ""), inline=True)
    add_field("Engineered by", info.get("Engineer", ""), inline=True)

    inst_list = info.get("Instrumental Names", []) or []
    if inst_list:
        add_field("Instrumental Name(s)", "\n".join(inst_list), inline=False)

    alt_titles = info.get("Alt Titles", []) or []
    if alt_titles:
        add_field("Alternate Titles", "\n".join(alt_titles[:10]), inline=False)


    if matched_files:
        shown = [os.path.basename(p) for p in matched_files if p][:5]
        if shown:
            add_field("Matched File", "\n".join(shown), inline=False)
    elif found_path:
        add_field("Matched File", os.path.basename(found_path), inline=False)

    embed.set_thumbnail(url=era_images.get(era, era_images.get("Posthumous", "")))
    return embed


def _score_filename(candidate_norm: str, file_norm: str) -> int:

    if candidate_norm == file_norm:
        return 100
    if candidate_norm and file_norm.startswith(candidate_norm):
        return 80
    if candidate_norm and candidate_norm in file_norm:

        return 60 - max(0, len(file_norm) - len(candidate_norm))
    return -10


def _iter_audio_files(search_dirs: Iterable[str]):
    for root_dir in search_dirs:
        if not root_dir:
            continue
        if not os.path.isdir(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in AUDIO_EXTS:
                    yield os.path.join(root, name)


def find_best_audio_match(search_dirs: List[str], candidates: List[str]) -> Optional[str]:
    if not candidates:
        return None

    candidate_norms = [normalize_text(c) for c in candidates if c]
    candidate_norms = [c for c in candidate_norms if c]
    if not candidate_norms:
        return None

    best: Tuple[int, Optional[str]] = (-1, None)

    for path in _iter_audio_files(search_dirs):
        stem = os.path.splitext(os.path.basename(path))[0]
        stem_norm = normalize_text(stem)

        for cand in candidate_norms:
            score = _score_filename(cand, stem_norm)

            if score <= 0:
                continue
            if score > best[0]:
                best = (score, path)
                if score >= 100:
                    return path


    return best[1] if best[0] >= MIN_MATCH_SCORE else None


def _stem_token_list(stem: str) -> List[str]:


    s = (stem or "").lower()
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return [p for p in s.split() if p]


def _numeric_token_in_stem(token_digits: str, stem: str) -> bool:
    if not token_digits or not token_digits.isdigit():
        return False
    parts = _stem_token_list(stem)
    return token_digits in parts


def find_best_audio_match_by_tokens(
    search_dirs: List[str],
    tokens: List[str],
    *,
    title: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Strict token-first match.

    Returns (path, matched_token). Only considers files that contain at least one token.
    """
    if not tokens:
        return None, None

    title_norm = normalize_text(title or "")

    token_pairs: List[Tuple[str, str]] = []
    for t in tokens:
        tn = normalize_text(t)
        if tn:
            token_pairs.append((t, tn))

    if not token_pairs:
        return None, None

    best_score = -1
    best_path: Optional[str] = None
    best_token: Optional[str] = None

    for path in _iter_audio_files(search_dirs):
        stem = os.path.splitext(os.path.basename(path))[0]
        stem_norm = normalize_text(stem)
        ext = os.path.splitext(path)[1].lower()

        for raw_tok, tok_norm in token_pairs:
            if tok_norm.isdigit():
                if not _numeric_token_in_stem(tok_norm, stem):
                    continue
            else:
                if tok_norm not in stem_norm:
                    continue


            score = 95


            if title_norm and title_norm in stem_norm:
                score += 12


            if ext == ".wav":
                score += 2


            score -= min(25, abs(len(stem_norm) - len(tok_norm)))

            if score > best_score:
                best_score = score
                best_path = path
                best_token = raw_tok

    return best_path, best_token


def _is_within_dir(path: str, root_dir: str) -> bool:
    try:
        path_abs = os.path.abspath(path)
        root_abs = os.path.abspath(root_dir)
        return os.path.commonpath([path_abs, root_abs]) == root_abs
    except Exception:
        return False


def _instrumental_cache_key(search_dirs: List[str], found_path: str) -> str:
    for root in search_dirs:
        if _is_within_dir(found_path, root):
            rel = os.path.relpath(found_path, root)
            rel = rel.replace("\\", "/")
            return f"instrumental:{rel.lower()}"

    return f"instrumental:{os.path.abspath(found_path).lower()}"


def _get_col(cols, idx: int) -> str:
    if idx >= len(cols):
        return ""
    c = cols[idx]
    for br in c.find_all("br"):
        br.replace_with("||BR||")
    text = c.get_text(strip=True)
    return text.replace("||BR||", "\n")


def search_tracks_by_title(query_term: str) -> List[dict]:
    results: List[dict] = []
    query_norm = normalize_text(query_term)
    soups = load_html_files()

    for html_file, soup in soups.items():
        is_unsurfaced = "unsurfaced" in html_file.lower()

        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue

            min_cols = 13 if is_unsurfaced else 16
            if len(cols) < min_cols:
                continue

            title_cell = _get_col(cols, 2)
            title_main, alt_titles = _parse_title_and_alts(title_cell)
            artist = clean_text(_get_col(cols, 3))

            all_titles = [title_main] + alt_titles
            if not any(query_norm in normalize_text(t) for t in all_titles if t):
                continue

            inst_raw = _get_col(cols, 8)
            inst_names = split_instrumental_names(inst_raw)

            res = {
                "Era": era_mapping.get(clean_text(_get_col(cols, 0)), clean_text(_get_col(cols, 0))),
                "Track Title": title_main,
                "Alt Titles": alt_titles,
                "Artist": artist,
                "Producer": clean_text(_get_col(cols, 4)),
                "Engineer": clean_text(_get_col(cols, 5)),
                "Additional Info": clean_text(_get_col(cols, 6)),
                "File Name": clean_text(_get_col(cols, 7)),
                "Instrumental Names": inst_names,
                "Recording Location": clean_text(_get_col(cols, 9)),
                "Recording Date": clean_text(_get_col(cols, 10), filter_out_words=["Recorded"]),
                "Preview Date": clean_text(_get_col(cols, 11), filter_out_words=["First Previewed"]),
            }

            if is_unsurfaced:
                res.update(
                    {
                        "Surfaced": "Not Surfaced",
                        "Duration": "",
                        "Category": clean_text(_get_col(cols, 12)),
                        "Properties": "",
                    }
                )
            else:
                res.update(
                    {
                        "Surfaced": clean_text(_get_col(cols, 12), filter_out_words=["Surfaced"]),
                        "Duration": clean_text(_get_col(cols, 13)),
                        "Category": clean_text(_get_col(cols, 14)),
                        "Properties": clean_text(_get_col(cols, 15)),
                    }
                )

            results.append(res)

    return results


class JuiceInstrumental(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot




        self.cooldown_file = "data/JuiceWRLD/instrumental_cooldown_data.json"
        self.cooldown_data = self._load_cooldown_data()
        self.EASTERN_TIMEZONE = pytz.timezone("EST")
        self.FREE_DAILY_DOWNLOAD_BYTES = 250 * 1024 * 1024

        self.cache: dict = {}
        self.bot.loop.create_task(self._load_cache())


        self.search_dirs = [
            d
            for d in DEFAULT_SEARCH_DIRS
            if isinstance(d, str)
            and d
            and d not in ("\\", "/")
            and os.path.isdir(d)
        ]


    def _load_cooldown_data(self) -> dict:
        if os.path.exists(self.cooldown_file):
            try:
                with open(self.cooldown_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cooldown_data(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.cooldown_file), exist_ok=True)
            with open(self.cooldown_file, "w", encoding="utf-8") as f:
                json.dump(self.cooldown_data, f, indent=4)
        except Exception:
            pass

    def is_premium_user(self, user_id: int) -> bool:
        for file in ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]:
            try:
                if os.path.exists(file):
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if str(user_id) in (data.get("whitelisted_ids", []) or []):
                        return True
            except Exception:
                continue
        return False

    def _check_and_consume_download_quota(self, user_id: int, bytes_to_add: int) -> bool:
        """Non-premium users have a daily byte quota; premium bypasses.

        Resets at 12:00 AM EST (same approach as the ProTools tracker).
        """
        if self.is_premium_user(user_id):
            return True

        user_id_str = str(user_id)
        if user_id_str not in self.cooldown_data:
            self.cooldown_data[user_id_str] = {"bytes": 0, "last_reset": 0}

        user_data = self.cooldown_data[user_id_str]


        if "bytes" not in user_data:
            user_data["bytes"] = 0

        now_est = datetime.now(self.EASTERN_TIMEZONE)
        today_midnight = now_est.replace(hour=0, minute=0, second=0, microsecond=0)

        if user_data.get("last_reset", 0) < today_midnight.timestamp():
            user_data["bytes"] = 0
            user_data["last_reset"] = today_midnight.timestamp()

        used = int(user_data.get("bytes", 0) or 0)
        add = max(0, int(bytes_to_add or 0))
        limit = int(self.FREE_DAILY_DOWNLOAD_BYTES)

        if used + add <= limit:
            user_data["bytes"] = used + add
            self._save_cooldown_data()
            return True

        next_reset = today_midnight + timedelta(days=1)
        self._save_cooldown_data()
        raise commands.CommandOnCooldown(
            commands.Cooldown(limit, 86400),
            (next_reset - now_est).total_seconds(),
            commands.BucketType.user,
        )

    def _format_bytes(self, num_bytes: int) -> str:
        try:
            b = float(max(0, int(num_bytes)))
        except Exception:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if b < 1024.0:
                return f"{b:.2f} {unit}" if unit != "B" else f"{int(b)} {unit}"
            b /= 1024.0
        return f"{b:.2f} PB"

    def _format_bytes_short(self, num_bytes: int) -> str:
        s = self._format_bytes(num_bytes)

        return s.replace(" ", "")

    def _get_user_used_bytes(self, user_id: int) -> int:
        uid = str(user_id)
        user_data = self.cooldown_data.get(uid)
        if not isinstance(user_data, dict):
            return 0
        try:
            return int(user_data.get("bytes", 0) or 0)
        except Exception:
            return 0

    def _ensure_daily_reset_no_consume(self, user_id: int) -> None:
        """Ensure the quota bucket is reset for the current EST day (without consuming bytes)."""
        if self.is_premium_user(user_id):
            return

        uid = str(user_id)
        if uid not in self.cooldown_data or not isinstance(self.cooldown_data.get(uid), dict):
            self.cooldown_data[uid] = {"bytes": 0, "last_reset": 0}

        user_data = self.cooldown_data[uid]
        if "bytes" not in user_data:
            user_data["bytes"] = 0

        now_est = datetime.now(self.EASTERN_TIMEZONE)
        today_midnight = now_est.replace(hour=0, minute=0, second=0, microsecond=0)

        if user_data.get("last_reset", 0) < today_midnight.timestamp():
            user_data["bytes"] = 0
            user_data["last_reset"] = today_midnight.timestamp()
            self._save_cooldown_data()

    def _resolve_audio_variants(self, found_path: str) -> dict:
        """Return available sibling variants for the matched file (currently MP3/WAV)."""
        if not found_path:
            return {}
        folder = os.path.dirname(found_path)
        stem = os.path.splitext(os.path.basename(found_path))[0]

        out = {}
        mp3 = os.path.join(folder, f"{stem}.mp3")
        wav = os.path.join(folder, f"{stem}.wav")
        if os.path.isfile(mp3):
            out["mp3"] = mp3
        if os.path.isfile(wav):
            out["wav"] = wav
        return out

    async def _load_cache(self):
        try:
            if os.path.exists(INSTRUMENTAL_CACHE_FILE):
                with open(INSTRUMENTAL_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
        except Exception:
            self.cache = {}

    async def _save_cache(self):
        def write():
            os.makedirs(os.path.dirname(INSTRUMENTAL_CACHE_FILE), exist_ok=True)
            with open(INSTRUMENTAL_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)

        await self.bot.loop.run_in_executor(None, write)

    async def send_message(self, ctx_or_int, *args, **kwargs):
        if isinstance(ctx_or_int, discord.Interaction):
            if ctx_or_int.response.is_done():
                return await ctx_or_int.followup.send(*args, **kwargs)
            return await ctx_or_int.response.send_message(*args, **kwargs)
        return await ctx_or_int.send(*args, **kwargs)

    class DownloadView(discord.ui.View):
        def __init__(
            self,
            cog,
            mp3_path: Optional[str],
            wav_path: Optional[str],
            mp3_cache_key: Optional[str],
            wav_cache_key: Optional[str],
            user: discord.abc.User,
        ):
            super().__init__(timeout=None)
            self.cog = cog
            self.mp3_path = mp3_path
            self.wav_path = wav_path
            self.mp3_cache_key = mp3_cache_key
            self.wav_cache_key = wav_cache_key
            self.user = user
            self.is_premium = self.cog.is_premium_user(getattr(user, "id", 0))

            def safe_size(path: Optional[str]) -> int:
                if not path:
                    return 0
                try:
                    return int(os.path.getsize(path))
                except Exception:
                    return 0

            self.mp3_size = safe_size(self.mp3_path)
            self.wav_size = safe_size(self.wav_path)

            self.add_item(self.MP3Button(self))
            self.add_item(self.WAVButton(self))
            self.add_item(self.DismissButton(self))

        async def _upload_and_get_url(self, archive_channel: discord.abc.Messageable, file_path: str, cache_key: str) -> Optional[str]:
            fresh_url = None
            cached_id = self.cog.cache.get(cache_key)
            if cached_id:
                try:
                    msg = await archive_channel.fetch_message(int(cached_id))
                    if msg.attachments:
                        fresh_url = msg.attachments[0].url
                except Exception:
                    fresh_url = None

            if fresh_url:
                return fresh_url

            try:
                f = discord.File(file_path, filename=os.path.basename(file_path))
                m = await archive_channel.send(content=f"Instrumental Archive: {cache_key}", file=f)
                if m.attachments:
                    fresh_url = m.attachments[0].url
                    self.cog.cache[cache_key] = m.id
                    await self.cog._save_cache()
            except Exception:
                return None

            return fresh_url

        async def _handle_download(self, interaction: discord.Interaction, file_path: str, cache_key: str, *, kind: str):
            if interaction.user.id != getattr(self.user, "id", None):
                return await interaction.response.send_message("This isn't your search.", ephemeral=True)


            if kind == "mp3":
                try:
                    file_size = os.path.getsize(file_path)
                except Exception:
                    file_size = 0
                try:
                    self.cog._check_and_consume_download_quota(interaction.user.id, file_size)
                except commands.CommandOnCooldown as e:
                    time_left = str(timedelta(seconds=int(e.retry_after)))
                    uid = str(interaction.user.id)
                    used_bytes = int(self.cog.cooldown_data.get(uid, {}).get("bytes", 0) or 0)
                    remaining = max(0, int(self.cog.FREE_DAILY_DOWNLOAD_BYTES) - used_bytes)
                    return await interaction.response.send_message(
                        "⭐ Free instrumental quota reached (250MB/day). "
                        f"Remaining today: `{self.cog._format_bytes(remaining)}`. Resets in: `{time_left}`.\n"
                        f"This file is `{self.cog._format_bytes(file_size)}`. Visit [Our Website](https://collagebot.info/premium) to purchase premium access for unlimited searches.",
                        ephemeral=True,
                    )


            if kind == "wav" and not self.is_premium:
                return await interaction.response.send_message(
                    "⭐ WAV downloads are a Premium feature. Use `@collage premium` to unlock.",
                    ephemeral=True,
                )

            await interaction.response.defer(ephemeral=True, thinking=True)

            archive_id = INSTRUMENTAL_ARCHIVE_CHANNEL_ID or ARCHIVE_CHANNEL_ID
            archive_channel = self.cog.bot.get_channel(archive_id) if archive_id else None
            if not archive_channel:
                return await interaction.followup.send("Archive channel not found/configured.", ephemeral=True)

            fresh_url = await self._upload_and_get_url(archive_channel, file_path, cache_key)
            if not fresh_url:
                return await interaction.followup.send("Upload failed: no attachment URL returned.", ephemeral=True)

            await interaction.followup.send(
                content=f"Click the link below for **{os.path.basename(file_path)}**:\n{fresh_url}",
                ephemeral=True,
            )

        class MP3Button(discord.ui.Button):
            def __init__(self, parent_view: "JuiceInstrumental.DownloadView"):
                self.parent_view = parent_view
                disabled = not bool(parent_view.mp3_path and parent_view.mp3_cache_key)
                if disabled:
                    label = "MP3 Not Available"
                else:
                    size_str = parent_view.cog._format_bytes_short(parent_view.mp3_size)
                    label = f"Download MP3 ({size_str})"
                super().__init__(label=label, style=discord.ButtonStyle.success, disabled=disabled)

            async def callback(self, interaction: discord.Interaction):
                v = self.parent_view
                if not v.mp3_path or not v.mp3_cache_key:
                    return await interaction.response.send_message("MP3 version not available.", ephemeral=True)
                await v._handle_download(interaction, v.mp3_path, v.mp3_cache_key, kind="mp3")

        class WAVButton(discord.ui.Button):
            def __init__(self, parent_view: "JuiceInstrumental.DownloadView"):
                self.parent_view = parent_view
                has_wav = bool(parent_view.wav_path and parent_view.wav_cache_key)
                disabled = (not has_wav) or (has_wav and not parent_view.is_premium)
                if not has_wav:
                    label = "WAV Not Available"
                else:
                    size_str = parent_view.cog._format_bytes_short(parent_view.wav_size)
                    label = f"WAV ({size_str}) Premium" if not parent_view.is_premium else f"Download WAV ({size_str})"
                super().__init__(label=label, style=discord.ButtonStyle.primary, disabled=disabled)

            async def callback(self, interaction: discord.Interaction):
                v = self.parent_view
                if not v.wav_path or not v.wav_cache_key:
                    return await interaction.response.send_message("WAV version not available.", ephemeral=True)
                await v._handle_download(interaction, v.wav_path, v.wav_cache_key, kind="wav")

        class DismissButton(discord.ui.Button):
            def __init__(self, parent_view: "JuiceInstrumental.DownloadView"):
                self.parent_view = parent_view
                super().__init__(label="Dismiss", style=discord.ButtonStyle.danger)

            async def callback(self, interaction: discord.Interaction):
                v = self.parent_view
                if interaction.user.id != getattr(v.user, "id", None) and not getattr(interaction.user, "guild_permissions", None):
                    return await interaction.response.send_message("You cannot dismiss this message.", ephemeral=True)
                try:
                    await interaction.message.delete()
                except Exception:
                    pass

    async def _find_file_for_track(self, track_info: dict) -> Optional[str]:




        title = (track_info.get("Track Title") or "").strip()
        inst_list = track_info.get("Instrumental Names", []) or []

        stop_tokens = {
            "juice",
            "wrld",
            "juicewrld",
            "instrumental",
            "instrumentals",
            "midi",
            "beat",
            "pack",
            "loop",
            "bpm",
            "prod",
            "producer",
            "produced",
            "demo",
            "inst",
            "stems",
            "stem",
            "trackout",
            "trackouts",
            "session",
            "sessions",
            "wav",
            "mp3",
        }

        def is_good_token(token: str) -> bool:
            t = (token or "").strip()
            if not t:
                return False
            tn = normalize_text(t)
            if not tn:
                return False
            if tn in stop_tokens:
                return False




            parts = re.findall(r"[a-z0-9]+", t.lower())
            if parts:
                if len(parts) == 1:
                    p = parts[0]
                    if p == "bpm" or re.fullmatch(r"bpm\d{2,4}", p) or re.fullmatch(r"\d{2,4}bpm", p):
                        return False
                if any("bpm" in p for p in parts):
                    meaningful = [
                        p
                        for p in parts
                        if p not in stop_tokens
                        and not (p == "bpm" or re.fullmatch(r"bpm\d{2,4}", p) or re.fullmatch(r"\d{2,4}bpm", p))
                    ]
                    if not meaningful:
                        return False

            if tn.isdigit():
                return len(tn) >= 3

            if any(ch.isdigit() for ch in t):
                return True

            if len(t.split()) >= 2:
                return len(tn) >= 6
            return len(tn) >= 7

        if not self.search_dirs:
            return None


        inst_tokens = [t for t in _extract_inst_tokens(inst_list) if is_good_token(t)]
        if inst_tokens:
            token_path, _matched_token = await asyncio.to_thread(
                find_best_audio_match_by_tokens,
                self.search_dirs,
                inst_tokens,
                title=title,
            )
            if token_path:
                return token_path


        candidates: List[str] = []
        if title:
            candidates.append(title)


            base_title = re.sub(r"(?i)\s*[\[(]\s*v\d+\s*[\])]", "", title).strip()
            if base_title and normalize_text(base_title) != normalize_text(title):
                candidates.append(base_title)


        fn = (track_info.get("File Name") or "").strip()
        if fn:
            for chunk in fn.split("\n"):
                chunk = chunk.strip()
                if chunk and normalize_text(chunk) != normalize_text(title):

                    if is_good_token(chunk) or (title and normalize_text(title) in normalize_text(chunk)):
                        candidates.append(chunk)

        return await asyncio.to_thread(find_best_audio_match, self.search_dirs, candidates)

    async def _send_instrumental(self, ctx_or_int, track_info: dict):
        found_path = await self._find_file_for_track(track_info)


        if found_path and self.search_dirs:
            if not any(_is_within_dir(found_path, d) for d in self.search_dirs):
                found_path = None

        missing_inst = not bool(track_info.get("Instrumental Names"))

        if not self.search_dirs:
            embed = build_instrumental_embed(track_info, None, search_dirs=self.search_dirs)
            return await self.send_message(
                ctx_or_int,
                embed=embed,
                content="❌ No instrumental search folder is configured. Set `INSTRUMENTALS_PATH` in config.py (or create an `Instrumentals` folder in the bot directory).",
            )

        if not found_path or not os.path.isfile(found_path):
            embed = build_instrumental_embed(track_info, None, search_dirs=self.search_dirs)
            return await self.send_message(
                ctx_or_int,
                embed=embed,
                content="❌ Couldn’t find a matching audio file in the instrumental folders.",
            )

        variants = self._resolve_audio_variants(found_path)
        mp3_path = variants.get("mp3")
        wav_path = variants.get("wav")



        ext = os.path.splitext(found_path)[1].lower()
        if not mp3_path and ext == ".mp3":
            mp3_path = found_path
        if not wav_path and ext == ".wav":
            wav_path = found_path


        user = ctx_or_int.user if isinstance(ctx_or_int, discord.Interaction) else ctx_or_int.author
        self._ensure_daily_reset_no_consume(getattr(user, "id", 0))

        mp3_cache_key = _instrumental_cache_key(self.search_dirs, mp3_path) if mp3_path else None
        wav_cache_key = _instrumental_cache_key(self.search_dirs, wav_path) if wav_path else None
        view = self.DownloadView(self, mp3_path, wav_path, mp3_cache_key, wav_cache_key, user)
        matched_files = [p for p in [mp3_path, wav_path] if p]
        embed = build_instrumental_embed(track_info, found_path, search_dirs=self.search_dirs, matched_files=matched_files)


        uid = getattr(user, "id", 0)
        if self.is_premium_user(uid):
            embed.set_footer(text="Premium: Unlimited downloads")
        else:
            used = self._get_user_used_bytes(uid)
            remaining = max(0, int(self.FREE_DAILY_DOWNLOAD_BYTES) - int(used))
            embed.set_footer(text=f"Free quota remaining today: {self._format_bytes(remaining)} / {self._format_bytes(self.FREE_DAILY_DOWNLOAD_BYTES)}")

        content = None
        if missing_inst:
            content = "⚠️ JuiceInfoDB has no instrumental listed for this track; using a title-based file search."

        await self.send_message(ctx_or_int, content=content, embed=embed, view=view)

    class TrackDropdown(discord.ui.Select):
        def __init__(self, results_page):
            self.results = results_page
            options = [
                discord.SelectOption(
                    label=f"{track['index']}. {track['Track Title']} ({track['Era']})"[:100],
                    value=str(track["absolute_index"]),
                )
                for track in self.results
            ]
            super().__init__(placeholder="Select a track to fetch instrumental", options=options)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            info = self.view.full_results[int(self.values[0])]
            await self.view.parent_cog._send_instrumental(interaction, info)

    class PaginationDropdown(discord.ui.Select):
        def __init__(self, num_pages, current_page):
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

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            await self.view.update_view_page(int(self.values[0]), interaction)

    class PaginatedSearchView(discord.ui.View):
        def __init__(self, full_results, parent_cog):
            super().__init__(timeout=180)
            self.parent_cog = parent_cog


            self.full_results = full_results[:625]

            for i, r in enumerate(self.full_results):
                r["absolute_index"] = i
                r["index"] = i + 1

            self.num_pages = (len(self.full_results) + MAX_DROPDOWN_RESULTS - 1) // MAX_DROPDOWN_RESULTS
            self.current_page = 0
            self._update_dropdowns()

        def _update_dropdowns(self):
            for item in list(self.children):
                if isinstance(item, (JuiceInstrumental.TrackDropdown, JuiceInstrumental.PaginationDropdown)):
                    self.remove_item(item)

            start = self.current_page * MAX_DROPDOWN_RESULTS
            new_children = []

            if self.num_pages > 1:
                new_children.append(JuiceInstrumental.PaginationDropdown(self.num_pages, self.current_page))

            page_results = self.full_results[start : start + MAX_DROPDOWN_RESULTS]
            new_children.append(JuiceInstrumental.TrackDropdown(page_results))

            for item in reversed(new_children):
                self.add_item(item)

        async def update_view_page(self, new_idx: int, interaction: discord.Interaction):
            self.current_page = new_idx
            self._update_dropdowns()
            await interaction.edit_original_response(view=self)

    @commands.hybrid_command(
        name="instrumental",
        description="Fetch the instrumental for a Juice WRLD track (uses JuiceInfoDB instrumental field).",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.describe(track_title="Track title to search (alt titles supported)")
    async def instrumental(self, ctx: commands.Context, *, track_title: str = None):
        if ctx.interaction:
            await ctx.defer()

        if not track_title:
            return await ctx.send("❌ Missing Track Name.")

        results = search_tracks_by_title(track_title)
        if not results:
            return await ctx.send(f":x: No Tracks Found for **{track_title}**.")

        if len(results) == 1:
            await self._send_instrumental(ctx, results[0])
            return

        view = self.PaginatedSearchView(results, self)
        await ctx.send(content="Multiple tracks found. Select one to fetch the instrumental:", view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(JuiceInstrumental(bot))
