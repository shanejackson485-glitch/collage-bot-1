# Collage Bot — Complete Technical Documentation

> **Status**: Sunset. No new updates. 24/7 hosting ends **August 6th, 2026**.  
> **Source**: [github.com/xigbotic/collage-bot](https://github.com/xigbotic/collage-bot)

---

## 1. System Overview

Collage is a locally-hosted, high-performance Discord bot built for music communities. It uses a **flat-file JSON database** and **local media indexing** instead of cloud storage or SQL. Audio files are scanned from local directories, ID3 metadata is parsed on-the-fly, and a Discord CDN caching layer prevents redundant uploads.

### Core Technical Operations

| Operation | Description |
|---|---|
| **Local Audio Indexing** | Scans configured directories for `.mp3`, `.flac`, `.m4a` files. Builds an in-memory lookup map on startup. |
| **Metadata Cross-Referencing** | Async HTTP requests to Last.fm and Genius APIs for auxiliary data (lyrics, play counts, producer credits). |
| **Discord CDN Caching** | Large files are uploaded once to a private "Caching Channel." The Discord attachment URL + message ID are saved to a JSON cache. Future requests serve the cached URL. |
| **Media Manipulation** | Uses `ffmpeg` (via `pydub`) for audio slicing, format conversion, and video compression. Uses `Pillow` for image manipulation. |
| **JuiceInfoDB Integration** | Parses local HTML tracker files to cross-reference track metadata (producer, era, instrumental, surfaced status). |

---

## 2. Prerequisites & Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10/11 or Linux (Ubuntu 20.04+) |
| **Python** | 3.9+ |
| **Discord.py** | 2.0+ |
| **ffmpeg** | Must be in system `PATH`. Required by `pydub` for audio processing. |
| **Bot Token** | Discord Developer Portal. Enable **all three** Privileged Intents: Presence, Server Members, Message Content. |
| **Genius API Key** | Required for `lyrics` command. Get from [genius.com/api-clients](https://genius.com/api-clients). |
| **Last.fm API Key** | Required for `lastfm` commands. Get from [last.fm/api](https://www.last.fm/api). |

### Python Dependencies (`requirements.txt`)

`discord.py`, `aiohttp`, `requests`, `Pillow`, `pilmoji`, `pydub`, `mutagen`, `yt-dlp`, `lyricsgenius`, `pyfiglet`, `uwuify`, `beautifulsoup4`, `psutil`, `humanize`, `regex`

---

## 3. Project Structure

```
Collage/
├── collage.py              # Main entry point, bot initialization, cog loader
├── config.py               # Global settings, paths, API keys, commands_dict
├── patched_gateway.py      # Custom Discord gateway (Android device spoofing)
├── watchdog.py             # Network monitor, auto-restart on connection loss
├── requirements.txt        # Python dependencies
├── cookies.txt             # Optional: yt-dlp cookies for platform auth
│
├── cogs/                   # Modular command categories (Cogs)
│   ├── developer.py        # Admin-only system commands
│   ├── moderation.py       # Server moderation tools
│   ├── listeners.py        # Global event handlers, blacklist, status rotation
│   ├── fun.py              # Entertainment, economy, games
│   ├── media.py            # Image manipulation suite
│   ├── util.py             # Help menu, server info, embeds, stats
│   ├── lastfm.py           # Last.fm API integration
│   ├── premium.py          # Premium features, leak converters
│   ├── metatag.py          # Audio file metadata tagging
│   ├── repost.py           # Social media video/slideshow reposter
│   ├── quote.py            # Stylized quote image generator
│   ├── announce.py         # Global announcement broadcaster
│   ├── boosterrole.py      # Custom booster role management
│   ├── reactionrole.py     # Reaction-based role assignment
│   ├── transcriber.py      # Audio-to-text transcription (Groq/Whisper)
│   ├── ariinfo.py          # Ariana Grande tracker
│   ├── cartiinfo.py        # Playboi Carti tracker
│   ├── taylorinfo.py       # Taylor Swift tracker
│   ├── ybinfo.py           # NBA YoungBoy tracker
│   ├── juice/              # Juice WRLD module (sub-cog)
│   │   ├── __init__.py
│   │   ├── helpers.py      # Shared utilities, JuiceInfoDB parser, metadata extraction
│   │   ├── leak.py         # Leak search & download
│   │   ├── instrumental.py # Instrumental search & download
│   │   └── ...             # Additional juice sub-modules
│   ├── juiceapi/           # JuiceWRLD API wrapper
│   └── uzi/               # Lil Uzi Vert module
│
├── data/                   # Flat-file JSON databases
│   ├── Developer/
│   │   ├── config.json     # Bot token, admin_user_id, whitelisted_users
│   │   ├── blacklist.json  # Banned guilds/users
│   │   ├── servers.json    # Server tracking data
│   │   ├── download_stats.json  # Global download analytics
│   │   ├── premium_whitelist.json
│   │   └── manual_whitelist.json
│   ├── Economy/
│   │   └── balances.json   # User wallets, banks, cooldowns
│   ├── LastFM/
│   │   └── lastfm_users.json  # Discord→Last.fm username mapping
│   ├── Moderation/
│   │   ├── jail_config.json
│   │   └── filters.json
│   ├── BoosterRoles/
│   │   ├── br_config.json
│   │   └── br_user_roles.json
│   └── Caches/
│       ├── leak_cache.json     # file_key → Discord message ID
│       ├── snippet_cache.json
│       └── cover_cache.json
│
├── logs/
│   └── collage.log         # Runtime error log
├── temp_media/             # Temporary download/processing directory
├── JuiceInfoDB/            # Local HTML tracker files
│   └── New/
│       ├── released.html
│       ├── unreleased.html
│       └── unsurfaced.html
└── assets/                 # Static assets (speech bubble, fonts, covers)
```

---

## 4. Core Files Explained

### `collage.py` — Entry Point
- Creates `commands.Bot` instance with `!` prefix and all intents enabled.
- Applies `patched_gateway.py` to spoof the bot as an Android device.
- Loads `data/Developer/config.json` for token and admin settings.
- Auto-loads all cogs from the `cogs/` directory via `bot.load_extension()`.
- Runs inside a `while True` reconnection loop.

### `config.py` — Global Configuration
Contains all configurable constants:
- **API Keys**: `GENIUS_KEY`, `LASTFM_API_KEY`
- **File Paths**: `LEAKS_PATH`, `STEMS_PATH`, `SESSIONS_PATH`, `INSTRUMENTAL_PATH`, `UZI_LEAK_PATH`, etc.
- **Cache Channels**: `COVER_CACHE_CHANNEL_ID`, `LEAK_ARCHIVE_CHANNEL_ID`, `SNIPPET_ARCHIVE_CHANNEL_ID`
- **`commands_dict`**: Master dictionary of all commands organized by category, used by the help menu.
- **`category_emojis`**: Emoji mapping for help menu categories.
- **`whitelist`**: Developer user IDs with elevated permissions.

### `patched_gateway.py` — Gateway Spoofing
Patches `discord.gateway.DiscordWebSocket.identify()` to set `browser: "Discord Android"` and `device: "Discord Android"`. This changes the bot's online status indicator to the mobile (green phone) icon.

### `watchdog.py` — Network Monitor
Pings `1.1.1.1` every 30 seconds. If the connection drops, it kills the bot process and restarts it when connectivity is restored. Use `python watchdog.py` instead of `python collage.py` for auto-recovery.

---

## 5. Deployment Instructions

### Step 1: Clone & Install
```bash
git clone https://github.com/xigbotic/collage-bot.git
cd collage-bot
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Step 2: Configure
1. Edit `data/Developer/config.json`:
   ```json
   {
     "token": "YOUR_BOT_TOKEN",
     "admin_user_id": YOUR_DISCORD_USER_ID,
     "whitelisted_users": [YOUR_DISCORD_USER_ID]
   }
   ```
2. Edit `config.py`: Set `GENIUS_KEY`, `LASTFM_API_KEY`, and all file path constants.

### Step 3: Set Up Caching Channel
1. Create a private Discord server for file storage.
2. Invite your bot to it.
3. Copy a text channel ID → paste into `config.py` as `COVER_CACHE_CHANNEL_ID` (and other cache channel vars).

### Step 4: Run
```bash
python collage.py          # Direct run
python watchdog.py         # With network auto-recovery
pm2 start collage.py       # Production (24/7)
```

---

## 6. Cog Reference — All Commands

### 6.1 Developer (`developer.py`)
> **Access**: Admin/whitelisted users only. All commands gated by `cog_check()`.

| Command | Usage | Description |
|---|---|---|
| `blacklist` | `-blacklist <guild\|user> <id> [reason]` | Blacklists a server or user. Auto-leaves blacklisted guilds. |
| `unblacklist` | `-unblacklist <guild\|user> <id>` | Removes a blacklist entry. |
| `leave` | `-leave <guild_id>` | Forces the bot to leave a server. |
| `addrole` | `-addrole <member\|all> <role>` | Adds a role to a user or all members (rate-limited). |
| `listservers` | `-listservers` | Paginated list of all servers the bot is in (name, ID, members, owner). |
| `createinvite` | `-createinvite <guild_id>` | Creates a one-time invite link for any server the bot is in. |
| `debug` | `-debug` | System diagnostics: platform, Python version, CPU/RAM, latency, uptime. |
| `reload` | `-reload <cog_name>` | Hot-reloads a cog without restarting the bot. |
| `logs` | `-logs [lines]` | Shows the last N lines of `logs/collage.log`. Default 15. |
| `clear_logs` | `-clear_logs` | Wipes the error log file. |
| `sync` | `-sync` | Syncs slash commands with Discord's API. |
| `backup` | `-backup` | Zips the `data/` folder and sends it as a Discord file. |
| `shutdown` | `-shutdown` | Gracefully shuts down the bot. |
| `eval` | `-eval <code>` | Executes arbitrary Python code. Supports async, multi-line, stdout capture. |
| `sql` | `-sql <query>` | Runs a raw SQL query on `database.db`. |
| `reset` | `-reset <filename.json>` | Resets a JSON file to `{}`. |
| `cmd_map` | `-cmd_map` | Lists all loaded commands grouped by Cog (paginated). |
| `serverfetch` | `-serverfetch <guild_id>` | Deep server inspection: channels, roles, permissions, bans, features. |

### 6.2 Moderation (`moderation.py`)
> **Access**: Requires respective Discord permissions (manage_messages, kick_members, etc.)

| Command | Usage | Description |
|---|---|---|
| `jail` | `-jail <member> [reason]` | Strips all roles and assigns the jail role/channel. |
| `unjail` | `-unjail <member>` | Restores saved roles and removes jail role. |
| `setjail` | `-setjail <role> <channel>` | Configures the jail role and channel for the server. |
| `hardban` | `-hardban <user_id> [reason]` | Bans a user by ID (works even if they're not in the server). |
| `purge` | `-purge <count>` | Bulk deletes messages from the channel. |
| `filter` | `-filter add/remove/list <word>` | Manages auto-moderation word filters per server. |
| `nuke` | `-nuke` | Clones and deletes the current channel (resets all messages). |
| `lock` / `unlock` | `-lock [channel]` | Toggles send-message permissions for @everyone. |
| `slowmode` | `-slowmode <seconds>` | Sets channel slowmode. |
| `role` | `-role <member> <role>` | Adds/removes a role from a member. |
| `hide` / `unhide` | `-hide [channel]` | Toggles channel visibility for @everyone. |

### 6.3 Listeners (`listeners.py`)
> **No user commands.** Passive event handlers.

| Event | Function |
|---|---|
| `on_ready` | Prints login info, starts status rotation loop. |
| `on_guild_join` | Checks if guild is blacklisted → auto-leave if so. |
| `on_message` | Checks if user is blacklisted → ignores. Runs word filter checks. |
| `on_command_error` | Global error handler. Catches cooldowns, missing permissions, etc. |
| **Status Rotation** | Cycles through custom status messages every 30 seconds. |

### 6.4 Fun & Economy (`fun.py`)
> Contains multiple Cog classes loaded together.

**Fun Cog:**

| Command | Description |
|---|---|
| `/say` | Bot repeats your message. Supports `freaky` (cursive font), `uwu`, `reverse` flags. |
| `urban` | Searches Urban Dictionary. Paginated results sorted by thumbs up. |
| `lyrics` | Fetches song lyrics from Genius API. Paginated with album art. Has autocomplete. |
| `fakemessage` | Generates a fake Discord message image with any user's avatar/name. Supports ash/dark themes. |
| `math` | Safe math expression evaluator with overflow protection. |
| `asciify` | Converts text to ASCII art using pyfiglet. Multiple fonts available. |
| `smoke` | Humorous substance simulation with randomized outcomes (weed, vape, crack, salvia, fent, meth, dmt). |
| `eightball` | Magic 8-ball. |

**Economy Cogs (BalanceCog, RewardsCog, BlackjackCog, GambleCog, RobCog, BegCog):**

| Command | Description |
|---|---|
| `balance` | Shows wallet + bank balance. |
| `setbal` | (Dev only) Sets a user's balance. |
| `deposit` / `withdraw` | Move coins between wallet and bank. Supports `all`. |
| `daily` / `weekly` / `monthly` | Claim timed rewards (1k–25k / 50k–100k / 150k–1M coins). |
| `blackjack` | Play blackjack against the dealer. Interactive hit/stand buttons. |
| `gamble` | 50/50 coin flip bet. |
| `rob` | Steal 50–1000 coins from another user. 30min cooldown. |
| `beg` | 50% chance to receive coins from a random character. 5min cooldown. |

### 6.5 Media (`media.py`)
> Image manipulation suite. All commands work with attachments or replies. Supports GIF processing.

| Command | Aliases | Description |
|---|---|---|
| `imagetogif` | `img2gif`, `togif` | Converts a static image to GIF format. |
| `speechbubble` | `bubble` | Overlays a transparent speech bubble on an image. |
| `caption` | `addcaption`, `cc` | Adds a white caption bar above an image (auto-sizing font). |
| `blackandwhite` | `bw`, `greyscale` | Converts to grayscale. |
| `pixelate` | — | Pixelates an image. Sizes: small (8px), medium (16px), large (32px). |
| `invert` | — | Inverts all colors. |
| `deepfry` | — | Applies sharpness, contrast, color boost, and noise overlay. |
| `stretch` | — | Horizontal stretch. Factor range: 0.5–2.0. |
| `saturate` | — | Adjusts color saturation. Factor range: 0.0–3.0. |
| `overlay` | — | Blends two images together with configurable opacity (0–100%). |
| `flip` | — | Flips image in any direction (left/right/up/down). |

### 6.6 Utility (`util.py`)
> Server utilities, help system, stats, embeds, user info.

| Command | Aliases | Description |
|---|---|---|
| `help` | `commands` | Interactive paginated help menu with category dropdown. |
| `stats` | `info`, `ping`, `botinfo` | Bot statistics: servers, users, latency, RAM, uptime, downloads. |
| `serverinfo` | `si`, `sinfo` | Server details: owner, members, channels, roles, boosts. |
| `userinfo` | `ui` | User profile with roles, join date, account age. Includes kick/ban/DM buttons. |
| `search` | — | Search for a specific command by name from the commands dictionary. |
| `embed` | — | Interactive embed builder with modal inputs (title, description, color, button, thumbnail). |
| `botclear` | `bc`, `cleanup` | Purges the bot's own messages from the channel. |
| `topdownloads` | `td`, `downloads` | Leaderboard of top file downloaders by count and size. |

### 6.7 Last.fm (`lastfm.py`)
> Full Last.fm integration. Hybrid command group: `lastfm` / `lf` / `fm`.

| Command | Aliases | Description |
|---|---|---|
| `lastfm login` | — | Links a Last.fm username. Optional `hidden` flag to hide username in embeds. |
| `lastfm nowplaying` | `np`, `fm` | Shows currently playing / last played track with play counts and album art. Dominant color extraction for embed. |
| `lastfm whoknows` | `wk` | Ranks server members by plays of your current artist. |
| `lastfm whoknowsalbum` | `wka` | Same but for albums. |
| `lastfm whoknowstrack` | `wkt` | Same but for tracks. |
| `lastfm toptracks` | `tt` | Your top 50 tracks. Periods: 7d, 1m, 3m, 6m, 1y, lifetime. |
| `lastfm topartists` | `ta` | Your top 50 artists. |
| `lastfm topalbums` | `talb` | Your top 50 albums. |
| `lastfm latest` | `recent`, `rt` | Your 50 most recent scrobbles with timestamps. |

### 6.8 Premium (`premium.py`)
> Features gated behind premium whitelist (`premium_whitelist.json` / `manual_whitelist.json`).

Key features include: leak format conversion (MP3↔FLAC↔M4A), batch downloads, extended search results, priority caching, and access to the `metatag` and `repost` commands.

### 6.9 MetaTag (`metatag.py`)
> Audio metadata tagger with Juice WRLD era presets. Premium only.

| Command | Description |
|---|---|
| `metatag` | Applies ID3 metadata (title, artist, album, year, genre, cover art) to an uploaded MP3/M4A/FLAC using a preset. |
| `metatag_presets` | Lists all 22 available presets (11 Sessions + 11 Era). |

**Presets** cover all Juice WRLD eras: JUTE, Affliction, HIH999, JW999, BDM, ND, GB&GR, WOD, DRFL, Outsiders, Posthumous — each with Sessions and Era variants. Each preset auto-applies: artist, album artist, album name, year, genre, and era-specific cover art.

**Supported formats**: MP3 (ID3v2.3), M4A/MP4 (iTunes tags), FLAC (Vorbis comments).

### 6.10 Repost (`repost.py`)
> Downloads and reposts videos/slideshows from TikTok, Instagram, Twitter/X, YouTube.

| Command | Description |
|---|---|
| `repost` | Downloads media via `yt-dlp`, compresses with ffmpeg if needed, uploads to Discord. Falls back to TikWM API for TikTok. Files >25MB are uploaded to Catbox. Embeds include uploader info, likes, comments, views. |

**Technical details**: Uses `yt-dlp` with Chrome impersonation, cookie support, and multiple retry strategies. Caches results for 30 minutes. Auto-cleans temp files every 10 minutes.

### 6.11 Quote (`quote.py`)
> Generates stylized quote images from Discord messages.

| Command | Description |
|---|---|
| **Quote Message** (context menu) | Right-click a message → "Quote Message" to generate a styled image. |

**Style options** (interactive buttons): Dark/Light mode, Contrast, Flip, Blur, Brightness, Pixelate, Solarize, GIF output, New layout, Font selection. Uses Pilmoji for emoji rendering.

### 6.12 Announce (`announce.py`)
> Admin-only global announcement system.

| Command | Description |
|---|---|
| `/announce` | Opens a modal to compose an embed (title, description, color, thumbnail, footer). Preview → Edit → Send to ALL servers. Auto-finds the best channel per server (system channel → #general → first available). |

### 6.13 Booster Role (`boosterrole.py`)
> Custom roles for server boosters.

| Command | Description |
|---|---|
| `br config role` | (Admin) Sets which role counts as the "booster" role. |
| `br create` | Creates a personal custom role for the booster. |
| `br name` | Changes the custom role's name. |
| `br color` | Changes the custom role's color (hex). |
| `br icon` | Sets a custom role icon (Level 2+ servers only). |

Auto-deletes custom roles when a user stops boosting.

### 6.14 Reaction Roles (`reactionrole.py`)
> Emoji-based role assignment system.

| Command | Description |
|---|---|
| `rr create` | Creates a new embed with a reaction role. Supports `--title`, `--color`, `--thumbnail` flags. |
| `rr add` | Adds a reaction role to an existing message by ID/link. |
| `rr remove` | Removes a reaction role mapping. |
| `rr list` | Lists all reaction roles on a message. |
| `rr bulkcreate` | Bulk setup: parses `emoji = @Role` lines from text input. |

### 6.15 Transcriber (`transcriber.py`)
> Audio-to-text transcription using Groq's Whisper API.

| Command | Description |
|---|---|
| `transcribe` | Transcribes an uploaded audio file or replied voice message. Max 3 minutes. |
| **Transcribe** (context menu) | Right-click a message with an attachment → "Transcribe". |

### 6.16 Artist Trackers
> Each tracker parses local HTML/CSV files from community-maintained spreadsheets.

| Cog | File | Artist | Description |
|---|---|---|---|
| `ariinfo.py` | Ariana Grande | Ariana Grande | Track info, era lookup, search |
| `cartiinfo.py` | Playboi Carti | Playboi Carti | Track info, era lookup, search |
| `taylorinfo.py` | Taylor Swift | Taylor Swift | Track info, era lookup, search |
| `ybinfo.py` | NBA YoungBoy | NBA YoungBoy | Track info, era lookup, search |

### 6.17 Juice WRLD Module (`cogs/juice/`)

**`helpers.py`** — Shared utilities:
- `parse_folder_name()`: Extracts main title and aliases from folder names (e.g., `"A-OK (A-Okay)"` → title: `"A-OK"`, aliases: `"A-Okay"`).
- `extract_metadata()`: Reads ID3/FLAC/MP4 tags from audio files (title, artist, album, duration, size, cover art).
- `get_juiceinfo_track()`: Best-effort lookup against the JuiceInfoDB HTML index. Uses normalized fuzzy matching with scoring for title, alt titles, file names, and era preference.
- `get_juiceinfo_shared_instrumental_titles()`: Finds other tracks sharing the same instrumental beat.
- `update_stats_sync()`: Writes download analytics to `download_stats.json`.
- Era color/image mappings for all Juice WRLD eras (Affliction, BDM, DRFL, GB&GR, HIH999, JW999, ND, Outsiders, Posthumous, JUTE, WOD + all released albums).

**`leak.py`** — Leak search & download:
- Builds an in-memory map of all folders in `LEAKS_PATH` on startup.
- Fuzzy search with normalized punctuation stripping.
- Multi-version support (dropdown selection when folder contains multiple files).
- Discord CDN caching via archive channel for persistent download links.
- Embeds show: title, aliases, album, duration, producer (from JuiceInfoDB), shared instrumentals, download count, and embedded cover art.

**`instrumental.py`** — Instrumental search & download (similar architecture to leak.py).

---

## 7. Database Schemas

### `data/Developer/config.json`
```json
{
  "token": "string — Discord bot token",
  "admin_user_id": "int — Primary admin Discord user ID",
  "whitelisted_users": ["int — Additional privileged user IDs"]
}
```

### `data/Developer/blacklist.json`
```json
{
  "guilds": { "guild_id": { "message": "reason", "date": "timestamp" } },
  "users": { "user_id": { "message": "reason", "date": "timestamp" } }
}
```

### `data/Developer/download_stats.json`
```json
{
  "total_downloads": "int",
  "total_size_bytes": "int",
  "users": { "user_id": { "downloads": "int", "size_bytes": "int" } },
  "files": { "cache_key": "int — download count" }
}
```

### `data/Economy/balances.json`
```json
{
  "user_id": {
    "balance": "int — wallet coins",
    "bank": "int — banked coins",
    "cooldowns": { "daily": "ISO timestamp", "weekly": "...", "rob": "..." }
  }
}
```

### `data/LastFM/lastfm_users.json`
```json
{ "user_id": { "username": "lastfm_username", "hidden": false } }
```

### Cache files (`leak_cache.json`, etc.)
```json
{ "folder_filename_key": "discord_message_id (int)" }
```

---

## 8. Maintenance & Troubleshooting

| Issue | Solution |
|---|---|
| **Memory climb** | Restart the bot process weekly. Caching is aggressive by design. |
| **HTTP 404 on cached files** | Someone deleted a message in the caching channel. Delete the entry from the relevant cache `.json` and let it rebuild. |
| **Commands not appearing** | Run `-sync` to push slash commands to Discord. May take up to 1 hour to propagate globally. |
| **Lyrics not working** | Verify `GENIUS_KEY` in `config.py` is valid. |
| **Last.fm errors** | Verify `LASTFM_API_KEY` in `config.py`. Check if the user has run `lastfm login`. |
| **Media commands fail** | Ensure `ffmpeg` is in system `PATH`. Verify `assets/speech_bubble.png` and `assets/font.ttf` exist. |
| **Leak/instrumental commands empty** | Verify `LEAKS_PATH` / `INSTRUMENTAL_PATH` in `config.py` point to valid directories containing audio folders. |
| **Repost downloads fail** | Platform may be blocking. Update `yt-dlp` (`pip install -U yt-dlp`). Provide a valid `cookies.txt`. |
| **Bot shows as phone icon** | This is intentional — `patched_gateway.py` spoofs the client as Android. |
| **Logs location** | All errors go to `logs/collage.log`. Review with `-logs` command or directly. |

---

## 9. Security Notes

- All tokens, API keys, and hardcoded IDs were scrubbed before open-sourcing.
- `config.json` and `config.py` must be secured — they contain secrets.
- The `eval` and `sql` commands execute arbitrary code/queries. They are restricted to whitelisted users only.
- Download stats contain Discord user IDs — handle with care per your privacy requirements.
- The `announce` command can message every server the bot is in — admin-only by design.

---

*Last updated: May 10th, 2026 — Final open-source release.*
*Keep the music alive.*
