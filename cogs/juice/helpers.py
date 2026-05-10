import os
import re
import discord
import json
import asyncio
import io
import random
import time
import unicodedata
import string
import threading
from discord.ext import commands, tasks
from discord.ui import Select, View, Button
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from bs4 import BeautifulSoup
from config import *

STATS_FILE = "data/Developer/download_stats.json"






ERA_COLORS = {
    "Death Race For Love (Sessions)": 0xb83d11,
    "Goodbye & Good Riddance Era": 0x3498db,
    "WRLD ON DRUGS Era": 0x0721ca,
    "The Outsiders (JW3) Era": 0x161213,
    "Affliction Era": 0x000000,
    "BINGEDRINKINGMUSIC Era": 0x000000,
    "NOTHINGS DIFFERENT </3": 0xcc5437,
    "Juice WRLD 999": 0x1b0706,
    "HEARTBROKEN IN HOLLYWOOD 999": 0x471422,
    "Posthumous": 0x131313,
    "JUICED UP THE EP": 0x578dcf
}


SESSION_ERA_COLORS = {
    "Death Race For Love (Session Edits)": 0xb83d11,
    "Goodbye & Good Riddance (Session Edits)": 0x3498db,
    "WRLD On Drugs (Session Edits)": 0x0721ca,
    "The Outsiders (JW3) [Session Edits]": 0x161213,
    "Affliction (Session Edits)": 0x000000,
    "BINGEDRINKINGMUSIC (Session Edits)": 0x000000,
    "NOTHING'S DIFFERENT </3 (Session Edits)": 0xcc5437,
    "JuiceWRLD 9 9 9 (Session Edits)": 0x1b0706,
    "Heartbroken In Hollywood 9 9 9 (Session Edits)": 0x471422,
    "Posthumous (Session Edits)": 0x131313,
    "JUICED UP THE EP (Session Edits)": 0x578dcf,
}






era_mapping = {
    "AFF": "Affliction",
    "BDM": "BINGEDRINKINGMUSIC",
    "DRFL": "Death Race For Love",
    "GB&GR": "Goodbye & Good Riddance",
    "HIH 9 9 9": "HEARTBROKEN IN HOLLYWOOD 999",
    "JW 9 9 9": "Juice WRLD 999",
    "ND </3": "NOTHINGS DIFFERENT </3",
    "OUT": "Outsiders",
    "POST": "Posthumous",
    "WOD": "WRLD On Drugs",
    "JUTE": "JUICED UP THE EP",
    "TS...": "Too Soon...",
    "GB&GR (AE)": "Goodbye & Good Riddance (Anniversary Edition)",
    "GB&GR (5YAE)": "Goodbye & Good Riddance (5 Year Anniversary Edition)",
    "DRFL (BTV)": "Death Race For Love (Bonus Track Version)",
    "LND": "Legends Never Die",
    "LND (5YAE)": "Legends Never Die (5 Year Anniversary Edition)",
    "FD": "Fighting Demons",
    "FD (CE)": "Fighting Demons (Complete Edition)",
    "FD (EE)": "Fighting Demons (Extended Edition)",
    "FD (DDE)": "Fighting Demons (Digital Deluxe Edition)",
    "TPP": "The Pre-Party",
    "TPP (EE)": "The Pre-Party (Extended Edition)",
    "TPNE": "The Party Never Ends",
    "TPNE (DDE)": "The Party Never Ends (Digital Deluxe Edition)",
    "Smule": "Smule",
    "You Tube": "YouTube",
    "Sound Cloud": "SoundCloud",
    "Mainstream": "Mainstream"
}

