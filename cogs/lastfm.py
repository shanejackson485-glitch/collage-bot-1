import discord
from discord.ext import commands
from discord import app_commands, ui
import aiohttp
import asyncio
import json
import os
import urllib.parse
import io
import time
from typing import Optional, List, Union, Dict, Any
from PIL import Image
from config import LASTFM_API_KEY


DATA_FILE = "data/LastFM/lastfm_users.json"


VALID_PERIODS = [
    app_commands.Choice(name="7 days", value="7day"),
    app_commands.Choice(name="1 month", value="1month"),
    app_commands.Choice(name="3 months", value="3month"),
    app_commands.Choice(name="6 months", value="6month"),
    app_commands.Choice(name="1 year", value="12month"),
    app_commands.Choice(name="lifetime", value="overall")
]

PERIOD_DISPLAY = {
    "7day": "last 7 days",
    "1month": "last month",
    "3month": "last 3 months",
    "6month": "last 6 months",
    "12month": "last year",
    "overall": "lifetime"
}


class Paginator(ui.View):
    def __init__(self, ctx, pages: List[Union[discord.Embed, str]], timeout=120):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.pages = pages
        self.current = 0
        self.message = None
        

        self.clear_items()
        

        if len(self.pages) > 1:
            self.setup_buttons()

    def setup_buttons(self):

        btn_first = ui.Button(emoji="⏮️", style=discord.ButtonStyle.secondary)
        btn_first.callback = self.first_page
        self.add_item(btn_first)

        btn_prev = ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary)
        btn_prev.callback = self.prev_page
        self.add_item(btn_prev)

        self.indicator_btn = ui.Button(label=f"1/{len(self.pages)}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(self.indicator_btn)

        btn_next = ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary)
        btn_next.callback = self.next_page
        self.add_item(btn_next)

        btn_last = ui.Button(emoji="⏭️", style=discord.ButtonStyle.secondary)
        btn_last.callback = self.last_page
        self.add_item(btn_last)

    def add_link_button(self, url: str, emoji: discord.PartialEmoji):
        if url and url.startswith("http"):
            self.add_item(ui.Button(style=discord.ButtonStyle.link, url=str(url), emoji=emoji))

    async def first_page(self, interaction: discord.Interaction):
        self.current = 0
        await self.update_message(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        self.current = (self.current - 1) % len(self.pages)
        await self.update_message(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.current = (self.current + 1) % len(self.pages)
        await self.update_message(interaction)

    async def last_page(self, interaction: discord.Interaction):
        self.current = len(self.pages) - 1
        await self.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        if hasattr(self, 'indicator_btn'):
            self.indicator_btn.label = f"{self.current + 1}/{len(self.pages)}"

        
        page = self.pages[self.current]
        kwargs = {"view": self}
        if isinstance(page, discord.Embed):
            kwargs["embed"] = page
            kwargs["content"] = None
        else:
            kwargs["content"] = str(page)
            kwargs["embed"] = None
        
        try:
            await interaction.response.edit_message(**kwargs)
        except: pass

    async def start(self):
        page = self.pages[0]
        kwargs = {"view": self}
        if isinstance(page, discord.Embed): kwargs["embed"] = page
        else: kwargs["content"] = str(page)
        self.message = await self.ctx.send(**kwargs)



class LastFMCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.data = self._load_data()
        self.cache = {} 

    def cog_unload(self):
        asyncio.create_task(self.session.close())


    def _load_data(self):
        if not os.path.exists(DATA_FILE):
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            return {}
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_user_data(self, user_id: int):
        uid = str(user_id)
        if uid in self.data:
            user = self.data[uid]
            if isinstance(user, str): return user, False
            return user.get("username"), user.get("hidden", False)
        return None

    async def set_user_data(self, user_id: int, username: str, hidden: bool = False):
        self.data[str(user_id)] = {"username": username, "hidden": hidden}
        self._save_data()


    async def get_dominant_color(self, image_input):
        try:
            if isinstance(image_input, str): 
                async with self.session.get(image_input) as resp:
                    if resp.status != 200: return discord.Color.default()
                    data = await resp.read()
            else:
                data = image_input

            def _process():
                try:
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    img = img.resize((64, 64)) 
                    pixels = list(img.getdata())
                    if not pixels: return discord.Color.default()
                    r = sum(p[0] for p in pixels) // len(pixels)
                    g = sum(p[1] for p in pixels) // len(pixels)
                    b = sum(p[2] for p in pixels) // len(pixels)
                    return discord.Color.from_rgb(r, g, b)
                except:
                    return discord.Color.default()

            return await asyncio.to_thread(_process)
        except:
            return discord.Color.default()

    async def get_spotify_link(self, query):
        url = "https://api.stats.fm/api/v1/search/elastic"
        params = {"query": query, "type": "track", "limit": "1"}
        headers = {"User-Agent": "Heist/3.0"}
        try:
            async with self.session.get(url, params=params, headers=headers, timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    tracks = data.get("items", {}).get("tracks", [])
                    if tracks:
                        t = tracks[0]
                        if t.get("externalIds", {}).get("spotify"):
                            return f"https://open.spotify.com/track/{t['externalIds']['spotify'][0]}"
        except: pass
        return None



    @commands.hybrid_group(name="lastfm", aliases=["lf", "fm"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def lastfm_group(self, ctx: commands.Context):
        """Last.fm commands. Use without subcommand for Now Playing."""
        if ctx.invoked_subcommand is None:
            await self.nowplaying(ctx)

    @lastfm_group.command(name="login", description="Link your Last.fm account")
    async def login(self, ctx: commands.Context, username: str, hidden: bool = False):
        await self.set_user_data(ctx.author.id, username, hidden)
        await ctx.send(embed=discord.Embed(description=f"✅ Last.fm username set to **{username}**.", color=0xD51007))

    @lastfm_group.command(name="nowplaying", aliases=["np", "playing", "fm"])
    async def nowplaying(self, ctx: commands.Context, username: Optional[str] = None):
        """See what you are currently playing on Last.fm."""
        async with ctx.typing():

            if username is None:
                user_data = self.get_user_data(ctx.author.id)
                if not user_data: 
                    return await ctx.send(f"❌ Not logged in. Use `/lastfm login`.")
                lastfm_username, hidden = user_data
                display_name = ctx.author.display_name 
                avatar_url = ctx.author.display_avatar.url
            else:
                lastfm_username, hidden = username, False
                display_name = lastfm_username
                avatar_url = None 


            base_url = "https://ws.audioscrobbler.com/2.0/"
            params = {
                "method": "user.getrecenttracks", 
                "user": lastfm_username, 
                "api_key": LASTFM_API_KEY, 
                "format": "json", 
                "limit": 1
            }

            try:
                async with self.session.get(base_url, params=params) as r:
                    data = await r.json()
            except Exception:
                return await ctx.send("❌ Failed to communicate with Last.fm.")

            if "error" in data: 
                return await ctx.send(f"❌ Last.fm Error: {data.get('message', 'Unknown Error')}")
            
            tracks = data.get("recenttracks", {}).get("track", [])
            if not tracks: 
                return await ctx.send(f"No tracks found for `{lastfm_username}`.")

            track = tracks[0]


            artist = str(track["artist"]["#text"])
            name = str(track["name"])
            album = str(track.get("album", {}).get("#text", ""))
            display_album = album if album else "Unknown"
            
            now_playing = "@attr" in track and track["@attr"].get("nowplaying") == "true"
            
            image_url = None
            images = track.get("image", [])
            if images and isinstance(images, list) and len(images) > 0:
                image_url = images[-1].get("#text")
            
            if not avatar_url and image_url:
                avatar_url = image_url


            safe_artist = urllib.parse.quote(artist)
            safe_name = urllib.parse.quote(name)
            
            t_url = f"{base_url}?method=track.getInfo&api_key={LASTFM_API_KEY}&artist={safe_artist}&track={safe_name}&username={lastfm_username}&format=json"
            u_url = f"{base_url}?method=user.getinfo&user={lastfm_username}&api_key={LASTFM_API_KEY}&format=json"
            
            reqs = [self.session.get(t_url), self.session.get(u_url)]

            if album:
                safe_album = urllib.parse.quote(album)
                a_url = f"{base_url}?method=album.getInfo&api_key={LASTFM_API_KEY}&artist={safe_artist}&album={safe_album}&username={lastfm_username}&format=json"
                reqs.append(self.session.get(a_url))

            responses = await asyncio.gather(*reqs, return_exceptions=True)
            
            track_plays = "0"
            total_plays = "0"
            album_plays = "0"

            if isinstance(responses[0], aiohttp.ClientResponse) and responses[0].status == 200:
                d = await responses[0].json()
                track_plays = str(d.get("track", {}).get("userplaycount", "0"))
            
            if isinstance(responses[1], aiohttp.ClientResponse) and responses[1].status == 200:
                d = await responses[1].json()
                total_plays = str(d.get("user", {}).get("playcount", "0"))

            if album and len(responses) > 2 and isinstance(responses[2], aiohttp.ClientResponse) and responses[2].status == 200:
                d = await responses[2].json()
                album_plays = str(d.get("album", {}).get("userplaycount", "0"))


            color = await self.get_dominant_color(image_url) if image_url else ctx.author.color


            embed = discord.Embed(
                title=f"{'Now Playing' if now_playing else 'Last Played'}",
                color=color
            )

            embed.set_author(
                name=f"{display_name} ({lastfm_username})",
                url=f"https://www.last.fm/user/{lastfm_username}",
                icon_url=avatar_url or ""
            )

            embed.add_field(
                name="**Track**",
                value=f"[{name}](https://www.last.fm/music/{safe_artist}/{safe_name})",
                inline=True,
            )
            embed.add_field(
                name="**Artist**",
                value=f"[{artist}](https://www.last.fm/music/{safe_artist})",
                inline=True,
            )

            footer_text = f"Track: {track_plays} | Album: {album_plays} | Total: {total_plays} | Album: {display_album}"
            embed.set_footer(text=footer_text)
            
            if image_url:
                embed.set_thumbnail(url=image_url)


            msg = await ctx.send(embed=embed)
            

            if ctx.interaction is None:
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")



    async def _whoknows_helper(self, ctx, mode, query=None):

        if not ctx.guild:
            return await ctx.send("❌ 'Who Knows' commands can only be used inside servers, not DMs.")
            
        await ctx.defer()
        target_artist, target_track, target_album = None, None, None


        if query:
            if " - " in query:
                parts = query.split(" - ", 1)
                target_artist = parts[0].strip()
                if mode == "track": target_track = parts[1].strip()
                elif mode == "album": target_album = parts[1].strip()
            else:
                if mode == "artist":
                    target_artist = query
                else:

                    method = "track.search" if mode == "track" else "album.search"
                    key = "track" if mode == "track" else "album"
                    url = f"https://ws.audioscrobbler.com/2.0/?method={method}&{key}={urllib.parse.quote(query)}&api_key={LASTFM_API_KEY}&format=json&limit=1"
                    async with self.session.get(url) as r:
                        d = await r.json()
                        matches = d.get("results", {}).get(f"{key}matches", {}).get(key, [])
                        if not matches: return await ctx.send(f"❌ Could not find {mode}.")
                        target_artist = matches[0]["artist"] if isinstance(matches[0]["artist"], str) else matches[0]["artist"]["name"]
                        if mode == "track": target_track = matches[0]["name"]
                        elif mode == "album": target_album = matches[0]["name"]
        else:

            udata = self.get_user_data(ctx.author.id)
            if not udata: return await ctx.send("❌ Log in or provide a query.")
            url = f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={udata[0]}&api_key={LASTFM_API_KEY}&format=json&limit=1"
            async with self.session.get(url) as r:
                d = await r.json()
                if not d.get("recenttracks", {}).get("track"): return await ctx.send("No recent tracks.")
                t = d["recenttracks"]["track"][0]
                target_artist = t["artist"]["#text"]
                target_track = t["name"]
                target_album = t.get("album", {}).get("#text")

        if mode == "track" and not target_track: return await ctx.send("Could not resolve track.")
        if mode == "album" and not target_album: return await ctx.send("Could not resolve album.")


        guild_users = []
        for member in ctx.guild.members:
            udata = self.get_user_data(member.id)
            if udata: guild_users.append((member, udata[0], udata[1]))

        if not guild_users: return await ctx.send("No one in this server uses the bot.")


        listeners = []
        sem = asyncio.Semaphore(8)

        async def fetch(member, username, hidden):
            async with sem:
                params = {"api_key": LASTFM_API_KEY, "username": username, "format": "json"}
                if mode == "artist":
                    params["method"] = "artist.getinfo"; params["artist"] = target_artist
                elif mode == "album":
                    params["method"] = "album.getinfo"; params["artist"] = target_artist; params["album"] = target_album
                elif mode == "track":
                    params["method"] = "track.getinfo"; params["artist"] = target_artist; params["track"] = target_track
                
                try:
                    async with self.session.get("https://ws.audioscrobbler.com/2.0/", params=params) as r:
                        if r.status == 200:
                            d = await r.json()
                            if mode == "artist": plays = int(d.get("artist", {}).get("stats", {}).get("userplaycount", 0))
                            elif mode == "album": plays = int(d.get("album", {}).get("userplaycount", 0))
                            elif mode == "track": plays = int(d.get("track", {}).get("userplaycount", 0))
                            
                            if plays > 0: listeners.append({"member": member, "username": username, "hidden": hidden, "plays": plays})
                except: pass

        await asyncio.gather(*(fetch(*u) for u in guild_users))

        if not listeners:
            item = target_artist
            if mode == "album": item = target_album
            elif mode == "track": item = target_track
            return await ctx.send(f"No one knows **{item}**.")


        listeners.sort(key=lambda x: x["plays"], reverse=True)
        total_plays = sum(l["plays"] for l in listeners)
        
        desc = []
        for i, l in enumerate(listeners[:15], 1):
            name = l["member"].display_name
            if l["hidden"]: desc.append(f"{i}. **{name}** — {l['plays']:,} plays")
            else: desc.append(f"{i}. [**{name}**](https://last.fm/user/{l['username']}) — {l['plays']:,} plays")

        title_item = target_artist
        if mode == "album": title_item = target_album
        elif mode == "track": title_item = target_track
        
        embed = discord.Embed(title=f"Who knows {title_item}?", description="\n".join(desc), color=ctx.author.color)
        embed.set_footer(text=f"{mode.capitalize()} • {len(listeners)} listeners • {total_plays:,} plays")
        await ctx.send(embed=embed)

    @lastfm_group.command(name="whoknows", aliases=["wk"])
    async def whoknows_artist(self, ctx, *, query: Optional[str] = None):
        """See who in the server knows your current artist."""
        await self._whoknows_helper(ctx, "artist", query)

    @lastfm_group.command(name="whoknowsalbum", aliases=["wka"])
    async def whoknows_album(self, ctx, *, query: Optional[str] = None):
        """See who in the server knows your current album."""
        await self._whoknows_helper(ctx, "album", query)

    @lastfm_group.command(name="whoknowstrack", aliases=["wkt"])
    async def whoknows_track(self, ctx, *, query: Optional[str] = None):
        """See who in the server knows your current track."""
        await self._whoknows_helper(ctx, "track", query)



    async def _top_logic(self, ctx, item_type, period, username):
        async with ctx.typing():
            if username is None:
                udata = self.get_user_data(ctx.author.id)
                if not udata: return await ctx.send("Not logged in.")
                username, hidden = udata
            else: hidden = False

            params = {
                "method": f"user.gettop{item_type}", "user": username, "period": period,
                "api_key": LASTFM_API_KEY, "format": "json", "limit": 50
            }
            async with self.session.get("https://ws.audioscrobbler.com/2.0/", params=params) as r:
                d = await r.json()
            
            key = f"top{item_type}"
            inner_key = item_type[:-1]
            items = d.get(key, {}).get(inner_key, [])
            if not items: return await ctx.send("No items found.")

            pages = []
            per_page = 10
            display_name = ctx.author.display_name if hidden else username

            for i in range(0, len(items), per_page):
                chunk = items[i:i+per_page]
                desc = ""
                for idx, item in enumerate(chunk, start=i+1):
                    name = item['name']
                    count = item.get('playcount', '0')
                    url = item.get('url', '')
                    if item_type == "tracks":
                        artist = item.get("artist", {}).get("name", "Unknown")
                        desc += f"{idx}. **[{name}]({url})** by {artist} ({count})\n"
                    else:
                        desc += f"{idx}. **[{name}]({url})** ({count})\n"
                
                embed = discord.Embed(
                    title=f"Top {item_type.capitalize()} ({PERIOD_DISPLAY.get(period, period)})",
                    description=desc, color=ctx.author.color
                )
                embed.set_author(name=display_name, icon_url=ctx.author.display_avatar.url)
                pages.append(embed)

            await Paginator(ctx, pages).start()

    @lastfm_group.command(name="toptracks", aliases=["tt"])
    @app_commands.choices(period=VALID_PERIODS)
    async def toptracks(self, ctx, username: Optional[str]=None, period: str="7day"):
        """View your top tracks within a specified time period."""
        await self._top_logic(ctx, "tracks", period, username)

    @lastfm_group.command(name="topartists", aliases=["ta"])
    @app_commands.choices(period=VALID_PERIODS)
    async def topartists(self, ctx, username: Optional[str]=None, period: str="7day"):
        """View your top artists within a specified time period."""
        await self._top_logic(ctx, "artists", period, username)

    @lastfm_group.command(name="topalbums", aliases=["talb"])
    @app_commands.choices(period=VALID_PERIODS)
    async def topalbums(self, ctx, username: Optional[str]=None, period: str="7day"):
        """View your top albums within a specified time period."""
        await self._top_logic(ctx, "albums", period, username)



    @lastfm_group.command(name="latest", aliases=["recent", "rt"])
    async def latest(self, ctx, username: Optional[str] = None):
        """View your latest tracks."""
        async with ctx.typing():
            if username is None:
                udata = self.get_user_data(ctx.author.id)
                if not udata: return await ctx.send("Not logged in.")
                username, hidden = udata
            else: hidden = False

            params = {
                "method": "user.getrecenttracks", "user": username,
                "api_key": LASTFM_API_KEY, "format": "json", "limit": 50
            }
            async with self.session.get("https://ws.audioscrobbler.com/2.0/", params=params) as r:
                d = await r.json()
            
            tracks = d.get("recenttracks", {}).get("track", [])
            if not tracks: return await ctx.send("No tracks found.")
            total_scrobbles = d.get("recenttracks", {}).get("@attr", {}).get("total", "0")

            pages = []
            per_page = 10
            display_name = ctx.author.display_name if hidden else username

            for i in range(0, len(tracks), 10):
                chunk = tracks[i:i+10]
                desc = ""
                for t in chunk:
                    name = str(t['name'])
                    artist = str(t['artist']['#text'])
                    url = t.get("url", "")
                    ts_str = ""
                    if "date" in t:
                        ts_str = f" <t:{t['date']['uts']}:R>"
                    else:
                        ts_str = " **(Now Playing)**"
                    
                    desc += f"**[{name}]({url})** by {artist}{ts_str}\n"

                embed = discord.Embed(description=str(desc), color=ctx.author.color)
                embed.set_author(name=f"Recent Tracks - {display_name}", icon_url=ctx.author.display_avatar.url)
                embed.set_footer(text=f"Total scrobbles: {total_scrobbles}")
                pages.append(embed)

            await Paginator(ctx, pages).start()


async def setup(bot):
    await bot.add_cog(LastFMCog(bot))