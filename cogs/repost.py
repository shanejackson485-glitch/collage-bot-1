import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import os
import re
import urllib.parse
import json
import asyncio
import aiohttp
import time
import functools
from typing import Optional, Dict, Any, List

CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_DISCORD_SIZE = 25 * 1024 * 1024
TEMP_DIR = "temp_media"

PLATFORM_ICONS = {
    "tiktok": "https://cdn-icons-png.flaticon.com/512/3046/3046120.png",
    "instagram": "https://cdn-icons-png.flaticon.com/512/2111/2111463.png",
    "twitter": "https://cdn-icons-png.flaticon.com/512/733/733579.png",
    "x": "https://cdn-icons-png.flaticon.com/512/733/733579.png",
    "youtube": "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
}

os.makedirs(TEMP_DIR, exist_ok=True)

class Repost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 1800
        self.cleanup_task.start()

    async def cog_unload(self):
        await self.session.close()
        self.cleanup_task.cancel()

    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        now = time.time()
        expiry = 3600
        
        try:
            for filename in os.listdir(TEMP_DIR):
                filepath = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < now - expiry:
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            print(f"Failed to delete {filepath}: {e}")
                            
            expired_keys = [k for k, v in self.cache.items() if now - v['timestamp'] > self.cache_ttl]
            for k in expired_keys:
                del self.cache[k]
        except Exception as e:
            print(f"Cleanup error: {e}")

    def clean_ansi(self, text: str) -> str:
        if not text:
            return ""
        ansi_escape = re.compile(r"(?:\x1B\[[0-?]*[ -/]*[@-~])|(?:\x1B[@-_][0-?]*[ -/]*[@-~])")
        return ansi_escape.sub('', str(text))

    def _is_tiktok_url(self, url: str) -> bool:
        try:
            host = urllib.parse.urlparse(url).netloc.lower()
        except Exception:
            return False
        return any(h in host for h in ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com"))

    async def _resolve_final_url(self, url: str) -> str:
        try:
            async with self.session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                return str(resp.url)
        except Exception:
            try:
                async with self.session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    return str(resp.url)
            except Exception:
                return url

    async def _download_file(self, url: str, out_path: str) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with self.session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return False
                with open(out_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 256):
                        if chunk:
                            f.write(chunk)
            return os.path.exists(out_path) and os.path.getsize(out_path) > 0
        except Exception:
            return False

    async def _download_tiktok_via_tikwm(self, url: str, filename_base: str):
        final_url = await self._resolve_final_url(url)
        api = "https://tikwm.com/api/"
        params = {"url": final_url, "hd": "1"}

        async with self.session.get(api, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                return None, None, f"TikWM API HTTP {resp.status}"
            payload = await resp.json(content_type=None)

        data = (payload or {}).get("data") or {}

        images = data.get("images") or []
        if isinstance(images, list) and images:
            downloaded = []
            for idx, img_url in enumerate(images[:10]):
                ext = ".jpg"
                out_path = os.path.join(TEMP_DIR, f"{filename_base}_{idx}{ext}")
                ok = await self._download_file(img_url, out_path)
                if ok:
                    downloaded.append(out_path)

            if downloaded:
                info = {
                    "webpage_url": final_url,
                    "uploader": (data.get("author") or {}).get("nickname") or "TikTok",
                    "uploader_id": (data.get("author") or {}).get("unique_id") or "unknown",
                    "description": data.get("title") or "",
                    "like_count": data.get("digg_count") or 0,
                    "comment_count": data.get("comment_count") or 0,
                    "view_count": data.get("play_count") or 0,
                }
                return downloaded, info, "slideshow"
            return None, None, "TikWM returned images but none downloaded"

        play_url = data.get("play") or data.get("wmplay")
        if not play_url:
            return None, None, "TikWM missing playable URL"

        out_path = os.path.join(TEMP_DIR, f"{filename_base}.mp4")
        ok = await self._download_file(play_url, out_path)
        if not ok:
            return None, None, "TikWM video download failed"

        info = {
            "webpage_url": final_url,
            "uploader": (data.get("author") or {}).get("nickname") or "TikTok",
            "uploader_id": (data.get("author") or {}).get("unique_id") or "unknown",
            "description": data.get("title") or "",
            "duration": data.get("duration") or 0,
            "like_count": data.get("digg_count") or 0,
            "comment_count": data.get("comment_count") or 0,
            "view_count": data.get("play_count") or 0,
        }
        return out_path, info, "video"

    def format_metric(self, number):
        try:
            n = float(number)
        except (ValueError, TypeError):
            return "0"
        if n >= 1_000_000_000: return f"{n / 1_000_000_000:.1f}b"
        elif n >= 1_000_000: return f"{n / 1_000_000:.1f}m"
        elif n >= 1_000: return f"{n / 1_000:.1f}k"
        return str(int(n))

    async def upload_to_catbox(self, file_path: str) -> Optional[str]:
        try:
            data = aiohttp.FormData()
            data.add_field('reqtype', 'fileupload')
            if os.path.getsize(file_path) > 200 * 1024 * 1024:
                return None
                
            with open(file_path, 'rb') as f:
                data.add_field('fileToUpload', f, filename=os.path.basename(file_path))
                async with self.session.post(CATBOX_URL, data=data) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception as e:
            print(f"Catbox upload failed: {e}")
        return None

    async def is_premium_user(self, user_id: int):
        return True

    async def process_video(self, input_path):
        output_path = os.path.join(TEMP_DIR, f"comp_{os.urandom(4).hex()}.mp4")
        
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-profile:v', 'main', '-level', '4.0',
            '-vf', 'scale=\'min(640,iw)\':-2,fps=30',
            '-preset', 'faster', '-crf', '25',
            '-maxrate', '2M', '-bufsize', '4M',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2',
            '-sn', '-map_metadata', '-1',
            '-movflags', '+faststart+frag_keyframe+empty_moov', output_path
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            print(f"Encoding error: {e}")
        
        return input_path

    async def download_content(self, url: str):
        filename_base = f"raw_{os.urandom(4).hex()}"
        output_template = os.path.join(TEMP_DIR, f"{filename_base}.%(ext)s")

        resolved_url = await self._resolve_final_url(url) if self._is_tiktok_url(url) else url
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "no_color": True,
            "outtmpl": output_template,
            "format": "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[acodec^=mp4a][ext=m4a]/bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "noplaylist": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "cookiefile": "cookies.txt",
            "retries": 3,
            "fragment_retries": 3,
            "extractor_retries": 3,
            "socket_timeout": 20,
            "merge_output_format": "mp4",
            
            "impersonate": "chrome",
            
            "extractor_args": {
                "tiktok": [
                    "web_client_names=web_browser_client",
                    "app_version=20.2.1"
                ]
            },
            
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.tiktok.com/",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            }
        }

        cookie_path = "cookies.txt"
        if os.path.exists(cookie_path):
            ydl_opts["cookiefile"] = cookie_path
            print(f"DEBUG: Using cookies from {cookie_path}")

        try:
            loop = asyncio.get_running_loop()
            func = functools.partial(self._run_ydl, ydl_opts, resolved_url, filename_base)
            info, files = await loop.run_in_executor(None, func)

            if not info:
                if self._is_tiktok_url(resolved_url):
                    return await self._download_tiktok_via_tikwm(resolved_url, filename_base)
                return None, None, "Failed to extract info (blocked request)"

            images = [f for f in files if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            video = next((f for f in files if f.endswith(('.mp4', '.mov', '.mkv', '.webm'))), None)

            if len(images) > 0 and not video:
                return images, info, "slideshow"
            elif video:
                for img in images:
                    try: os.remove(img)
                    except: pass
                return video, info, "video"
            else:
                return None, info, "No video files found"

        except Exception as e:
            error_str = self.clean_ansi(str(e))
            if self._is_tiktok_url(resolved_url):
                try:
                    fb_file, fb_info, fb_type = await self._download_tiktok_via_tikwm(resolved_url, filename_base)
                    if fb_file:
                        return fb_file, fb_info, fb_type
                except Exception as fb_e:
                    error_str = f"{error_str} | Fallback failed: {self.clean_ansi(str(fb_e))}"
            return None, None, error_str

    def _run_ydl(self, opts, url, filename_base):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                created_files = []
                for f in os.listdir(TEMP_DIR):
                    if f.startswith(filename_base):
                        created_files.append(os.path.join(TEMP_DIR, f))
                return info, created_files
        except Exception as e:
            if "Impersonate target" in str(e) or "chrome" in str(e).lower():
                new_opts = opts.copy()
                if "impersonate" in new_opts:
                    del new_opts["impersonate"]
                
                with yt_dlp.YoutubeDL(new_opts) as ydl_retry:
                    info = ydl_retry.extract_info(url, download=True)
                    created_files = []
                    for f in os.listdir(TEMP_DIR):
                        if f.startswith(filename_base):
                            created_files.append(os.path.join(TEMP_DIR, f))
                    return info, created_files
            
            if "extractor_args" in opts:
                opts["extractor_args"]["tiktok"] = ["web_client_names=web_browser_client"]
            with yt_dlp.YoutubeDL(opts) as ydl_retry_final:
                info = ydl_retry_final.extract_info(url, download=True)
                created_files = []
                for f in os.listdir(TEMP_DIR):
                    if f.startswith(filename_base):
                        created_files.append(os.path.join(TEMP_DIR, f))
                return info, created_files


    def build_embed(self, info, ctx_author, media_type="video"):
        web_url = info.get("webpage_url", "")
        domain = urllib.parse.urlparse(web_url).netloc.lower()
        
        platform = "tiktok"
        if "instagram" in domain: platform = "instagram"
        elif "twitter" in domain or "x.com" in domain: platform = "x"
        elif "youtube" in domain or "youtu.be" in domain: platform = "youtube"

        caption = info.get("description", "") or info.get("title", "") or ""

        def replace_mention(match):
            name = match.group(1)
            if platform == "instagram": return f"[`@{name}`](https://www.instagram.com/{name}/)"
            if platform == "x": return f"[`@{name}`](https://x.com/{name})"
            return f"[`@{name}`](https://www.tiktok.com/@{name})"

        def replace_hashtag(match):
            tag = match.group(1)
            if platform == "instagram": return f"[`#{tag}`](https://www.instagram.com/explore/tags/{tag}/)"
            if platform == "x": return f"[`#{tag}`](https://x.com/hashtag/{tag})"
            return f"[`#{tag}`](https://www.tiktok.com/tag/{tag})"

        if len(caption) < 1000:
            caption = re.sub(r"(?<!\w)@(\w+)", replace_mention, caption)
            caption = re.sub(r"(?<!\w)#(\w+)", replace_hashtag, caption)

        embed = discord.Embed(description=caption[:4096], color=discord.Color.from_rgb(43, 45, 49))
        embed.set_author(
            name=f"{info.get('uploader', 'Unknown')} (@{info.get('uploader_id', 'unknown')})",
            icon_url=PLATFORM_ICONS.get(platform, PLATFORM_ICONS["tiktok"]),
            url=web_url
        )
        
        likes = self.format_metric(info.get("like_count", 0))
        comments = self.format_metric(info.get("comment_count", 0))
        views = self.format_metric(info.get("view_count", 0))
        
        footer_text = f"Requested by {ctx_author.display_name} • ❤️ {likes} 💬 {comments} 👁️ {views}"
        if media_type == "video":
            dur = info.get('duration', 0)
            footer_text += f" • ⏱️ {int(dur)}s"
            
        embed.set_footer(text=footer_text)
        return embed

    @commands.hybrid_command(name="repost", description="(Premium) Repost a video/slideshow")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(url="The link to the TikTok, Instagram, or Twitter post")
    async def repost(self, ctx: commands.Context, url: str):
        if ctx.interaction: await ctx.defer()
        else: await ctx.typing()

        if not await self.is_premium_user(ctx.author.id):
            return await ctx.send(embed=discord.Embed(description="🔒 **Premium Only**", color=discord.Color.gold()))

        cached = self.cache.get(url)
        if cached and (time.time() - cached['timestamp'] < self.cache_ttl):
            res = cached['result']
            if isinstance(res, str) and os.path.exists(res):
                await ctx.send(file=discord.File(res), embed=cached['embed'])
                return
            elif isinstance(res, list) and all(os.path.exists(p) for p in res):
                await ctx.send(files=[discord.File(p) for p in res[:4]], embed=cached['embed'])
                return

        file_result, info, type_result = await self.download_content(url)
        
        if not file_result or "failed" in str(type_result):
            error_msg = str(type_result)
            if "Sign in to confirm" in error_msg:
                short_err = "Access Denied: The platform is blocking the bot. Cookies may be required."
            elif "Video unavailable" in error_msg:
                short_err = "The video is private, deleted, or region-locked."
            else:
                short_err = error_msg[:250]
            return await ctx.send(f"❌ **Download Failed**\n`{short_err}`")

        embed = self.build_embed(info, ctx.author, type_result)
        
        temp_files_to_clean = []

        try:
            if type_result == "slideshow":
                files_to_send = [discord.File(img) for img in file_result[:10]]
                await ctx.send(files=files_to_send, embed=embed)
                self.cache[url] = {'result': file_result, 'embed': embed, 'timestamp': time.time()}

            elif type_result == "video":
                duration = info.get('duration', 0) or 0
                final_path = file_result
                file_size = os.path.getsize(file_result)
                

                if file_size > MAX_DISCORD_SIZE or duration > 30:
                    final_path = await self.process_video(file_result)
                    if final_path != file_result:
                        temp_files_to_clean.append(file_result)
                    file_size = os.path.getsize(final_path)

                if file_size <= MAX_DISCORD_SIZE:
                    await ctx.send(file=discord.File(final_path), embed=embed)
                    self.cache[url] = {'result': final_path, 'embed': embed, 'timestamp': time.time()}
                else:
                    catbox_link = await self.upload_to_catbox(final_path)
                    if catbox_link:
                        embed.description = (embed.description or "") + f"\n\n📂 **File too large for Discord**\n[👉 Click to Watch/Download]({catbox_link})"
                        await ctx.send(embed=embed)
                        temp_files_to_clean.append(final_path)
                    else:
                        await ctx.send("❌ File is too large and external upload failed.", embed=embed)
                        temp_files_to_clean.append(final_path)

        except Exception as e:
            print(f"Handler Error: {e}")
            await ctx.send(f"❌ An error occurred processing the media.")
        finally:
            for f in temp_files_to_clean:
                try: 
                    if os.path.exists(f): os.remove(f)
                except: pass

async def setup(bot):
    await bot.add_cog(Repost(bot))