era_images = {
    "Affliction": r"https://i.ibb.co/Dg78D9SL/affliction2.jpg",
    "BINGEDRINKINGMUSIC": r"https://i.ibb.co/HLXqCLg9/BINGEDRINKINGMUSIC.jpg",
    "Death Race For Love": r"https://i.ibb.co/20cC9BTC/deathraceforlove.png",
    "Goodbye & Good Riddance": r"https://i.ibb.co/Nds1hHVW/goodbyegoodriddance.jpg",
    "HEARTBROKEN IN HOLLYWOOD 999": r"https://i.ibb.co/wNyGCZB7/heartbrokeninhollywood2.jpg",
    "Juice WRLD 999": r"https://i.ibb.co/spskD3Qj/999.jpg",
    "NOTHINGS DIFFERENT </3": r"https://i.ibb.co/YBFQJX8s/nothingsdifferent.jpg",
    "Outsiders": r"https://i.ibb.co/93hFgB16/jw3-cover.jpg",
    "Posthumous": r"https://i.ibb.co/QF7dCqWY/posthumous.webp",
    "WRLD On Drugs": r"https://i.ibb.co/gbzZsCPN/wod.jpg",
    "JUICED UP THE EP": r"https://i.ibb.co/20bWyHmg/juiceduptheep.jpg",
    "Too Soon...": r"https://i.ibb.co/jFBwxzG/toosoon.jpg",
    "Goodbye & Good Riddance (Anniversary Edition)": r"https://i.ibb.co/Nds1hHVW/goodbyegoodriddance.jpg",
    "Goodbye & Good Riddance (5 Year Anniversary Edition)": r"https://i.ibb.co/R4dfmXpK/gbgr5yae.jpg",
    "Death Race For Love (Bonus Track Version)": r"https://i.ibb.co/20cC9BTC/deathraceforlove.png",
    "Legends Never Die": r"https://i.ibb.co/0RshTjyN/lnd.jpg",
    "Legends Never Die (5 Year Anniversary Edition)": r"https://i.ibb.co/YFMGLKXd/lnd5yae.jpg",
    "Fighting Demons": r"https://i.ibb.co/qF05xQmH/fighting-demons.jpg",
    "Fighting Demons (Complete Edition)": r"https://i.ibb.co/qF05xQmH/fighting-demons.jpg",
    "Fighting Demons (Extended Edition)": r"https://i.ibb.co/qF05xQmH/fighting-demons.jpg",
    "Fighting Demons (Digital Deluxe Edition)": r"https://i.ibb.co/qF05xQmH/fighting-demons.jpg",
    "The Pre-Party": r"https://i.ibb.co/LhQntXLs/thepreparty.jpg",
    "The Pre-Party (Extended Edition)": r"https://i.ibb.co/LhQntXLs/thepreparty.jpg",
    "The Party Never Ends": r"https://i.ibb.co/vvDzkFmR/tpne.jpg",
    "The Party Never Ends (Digital Deluxe Edition)": r"https://i.ibb.co/vvDzkFmR/tpne.jpg",
    "Mainstream": r"https://i.ibb.co/NgrZTDq0/mainstream.jpg",
    "YouTube": r"https://i.ibb.co/RpW6d74j/youtube-play-button-28308.png",
    "SoundCloud": r"https://i.ibb.co/svjsMZFx/soundcloud-logopng-28204.png"
}

era_colors = {
    "Death Race For Love": 0xb83d11,
    "Death Race For Love (Bonus Track Version)": 0xb83d11,
    "Goodbye & Good Riddance": discord.Color.blue().value,
    "Goodbye & Good Riddance (Anniversary Edition)": discord.Color.blue().value,
    "Goodbye & Good Riddance (5 Year Anniversary Edition)": 0x3b59a7,
    "WRLD On Drugs": 0x1931c1,
    "Outsiders": 0x161213,
    "Affliction": 0x000000,
    "BINGEDRINKINGMUSIC": 0x000000,
    "NOTHINGS DIFFERENT </3": 0xcc5437,
    "Juice WRLD 999": 0x1b0706,
    "HEARTBROKEN IN HOLLYWOOD 999": 0x471422,
    "Posthumous": 0x131313,
    "JUICED UP THE EP": 0x578dcf,
    "Too Soon...": 0xf3f3f3,
    "Legends Never Die": 0x0f0f0f,
    "Legends Never Die (5 Year Anniversary Edition)": 0x222222,
    "Fighting Demons": 0x1e2832,
    "Fighting Demons (Complete Edition)": 0x1e2832,
    "Fighting Demons (Extended Edition)": 0x1e2832,
    "Fighting Demons (Digital Deluxe Edition)": 0x1e2832,
    "The Pre-Party": discord.Color.blue().value,
    "The Pre-Party (Extended Edition)": discord.Color.blue().value,
    "The Party Never Ends": 0x63267d,
    "The Party Never Ends (Digital Deluxe Edition)": 0x63267d,
    "Mainstream": 0x4f4c51,
    "YouTube": 0xc42421,
    "SoundCloud": 0xff3b00
}






