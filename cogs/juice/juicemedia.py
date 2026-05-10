import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import re
import json
import asyncio
import mimetypes
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import secrets
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

import aiohttp


from .helpers import (
    IMAGE_DIRECTORY, 
    COVERS_FOLDER, 
    COVER_CACHE_FILE, 
    COVER_CACHE_CHANNEL_ID
)




class JuiceMedia(commands.Cog):
    """Handles random media commands like Images and GIFs."""
    def __init__(self, bot):
        self.bot = bot

        self.cover_image_url = "https://i.ibb.co/PshC2Lcx/sessions.jpg"


        self._components_v2_flag = 1 << 15



        self._media_sessions: Dict[str, dict] = {}




        self._page_size = 10
        self._max_session_items = 100

    def _prune_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._media_sessions.items() if (now - s["created_at"]) > timedelta(minutes=30)]
        for sid in expired:
            self._media_sessions.pop(sid, None)

    def _safe_attachment_filename(self, filename: str, *, prefix: str = "") -> str:
        base, ext = os.path.splitext(filename)
        ext = (ext or "").lower()


        safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", base).strip("._-")
        if not safe_base:
            safe_base = "file"

        safe = f"{prefix}{safe_base}{ext}"
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", safe)
        return safe

    def _build_v2_media_payload(
        self,
        *,
        title: str,
        attachment_filenames: List[str],
        accent_color: Optional[int] = 0xF1C40F,
        pager: Optional[dict] = None,
    ) -> dict:

        galleries = []
        if attachment_filenames:
            galleries.append({
                "type": 12,
                "items": [{"media": {"url": f"attachment://{name}"}} for name in attachment_filenames],
            })

        container_children: List[dict] = [
            {"type": 10, "content": title},
        ]
        if galleries:
            container_children.append({"type": 14, "divider": True, "spacing": 1})
            container_children.extend(galleries)

        if pager is not None:
            container_children.append({"type": 14, "divider": True, "spacing": 1})
            container_children.append(pager)

        container = {"type": 17, "components": container_children}
        if accent_color is not None:
            container["accent_color"] = int(accent_color)

        return {"flags": self._components_v2_flag, "components": [container], "allowed_mentions": {"parse": []}}

    async def _post_v2_message_to_channel(self, *, channel_id: int, payload: dict, files: List[Tuple[str, str]]) -> int:
        """Send a Components V2 message to a channel via bot-authenticated Create Message."""
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {self.bot.http.token}"}


        payload = dict(payload)
        payload["attachments"] = [{"id": i, "filename": filename} for i, (_, filename) in enumerate(files)]

        form = aiohttp.FormData()
        form.add_field("payload_json", json.dumps(payload), content_type="application/json")

        with ExitStack() as stack:
            for i, (path, filename) in enumerate(files):
                fp = stack.enter_context(open(path, "rb"))
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(f"files[{i}]", fp, filename=filename, content_type=content_type)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, headers=headers) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise RuntimeError(f"Discord API error {resp.status}: {text}")
                    data = await resp.json()
                    return int(data["id"])

        raise RuntimeError("Failed to send message")

    async def _patch_v2_message_in_channel(self, *, channel_id: int, message_id: int, payload: dict, files: List[Tuple[str, str]]) -> None:
        """Edit an existing message (already using Components V2) via bot-authenticated Edit Message."""
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        headers = {"Authorization": f"Bot {self.bot.http.token}"}

        payload = dict(payload)
        payload["attachments"] = [{"id": i, "filename": filename} for i, (_, filename) in enumerate(files)]

        form = aiohttp.FormData()
        form.add_field("payload_json", json.dumps(payload), content_type="application/json")

        with ExitStack() as stack:
            for i, (path, filename) in enumerate(files):
                fp = stack.enter_context(open(path, "rb"))
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(f"files[{i}]", fp, filename=filename, content_type=content_type)

            async with aiohttp.ClientSession() as session:
                async with session.patch(url, data=form, headers=headers) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise RuntimeError(f"Discord API error {resp.status}: {text}")

    async def _upsert_v2_interaction_message(self, *, interaction: discord.Interaction, payload: dict, files: List[Tuple[str, str]], edit_original: bool) -> int:
        """Send or edit an interaction response using webhook endpoints (supports multipart)."""
        app_id = interaction.application_id
        token = interaction.token

        if edit_original:

            method = "PATCH"
            url = f"https://discord.com/api/v10/webhooks/{app_id}/{token}/messages/@original"
        else:

            method = "POST"
            url = f"https://discord.com/api/v10/webhooks/{app_id}/{token}?wait=true"

        payload = dict(payload)
        payload["attachments"] = [{"id": i, "filename": filename} for i, (_, filename) in enumerate(files)]

        form = aiohttp.FormData()
        form.add_field("payload_json", json.dumps(payload), content_type="application/json")

        with ExitStack() as stack:
            for i, (path, filename) in enumerate(files):
                fp = stack.enter_context(open(path, "rb"))
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(f"files[{i}]", fp, filename=filename, content_type=content_type)

            async with aiohttp.ClientSession() as session:
                req = session.patch if method == "PATCH" else session.post
                async with req(url, data=form) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise RuntimeError(f"Discord API error {resp.status}: {text}")
                    data = await resp.json()
                    return int(data["id"])

        raise RuntimeError("Failed to send interaction message")

    def _build_pager_row(self, *, session_id: str, page_index: int, total_pages: int) -> dict:
        prev_disabled = page_index <= 0
        next_disabled = page_index >= (total_pages - 1)
        return {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "label": "Prev",
                    "custom_id": f"jm:{session_id}:prev",
                    "disabled": prev_disabled,
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": f"Page {page_index + 1}/{total_pages}",
                    "custom_id": f"jm:{session_id}:noop",
                    "disabled": True,
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": "Next",
                    "custom_id": f"jm:{session_id}:next",
                    "disabled": next_disabled,
                },
            ],
        }

    def _get_page(self, items: List[Tuple[str, str]], page_index: int, page_size: int) -> List[Tuple[str, str]]:
        start = page_index * page_size
        end = start + page_size
        return items[start:end]

    def _build_page_files(self, *, items: List[Tuple[str, str]], page_index: int) -> List[Tuple[str, str]]:
        page_items = self._get_page(items, page_index, self._page_size)
        pairs: List[Tuple[str, str]] = []
        for i, (path, original_name) in enumerate(page_items):
            safe_name = self._safe_attachment_filename(original_name, prefix=f"p{page_index}_{i}_")
            pairs.append((path, safe_name))
        return pairs

    async def _send_or_edit_page(
        self,
        *,
        kind: str,
        session_id: str,
        channel_id: int,
        message_id: Optional[int],
        items: List[Tuple[str, str]],
        page_index: int,
        accent_color: int,
        header: str,
        interaction: Optional[discord.Interaction] = None,
    ) -> int:
        total_pages = max(1, (len(items) + self._page_size - 1) // self._page_size)
        page_index = max(0, min(page_index, total_pages - 1))
        page_files = self._build_page_files(items=items, page_index=page_index)

        title = f"{header} (Page {page_index + 1}/{total_pages})"
        pager = self._build_pager_row(session_id=session_id, page_index=page_index, total_pages=total_pages) if total_pages > 1 else None
        payload = self._build_v2_media_payload(
            title=title,
            attachment_filenames=[fn for _, fn in page_files],
            accent_color=accent_color,
            pager=pager,
        )


        if message_id is None:
            if interaction is not None:
                return await self._upsert_v2_interaction_message(
                    interaction=interaction,
                    payload=payload,
                    files=page_files,
                    edit_original=True,
                )
            return await self._post_v2_message_to_channel(channel_id=channel_id, payload=payload, files=page_files)


        await self._patch_v2_message_in_channel(channel_id=channel_id, message_id=message_id, payload=payload, files=page_files)
        return message_id

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if interaction.type != discord.InteractionType.component:
            return

        data = getattr(interaction, "data", None) or {}
        custom_id = data.get("custom_id") if isinstance(data, dict) else None
        if not custom_id or not custom_id.startswith("jm:"):
            return

        parts = custom_id.split(":", 2)
        if len(parts) != 3:
            return

        _, session_id, action = parts

        self._prune_sessions()
        session = self._media_sessions.get(session_id)
        if not session:
            try:
                await interaction.response.send_message("⏰ This pager expired. Please run the command again.", ephemeral=True)
            except Exception:
                pass
            return

        if interaction.user.id != session["user_id"]:
            try:
                await interaction.response.send_message("❌ Only the command invoker can use these buttons.", ephemeral=True)
            except Exception:
                pass
            return


        if action == "noop":
            try:
                await interaction.response.defer()
            except Exception:
                pass
            return


        try:
            await interaction.response.defer()
        except Exception:
            pass


        page_index = session.get("page_index", 0)
        if action == "prev":
            page_index -= 1
        elif action == "next":
            page_index += 1
        else:
            return

        total_pages = max(1, (len(session["items"]) + session["page_size"] - 1) // session["page_size"])
        page_index = max(0, min(page_index, total_pages - 1))
        session["page_index"] = page_index

        try:
            await self._send_or_edit_page(
                kind=session["kind"],
                session_id=session_id,
                channel_id=interaction.channel_id,
                message_id=interaction.message.id if interaction.message else None,
                items=session["items"],
                page_index=page_index,
                accent_color=session["accent_color"],
                header=session["header"],
                interaction=None,
            )
        except Exception:

            return


    @commands.hybrid_command(
        name="juicepic",
        description="Send random Juice WRLD images from the collection."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def juicepic(self, ctx: commands.Context, number: int = 1):
        """Sends random images from the specified directory."""
        if ctx.interaction:
            await ctx.defer()
            
        try:

            if not os.path.exists(IMAGE_DIRECTORY):
                if ctx.interaction:
                    await ctx.reply("❌ Image directory configuration is invalid.", ephemeral=True)
                else:
                    await ctx.reply("❌ Image directory configuration is invalid.")
                return

            image_files = [
                f for f in os.listdir(IMAGE_DIRECTORY)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
            ]

            if not image_files:
                if ctx.interaction:
                    await ctx.reply("No images found in the directory.", ephemeral=True)
                else:
                    await ctx.reply("No images found in the directory.")
                return


            self._prune_sessions()
            number = max(1, min(number, len(image_files), self._max_session_items))
            selected = random.sample(image_files, number)
            items = [(os.path.join(IMAGE_DIRECTORY, name), name) for name in selected]

            session_id = secrets.token_urlsafe(8)
            self._media_sessions[session_id] = {
                "user_id": ctx.author.id,
                "kind": "juicepic",
                "items": items,
                "page_size": self._page_size,
                "page_index": 0,
                "created_at": datetime.now(timezone.utc),
                "accent_color": 0xF1C40F,
                "header": f"Here are {number} random images",
            }

            message_id = await self._send_or_edit_page(
                kind="juicepic",
                session_id=session_id,
                channel_id=ctx.channel.id,
                message_id=None,
                items=items,
                page_index=0,
                accent_color=0xF1C40F,
                header=f"Here are {number} random images",
                interaction=ctx.interaction if ctx.interaction else None,
            )


            if len(self._media_sessions) > 200:
                self._prune_sessions()

        except Exception as e:
            if ctx.interaction:
                await ctx.reply(f"An error occurred: `{str(e)}`", ephemeral=True)
            else:
                await ctx.reply(f"An error occurred: `{str(e)}`")


    @commands.hybrid_command(
        name="juicegif",
        with_app_command=True,
        description="Sends a random Juice WRLD GIF (up to 5 at a time)."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def juicegif(self, ctx: commands.Context, count: int = 1):
        """Sends a random Juice WRLD GIF."""
        if ctx.interaction:
            await ctx.defer()


        gif_folder = r'D:\JBDB\gifs'

        if not os.path.isdir(gif_folder):
            return await ctx.send("❌ GIF folder not found. Please contact the bot owner.")

        gif_files = [f for f in os.listdir(gif_folder) if f.lower().endswith('.gif')]
        if not gif_files:
            return await ctx.send("🤷 No GIFs found in the folder.")


        self._prune_sessions()
        count = max(1, min(count, len(gif_files), self._max_session_items))
        selected = random.sample(gif_files, count)
        items = [(os.path.join(gif_folder, name), name) for name in selected]

        session_id = secrets.token_urlsafe(8)
        self._media_sessions[session_id] = {
            "user_id": ctx.author.id,
            "kind": "juicegif",
            "items": items,
            "page_size": self._page_size,
            "page_index": 0,
            "created_at": datetime.now(timezone.utc),
            "accent_color": 0x9B59B6,
            "header": f"Here are {count} random GIFs",
        }

        try:
            await self._send_or_edit_page(
                kind="juicegif",
                session_id=session_id,
                channel_id=ctx.channel.id,
                message_id=None,
                items=items,
                page_index=0,
                accent_color=0x9B59B6,
                header=f"Here are {count} random GIFs",
                interaction=ctx.interaction if ctx.interaction else None,
            )
        except Exception as e:
            if ctx.interaction:
                await ctx.reply(f"An error occurred: `{str(e)}`", ephemeral=True)
            else:
                await ctx.reply(f"An error occurred: `{str(e)}`")





class Cover(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover_index = {} 
        self.cache = {}
        self.is_indexing = True
        
        self.bot.loop.create_task(self.load_cache())
        self.bot.loop.create_task(self.build_index())

    @lru_cache(maxsize=50000)
    def normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return " ".join(text.split())

    async def build_index(self):
        self.is_indexing = True
        print("[Cover Cog] Building index...")
        
        def scan_disk():
            index = {}
            count = 0
            if os.path.exists(COVERS_FOLDER):
                for root, dirs, files in os.walk(COVERS_FOLDER):
                    for file in files:
                        filename, ext = os.path.splitext(file)
                        if ext.lower() not in [".png", ".jpg", ".jpeg"]:
                            continue
                        norm_name = self.normalize(filename)
                        index.setdefault(norm_name, []).append(os.path.join(root, file))
                        count += 1
            return index, count

        self.cover_index, count = await self.bot.loop.run_in_executor(None, scan_disk)
        self.is_indexing = False
        print(f"[Cover Cog] Indexed {count} covers.")

    async def load_cache(self):
        if os.path.exists(COVER_CACHE_FILE):
            try:
                with open(COVER_CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
        else:
            self.cache = {}

    async def save_cache(self):
        def write():
            with open(COVER_CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=4)
        await self.bot.loop.run_in_executor(None, write)

    @commands.hybrid_command(name="cover", description="Search and display cover images by song name.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def cover(self, ctx: commands.Context, *, query: str):
        if self.is_indexing:
            await ctx.reply("⚠️ The bot is currently indexing covers. Please wait a moment.", ephemeral=True)
            return

        search_query = self.normalize(query)
        
        progress_embed = discord.Embed(
            title="<a:GTALoading:1348124710394662995> Searching for covers...",
            description=f"Please wait while I search for **{query}**.",
            color=discord.Color.yellow()
        )
        
        if ctx.interaction:
            await ctx.interaction.response.defer()
            progress_msg = await ctx.interaction.followup.send(embed=progress_embed, wait=True)
        else:
            progress_msg = await ctx.send(embed=progress_embed)

        matched_keys = []
        pattern = re.compile(r'\b' + re.escape(search_query))

        if search_query in self.cover_index:
            matched_keys.append(search_query)
        
        for key in self.cover_index:
            if key == search_query: continue 
            if pattern.search(key):
                matched_keys.append(key)

        if not matched_keys:
            error_embed = discord.Embed(title="❌ No covers found", description=f"No covers found for **{query}**.", color=discord.Color.red())
            try: await progress_msg.edit(embed=error_embed)
            except: await ctx.send(embed=error_embed)
            return

        urls_to_send = []
        cache_updated = False
        cache_channel = self.bot.get_channel(COVER_CACHE_CHANNEL_ID)

        for key in matched_keys[:5]: 
            cached_urls = self.cache.get(key)
            if cached_urls:
                urls_to_send.extend(cached_urls)
            else:
                local_paths = self.cover_index[key]
                new_urls = []
                if cache_channel:
                    for path in local_paths:
                        try:
                            if os.path.exists(path):
                                discord_file = discord.File(path, filename=os.path.basename(path))
                                msg = await cache_channel.send(file=discord_file)
                                new_urls.append(msg.attachments[0].url)
                        except Exception as e:
                            print(f"Error uploading {path}: {e}")

                    if new_urls:
                        self.cache[key] = new_urls
                        urls_to_send.extend(new_urls)
                        cache_updated = True

        if cache_updated:
            await self.save_cache()

        urls_to_send = list(set(urls_to_send))
        urls_to_send.sort()

        sent_messages = []
        if not urls_to_send:
             await progress_msg.edit(content="❌ Covers found but upload failed.", embed=None)
             return

        batch_size = 10
        for i in range(0, len(urls_to_send), batch_size):
            batch = urls_to_send[i:i + batch_size]
            msg_content = "\n".join(batch)
            if len(msg_content) > 2000: msg_content = batch[0] 
            msg = await ctx.send(msg_content)
            sent_messages.append(msg)

        async def delete_messages():
            await asyncio.sleep(300)
            for msg in sent_messages:
                try: await msg.delete()
                except: pass
            try:
                del_embed = discord.Embed(title=f"🗑️ Covers deleted", color=discord.Color.red())
                del_embed.set_footer(text="Cleaned up after 5 minutes.")
                await ctx.send(embed=del_embed)
            except: pass

        self.bot.loop.create_task(delete_messages())
        try: await progress_msg.delete()
        except: pass

async def setup(bot):
    await bot.add_cog(JuiceMedia(bot))
    await bot.add_cog(Cover(bot))