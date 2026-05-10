import discord
from discord.ext import commands
import json
import logging


IMAGE_DIRECTORY = r"./assets/pictures"
SPREADSHEET_HTML_PATH = r"./assets/leaks.html"
MAIN_DIRECTORY = r"./assets/leaks"
SNIPPETS_FOLDER_PATH = r"./assets/snippets"
LEAKS_PATH = r"./assets/LeaksNEW"
REMASTERS_PATH = r"./assets/Remasters"
STEMS_PATH = r"./assets/Stems"
FREESTYLES_PATH = r"./assets/Freestyles"
UZI_PATH = r"./assets/UziLeaks"
COVERS_FOLDER = r"./assets/coverart"
SESSIONS_PATH = r"./assets/Sessions"
GUNNA_LEAK_PATH = r"./assets/GunnaLeak"
CARTI_LEAK_PATH = r"./assets/CartiLeak"


BALANCE_FILE = "data/Economy/balances.json"
BOOSTER_ROLE_ID = 0
GENIUS_KEY = ''


COVER_CACHE_FILE = "data/Caches/cover_cache.json"  
COVER_CACHE_CHANNEL_ID = 0 
LEAK_CACHE_FILE = "data/Caches/leak_cache.json"
LEAK_ARCHIVE_CHANNEL_ID = 0
SNIPPET_CACHE_FILE = "data/Caches/snippet_cache.json"
ARCHIVE_CHANNEL_ID = 0
SESSION_ARCHIVE_CHANNEL_ID = 0





def load_data():
    try:
        with open("data.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error("data.json not found!")
        return {"whitelist": {}, "reasons": {}, "deleted_messages": []}

def save_data(data):
    with open("data.json", "w") as file:
        json.dump(data, file, indent=4)

data = load_data()
whitelist = []
afk_users = {}
premium_role = []
deleted_messages = data["deleted_messages"]
LASTFM_API_KEY = ""



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
    "JUTE": "JUICED UP THE EP"
}

era_sort_order = ["POST", "OUT", "DRFL", "WOD", "GB&GR", "ND </3", "BDM", "JW 9 9 9", "HIH 9 9 9", "AFF", "JUTE"]

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
    "JUICED UP THE EP": r"https://i.ibb.co/20bWyHmg/juiceduptheep.jpg"
}


era_colors = {
    "Death Race For Love": 0xb83d11,
    "Goodbye & Good Riddance": discord.Color.blue().value,
    "WRLD on drugs": 0x0721ca,
    "Outsiders": 0x161213,
    "Affliction": 0x000000,
    "BINGEDRINKINGMUSIC": 0x000000,
    "NOTHINGS DIFFERENT </3": 0xcc5437,
    "Juice WRLD 999": 0x1b0706,
    "HEARTBROKEN IN HOLLYWOOD 999": 0x471422,
    "Posthumous": 0x131313,
    "JUICED UP THE EP": 0x578dcf
}





