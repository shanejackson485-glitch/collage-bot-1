<div align="center">
  
# Collage Bot

*The only music bot worth using. Everyone else is just pretending.*

[![Website](https://img.shields.io/badge/Website-collagebot.info-purple.svg)](https://collagebot.info)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-red.svg)](https://discordpy.readthedocs.io/)
[![Status](https://img.shields.io/badge/Status-Sunset-yellow.svg)]()

> **Note**: Collage is still running as of May 10th, 2026, but will be officially shut down on August 6th, 2026. This repository serves as the final open-source archive of the codebase.

</div>

---

## A Message from the Creator

It’s been a wild ride since this started as a small side project, but the time has come to sunset `@collage`. 

As of this release, the bot will no longer be receiving updates, and on August 6th, 2026, we will officially be ending 24/7 uptime. We peaked at **227 servers and 92.7k users**—numbers I never could have imagined when I first started organizing leaks for a single server.

To everyone who used the bot to keep the music alive, sent feedback, and supported the project: thank you. (Also, the total downloads and size stats somehow reset themselves recently, but the real ones know how much traffic we actually moved).

Truthfully, I no longer have the time or the motivation to keep this running. The community has changed, and maintaining a project of this scale has become a massive headache that I’m ready to be done with. I don’t want the work to just disappear, so I'm releasing the entire source code for Collage. 

Even though I’m stepping away from hosting, this might not be the total end for the bot. Hounds or others I grant access to the application may choose to start hosting it themselves to keep it alive.

Thanks for being part of this chapter.

---

## Features (System Modules)

Collage isn't just a basic moderation bot—it's a massive, multi-functional powerhouse designed for music communities.

**The Vault (Artist & Music Archives)**
We index everything. If it leaked, we have it. If we don't have it, it doesn't exist.
- Direct integration with massive local databases for **Juice WRLD, Lil Uzi Vert, Playboi Carti, Gunna, YoungBoy (YB), Taylor Swift, Ariana Grande, and Instrumentals**.
- Fetch track info, snippets, sessions, cover art, and era-specific data instantly.
- Grail tracking systems for users to manage their most wanted tracks.

**Last.fm Integration**
- Full Last.fm ecosystem to track listening habits.
- `Whoknows` commands for artists, albums, and tracks globally within the server.
- Beautifully generated top artist/album visual grids.

**Advanced Moderation & Server Utilities**
- Robust jailing, hard-banning, purging, and filtering systems.
- Complete channel and role manipulation toolkit.
- Advanced server/user info parsing and dynamic voice/text channel creation.

**Economy**
A (almost) fully functional gambling addiction simulator. Earn coins, lose them in Blackjack, and cry about it.
- Integrated global economy system (blackjack, gambling, dailies, robberies).
- Sophisticated image manipulation suite (deepfry, pixelate, speechbubbles, stretching).
- Heardle game integration for Juice WRLD music.

**Instant Speed & Developer Tooling**
- Rewritten caching engine. Commands execute faster than your internet can handle.
- In-Discord database querying (`-sql`) and live code evaluation (`-eval`).
- Dynamic global blacklisting and server management.

---

## Setup & Installation

If you wish to fork this project and host your own instance of Collage, follow these steps:

### 1. Prerequisites
- **Python 3.9+**
- ffmpeg (required for audio/video media manipulation)
- A registered Discord Bot Token (enable `Message Content`, `Server Members`, and `Presence` intents).

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/collage.git
cd collage
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Before starting the bot, you must configure your local environment:

1. **Tokens**: Edit `data/Developer/config.json` and insert your Discord bot token and your admin user ID.
2. **API Keys**: Open `config.py` and populate `GENIUS_KEY` and `LASTFM_API_KEY` if you plan to use lyrics and Last.fm features.
3. **Database Paths**: Collage relies on local storage for its music libraries. Update the path constants in `config.py` (e.g., `LEAKS_PATH`, `STEMS_PATH`, etc.) to point to your respective media directories. *Note: Local database files are not included in this repository.*

### 5. Running the Bot
```bash
python collage.py
```
*Logs will automatically generate inside the `logs/` directory.*

---

## Project Structure

```text
Collage/
├── cogs/                   # Core modular command categories
│   ├── developer.py        # Dev-only system commands
│   ├── fun.py              # Image generation & games
│   ├── juice/              # Juice WRLD specific commands
│   ├── uzi/                # Uzi specific commands
│   ├── lastfm.py           # Last.fm API wrapper
│   ├── listeners.py        # Global event listeners & error handling
│   ├── moderation.py       # Mod tools & anti-spam
│   └── ...                 
├── data/                   # JSON caches, config, and economy tracking
├── logs/                   # Rotating runtime application logs
├── collage.py              # Main bot entry point & loop 
├── config.py               # Global settings, paths, and aesthetic variables
└── requirements.txt        # Python dependency manifest
```

---

## Credits
*The people we actually respect. Everyone else is irrelevant.*

### The Architects
*These two built the bot. Send money.*
- **xig** - [X / Twitter](https://x.com/CommitedToArson) | [GitHub](https://github.com/xigbotic)
- **hounds** - [X / Twitter](https://twitter.com/houndswrld) | [GitHub](https://github.com/houndswrld)

### The Enablers (Special Thanks)
- **@merikaaaaa**: Extremely skilled developer who contributed to this entire project. Unlike you, he knows how to code. [Check out his FH5 Trainer Here.](https://merika.dev/)
- **@VerzeHxD**: Provided the database for the snippet command. Saved us from doing manual labor.
- **@gabedoesntgaf**: Created the Juice WRLD groupbuy spreadsheet. Organized chaos.
- **@192kbps**: Compiled the Juice WRLD information spreadsheet. Audio nerd.
- **@WRLDOverlord**: Compiled the Lil Uzi Vert information spreadsheet. Data hoarder.
- **@juicewrldapi**: Provided the JuiceWRLDAPI. We stole their data so you could enjoy it.
- **@themarksmanxii**: We ignored his request for an instrumental command for over a month, then decided to code the entire thing in a single manic afternoon. He spends a concerning amount of time hunting for beats.
- **quixotic (@feelings.mutual)** & **exo (@1exodvs)**: Owners of the Playboi Carti tracker. We scraped their hard work so you can pretend to be a vamp.
- **@manwithaplan2**: Compiled the massive NBA YoungBoy tracker. YB Better? Our database says yes.
- **Rain51db & Animal Crackers**: Maintainers of the Taylor Swift tracker. We added this for the Swifties. Please don't dox us.
- **lioaf, strangersagain, coal124, tonixander & lvsk**: The architects of the Ariana Grande tracker. Comprehensive data for high-note enthusiasts.
- **@0wnerr & @827369hlj**: Solely responsible for putting us on to Ariana's music. Without their influence, the ariinfo command simply would not exist. Blame them.

### The Crash Dummies (Testers)
*These people ran broken commands repeatedly for free. We appreciate their lack of self-preservation.*
- @sharkky999, @angzyjr, @999ashton, @nick1616, @truesecurity, @jo097951, @squiregilligan, @kfjaf, @aussigirl2, @blxssedfr, @karmaptx

*Official Site: [collagebot.info](https://collagebot.info/)*  
*Official Docs: [collagebot.info/docs](https://collagebot.info/docs/)*
*Local Repository Docs: [DOCS.md](DOCS.md)*

---

## Security Notice
Prior to open-sourcing, all sensitive credentials, database keys, server-specific paths, and developer comments were scrubbed from this repository. 

If you are setting this up, ensure that your `config.json` and local database structures are properly secured.

---

<div align="center">
  <i>Keep the music alive.</i>
</div>
