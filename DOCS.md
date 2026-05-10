# Collage Bot System Architecture & Documentation

Welcome to the technical documentation for Collage. This document provides an in-depth breakdown of the bot's system architecture, prerequisite requirements, database structures, and step-by-step instructions for deploying an instance. 

---

## 1. System Overview & Core Capabilities

Collage was engineered as a high-performance, locally-hosted multimedia Discord bot. Instead of relying on cloud storage or external SQL databases, Collage depends entirely on a localized file architecture. This design choice guarantees maximum retrieval speeds for large media files (such as `.flac` and `.mp3` audio files) while ensuring the system remains highly portable and independent of third-party database outages.

### Key Technical Operations:
1. **Local Audio Indexing**: The bot scans specified local directories for audio files. When a user queries a song, Collage parses the ID3 tags of the local file on-the-fly to extract metadata (duration, bitrate, cover art).
2. **Metadata Cross-Referencing**: For advanced queries, the bot makes asynchronous HTTP requests to `juicewrldapi.com` or Last.fm to fetch auxiliary data (e.g., exact recording dates, producer credits, and user listening history).
3. **Discord CDN Caching**: To prevent hitting Discord's API rate limits or consuming excessive local bandwidth, Collage utilizes a "Caching Channel." When a large file is uploaded to Discord for the first time, its Discord attachment URL and message ID are saved to a local JSON cache. Future requests for the same file instantly serve the Discord CDN link instead of re-uploading the file.
4. **Media Manipulation**: Collage utilizes the `ffmpeg` library natively to slice audio files, generate session edits, and format MP3s for Discord.

---

## 2. Prerequisites & Requirements

To successfully host Collage, the underlying operating system must meet the following requirements:

- **Environment**: Windows 10/11 or a Linux equivalent (Ubuntu 20.04+ recommended).
- **Python Framework**: Python 3.9 or higher.
- **Discord Framework**: `discord.py` version 2.0 or higher.
- **System Libraries**: 
  - `ffmpeg` must be installed and added to the system's `PATH`. This is strictly required for the `pydub` wrapper to handle audio processing.
- **API Keys**:
  - A Discord Bot Token (with all Privileged Intents enabled: Presence, Server Members, Message Content).
  - A Genius API Key (for lyrics generation).
  - A Last.fm API Key (for scrobble tracking and user queries).

---

## 3. Database & Directory Structure

Collage uses a flat-file JSON structure to manage persistent data. This eliminates the need for a background database service, though it requires strict path management.

### The `data/` Directory Map
```text
data/
├── Developer/
│   ├── config.json         # Stores the Discord Bot Token, default prefix, and Admin IDs.
│   └── commands.json       # Tracks command usage analytics.
├── Economy/
│   └── balances.json       # Maps User IDs to integers representing global currency.
├── LastFM/                 # Maps Discord User IDs to their registered Last.fm usernames.
├── Moderation/             
│   ├── jail_config.json    # Maps Server IDs to designated 'Jail' Role/Channel IDs.
│   └── filters.json        # Auto-moderation word filters per server.
└── Caches/                 # The critical Discord CDN caching layer.
    ├── leak_cache.json     # Maps local file paths to Discord Attachment URLs.
    ├── snippet_cache.json  # Cached URLs for audio snippets.
    └── cover_cache.json    # Cached URLs for high-resolution album covers.
```

### The `assets/` & Local Media Map
To utilize the music functionalities, the host must manually provide the music databases. These paths are configured globally inside `config.py`. 
- `LEAKS_PATH`: Standard MP3/FLAC files for primary artist (Juice WRLD).
- `STEMS_PATH`: Isolated vocal and instrumental tracks.
- `SESSIONS_PATH`: Raw, unedited studio recording blocks.
- `INSTRUMENTAL_PATH`: Official beats.
- `UZI_LEAK_PATH`, `CARTI_LEAK_PATH`, etc.: Directories for secondary artists.

*Note: If these paths are empty or misconfigured, all media-related commands will fail to execute or return empty results.*

---

## 4. Deployment Instructions

Follow these steps to deploy Collage in a production environment:

### Step 1: Clone & Install Dependencies
Download the source code and install the required Python packages. It is highly recommended to use a virtual environment (`venv`).
```bash
git clone <repository_url> collage
cd collage
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
1. Navigate to `data/Developer/config.json`. Insert your Bot Token and set your personal Discord User ID as the `admin_user_id`.
2. Open `config.py` in the root directory.
3. Locate the `GENIUS_KEY` and `LASTFM_API_KEY` variables and insert your respective developer keys.
4. Verify that the file paths defined under `#==========PATHS==========#` accurately point to your local media directories.

### Step 3: Initialize the Caching Channel
1. Create a private Discord server intended solely for file storage.
2. Invite your bot to this server.
3. Copy the ID of a text channel in this server.
4. Paste this ID into `config.py` under the variable `COVER_CACHE_CHANNEL_ID` (and any other cache channel variables). The bot will use this channel to silently upload and cache files.

### Step 4: Execution & Process Management
To start the bot, execute the main script:
```bash
python collage.py
```
For 24/7 deployment, it is recommended to run the bot using a process manager such as `pm2` or `systemd` to ensure automatic restarts upon failure.
```bash
pm2 start collage.py --name "CollageBot"
```

### Optional: Utilizing the Watchdog Script
Included in the root directory is `watchdog.py`. This script acts as a localized monitor that pings external DNS servers (1.1.1.1) to verify internet connectivity. If the connection drops, it safely suspends the bot and restarts it once the connection is restored, preventing socket hang-ups.
To use the watchdog instead of directly running the bot:
```bash
python watchdog.py
```

---

## 5. Maintenance & Troubleshooting

- **Memory Leaks**: Due to extensive caching, memory usage may climb over time. The bot is designed to handle this, but restarting the process weekly is advised for optimal performance.
- **Corrupted Caches**: If a file is deleted from the Discord caching channel, the bot will throw `HTTP 404 Not Found` errors when attempting to serve it. To resolve this, simply delete the contents of the respective `.json` file inside `data/Caches/` and let the bot rebuild the cache organically.
- **Logs**: All runtime errors, warnings, and tracebacks are automatically captured and written to `logs/collage.log`. Always review this file when diagnosing an issue.
