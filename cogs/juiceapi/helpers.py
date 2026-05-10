import aiohttp
import urllib.parse
import json
import os
import pytz
import discord
from datetime import datetime, timedelta
from discord.ext import commands


API_BASE = "https://juicewrldapi.com/juicewrld"
EASTERN_TIMEZONE = pytz.timezone('EST')
COOLDOWN_FILE = 'data/JuiceWRLD/cooldown_data.json'


class JuiceAPI:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    async def get(self, endpoint, params=None):
        endpoint = endpoint.strip("/")
        url = f"{API_BASE}/{endpoint}/" 
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None 
        except Exception as e:
            print(f"API Error: {e}")
            return None

    def get_download_url(self, file_path):
        if not file_path or file_path == "N/A": return None
        clean_path = file_path.strip()
        encoded_path = urllib.parse.quote(clean_path)
        return f"{API_BASE}/files/download/?path={encoded_path}"

    def _normalize_response(self, data):
        if not data: return None
        if isinstance(data, dict) and 'song' in data and isinstance(data['song'], dict):
            song_data = data['song']
            if 'path' in data:
                song_data['file_names'] = data['path']
            return song_data
        if isinstance(data, list):
            return data[0] if len(data) > 0 else None
        if isinstance(data, dict):
            if 'results' in data and isinstance(data['results'], list):
                return data['results'][0] if len(data['results']) > 0 else None
            return data
        return None

    async def get_random_song(self):
        raw_data = await self.get("radio/random")
        return self._normalize_response(raw_data)

    async def search_songs(self, query):
        return await self.get("songs", params={'search': query, 'file_names_array': 'true'})

    async def get_song_by_id(self, pid):
        raw_data = await self.get(f"songs/{pid}", params={'file_names_array': 'true'})
        return self._normalize_response(raw_data)

    async def browse_files(self, path="", params=None):
        p = params if params else {}
        if path: p['path'] = path
        return await self.get("files/browse", params=p)


api_client = JuiceAPI()



def is_premium_user(user_id):
    """Check whitelist files."""
    for file in ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]:
        try:
            if os.path.exists(file):
                with open(file, "r", encoding="utf-8") as f:
                    if str(user_id) in json.load(f).get("whitelisted_ids", []): return True
        except: continue
    return False

class RateLimiter:
    """Handles loading, saving, and checking rate limits."""
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(COOLDOWN_FILE):
            try:
                with open(COOLDOWN_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(COOLDOWN_FILE), exist_ok=True)
            with open(COOLDOWN_FILE, 'w') as f: json.dump(self.data, f, indent=4)
        except: pass

    def check(self, user_id):
        if is_premium_user(user_id): return True
        
        uid = str(user_id)
        if uid not in self.data:
            self.data[uid] = {'uses': 0, 'last_reset': 0}

        user_data = self.data[uid]
        now_est = datetime.now(EASTERN_TIMEZONE)
        today_midnight = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
        

        if user_data.get('last_reset', 0) < today_midnight.timestamp():
            user_data['uses'] = 0
            user_data['last_reset'] = today_midnight.timestamp()

        if user_data['uses'] < 10:
            user_data['uses'] += 1
            self._save()
            return True
        else:
            next_reset = today_midnight + timedelta(days=1)
            user_data['reset_time'] = next_reset.isoformat()
            self._save()
            raise commands.CommandOnCooldown(commands.Cooldown(10, 86400), (next_reset - now_est).total_seconds(), commands.BucketType.user)

    def get_reset_msg(self, user_id):
        uid = str(user_id)
        if reset_iso := self.data.get(uid, {}).get('reset_time'):
            try:
                dt = datetime.fromisoformat(reset_iso)
                return f"The counter will reset automatically at **{dt.strftime('%I:%M %p EST')}**."
            except: pass
        return "The counter will reset automatically at **12:00 AM EST**."


rate_limiter = RateLimiter()


ERA_MAPPING = {
        "GB&GR": {
            "name_long": "Goodbye & Good Riddance", 
            "color": discord.Color.from_rgb(0, 100, 150), 
            "cover_url": r"https://i.ibb.co/Nds1hHVW/goodbyegoodriddance.jpg"
        },
        "WOD": {
            "name_long": "WRLD On Drugs", 
            "color": discord.Color.from_rgb(7, 33, 202),
            "cover_url": r"https://i.ibb.co/gbzZsCPN/wod.jpg"
        },
        "DRFL": {
            "name_long": "Death Race for Love", 
            "color": discord.Color.from_rgb(184, 61, 17),
            "cover_url": r"https://i.ibb.co/20cC9BTC/deathraceforlove.png"
        },
        

        "OUT": {
            "name_long": "Outsiders", 
            "color": discord.Color.from_rgb(22, 18, 19),
            "cover_url": r"https://i.ibb.co/93hFgB16/jw3-cover.jpg"
        },
        "AFFLICTIONS": {
            "name_long": "Affliction", 
            "color": discord.Color.from_rgb(0, 0, 0),
            "cover_url": r"https://i.ibb.co/Dg78D9SL/affliction2.jpg"
        },
        "BDM": {
            "name_long": "BINGEDRINKINGMUSIC", 
            "color": discord.Color.from_rgb(0, 0, 0),
            "cover_url": r"https://i.ibb.co/HLXqCLg9/BINGEDRINKINGMUSIC.jpg"
        },
        "ND": {
            "name_long": "NOTHINGS DIFFERENT </3", 
            "color": discord.Color.from_rgb(204, 84, 55),
            "cover_url": r"https://i.ibb.co/YBFQJX8s/nothingsdifferent.jpg"
        },
        "JW 999": {
            "name_long": "Juice WRLD 999", 
            "color": discord.Color.from_rgb(27, 7, 6),
            "cover_url": r"https://i.ibb.co/spskD3Qj/999.jpg"
        },
        "HIH 999": {
            "name_long": "HEARTBROKEN IN HOLLYWOOD 999", 
            "color": discord.Color.from_rgb(71, 20, 34),
            "cover_url": r"https://i.ibb.co/wNyGCZB7/heartbrokeninhollywood2.jpg"
        },
        "POST": {
            "name_long": "Posthumous", 
            "color": discord.Color.from_rgb(19, 19, 19),
            "cover_url": r"https://i.ibb.co/QF7dCqWY/posthumous.webp"
        },
        "JUTE": {
            "name_long": "JUICED UP THE EP", 
            "color": discord.Color.from_rgb(87, 141, 207),
            "cover_url": r"https://i.ibb.co/20bWyHmg/juiceduptheep.jpg"
        },

        "DEFAULT": {
            "name_long": "Unreleased", 
            "color": discord.Color.from_rgb(100, 100, 100), 
            "cover_url": "YOUR_DEFAULT_COVER_URL" 
        }
    }