commands_dict = {

    "Artists": [
        {"name": "leak", "description": "Provides song file and information for a song."},
        {"name": "snippet", "description": "Provides known snippets of a provided song."},
        {"name": "sotd", "description": "Sends a randomly picked Juice WRLD song each day."},
        {"name": "randomsong", "description": "Sends a randomly picked Juice WRLD song."},
        {"name": "juiceinfo", "description": "Provides all known information on a song by Juice WRLD."},
        {"name": "juicegb", "description": "Get information on a Juice WRLD group buy."},
        {"name": "juicepic", "description": "Provides up to 10 random pictures of Juice WRLD."},
        {"name": "juicegif", "description": "Provides up to 10 random GIF's of Juice WRLD."},
        {"name": "session", "description": "Provides a session edit for a song."},
        {"name": "listallsessions", "description": "Lists all session edits on the bot."},
        {"name": "stem", "description": "Provides a specified stem edit."},
        {"name": "remaster", "description": "Provides a specified remaster."},
        {"name": "freestyle", "description": "Get a freestyle."},
        {"name": "erainfo", "description": "Get information of a specified era."},
        {"name": "cover", "description": "Provides covers for a specified Juice WRLD song or album."},
        {"name": "grail", "description": "Display your grail list."},
        {"name": "grail add", "description": "Add a song to your grail list."},
        {"name": "grail remove", "description": "Remove a song from your grail list."},
        {"name": "grail clear", "description": "Clear your grail list."},
        {"name": "grail update", "description": "Update your grail list."},
        {"name": "grail gifadd", "description": "Add a specified GIF to your grail list embed."},
        {"name": "grail gifremove", "description": "Remove your GIF from your grail list embed."},

    ],

    "Premium" : [
        {"name": "yt2mp3", "description": "Convert any Youtube link into a MP3 file."},
        {"name": "repost", "description": "Reposts a Instagram Reel, Tiktok, or Twitter video into the chat."},
        {"name": "juiceproducer", "description": "Get all tracks produced by a specified producer."},
        {"name": "juicepreview", "description": "Find all songs previewed on a specific date."},
        {"name": "juiceengineer", "description": "Find all tracks made by a specific engineer."},
        {"name": "juiceloc", "description": "Find all tracks recorded at a specific studio."},
        {"name": "uzileak", "description": "Get any song from Lil Uzi Vert."},
        {"name": "gunnaleak", "description": "Get any song from Gunna."},
        {"name": "cartileak", "description": "Get any song from Playboi Carti."},
        {"name": "comp", "description": "Get an updated Juice WRLD, Lil Uzi Vert, Playboi Carti, & Gunna comp."},
        {"name": "protools", "description": "Get any leaked Juice WRLD Pro Tools session."},
        {"name": "ogfile", "description": "Get any leaked Juice WRLD original file."},
        {"name": "uziinfo", "description": "Provides all known information on a song by Lil Uzi Vert."},

          
    ],

    "Moderation": [
        {"name": "ban", "description": "Ban a user from the server."},
        {"name": "unban", "description": "Unban a user from the server."},
        {"name": "hardban", "description": "Ban a user and add them to the hardban list."},
        {"name": "unhardban", "description": "Unban a user and remove them from the hardban list."},
        {"name": "kick", "description": "Kick a user from the server."},
        {"name": "mute", "description": "Mute a user for a specified duration."},
        {"name": "unmute", "description": "Unmute a currently muted user."},
        {"name": "lock", "description": "Lock the current channel."},
        {"name": "unlock", "description": "Unlock the current channel."},
        {"name": "slowmode", "description": "Set the slowmode delay for the channel."},
        {"name": "nuke", "description": "Clone and recreate the channel to clear all history."},
        {"name": "purge", "description": "Delete a specified amount of messages."},
        {"name": "purge user", "description": "Delete messages from a specific user."},
        {"name": "purge bots", "description": "Delete messages sent by bots."},
        {"name": "purge contains", "description": "Delete messages containing a specific keyword."},
        {"name": "embed", "description": "Create a highly customizable embed."},
        {"name": "bc", "description": "Clear all bot messages."},
        {"name": "warn", "description": "Warns a user with a optional warning message."},
        {"name": "warnings", "description": "Check a mentioned users past warnings."},
        {"name": "removewarn", "description": "Removes a warning from a user by specifying the warn ID."},
        {"name": "delwarn", "description": "Alias for removewarn."},
        {"name": "clearwarns", "description": "Clear all warns from a mentioned user."},
        {"name": "jail", "description": "Jail a user."},
        {"name": "unjail", "description": "Unjail a user."},
        {"name": "setup", "description": "Run the setup configuration for the jail system."},
        {"name": "banreason", "description": "Update or view the reason for a ban."},
        {"name": "forcenick", "description": "Force a nickname on a user and prevent them from changing it."},
        {"name": "role", "description": "Manage roles (add/remove) for a user."},
        {"name": "role create", "description": "Create a new role in the server."},
        {"name": "role delete", "description": "Delete an existing role."},
        {"name": "role humans", "description": "Add or remove a role for all humans."},
        {"name": "channel create", "description": "Create a new text or voice channel."},
        {"name": "channel delete", "description": "Delete a specified channel."},
        {"name": "channel hide", "description": "Hide a channel from standard users."},
        {"name": "channel reveal", "description": "Make a channel visible to standard users."},
    ],
    "Server": [
        {"name": "si", "description": "Displays server information."},
        {"name": "ui", "description": "Displays user information."},
        {"name": "ping", "description": "Displays bot ping, user count, server count, and uptime information."},
        {"name": "br config role", "description": "Configurate the server booster role ID in order for server boosters to be able to create a role."},
        {"name": "stealemoji", "description": "Steal an emoji from any server."},
        {"name": "stealsticker", "description": "Steal a sticker from any server."},
        {"name": "joins", "description": "Show a list of the most recent members to join."},
        {"name": "bots", "description": "List all bots currently in the server."},
        {"name": "roleinfo", "description": "Get detailed information about a specific role."},
        {"name": "perms", "description": "Check the permissions of a user or role."},
        {"name": "av", "description": "Display a user's avatar."},
        {"name": "banner", "description": "Display a user's profile banner."},
        {"name": "sav", "description": "Display a users server avatar."},
        {"name": "sbanner", "description": "Display the server's banner image."},
        {"name": "channelinfo", "description": "Get detailed info about the current channel."},
        {"name": "roles", "description": "List all roles in the server."},
        {"name": "inviteinfo", "description": "Get information about a specific invite code."},
        {"name": "invites", "description": "Check information of invite codes."},
        {"name": "inrole", "description": "List all users who have a specific role."},
        {"name": "boosters", "description": "List all users currently boosting the server."},
        {"name": "getbotinvite", "description": "Get the invite link for a specific bot."},
    ],



    
    "Fun": [
        {"name": "qp", "description": "Create a quick poll on your message."},
        {"name": "heardle", "description": "Play a game of Juice WRLD Heardle."},
        {"name": "hstats", "description": "View your Heardle stats."},
        {"name": "htop", "description": "View the global Heardle leaderboard."},
        {"name": "br create", "description": "Create a custom booster role if you are boosting a server."},
        {"name": "br name", "description": "Rename your booster role."},
        {"name": "br color", "description": "Change the color of your booster role."},
        {"name": "br icon", "description": "Change the icon of your booster role."},
        {"name": "8ball", "description": "Ask the magic 8 Ball a question."},
        {"name": "smoke", "description": "No description avaliable."},
        {"name": "say", "description": "Make the bot say a message."},
        {"name": "urban", "description": "Search for a definition on Urban Dictionary."},
        {"name": "lyrics", "description": "Get the lyrics for a specific song."},
        {"name": "fakemsg", "description": "Create a fake message screenshot."},
        {"name": "math", "description": "Solve a math problem."},
        {"name": "asciify", "description": "Convert text into ASCII art."},
        {"name": "quote", "description": "Generate a quote image from a message. This works by using the context menu only."},
        {"name": "imagetogif", "description": "Turn a static image into a GIF."},
        {"name": "speechbubble", "description": "Add a transparent speech bubble to an image."},
        {"name": "caption", "description": "Add a caption text to the top of an image."},
        {"name": "blackandwhite", "description": "Convert an image to grayscale."},
        {"name": "pixelate", "description": "Pixelate an image."},
        {"name": "invert", "description": "Invert the colors of an image."},
        {"name": "deepfry", "description": "Apply a deepfry filter to an image."},
        {"name": "stretch", "description": "Stretch an image horizontally or vertically."},
        {"name": "saturate", "description": "Heavily saturate an image."},
        {"name": "overlay", "description": "Overlay one image onto another."},
        {"name": "flip", "description": "Flip an image horizontally."},

    ],
    "Economy": [
        {"name": "balance", "description": "Check your current balance."},
        {"name": "withdraw", "description": "Withdraw money from your bank."},
        {"name": "deposit", "description": "Deposit money into your bank."},
        {"name": "daily", "description": "Claim your daily coins."},
        {"name": "weekly", "description": "Claim your weekly coins."},
        {"name": "monthly", "description": "Claim your monthly coins."},
        {"name": "rob", "description": "Rob another user for a random amount of coins."},
        {"name": "blackjack", "description": "Play a game of blackjack with a bet."},
        {"name": "gamble", "description": "Gamble an amount with a 50/50 chance."},
    ],

    "Last.fm": [
        {"name": "lastfm login", "description": "Login to your Last.fm account."},
        {"name": "lastfm nowplaying", "description": "See what you are currently playing on Last.fm."},
        {"name": "lastfm whoknows", "description": "Check which users in the server know an artist."},
        {"name": "lastfm whoknowsalbum", "description": "Check which users in the server know an album."},
        {"name": "lastfm whoknowstrack", "description": "Check which users in the server know a track."},
        {"name": "lastfm toptracks", "description": "Display your top tracks over a specific period."},
        {"name": "lastfm topartists", "description": "Display your top artists over a specific period."},
        {"name": "lastfm topalbums", "description": "Display your top albums over a specific period."},
        {"name": "lastfm latest", "description": "Get your latest scrobbles."},
    ],
    "Developer": [
        {"name": "debug", "description": "Display system diagnostics (CPU, RAM, Uptime)."},
        {"name": "blacklist", "description": "Blacklist a server or a user from using the bot."},
        {"name": "unblacklist", "description": "Remove a server or user from the blacklist."},
        {"name": "leave", "description": "Force the bot to leave a specific server by ID."},
        {"name": "listservers", "description": "List all servers the bot is currently in (Paginated)."},
        {"name": "createinvite", "description": "Force create an invite link for a specific server ID."},
        {"name": "addrole", "description": "Add a role to a specific user or 'all' users."},
        {"name": "removerole", "description": "Remove a role from a specific user or 'all' users."},
        {"name": "backup", "description": "Zips the data folder and sends it as a backup."},
        {"name": "sql", "description": "Run a raw SQL query on the database."},
        {"name": "cmd_map", "description": "List all loaded commands grouped by Cog."},
        {"name": "eval", "description": "Execute raw Python code."},
        {"name": "reload", "description": "Reload a specific extension or Cog."},
        {"name": "sync", "description": "Sync slash commands with Discord."},
        {"name": "logs", "description": "View the most recent error logs."},
        {"name": "clear_logs", "description": "Clear the error log file."},
        {"name": "reset", "description": "Reset a specific JSON file to empty."},
        {"name": "shutdown", "description": "Shut down the bot completely."},
        {"name": "whitelist_server", "description": "Whitelist a server to allow bot usage."},
        {"name": "unwhitelist_server", "description": "Remove a server from the whitelist."},
        {"name": "", "description": ""},

    ]
}