_JUICEINFO_LOCK = threading.Lock()
_JUICEINFO_INDEX = None
_JUICEINFO_INSTRUMENTAL_MAP = None


def _juiceinfo_normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
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


def _juiceinfo_clean_text(text: str, filter_out_words=None) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ").strip()
    if filter_out_words:
        for word in filter_out_words:
            text = re.sub(re.escape(word), "", text, flags=re.IGNORECASE).strip()
    return text.strip()


def _juiceinfo_clean_instrumental_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ").strip()
    if text.lower() in ["n/a", "-", "none", "", "unknown"]:
        return ""
    return text


def _juiceinfo_parse_instrumental_names(text: str) -> list[str]:
    """Extract only the actual instrumental name(s) from the tracker cell.

    The JuiceInfoDB instrumental column often includes multiple labeled lines like:
      Instrumental: ...
      Loop: ...
      Loop Kit: ...
      Beat Pack: ...

    We ONLY treat the 'Instrumental:' value as the instrumental key to avoid
    broad matches on shared loop kits / beat packs.
    """
    cleaned = _juiceinfo_clean_instrumental_text(text)
    if not cleaned:
        return []

    names = []
    for line in cleaned.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(?i)^instrumental\s*:\s*(.+)$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if val:
            names.append(val)


    if not names:
        return []


    seen = set()
    uniq = []
    for n in names:
        key = _juiceinfo_normalize_text(n)
        if key and key not in seen:
            seen.add(key)
            uniq.append(n)
    return uniq


def _juiceinfo_get_col_text(cols, idx: int) -> str:
    if idx >= len(cols):
        return ""
    c = cols[idx]
    try:
        for br in c.find_all("br"):
            br.replace_with("||BR||")
        text = c.get_text(strip=True) if hasattr(c, "get_text") else str(c).strip()
        return text.replace("||BR||", "\n")
    except Exception:
        try:
            return str(c).strip()
        except Exception:
            return ""


def _juiceinfo_split_alt_titles(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\||\n", text) if p and p.strip()]
    return parts


def _juiceinfo_title_variants(title: str) -> list[str]:
    """Generate reasonable lookup variants for a JuiceInfoDB track title.

    This helps match local names like "Tonight [v2]" to DB rows like
    "Tonight (feat. Valee) [v2]" and "Rental" to "Rental (v1)".
    """
    if not title:
        return []
    t = title.strip()

    variants = [t]


    variants.append(re.sub(r"\*+\s*$", "", t).strip())


    variants.append(re.sub(r"(?i)\s*\(\s*(feat|ft|featuring)\.?[^)]*\)", "", t).strip())
    variants.append(re.sub(r"(?i)\s+(feat|ft|featuring)\.?\s+.*$", "", t).strip())


    variants.append(re.sub(r"(?i)\s*[\[(]\s*v\d+\s*[\])]", "", t).strip())
    variants.append(re.sub(r"(?i)\s*[\[(]\s*(og|original|demo|alt|alternate|remaster|mix)\s*[\])]", "", t).strip())


    variants.append(re.sub(r"\s*[\[(][^\]\)]*[\])]", "", t).strip())


    seen = set()
    out = []
    for v in variants:
        v = v.strip()
        if not v:
            continue
        key = _juiceinfo_normalize_text(v)
        if key and key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _build_juiceinfo_index_and_instrumentals():
    """Build lookup structures from JuiceInfoDB html files.

    Returns (index, instrumental_map)
    - index: normalized title/file-name -> record dict
    - instrumental_map: normalized instrumental -> set of Track Titles
    """
    base_dir = os.getcwd()
    html_files = [
        os.path.join(base_dir, "JuiceInfoDB", "New", "released.html"),
        os.path.join(base_dir, "JuiceInfoDB", "New", "unreleased.html"),
        os.path.join(base_dir, "JuiceInfoDB", "New", "unsurfaced.html"),
    ]

    index = {}
    instrumental_map = {}

    for html_file in html_files:
        if not os.path.exists(html_file):
            continue
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
            soup = BeautifulSoup(content, "html.parser")
        except Exception:
            continue

        is_unsurfaced = "unsurfaced" in html_file.lower()
        min_cols = 13 if is_unsurfaced else 16

        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if not cols or len(cols) < min_cols:
                continue

            era_raw = _juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 0))
            era = era_mapping.get(era_raw, era_raw)

            title_cell = _juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 2))
            title_lines = [l.strip() for l in title_cell.splitlines() if l.strip()]
            main_title = title_lines[0] if title_lines else title_cell



            cell_alt_titles = []
            for l in (title_lines[1:] if len(title_lines) > 1 else []):
                cell_alt_titles.extend(_juiceinfo_split_alt_titles(l))
            alt_titles = []
            for t in cell_alt_titles:
                if t and t not in alt_titles:
                    alt_titles.append(t)

            instrumental_raw = _juiceinfo_get_col_text(cols, 8)
            instrumental_names = _juiceinfo_parse_instrumental_names(instrumental_raw)
            instrumental_keys = [_juiceinfo_normalize_text(n) for n in instrumental_names if _juiceinfo_normalize_text(n)]

            producer = " ".join(_juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 4)).split())
            engineer = " ".join(_juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 5)).split())
            preview_date = _juiceinfo_clean_text(
                _juiceinfo_get_col_text(cols, 11),
                filter_out_words=["First Previewed"],
            )

            if is_unsurfaced:
                surfaced = "Not Surfaced"
            else:
                surfaced = " ".join(_juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 12)).split())

            file_name_field = _juiceinfo_clean_text(_juiceinfo_get_col_text(cols, 7))

            rec = {
                "Era": era,
                "Track Title": main_title,
                "Alt Titles": alt_titles,
                "Producer": producer,
                "Engineer": engineer,
                "Preview Date": preview_date,
                "Surfaced": surfaced,
                "File Name": file_name_field,
                "Instrumental Names": instrumental_names,
                "Instrumental Keys": instrumental_keys,
            }


            for ik in instrumental_keys:
                if not ik:
                    continue
                if ik not in instrumental_map:
                    instrumental_map[ik] = set()
                if main_title:
                    instrumental_map[ik].add(main_title)


            for t in [main_title] + alt_titles:
                for v in _juiceinfo_title_variants(t):
                    key = _juiceinfo_normalize_text(v)
                    if not key:
                        continue
                    index.setdefault(key, []).append(rec)


            for fn in re.split(r"[\n,]", file_name_field or ""):
                fn = fn.strip()
                if not fn:
                    continue
                for v in _juiceinfo_title_variants(fn):
                    key = _juiceinfo_normalize_text(v)
                    if not key:
                        continue
                    index.setdefault(key, []).append(rec)

    return index, instrumental_map


