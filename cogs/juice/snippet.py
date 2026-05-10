import os
import json
import asyncio
import re
import mimetypes
import inspect
import functools
from urllib.parse import urlparse
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import secrets

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from discord import ui


from .helpers import (
    SNIPPETS_FOLDER_PATH,
    SNIPPET_CACHE_FILE,
    ARCHIVE_CHANNEL_ID,
    get_juiceinfo_track,
    parse_folder_name,
    era_colors,
    era_images,
)




class SnippetSelect(ui.Select):
    def __init__(self, options, ctx, snippet_cog, user_avatar, bot_avatar):
        super().__init__(placeholder="Select the correct snippet", options=options, min_values=1, max_values=1)
        self.ctx = ctx
        self.snippet_cog = snippet_cog
        self.user_avatar = user_avatar
        self.bot_avatar = bot_avatar

    async def callback(self, interaction: discord.Interaction):
        selected_folder = self.values[0]

        await interaction.response.defer()
        await self.snippet_cog.send_snippet(interaction, selected_folder, self.user_avatar, self.bot_avatar)

class SnippetDeliveryView(discord.ui.View):
    def __init__(self, cog, folder_path, valid_files, cache_key, folder_name):
        super().__init__(timeout=None)
        self.cog = cog
        self.folder_path = folder_path
        self.valid_files = valid_files
        self.cache_key = cache_key
        self.folder_name = folder_name

    @discord.ui.button(label="View Snippet(s)", style=discord.ButtonStyle.primary, emoji="🫣")
    async def show_hidden(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        archive_channel = self.cog.bot.get_channel(ARCHIVE_CHANNEL_ID)
        cached_ids = self.cog.cache.get(self.cache_key, [])
        links_to_send = []
        new_cached_ids = []
        cache_updated = False

        def get_slug(filename: str) -> str:
            return re.sub(r"[^a-z0-9]", "", (filename or "").lower())

        found_slugs = set()


        if cached_ids and archive_channel:
            for msg_id in cached_ids:
                try:
                    archived_msg = await archive_channel.fetch_message(msg_id)
                    if archived_msg.attachments:
                        att = archived_msg.attachments[0]
                        links_to_send.append(att.url)
                        new_cached_ids.append(msg_id)
                        found_slugs.add(get_slug(att.filename))
                except:
                    cache_updated = True


        missing_files = []
        for f in self.valid_files:
            if get_slug(f) not in found_slugs:
                missing_files.append(f)


        if missing_files:
            if not archive_channel:
                await interaction.followup.send("❌ Bot cannot access Archive Channel.", ephemeral=True)
                return

            for file in missing_files:
                file_path = os.path.join(self.folder_path, file)
                try:
                    archive_msg = await archive_channel.send(
                        content=f"Snippet: {os.path.basename(self.folder_name)}",
                        file=discord.File(file_path)
                    )
                    att = archive_msg.attachments[0]
                    links_to_send.append(att.url)
                    new_cached_ids.append(archive_msg.id)
                    found_slugs.add(get_slug(att.filename))
                    cache_updated = True
                except Exception as e:
                    await interaction.followup.send(f"❌ Error uploading: {e}", ephemeral=True)
                    return


        if cache_updated:
            self.cog.cache[self.cache_key] = new_cached_ids
            await self.cog.save_cache()


        if links_to_send:
            content = f"**{self.folder_name}**:\n" + "\n".join(links_to_send)
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.followup.send("❌ Could not retrieve files.", ephemeral=True)





class Snippet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.snippet_map = {} 
        self.is_indexing = True


        self._components_v2_flag = 1 << 15
        self._snippet_sessions = {}
        self._snippet_session_ttl = timedelta(minutes=30)
        
        self.bot.loop.create_task(self.load_cache())
        self.bot.loop.create_task(self.build_snippet_map())

    def _prune_snippet_sessions(self):
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._snippet_sessions.items() if (now - s["created_at"]) > self._snippet_session_ttl]
        for sid in expired:
            self._snippet_sessions.pop(sid, None)

    async def _send_v2_followup(self, interaction: discord.Interaction, payload: dict, files):
        app_id = interaction.application_id
        token = interaction.token
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
                async with session.post(url, data=form) as resp:
                    if resp.status >= 400:
                        raise RuntimeError(await resp.text())
                    return await resp.json()

    async def _send_v2_channel_message(self, channel_id: int, payload: dict, files):
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
                        raise RuntimeError(await resp.text())
                    return await resp.json()

    async def _patch_v2_channel_message(self, channel_id: int, message_id: int, payload: dict):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=payload) as resp:
                if resp.status >= 400:
                    raise RuntimeError(await resp.text())
                return await resp.json()

    def _build_snippet_v2_payload(
        self,
        *,
        title: str,
        header_meta_lines: list[str] | None,
        subtitle: str | None,
        thumb_url: str | None,
        accent_color: int,
        media_urls: list[str] | None,
        links_text: str,
        footer_text: str | None,
        session_id: str,
        page_index: int,
        total_pages: int,
    ) -> dict:
        meta_text = "\n".join([ln for ln in (header_meta_lines or []) if ln]).strip()
        header_parts = [f"# {title}"]
        if meta_text:
            header_parts.append(meta_text)
        if subtitle:
            header_parts.append(subtitle)

        header_section = {
            "type": 9,
            "components": [

                {"type": 10, "content": "\n".join(header_parts)},
            ],
        }
        if thumb_url:
            header_section["accessory"] = {"type": 11, "media": {"url": thumb_url}}

        blocks: list[dict] = [header_section]


        if media_urls:
            trimmed = [u for u in media_urls if u][:10]
            if trimmed:
                blocks.append({"type": 14, "divider": True, "spacing": 1})
                blocks.append({
                    "type": 12,
                    "items": [{"media": {"url": u}} for u in trimmed],
                })

        blocks.append({"type": 14, "divider": True, "spacing": 1})
        blocks.append({"type": 10, "content": links_text or " "})

        if footer_text:
            blocks.append({"type": 14, "divider": True, "spacing": 1})
            blocks.append({"type": 10, "content": footer_text})

        prev_disabled = page_index <= 0
        next_disabled = page_index >= (total_pages - 1)
        pager = {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "label": "Prev",
                    "custom_id": f"snipv2:{session_id}:prev",
                    "disabled": prev_disabled,
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": "Next",
                    "custom_id": f"snipv2:{session_id}:next",
                    "disabled": next_disabled,
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": "Links",
                    "custom_id": f"snipv2:{session_id}:links",
                },
                {
                    "type": 2,
                    "style": 4,
                    "label": "Dismiss",
                    "custom_id": f"snipv2:{session_id}:dismiss",
                },
            ],
        }

        return {
            "flags": self._components_v2_flag,
            "allowed_mentions": {"parse": []},
            "components": [
                {
                    "type": 17,
                    "accent_color": int(accent_color) & 0xFFFFFF,
                    "components": [
                        *blocks,
                        {"type": 14, "divider": True, "spacing": 1},
                        pager,
                    ],
                }
            ],
        }

    def _page_slice(self, items: list, page_index: int, page_size: int):
        start = page_index * page_size
        end = start + page_size
        return items[start:end]

    def _filter_gallery_urls(self, urls: list[str] | None, *, allow_mov: bool = True) -> list[str]:
        if not urls:
            return []
        allowed_exts = {".mp4", ".webm", ".mov", ".png", ".jpg", ".jpeg", ".gif"} if allow_mov else {".mp4", ".webm", ".png", ".jpg", ".jpeg", ".gif"}

        out: list[str] = []
        for u in urls:
            if not u:
                continue
            try:
                path = urlparse(u).path or ""
                ext = os.path.splitext(path)[1].lower()
            except Exception:
                ext = ""
            if ext in allowed_exts:
                out.append(u)
        return out

    def _pretty_snippet_name(self, filename: str | None) -> str:
        if not filename:
            return "Snippet"
        base = os.path.splitext(os.path.basename(filename))[0]
        base = base.replace("_", " ").strip()
        return base or "Snippet"

    def _build_inline_meta(self, *, producer: str | None, engineer: str | None, preview_date: str | None, surfaced: str | None) -> str:
        parts = []
        if producer and producer not in ["N/A", "-"]:
            parts.append(f"Producer: {producer}")
        if engineer and engineer not in ["N/A", "-"]:
            parts.append(f"Engineer: {engineer}")
        if preview_date and preview_date not in ["N/A", "-"]:
            parts.append(f"Preview Date: {preview_date}")
        if surfaced and surfaced not in ["Not Surfaced", "N/A", "-"]:
            parts.append(f"Leak Date: {surfaced}")

        meta = " • ".join(parts)

        if len(meta) > 240:
            meta = meta[:237] + "..."
        return meta

    def _build_meta_lines(self, *, producer: str | None, engineer: str | None, preview_date: str | None, surfaced: str | None) -> list[str]:
        lines: list[str] = []
        if producer and producer not in ["N/A", "-"]:
            lines.append(f"**Producer:** {producer}")
        if engineer and engineer not in ["N/A", "-"]:
            lines.append(f"**Engineer:** {engineer}")
        if preview_date and preview_date not in ["N/A", "-"]:
            lines.append(f"**Preview Date:** {preview_date}")
        if surfaced and surfaced not in ["Not Surfaced", "N/A", "-"]:
            lines.append(f"**Leak Date:** {surfaced}")
        return lines

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        data = getattr(interaction, "data", None) or {}
        custom_id = data.get("custom_id") if isinstance(data, dict) else None
        if not custom_id or not custom_id.startswith("snipv2:"):
            return

        parts = custom_id.split(":", 2)
        if len(parts) != 3:
            return

        _, session_id, action = parts
        self._prune_snippet_sessions()
        session = self._snippet_sessions.get(session_id)
        if not session:
            return await interaction.response.send_message("⏰ This snippet list expired. Run the command again.", ephemeral=True)

        if interaction.user.id != session["user_id"]:
            return await interaction.response.send_message("❌ Only the command invoker can use these buttons.", ephemeral=True)

        if action == "dismiss":
            try:
                await interaction.message.delete()
            except Exception:
                return await interaction.response.send_message("❌ I couldn't delete that message.", ephemeral=True)
            return

        if action == "links":
            page_items = self._page_slice(session["links"], session["page_index"], session["page_size"])
            if not page_items:
                return await interaction.response.send_message("No snippets on this page.", ephemeral=True)

            lines = []
            for name, url in page_items:
                display = self._pretty_snippet_name(name)
                lines.append(f"• [{display}]({url})")
            return await interaction.response.send_message("\n".join(lines), ephemeral=True)

        if action not in {"prev", "next"}:
            return

        if action == "prev" and session["page_index"] > 0:
            session["page_index"] -= 1
        elif action == "next" and session["page_index"] < (session["total_pages"] - 1):
            session["page_index"] += 1


        page_items = self._page_slice(session["links"], session["page_index"], session["page_size"])
        links_text = "-# Use **Links** to get direct URLs (some .mov may not embed in the preview)."
        footer = f"-# Page {session['page_index'] + 1}/{max(1, session['total_pages'])} • {len(session['links'])} total snippet(s)."

        raw_media_urls = [url for _, url in page_items]
        payload = self._build_snippet_v2_payload(
            title=session["song_title"],
            header_meta_lines=session.get("header_meta_lines"),
            subtitle=session.get("subtitle"),
            thumb_url=session.get("thumb_url"),
            accent_color=session["accent_color"],
            media_urls=self._filter_gallery_urls(raw_media_urls, allow_mov=True),
            links_text=links_text,
            footer_text=footer,
            session_id=session_id,
            page_index=session["page_index"],
            total_pages=session["total_pages"],
        )

        try:
            await interaction.response.defer_update()
        except Exception:
            pass

        try:
            await self._patch_v2_channel_message(interaction.channel_id, interaction.message.id, payload)
        except Exception as e:

            try:
                payload_no_mov = self._build_snippet_v2_payload(
                    title=session["song_title"],
                    header_meta_lines=session.get("header_meta_lines"),
                    subtitle=session.get("subtitle"),
                    thumb_url=session.get("thumb_url"),
                    accent_color=session["accent_color"],
                    media_urls=self._filter_gallery_urls(raw_media_urls, allow_mov=False),
                    links_text=links_text,
                    footer_text=footer,
                    session_id=session_id,
                    page_index=session["page_index"],
                    total_pages=session["total_pages"],
                )
                await self._patch_v2_channel_message(interaction.channel_id, interaction.message.id, payload_no_mov)
            except Exception:

                try:
                    await interaction.followup.send("❌ Failed to update page.", ephemeral=True)
                except Exception:
                    pass
            print(f"[Snippet V2] Page update failed (maybe .mov gallery): {e}")

    async def load_cache(self):
        if os.path.exists(SNIPPET_CACHE_FILE):
            try:
                with open(SNIPPET_CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, Exception):
                self.cache = {}
        else:
            self.cache = {}

    async def save_cache(self):
        def write():
            with open(SNIPPET_CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=4)
        await self.bot.loop.run_in_executor(None, write)

    async def build_snippet_map(self):
        self.is_indexing = True
        print(f"[Snippet Cog] Indexing {SNIPPETS_FOLDER_PATH}...")
        def scan_disk():
            cache = {}
            if os.path.exists(SNIPPETS_FOLDER_PATH):
                for root, dirs, files in os.walk(SNIPPETS_FOLDER_PATH):
                    for d in dirs:
                        full_path = os.path.join(root, d)
                        rel_path = os.path.relpath(full_path, SNIPPETS_FOLDER_PATH)
                        cache[d.lower()] = rel_path
            return cache
        self.snippet_map = await self.bot.loop.run_in_executor(None, scan_disk)
        self.is_indexing = False
        print(f"[Snippet Cog] Indexed {len(self.snippet_map)} snippet folders.")

    async def safe_send(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                return await ctx.followup.send(**kwargs)
            else:
                return await ctx.response.send_message(**kwargs)
        else:
            return await ctx.send(**kwargs)

    @commands.hybrid_command(name='snippet', aliases=['snip'], description="Send a song snippet")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def snippet(self, ctx, *, query: str = None):
        if self.is_indexing:
            await self.safe_send(ctx, content="⚠️ Still indexing snippets. Please wait a moment.", ephemeral=True)
            return

        if not query:
            embed = discord.Embed(title="Missing Song Name", description="Example: `-snippet stainless`", color=discord.Color.red())
            await self.safe_send(ctx, embed=embed)
            return

        query = query.lower()
        matching_folders = []
        for name, rel_path in self.snippet_map.items():
            if query in name:
                matching_folders.append(rel_path)

        if not matching_folders:
            embed = discord.Embed(title=":x: No Snippets Found", color=discord.Color.red())
            await self.safe_send(ctx, embed=embed)
            return

        user_avatar = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else ctx.bot.user.default_avatar.url

        if len(matching_folders) == 1:
            await self.send_snippet(ctx, matching_folders[0], user_avatar, bot_avatar)
        else:
            matching_folders.sort(key=lambda x: os.path.basename(x))
            options = [discord.SelectOption(label=os.path.basename(f)[:100], value=f) for f in matching_folders[:25]]
            select_menu = SnippetSelect(options, ctx, self, user_avatar, bot_avatar)
            view = discord.ui.View()
            view.add_item(select_menu)
            embed = discord.Embed(description=f"**{len(matching_folders)} Snippets Found**", color=discord.Color.default())
            await self.safe_send(ctx, embed=embed, view=view)

    async def send_snippet(self, ctx, folder_name, user_avatar, bot_avatar):
        interaction = ctx if isinstance(ctx, discord.Interaction) else getattr(ctx, "interaction", None)
        requester_display_name = ctx.user.display_name if isinstance(ctx, discord.Interaction) else ctx.author.display_name

        loading_msg = None
        try:
            loading_embed = discord.Embed(
                description="⏳ Uploading snippet(s)…",
                color=discord.Color.orange(),
            )

            if interaction:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=loading_embed, ephemeral=True)
                    try:
                        loading_msg = await interaction.original_response()
                    except Exception:
                        loading_msg = None
                else:
                    try:
                        loading_msg = await interaction.followup.send(embed=loading_embed, ephemeral=True)
                    except Exception:
                        loading_msg = None
            else:

                try:
                    loading_msg = await ctx.send(embed=loading_embed)
                except Exception:
                    loading_msg = None
        except Exception:
            loading_msg = None

        folder_path = os.path.join(SNIPPETS_FOLDER_PATH, folder_name)
        cache_key = folder_name
        sent_messages = []

        display_name = os.path.basename(folder_name)
        main_title, aliases = parse_folder_name(display_name)
        if not main_title:
            main_title = display_name



        preferred_era = None
        def _norm_label(s: str) -> str:
            s = (s or "").strip().lower()

            s = re.sub(r"^\s*\d+\s*[\.|\-|\)]\s*", "", s)
            s = re.sub(r"\s+", " ", s).strip()

            return re.sub(r"[^a-z0-9]", "", s)

        try:
            parts = [p for p in re.split(r"[\\/]", str(folder_name)) if p]
            for part in parts:
                part_norm = _norm_label(part)
                if not part_norm:
                    continue
                for era in era_images.keys():
                    era_norm = _norm_label(str(era))
                    if not era_norm:
                        continue
                    if part_norm == era_norm or era_norm in part_norm or part_norm in era_norm:
                        preferred_era = era
                        break
                if preferred_era:
                    break
        except Exception:
            preferred_era = None

        try:
            params = inspect.signature(get_juiceinfo_track).parameters
            supports_preferred_era = "preferred_era" in params
        except Exception:
            supports_preferred_era = False

        if supports_preferred_era:
            lookup_fn = functools.partial(
                get_juiceinfo_track,
                main_title,
                aliases,
                None,
                display_name,
                preferred_era=preferred_era,
            )
        else:
            lookup_fn = functools.partial(
                get_juiceinfo_track,
                main_title,
                aliases,
                None,
                display_name,
            )

        db_info = await self.bot.loop.run_in_executor(None, lookup_fn)


        def scan_files():
            try:
                all_f = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                max_s = 50 * 1024 * 1024
                valid = [f for f in all_f if os.path.getsize(os.path.join(folder_path, f)) <= max_s]
                oversized = [f for f in all_f if os.path.getsize(os.path.join(folder_path, f)) > max_s]
                return valid, oversized
            except: return [], []
        
        valid_files, oversized_files = await self.bot.loop.run_in_executor(None, scan_files)


        title_text = f"**{len(valid_files)} Snippet(s)**" if valid_files else ":x: No Files"
        embed_color = discord.Color.default()
        if db_info and db_info.get("Era"):
            embed_color = discord.Color(era_colors.get(db_info["Era"], embed_color.value))

        main_embed = discord.Embed(
            title=title_text,
            description=f"Showing snippets for **{display_name}**",
            color=embed_color
        )
        main_embed.set_author(name=self.bot.user.display_name, icon_url=bot_avatar)
        main_embed.set_footer(text=f"Requested by {requester_display_name}", icon_url=user_avatar)


        if db_info:
            producer = db_info.get("Producer")
            engineer = db_info.get("Engineer")
            preview_date = db_info.get("Preview Date")
            surfaced = db_info.get("Surfaced")

            if producer and producer not in ["N/A", "-"]:
                main_embed.add_field(name="Producer", value=producer, inline=True)
            if engineer and engineer not in ["N/A", "-"]:
                main_embed.add_field(name="Engineer", value=engineer, inline=True)
            if preview_date and preview_date not in ["N/A", "-"]:
                main_embed.add_field(name="Preview Date", value=preview_date, inline=True)
            if surfaced and surfaced not in ["Not Surfaced", "N/A", "-"]:
                main_embed.add_field(name="Leak Date", value=surfaced, inline=True)

            era = db_info.get("Era")
            if era:
                main_embed.set_thumbnail(url=era_images.get(era, era_images.get("Posthumous", "")))




        archive_channel = self.bot.get_channel(ARCHIVE_CHANNEL_ID)
        cached_ids = self.cache.get(cache_key, [])

        def get_slug(filename: str) -> str:
            return re.sub(r"[^a-z0-9]", "", (filename or "").lower())

        links: list[tuple[str, str]] = []
        found_slugs = set()
        valid_cached_ids = []
        cache_needs_update = False


        if cached_ids and archive_channel:
            for msg_id in cached_ids:
                try:
                    archived_msg = await archive_channel.fetch_message(int(msg_id))
                    if archived_msg.attachments:
                        att = archived_msg.attachments[0]
                        links.append((att.filename, att.url))
                        valid_cached_ids.append(int(msg_id))
                        found_slugs.add(get_slug(att.filename))
                except Exception:
                    cache_needs_update = True


        missing_files = [f for f in valid_files if get_slug(f) not in found_slugs]
        if missing_files and archive_channel:
            for file in missing_files:
                file_path = os.path.join(folder_path, file)
                try:
                    archive_msg = await archive_channel.send(
                        content=f"Snippet: {os.path.basename(folder_name)}",
                        file=discord.File(file_path),
                    )
                    if archive_msg.attachments:
                        att = archive_msg.attachments[0]
                        links.append((att.filename, att.url))
                        valid_cached_ids.append(archive_msg.id)
                        found_slugs.add(get_slug(att.filename))
                        cache_needs_update = True
                except Exception as e:
                    print(f"Snippet Send Error: {e}")


        if archive_channel and (cache_needs_update or len(valid_cached_ids) != len(cached_ids)):
            self.cache[cache_key] = valid_cached_ids
            await self.save_cache()


        if not archive_channel:
            view = SnippetDeliveryView(self, folder_path, valid_files, cache_key, os.path.basename(folder_name))
            await self.safe_send(ctx, embed=main_embed, view=view)
            if oversized_files:
                await self.safe_send(
                    ctx,
                    embed=discord.Embed(description="⚠️ Some files >50MB skipped.", color=discord.Color.orange()),
                    ephemeral=True,
                )
            return


        links.sort(key=lambda t: (t[0] or "").lower())




        db_era = db_info.get("Era") if db_info else None
        accent = era_colors.get(db_era, discord.Color.default().value) if db_era else discord.Color.default().value
        thumb = era_images.get(db_era, era_images.get("Posthumous", "")) if db_era else None
        if thumb == "":
            thumb = None

        producer = db_info.get("Producer") if db_info else None
        engineer = db_info.get("Engineer") if db_info else None
        preview_date = db_info.get("Preview Date") if db_info else None
        surfaced = db_info.get("Surfaced") if db_info else None

        header_meta_lines = self._build_meta_lines(
            producer=producer,
            engineer=engineer,
            preview_date=preview_date,
            surfaced=surfaced,
        )
        song_title = main_title or os.path.basename(folder_name)

        self._prune_snippet_sessions()
        session_id = secrets.token_urlsafe(8)
        page_size = 10
        total_pages = max(1, (len(links) - 1) // page_size + 1)
        self._snippet_sessions[session_id] = {
            "created_at": datetime.now(timezone.utc),
            "user_id": (ctx.user.id if isinstance(ctx, discord.Interaction) else ctx.author.id),
            "song_title": song_title,
            "header_meta_lines": header_meta_lines,
            "subtitle": f"-# {len(valid_files)} snippet(s){' • ' + str(db_era) if db_era else ''}",
            "thumb_url": thumb,
            "accent_color": int(accent),
            "links": links,
            "page_index": 0,
            "page_size": page_size,
            "total_pages": total_pages,
        }

        page_items = self._page_slice(links, 0, page_size)
        links_text = "-# Use **Links** to get direct URLs (some .mov may not embed in the preview)."
        footer = f"-# Page 1/{max(1, total_pages)} • {len(links)} total snippet(s)."

        raw_media_urls = [url for _, url in page_items]
        payload = self._build_snippet_v2_payload(
            title=song_title,
            header_meta_lines=header_meta_lines,
            subtitle=self._snippet_sessions[session_id]["subtitle"],
            thumb_url=thumb,
            accent_color=accent,
            media_urls=self._filter_gallery_urls(raw_media_urls, allow_mov=True),
            links_text=links_text,
            footer_text=footer,
            session_id=session_id,
            page_index=0,
            total_pages=total_pages,
        )

        try:
            if interaction:
                await self._send_v2_followup(interaction, payload, [])
            else:
                await self._send_v2_channel_message(ctx.channel.id, payload, [])
        except Exception as e:

            try:
                payload_no_mov = self._build_snippet_v2_payload(
                    title=song_title,
                    header_meta_lines=header_meta_lines,
                    subtitle=self._snippet_sessions[session_id]["subtitle"],
                    thumb_url=thumb,
                    accent_color=accent,
                    media_urls=self._filter_gallery_urls(raw_media_urls, allow_mov=False),
                    links_text=links_text,
                    footer_text=footer,
                    session_id=session_id,
                    page_index=0,
                    total_pages=total_pages,
                )
                if interaction:
                    await self._send_v2_followup(interaction, payload_no_mov, [])
                else:
                    await self._send_v2_channel_message(ctx.channel.id, payload_no_mov, [])
            except Exception:

                await self.safe_send(ctx, embed=main_embed)
                for _, url in links:
                    try:
                        await ctx.channel.send(content=url)
                    except Exception:
                        pass
            print(f"[Snippet V2] Initial send failed (maybe .mov gallery): {e}")
        finally:
            if loading_msg:
                try:
                    await loading_msg.delete()
                except Exception:
                    pass

        if oversized_files:
            await self.safe_send(
                ctx,
                embed=discord.Embed(description="⚠️ Some files >50MB skipped.", color=discord.Color.orange()),
                ephemeral=isinstance(ctx, discord.Interaction),
            )

async def setup(bot):
    await bot.add_cog(Snippet(bot))