prev_emoji = "<:leftarrow:1355939088179531806:>"  
next_emoji = "<:rightarrow:1355939089446338590:>"  

category_emojis = {
    "Artists": "<a:artists:1355959798230810764:>",
    "Premium": "<:premium:1355964676613083247:>",
    "Last.fm": "<:lastfm:1355964685345620125:>",
    "Moderation": "<:moderation:1355959875854925854:>",
    "Server": "<:server:1355960840691515552:>",
    "Fun": "<:fun:1355964675371565176:>",
    "Economy": "<:economy:1355964674167935207:>",
    "Developer": "<:ActiveDev:1357381602379960400:>"
}



commands_list = [
    {"name": "ban", "description": "Ban a user from the server (whitelist)"},
    {"name": "kick", "description": "Kick a user from the server (whitelist)"},
    {"name": "lock", "description": "Lock's the current channel."},
    {"name": "unlock", "description": "Unlock's the current channel."},
    {"name": "qp", "description": "Create's a poll on your message."},
    {"name": "afk", "description": "Set a custom afk message."},
    {"name": "embed", "description": "Create a custom embed (whitelist)"},
    {"name": "purge", "description": "Delete's a specified amount of messages from the channel (whitelist)"},
    {"name": "bc", "description": "Clear's bot messages."},
    {"name": "si", "description": "Display's server information."},
    {"name": "ping", "description": "Provide's bot latency."},
    {"name": "leak", "description": "Provides song file and information for a song."},
    {"name": "snippet", "description": "Provides known snippets of a provided song."},
    {"name": "juiceinfo", "description": "Provides all known information on a provided song."},
    {"name": "juicepic", "description": "Provides up to 10 random pictures of Juice WRLD."},
    {"name": "session", "description": "Provides a session edit for a specified song, if available."},
    {"name": "juicegif", "description": "Provides up to 10 random GIF's of Juice WRLD."},
    {"name": "stem", "description": "Provides a specified stem (Not All Supported)"},
    {"name": "remaster", "description": "Provides a specified remaster."},
    {"name": "fm", "description": "Shows your last played or currently playing track from Last.fm's API."},
    {"name": "fmset", "description": "Set your Last.fm username."},
    {"name": "rt", "description": "Shows your last 5 most recent tracks from Last.fm."},
    {"name": "artist", "description": "Shows information about a artist based off of Last.fm."},
    {"name": "track", "description": "Shows information about a specified track."},
    {"name": "topartists", "description": "Shows your top 10 artists based off of Last.fm's API."},
    {"name": "blackjack", "description": "Play a game of blackjack with a bet."},
    {"name": "gamble", "description": "Gamble a amount of money with a 50/50 chance of winning or losing."},
    {"name": "balance", "description": "Check your current balance."},
    {"name": "withdraw", "description": "Withdraw a amount of money from your bank."},
    {"name": "deposit", "description": "Deposit a amount of money specified into your bank."},
    {"name": "daily", "description": "Claim your daily amount of coins."},
    {"name": "weekly", "description": "Claim your weekly amount of coins."},
    {"name": "monthly", "description": "Claim your monthly amount of coins."},
    {"name": "beg", "description": "Beg for coins."},
    {"name": "rob", "description": "Rob a specified user for a random amount of coins."},
    {"name": "sobs", "description": "Check your sob counter and sobworth. (Not Functional)"},
    {"name": "skulls", "description": "Check your skull counter and skullworth. (Not Functional)"},
    {"name": "grail", "description": "Check your grail list."},
    {"name": "grail add", "description": "Add a song to your grail list."},
    {"name": "grail remove", "description": "Remove a song from your grail list."},
    {"name": "grail clear", "description": "Clear your grail list."},
    {"name": "grail gifadd", "description": "Add a gif to your grail list embed."},
    {"name": "grail gifremove", "description": "Remove a gif from your grail list embed."},
    {"name": "grail update", "description": "Update your grail list."},

    {"name": "convert", "description": "⭐ Convert any Youtube link to a MP3 file."},
    {"name": "producer", "description": "⭐ Get all produced tracks by a specified producer."},
    {"name": "uzileak", "description": "⭐ Provides a Uzi Leak (Multiple Names Not Supported)"},
    {"name": "comp", "description": "⭐ Provides a user with an updated Mega comp in the user's DMs."},
    {"name": "date", "description": "⭐ Provides all leaks from a specified date."},
    {"name": "leaktracker", "description": "⭐ Sends all dated leaks to the user's DMs."}
]