def _ensure_juiceinfo_loaded():
    global _JUICEINFO_INDEX, _JUICEINFO_INSTRUMENTAL_MAP

    def _index_needs_rebuild(idx) -> bool:


        if idx is None:
            return True
        if not isinstance(idx, dict):
            return True
        for v in idx.values():
            if isinstance(v, list):
                return False
            if isinstance(v, dict):
                return True

        return False

    if (_JUICEINFO_INDEX is not None and _JUICEINFO_INSTRUMENTAL_MAP is not None
            and not _index_needs_rebuild(_JUICEINFO_INDEX)):
        return
    with _JUICEINFO_LOCK:
        if (_JUICEINFO_INDEX is None
                or _JUICEINFO_INSTRUMENTAL_MAP is None
                or _index_needs_rebuild(_JUICEINFO_INDEX)):
            idx, inst_map = _build_juiceinfo_index_and_instrumentals()
            _JUICEINFO_INDEX = idx
            _JUICEINFO_INSTRUMENTAL_MAP = inst_map


def get_juiceinfo_track(
    main_title: str = None,
    aliases: str = None,
    file_name: str = None,
    folder_name: str = None,
    preferred_era: str = None,
):
    """Best-effort lookup of a JuiceInfoDB record for a local leak/snippet.

    Returns a dict with keys like: Era, Producer, Engineer, Preview Date, Surfaced.
    """
    _ensure_juiceinfo_loaded()

    candidates = []
    if main_title:
        candidates.append(main_title)
    if aliases:
        for a in aliases.split("|"):
            a = a.strip()
            if a:
                candidates.append(a)
    if folder_name:
        candidates.append(folder_name)
    if file_name:
        candidates.append(os.path.splitext(os.path.basename(file_name))[0])
        candidates.append(os.path.basename(file_name))


    expanded_candidates = []
    for c in candidates:
        expanded_candidates.append(c)
        expanded_candidates.extend(_juiceinfo_title_variants(c))


    unique_candidates = {}
    for c in expanded_candidates:
        key = _juiceinfo_normalize_text(c)
        if not key:
            continue
        existing = unique_candidates.get(key)
        if existing is None or len(str(c)) > len(str(existing)):
            unique_candidates[key] = c

    def score_record(rec: dict, cand: str) -> int:
        cand_key = _juiceinfo_normalize_text(cand)
        if not cand_key:
            return 0

        title = rec.get("Track Title") or ""
        title_key = _juiceinfo_normalize_text(title)
        title_variant_keys = {_juiceinfo_normalize_text(v) for v in _juiceinfo_title_variants(title)}
        alt_variant_keys = set()
        for a in (rec.get("Alt Titles") or []):
            for v in _juiceinfo_title_variants(a):
                alt_variant_keys.add(_juiceinfo_normalize_text(v))

        file_field = rec.get("File Name") or ""
        file_keys = set()
        for fn in re.split(r"[\n,]", file_field):
            fn = fn.strip()
            if fn:
                for v in _juiceinfo_title_variants(fn):
                    file_keys.add(_juiceinfo_normalize_text(v))


        if cand_key == title_key:
            return 100
        if cand_key in title_variant_keys:
            return 98
        if cand_key in alt_variant_keys:
            return 95
        if cand_key in file_keys:
            return 90


        if cand_key and title_key and cand_key in title_key:
            return 70
        if cand_key and title_key and title_key in cand_key:
            return 60


        surfaced = (rec.get("Surfaced") or "").lower()
        if surfaced and "not surfaced" not in surfaced:
            return 10
        return 0

    def score_era(rec: dict) -> int:
        if not preferred_era:
            return 0
        rec_era = (rec.get("Era") or "").strip()
        if not rec_era:
            return 0
        pref = str(preferred_era).strip()
        if not pref:
            return 0

        rec_key = _juiceinfo_normalize_text(rec_era)
        pref_key = _juiceinfo_normalize_text(pref)
        if not rec_key or not pref_key:
            return 0
        if rec_key == pref_key:
            return 50
        if pref_key in rec_key or rec_key in pref_key:
            return 35
        return 0


    scored = {}
    for key, cand in unique_candidates.items():
        recs = _JUICEINFO_INDEX.get(key)
        if not recs:
            continue
        for rec in recs:
            rid = id(rec)
            if rid not in scored:
                scored[rid] = {
                    "rec": rec,
                    "total": 0,
                    "best": 0,
                    "hits": 0,
                }
            s = score_record(rec, cand)
            if s > 0:
                scored[rid]["hits"] += 1
            scored[rid]["total"] += s
            scored[rid]["best"] = max(scored[rid]["best"], s)

    if not scored:
        return None


    if preferred_era:
        for entry in scored.values():
            entry["total"] += score_era(entry["rec"])

    best_entry = max(scored.values(), key=lambda x: (x["total"], x["hits"], x["best"]))


    if best_entry["best"] < 70:
        return None
    return best_entry["rec"]


def get_juiceinfo_shared_instrumental_titles(db_info: dict, exclude_title: str = None) -> list[str]:
    """Given a JuiceInfoDB record, return other Track Titles sharing any instrumental.

    - Excludes the same track title (and optionally an explicit exclude_title).
    - Returns unique, sorted titles.
    """
    if not db_info:
        return []

    _ensure_juiceinfo_loaded()
    if not _JUICEINFO_INSTRUMENTAL_MAP:
        return []

    base_title = db_info.get("Track Title") or ""
    exclude_norms = { _juiceinfo_normalize_text(base_title) }
    if exclude_title:
        exclude_norms.add(_juiceinfo_normalize_text(exclude_title))

    titles = set()
    for ik in db_info.get("Instrumental Keys", []) or []:
        for t in _JUICEINFO_INSTRUMENTAL_MAP.get(ik, set()):
            if _juiceinfo_normalize_text(t) in exclude_norms:
                continue
            titles.add(t)

    return sorted(titles, key=lambda s: s.lower())


def load_download_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    else:
        return {"total_downloads": 0, "total_size_bytes": 0, "users": {}}

def save_download_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


def load_data(filename):
    try:
        with open(filename, "r") as file: return json.load(file)
    except: return {}

def save_data(data, filename):
    with open(filename, "w") as file: json.dump(data, file, indent=4)

def parse_folder_name(folder_name):
    """
    Parses folder name based on the rule: 
    Text before first '(' is Main Title. 
    Text inside '()' are Aliases.
    Example: "A-OK (A-Okay) (Bonjour)" -> Title: "A-OK", Aliases: "A-Okay | Bonjour"
    """
    parts = folder_name.split('(', 1)
    main_title = parts[0].strip()
    raw_aliases = re.findall(r'\((.*?)\)', folder_name)
    
    formatted_aliases = None
    if raw_aliases:
        clean_aliases = [a.strip() for a in raw_aliases if a.strip()]
        if clean_aliases:
            formatted_aliases = " | ".join(clean_aliases)
            
    return main_title, formatted_aliases

def format_length(seconds):
    if seconds is None:
        return "Unknown"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02}"

def format_size(size_bytes):
    if not size_bytes: return "Unknown"
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def get_album_from_path(file_path):
    try:
        ext = file_path.lower().split('.')[-1]
        if ext == "mp3":
            audio = MP3(file_path, ID3=ID3)
            return audio.tags.get("TALB", ["Unknown Album"])[0]
        elif ext == "flac":
            audio = FLAC(file_path)
            return audio.get("album", ["Unknown Album"])[0]
        elif ext in ["m4a", "mp4"]:
            audio = MP4(file_path)
            return audio.get("\xa9alb", ["Unknown Album"])[0]
    except:
        return "Unknown Album"
    return "Unknown Album"

def extract_metadata(file_path):
    if not file_path or not os.path.exists(file_path):
        return None

    file_size = os.path.getsize(file_path)
    metadata = {
        "title": "Unknown",
        "artist": "Unknown",
        "album": "Unknown",
        "length": "Unknown",
        "size_str": format_size(file_size),
        "cover_data": None 
    }

    try:
        ext = file_path.lower().split('.')[-1]

        if ext == "mp3":
            audio = MP3(file_path, ID3=ID3)
            metadata["length"] = format_length(audio.info.length)
            tags = audio.tags
            if tags:
                metadata["title"] = tags.get("TIT2", ["Unknown"])[0]
                metadata["artist"] = tags.get("TPE1", ["Unknown"])[0]
                metadata["album"] = tags.get("TALB", ["Unknown"])[0]
            if "APIC:" in tags:
                metadata["cover_data"] = tags["APIC:"].data

        elif ext == "flac":
            audio = FLAC(file_path)
            metadata["length"] = format_length(audio.info.length)
            metadata["title"] = audio.get("title", ["Unknown"])[0]
            metadata["artist"] = audio.get("artist", ["Unknown"])[0]
            metadata["album"] = audio.get("album", ["Unknown"])[0]
            if audio.pictures:
                metadata["cover_data"] = audio.pictures[0].data

        elif ext in ["m4a", "mp4"]:
            audio = MP4(file_path)
            metadata["length"] = format_length(audio.info.length)
            metadata["title"] = audio.get("\xa9nam", ["Unknown"])[0]
            metadata["artist"] = audio.get("\xa9ART", ["Unknown"])[0]
            metadata["album"] = audio.get("\xa9alb", ["Unknown"])[0]
            if "covr" in audio:
                metadata["cover_data"] = audio["covr"][0]

    except Exception as e:
        print(f"Error extracting metadata: {e}")

    return metadata

def get_file_download_count(cache_key):
    if not os.path.exists(STATS_FILE):
        return 0
    try:
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
            return stats.get("files", {}).get(cache_key, 0)
    except Exception:
        return 0

def update_stats_sync(f_path, u_id, cache_key):
    try:
        f_size = os.path.getsize(f_path)
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f: stats = json.load(f)
        else:
            stats = {"total_downloads": 0, "total_size_bytes": 0, "users": {}, "files": {}}

        if "files" not in stats: stats["files"] = {}
        if "users" not in stats: stats["users"] = {}

        stats["total_downloads"] += 1
        stats["total_size_bytes"] += f_size
        
        if u_id not in stats["users"]:
            stats["users"][u_id] = {"downloads": 0, "size_bytes": 0}
        stats["users"][u_id]["downloads"] += 1
        stats["users"][u_id]["size_bytes"] += f_size

        current_file_count = stats["files"].get(cache_key, 0)
        stats["files"][cache_key] = current_file_count + 1

        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        print(f"[Stats Error] {e}")