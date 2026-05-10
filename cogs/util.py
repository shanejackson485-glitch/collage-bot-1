from __future__ import annotations
import re
from typing import Iterable, List, Tuple, Optional
import humanize
import json
import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from discord.ui import Select
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from config import category_emojis, prev_emoji, next_emoji, commands_dict
import io
import aiohttp
import requests
import asyncio
import psutil
from discord.ext.commands import Cog, Context, command, hybrid_command
from discord import app_commands, Embed, User, Member, Role, Invite, TextChannel, VoiceChannel, CategoryChannel, ForumChannel, StageChannel, AuditLogAction
from discord.utils import format_dt
import os

MENTION_RE = re.compile(r"<@!?(\d+)>|(\d{15,20})")
DEV_CODE = "DM1702403000269" 



class TopDownloads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["td", "downloads"])
    async def topdownloads(self, ctx):
        """Shows the top users ranked by file downloads."""
        try:
            with open("data/Developer/download_stats.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return await ctx.send("⚠️ No download data found.")
        
        users_data = data.get("users", {})
        if not users_data:
            return await ctx.send("⚠️ No user downloads recorded.")


        sorted_users = sorted(users_data.items(), key=lambda x: x[1]["downloads"], reverse=True)


        pages = []
        for i in range(0, len(sorted_users), 10):
            chunk = sorted_users[i:i+10]
            leaderboard = []
            for rank, (user_id, stats) in enumerate(chunk, start=i+1):
                user_obj = self.bot.get_user(int(user_id))
                if not user_obj:
                    try:
                        user_obj = await self.bot.fetch_user(int(user_id))
                    except:
                        user_obj = None
                name = user_obj.name if user_obj else f"<@{user_id}>"

                leaderboard.append(
                    f"**{rank}. {name}** — "
                    f"Downloads: `{stats['downloads']}` | Size: `{humanize.naturalsize(stats['size_bytes'])}`"
                )

            embed = discord.Embed(
                title="📥 Top Downloaders",
                description=(
                    f"Total Downloads: **{data['total_downloads']}**\n"
                    f"Total Size: **{humanize.naturalsize(data['total_size_bytes'])}**\n"
                    f"Total Users: **{len(users_data)}**"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(name="🏆 Leaderboard", value="\n".join(leaderboard), inline=False)
            embed.set_footer(
                text=f"Page {len(pages)+1}/{(len(sorted_users)-1)//10+1} • Requested by {ctx.author}", 
                icon_url=ctx.author.display_avatar.url
            )
            pages.append(embed)


        if len(pages) == 1:
            return await ctx.send(embed=pages[0])


        class Paginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.current = 0

            @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn’t your leaderboard.", ephemeral=True)
                self.current = (self.current - 1) % len(pages)
                await interaction.response.edit_message(embed=pages[self.current], view=self)

            @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn’t your leaderboard.", ephemeral=True)
                self.current = (self.current + 1) % len(pages)
                await interaction.response.edit_message(embed=pages[self.current], view=self)

        await ctx.send(embed=pages[0], view=Paginator())





class UtilityCog(commands.Cog, name="Utility"):
    """Commands for server utility and information."""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='bc', aliases=['botclear', 'cleanup'])
    @commands.has_permissions(manage_messages=True)
    async def botclear(self, ctx, limit: int = 50):
        """Clears the bot's messages from the channel."""
        

        def is_me(m):
            return m.author == self.bot.user

        try:

            deleted = await ctx.channel.purge(limit=limit, check=is_me, bulk=True)
            
            embed = discord.Embed(
                description=f"✅ Cleared **{len(deleted)}** of my messages.", 
                color=discord.Color.green()
            )
            await ctx.send(embed=embed, delete_after=5)
            
        except discord.Forbidden:
            embed = discord.Embed(
                description="❌ I don't have the `Manage Messages` permission to do this.", 
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)

    @commands.command(name='si', aliases=['serverinfo', 'sinfo'])
    async def serverinfo(self, ctx, guild: discord.Guild = None):
        """Displays information about the server."""
        guild = guild or ctx.guild

        if not guild:
            return await ctx.send("❌ Could not determine the server. Are you in a DM?")

        embed = discord.Embed(
            title=f"📊 Server Information - {guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        if guild.banner:
            embed.set_image(url=guild.banner.url)


        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        

        embed.add_field(name="📅 Created On", value=discord.utils.format_dt(guild.created_at, style='D'), inline=True)
        

        embed.add_field(name="👥 Members", value=f"{guild.member_count}", inline=True)
        embed.add_field(name="💬 Channels", value=f"Text: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}", inline=True)
        embed.add_field(name="🎭 Roles", value=f"{len(guild.roles)}", inline=True)
        

        embed.add_field(name="🚀 Boosts", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} Boosts)", inline=False)
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)



class DMModal(Modal, title="Send a DM"):

    def __init__(self, target_user: discord.User):
        super().__init__()
        self.target_user = target_user
        self.add_item(TextInput(label="Sender Name", placeholder="e.g., Server Moderation", required=True))
        self.add_item(TextInput(label="Message", style=discord.TextStyle.paragraph, required=True))
        self.add_item(TextInput(label="Developer Code", placeholder="Enter the secure dev code", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        sender = self.children[0].value
        message = self.children[1].value
        input_dev_code = self.children[2].value.strip()
        if input_dev_code != DEV_CODE:
            return await interaction.response.send_message("❌ Invalid developer code.", ephemeral=True)
        embed = discord.Embed(title=f"📩 Message from {sender}", description=message, color=discord.Color.blurple())
        try:
            await self.target_user.send(embed=embed)
            await interaction.response.send_message("✅ Message sent successfully!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Could not send DM.", ephemeral=True)


class UserInfoCog(commands.Cog, name="User Info"):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        custom_id = interaction.data.get("custom_id")
        if not custom_id or "_" not in custom_id: return
        action, user_id_str = custom_id.split("_", 1)
        if not user_id_str.isdigit(): return
        user_id = int(user_id_str)
        try: target_user = await self.bot.fetch_user(user_id)
        except discord.NotFound: return await interaction.response.send_message("❌ User not found.", ephemeral=True)
        if action == "kick": await self.handle_kick(interaction, target_user)
        elif action == "ban": await self.handle_ban(interaction, target_user)
        elif action == "unban": await self.handle_unban(interaction, target_user)
        elif action == "dm": await interaction.response.send_modal(DMModal(target_user))




    async def handle_kick(self, interaction: discord.Interaction, target_user: discord.User):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ You lack permission to kick members.", ephemeral=True)

        if not interaction.guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ I don't have permission to kick members.", ephemeral=True)
        
        member = interaction.guild.get_member(target_user.id)
        if member:
            try:
                await member.kick(reason=f"Kicked by {interaction.user.name}")
                await interaction.response.send_message(f"✅ {member.mention} has been kicked.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I lack the necessary permissions to kick this specific user.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ User is not in the server.", ephemeral=True)

    async def handle_ban(self, interaction: discord.Interaction, target_user: discord.User):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You lack permission to ban members.", ephemeral=True)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ I don't have permission to ban members.", ephemeral=True)

        try:
            await interaction.guild.ban(target_user, reason=f"Banned by {interaction.user.name}")
            await interaction.response.send_message(f"✅ {target_user.name} has been banned.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack the necessary permissions to ban this specific user.", ephemeral=True)


    async def handle_unban(self, interaction: discord.Interaction, target_user: discord.User):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You lack permission to unban members.", ephemeral=True)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ I don't have permission to unban members.", ephemeral=True)

        try:
            await interaction.guild.unban(target_user, reason=f"Unbanned by {interaction.user.name}")
            await interaction.response.send_message(f"✅ {target_user.name} has been unbanned.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ User was not banned.", ephemeral=True)

    @commands.command(name="ui", aliases=["userinfo"])
    async def userinfo(self, ctx, *, member_or_user: str = None):

        if member_or_user is None:
            user = ctx.author
        else:
            try:


                user = await commands.MemberConverter().convert(ctx, member_or_user)
            except commands.MemberNotFound:
                try:


                    user = await commands.UserConverter().convert(ctx, member_or_user)
                except commands.UserNotFound:
                    return await ctx.send(f"❌ Could not find user: `{member_or_user}`")


        member = ctx.guild.get_member(user.id)
        embed_color = member.color if member else discord.Color.default()
        
        embed = discord.Embed(title=f"User Info for {user.name}", color=embed_color)
        embed.set_thumbnail(url=user.display_avatar.url)
        

        embed.add_field(name="User ID", value=f"`{user.id}`", inline=False)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(user.created_at, style='D'), inline=False)

        view = View()
        bot_member = ctx.guild.me

        if member:
            embed.add_field(name="Server Joined", value=discord.utils.format_dt(member.joined_at, style='D'), inline=False)
            roles = [role.mention for role in reversed(member.roles) if not role.is_default()]
            roles_str = ", ".join(roles) if roles else "None"
            if len(roles_str) > 1024: roles_str = f"{len(roles)} roles (too many to display)"
            embed.add_field(name=f"Roles [{len(roles)}]", value=roles_str, inline=False)
            

            if ctx.author.guild_permissions.kick_members and bot_member.guild_permissions.kick_members:
                view.add_item(Button(label="Kick", style=discord.ButtonStyle.danger, custom_id=f"kick_{user.id}"))
            if ctx.author.guild_permissions.ban_members and bot_member.guild_permissions.ban_members:
                view.add_item(Button(label="Ban", style=discord.ButtonStyle.danger, custom_id=f"ban_{user.id}"))
        else:
            try:
                await ctx.guild.fetch_ban(user)
                embed.set_footer(text="User is banned from this server.")
                if ctx.author.guild_permissions.ban_members and bot_member.guild_permissions.ban_members:
                    view.add_item(Button(label="Unban", style=discord.ButtonStyle.success, custom_id=f"unban_{user.id}"))
            except discord.NotFound:
                embed.set_footer(text="User is not in this server.")
        
        view.add_item(Button(label="Send DM", style=discord.ButtonStyle.primary, custom_id=f"dm_{user.id}"))
        await ctx.send(embed=embed, view=view)


    @commands.command(name="search")
    async def search_command(self, ctx, *, command_name: str):
        """Allows users to search for a specific command."""
        query = command_name.lower().strip()
        for category, commands in commands_dict.items():
            for cmd in commands:
                if cmd["name"].lower() == query:
                    embed = discord.Embed(
                        title=f"Command: `-{cmd['name']}`",
                        description=cmd["description"],
                        color=0x2b2d31
                    )
                    embed.set_footer(text=f"Category: {category}")
                    return await ctx.send(embed=embed)

        await ctx.send(f"⚠️ Command `{command_name}` not found.")




def parse_color(color_input: str) -> Optional[discord.Color]:
    color_input = color_input.lower().strip()
    if not color_input:
        return discord.Color.default()
    hex_match = re.match(r"^#?([0-9a-fA-F]{6})$", color_input)
    if hex_match:
        return discord.Color(int(hex_match.group(1), 16))
    try:
        color_method = getattr(discord.Color, color_input)
        if callable(color_method):
            return color_method()
    except (AttributeError, TypeError):
        return None
    return None


class EmbedModal(Modal, title="Embed Creator (Part 1/2)"):
    def __init__(self, bot: discord.Client | discord.Bot | discord.AutoShardedClient, channel: discord.TextChannel):
        super().__init__()
        self.bot = bot
        self.channel = channel

        self.add_item(TextInput(label="Title", placeholder="The main title of the embed", required=True))
        self.add_item(TextInput(label="Description", placeholder="The main text content. Supports Markdown.", style=discord.TextStyle.paragraph, required=False))
        self.add_item(TextInput(label="Color", placeholder="Hex code (#ff0000) or a common color name (red)", required=False))
        self.add_item(TextInput(label="Button Text", placeholder="Optional: The text that appears on the button", required=False))
        self.add_item(TextInput(label="Button URL", placeholder="Optional: The URL the button will link to", required=False))

    async def on_submit(self, interaction: discord.Interaction):

        title = self.children[0].value
        description = self.children[1].value
        color_str = self.children[2].value
        button_text = self.children[3].value
        button_url = self.children[4].value


        color = parse_color(color_str)
        if color is None and color_str:
            return await interaction.response.send_message(f"❌ Invalid color: `{color_str}`.", ephemeral=True)
        elif color is None:
            color = discord.Color.default()


        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=interaction.guild.name if interaction.guild else "", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)


        final_view = View(timeout=None)
        if button_text and button_url:
            if not button_url.startswith(("http://", "https://")):
                return await interaction.response.send_message("❌ Invalid Button URL. It must start with `http://` or `https://`.", ephemeral=True)
            final_view.add_item(Button(label=button_text, url=button_url))


        prompt_view = ThumbnailPromptView(
            bot=self.bot,
            original_interaction=interaction,
            embed=embed,
            final_view=final_view,
            channel_to_send_in=self.channel
        )
        await interaction.response.send_message(
            "**Part 1 Complete!** Here is your embed so far.\nWould you like to add a thumbnail image?",
            embed=embed,
            view=prompt_view,
            ephemeral=True
        )


class ThumbnailPromptView(View):
    """
    Presents options to add thumbnail: either provide URL via modal
    or upload an image to a temporary private thread (no message.content read).
    """
    def __init__(self, bot, original_interaction: discord.Interaction, embed: discord.Embed, final_view: View, channel_to_send_in: discord.TextChannel):
        super().__init__(timeout=180)
        self.bot = bot
        self.original_interaction = original_interaction
        self.embed = embed
        self.final_view = final_view
        self.channel_to_send_in = channel_to_send_in

    @ui.button(label="Yes, Add Thumbnail", style=discord.ButtonStyle.green, row=0)
    async def yes_button(self, interaction: discord.Interaction, button: Button):


        if interaction.user.id != self.original_interaction.user.id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)


        await interaction.response.edit_message(content="Choose how to provide the thumbnail:", view=ThumbnailChoiceView(self))

    @ui.button(label="No, Continue", style=discord.ButtonStyle.grey, row=0)
    async def no_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.original_interaction.user.id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)
        await self._show_final_confirmation(interaction, success=False)

    async def _show_final_confirmation(self, interaction: discord.Interaction, success: bool):
        confirm_view = View(timeout=180)

        send_button = Button(label="Send to Channel", style=discord.ButtonStyle.green)
        async def send_callback(callback_interaction: discord.Interaction):
            if callback_interaction.user.id != self.original_interaction.user.id:
                return await callback_interaction.response.send_message("This isn't for you!", ephemeral=True)
            try:
                await self.channel_to_send_in.send(embed=self.embed, view=self.final_view if self.final_view and self.final_view.children else None)
                await callback_interaction.response.edit_message(content="✅ Embed sent!", embed=None, view=None)
            except discord.Forbidden:
                await callback_interaction.response.edit_message(content="❌ I don't have permission to send messages in that channel.", embed=None, view=None)
        send_button.callback = send_callback
        confirm_view.add_item(send_button)

        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel_callback(callback_interaction: discord.Interaction):
            if callback_interaction.user.id != self.original_interaction.user.id:
                return await callback_interaction.response.send_message("This isn't for you!", ephemeral=True)
            await callback_interaction.response.edit_message(content="❌ Canceled.", embed=None, view=None)
        cancel_button.callback = cancel_callback
        confirm_view.add_item(cancel_button)

        message_content = "**Part 2 Complete!** Here is your final embed preview. Ready to send it?" if success else "**Here is your final embed preview. Ready to send it?**"

        try:
            await self.original_interaction.edit_original_response(content=message_content, embed=self.embed, view=confirm_view)
        except Exception:

            await interaction.response.send_message(message_content, embed=self.embed, view=confirm_view, ephemeral=True)


class ThumbnailChoiceView(View):
    def __init__(self, parent: ThumbnailPromptView):
        super().__init__(timeout=120)
        self.parent = parent

    @ui.button(label="Provide URL (modal)", style=discord.ButtonStyle.primary)
    async def url_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.parent.original_interaction.user.id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)


        class URLModal(Modal, title="Thumbnail URL"):
            url_input = TextInput(label="Image URL", placeholder="https://example.com/image.png", required=True, max_length=500)

            def __init__(self, parent_view: ThumbnailPromptView):
                super().__init__()
                self.parent_view = parent_view

            async def on_submit(self, modal_interaction: discord.Interaction):
                url = self.url_input.value.strip()
                if not url.startswith(("http://", "https://")):
                    return await modal_interaction.response.send_message("❌ Invalid URL. Must start with http:// or https://", ephemeral=True)


                self.parent_view.embed.set_thumbnail(url=url)
                await modal_interaction.response.send_message("✅ Thumbnail URL set.", ephemeral=True)
                await self.parent_view._show_final_confirmation(modal_interaction, success=True)

        await interaction.response.send_modal(URLModal(self.parent))

    @ui.button(label="Upload Image (private thread)", style=discord.ButtonStyle.secondary)
    async def upload_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.parent.original_interaction.user.id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)


        channel = self.parent.original_interaction.channel
        guild = interaction.guild
        thread = None
        try:

            thread_name = f"thumbnail-upload-{interaction.user.id}"

            try:
                thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread, auto_archive_duration=60)
            except Exception:

                thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread, auto_archive_duration=60)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Could not create temporary thread: {e}", ephemeral=True)


        try:
            if thread.type == discord.ChannelType.private_thread:

                try:
                    await thread.add_user(interaction.user)
                except Exception:
                    pass
        except Exception:
            pass


        try:
            instructions = await thread.send(f"{interaction.user.mention} — Please reply to this message with an image file. I will accept the first valid image upload and then close this thread. (You can upload as an attachment.)")
        except discord.Forbidden:

            await interaction.response.send_message("❌ I couldn't send instructions in the thread. Make sure I can create/send messages in threads.", ephemeral=True)
            return


        await interaction.response.send_message("✅ Thread created — upload your image there now. I'll process it automatically.", ephemeral=True)

        def check(m: discord.Message):

            return m.channel.id == thread.id and m.author.id == interaction.user.id and bool(m.attachments)

        try:
            msg = await self.parent.bot.wait_for("message", check=check, timeout=120.0)
        except asyncio.TimeoutError:
            try:
                await thread.send("⏰ Timeout — no image uploaded. Thread will be archived.")
            except Exception:
                pass

            try:
                await thread.edit(auto_archive_duration=60)
            except Exception:
                pass
            return


        attachment = msg.attachments[0]
        content_type = getattr(attachment, "content_type", "") or ""
        if not content_type.startswith("image"):
            await thread.send("❌ That attachment doesn't look like an image. Please try again.")

            return

        thumbnail_url = None

        asset_channel_id = getattr(self.parent.bot, "config", {}).get("asset_channel_id") if getattr(self.parent.bot, "config", None) else None
        if asset_channel_id:
            try:
                asset_channel = self.parent.bot.get_channel(int(asset_channel_id))
                if asset_channel:
                    image_bytes = await attachment.read()
                    asset_msg = await asset_channel.send(file=discord.File(io.BytesIO(image_bytes), filename=attachment.filename))
                    if asset_msg.attachments:
                        thumbnail_url = asset_msg.attachments[0].url
            except Exception as e:

                thumbnail_url = attachment.url
        else:
            thumbnail_url = attachment.url


        if thumbnail_url:
            self.parent.embed.set_thumbnail(url=thumbnail_url)
            await thread.send("✅ Thumbnail accepted and set on the embed. The thread will be archived shortly.")



            try:
                await self.parent._show_final_confirmation(interaction, success=True)
            except Exception:

                try:
                    await interaction.followup.send("✅ Thumbnail set. Preview available.", ephemeral=True)
                except Exception:
                    pass


        try:
            await thread.edit(archived=True, locked=True)
        except Exception:
            pass


class EmbedLaunchView(ui.View):
    def __init__(self, bot: discord.Client | discord.Bot | discord.AutoShardedClient, author: discord.Member, channel: discord.TextChannel):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author
        self.channel = channel

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return False
        return True

    @ui.button(label="Create Embed", style=discord.ButtonStyle.primary)
    async def launch_modal_button(self, interaction: discord.Interaction, button: Button):
        modal = EmbedModal(bot=self.bot, channel=self.channel)
        await interaction.response.send_modal(modal)
        self.stop()
        button.disabled = True

        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass


class EmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(name="embed", description="Create a custom embed.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.default_permissions(manage_messages=True)
    async def embed_command(self, ctx: commands.Context):
        view = EmbedLaunchView(bot=self.bot, author=ctx.author, channel=ctx.channel)
        await ctx.reply("Click below to create an embed.", view=view, mention_author=False)






class HelpView(View):
    def __init__(self, ctx, whitelist, commands_dict_from_cog, category_emojis_from_cog, initial_category="Artists"):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.author = ctx.author
        self.whitelist = whitelist
        self.category = initial_category
        self.page = 1
        self.commands_dict = commands_dict_from_cog
        self.category_emojis = category_emojis_from_cog
        self.message = None 

        self.add_item(self.category_select_dropdown())
        
        self.prev_button = Button(emoji="◀", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_page
        self.add_item(self.prev_button)

        self.next_button = Button(emoji="▶", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)
        
        self.close_button = Button(emoji="🗑️", style=discord.ButtonStyle.danger)
        self.close_button.callback = self.close_menu
        self.add_item(self.close_button)

        self.update_button_states()

    def category_select_dropdown(self):
        options = []
        for cat, emoji in self.category_emojis.items():
            if cat == "Developer" and self.author.id not in self.whitelist:
                continue
            

            if isinstance(emoji, str) and emoji.startswith("<"):
                try: 
                    emoji = discord.PartialEmoji.from_str(emoji)
                except: 
                    emoji = None
            
            options.append(discord.SelectOption(
                label=cat, 
                emoji=emoji,
                default=(cat == self.category)
            ))
        
        if not options: 
            options.append(discord.SelectOption(label="No Categories"))

        select = Select(placeholder="Select a category", options=options, custom_id="help_select")
        select.callback = self.on_category_select
        return select

    def update_button_states(self):
        commands_in_category = self.commands_dict.get(self.category, [])
        total_pages = max(1, (len(commands_in_category) - 1) // 10 + 1)
        self.prev_button.disabled = (self.page <= 1)
        self.next_button.disabled = (self.page >= total_pages)
        if total_pages <= 1:
            self.prev_button.disabled = True
            self.next_button.disabled = True

    def get_embed(self):
        commands_in_category = self.commands_dict.get(self.category, [])
        total_pages = max(1, (len(commands_in_category) - 1) // 10 + 1)
        self.page = max(1, min(self.page, total_pages)) 
        
        start_index = (self.page - 1) * 10
        end_index = start_index + 10
        commands_subset = commands_in_category[start_index:end_index]

        emoji = self.category_emojis.get(self.category, "❓")

        embed = discord.Embed(color=0x2b2d31, timestamp=discord.utils.utcnow())
        embed.title = f"Help: {self.category}"
        
        embed.description = f"Use {self.ctx.me.mention} `command` to start."

        if not commands_subset:
            embed.description += "\n\n*No commands found in this category.*"
        else:
            for command in commands_subset:
                name = command.get("name", "Unknown")
                desc = command.get("description", "No description.")
                
                embed.add_field(
                    name=f"**{name}**", 
                    value=f"{self.ctx.me.mention} {name}\n└ {desc}",
                    inline=False
                )

        embed.set_footer(
            text=f"Page {self.page}/{total_pages} • {len(commands_in_category)} Commands", 
            icon_url=self.author.display_avatar.url
        )
        
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("❌ This help menu is not for you. Run `help` yourself!", ephemeral=True)
            return False
        return True

    async def on_category_select(self, interaction: discord.Interaction):
        selected_category = interaction.data["values"][0]
        self.category = selected_category
        self.page = 1
        
        self.clear_items()
        self.add_item(self.category_select_dropdown())
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.close_button)
        
        self.update_button_states()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_button_states()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.page += 1
        self.update_button_states()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def close_menu(self, interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


class HelpCog(commands.Cog, name="Help"):
    """The help command for the bot."""
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(name="help", aliases=["commands"], description="Displays the interactive help menu.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def help_command(self, ctx):
        """Displays the interactive help menu."""
        
        whitelist = self.bot.config.get("whitelisted_users", [])
        
        if self.bot.owner_id and self.bot.owner_id not in whitelist:
            whitelist.append(self.bot.owner_id)



        view = HelpView(ctx, whitelist, commands_dict, category_emojis)
        
        embed = view.get_embed()
        msg = await ctx.send(embed=embed, view=view)
        

        if ctx.interaction:

            view.message = await ctx.interaction.original_response()
        else:

            view.message = msg



class StatsCog(commands.Cog):
    """A cog for displaying bot statistics."""
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'start_time'):
            self.bot.start_time = time.time()

    @commands.command(aliases=["info", "ping", "botstats", "botinfo"])
    async def stats(self, ctx):
        """Displays bot statistics using Heist styling."""
        total_commands = 126
        if os.path.exists("commands.json"):
            try:
                with open("commands.json", "r") as f:
                    data = json.load(f)
                    total_commands = data.get("command_count", 0)
            except Exception:
                pass

        total_downloads = 0
        size_in_mb = 0
        if os.path.exists("data/Developer/download_stats.json"):
            try:
                with open("data/Developer/download_stats.json", "r") as f:
                    dl_stats = json.load(f)
                    total_downloads = dl_stats.get("total_downloads", 0)
                    total_size_bytes = dl_stats.get("total_size_bytes", 0)
                    size_in_mb = round(total_size_bytes / (1024 * 1024), 2)
            except Exception:
                pass

        guild_count = len(self.bot.guilds)
        
        total_members = sum(g.member_count for g in self.bot.guilds)
        
        total_bots = sum(1 for g in self.bot.guilds for m in g.members if m.bot)
        total_users = total_members - total_bots
        
        latency = round(self.bot.latency * 1000)

        try:
            process = psutil.Process()
            ram_usage = process.memory_full_info().rss / 1024**2
        except:
            ram_usage = 0


        uptime = f"<t:{int(self.bot.start_time)}:R>"


        stats_txt = (
            f"-# Total Commands » `{total_commands:,}`\n"
            f"-# Latency » `{latency}ms`\n"
            f"-# Uptime » {uptime}\n"
            f"-# Servers » `{guild_count:,}`\n"
            f"-# Users » `{total_users:,}`\n"
            f"-# Memory » `{ram_usage:.2f} MiB`\n"
            f"-# Total Downloads » `{total_downloads:,}`\n"
            f"-# Total Size » `{size_in_mb} MB`"
        )



        embed = discord.Embed(color=discord.Color.blurple())
        
        embed.title = f"{self.bot.user.name}"
        
        embed.description = (
            "-# Developed by **@xbox360s**\n\n" 
            + stats_txt + "\n\n"
        )
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)


        view = View()
        view.add_item(Button(
            label="Invite Bot", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/oauth2/authorize?client_id=1342901357568458772"
        ))
        view.add_item(Button(
            label="Join Server", 
            style=discord.ButtonStyle.link, 
            url="https://discord.gg/wotp"
        ))

        await ctx.send(embed=embed, view=view)


class Copier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @commands.command(name="stealemoji")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    @commands.bot_has_permissions(manage_emojis_and_stickers=True)
    async def steal_emoji(self, ctx, *, content: str = None):
        """Copy emoji(s) from a message or arguments and add them to the server."""
        guild = ctx.guild


        text_sources = []
        if ctx.message.reference:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_sources.append(ref_msg.content)
        if content:
            text_sources.append(content)

        if not text_sources:
            return await ctx.send("❌ Please reply to a message with emojis or provide emojis as arguments.")


        u_emojis = {}
        for text in text_sources:
            matches = re.findall(r"<(a?):(\w+):(\d+)>", text)
            for animated, name, emoji_id in matches:
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}"
                u_emojis[emoji_id] = (name, url)

        if not u_emojis:
            return await ctx.send("❌ No custom emojis found to steal.")

        msg = await ctx.send(f"⏳ Found {len(u_emojis)} emoji(s). Downloading and adding...")
        
        added = []
        failed = []

        async with aiohttp.ClientSession() as session:
            for em_id, (name, url) in u_emojis.items():
                try:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            failed.append(name)
                            continue
                        emoji_bytes = await resp.read()
                    
                    new_emoji = await guild.create_custom_emoji(name=name, image=emoji_bytes)
                    added.append(str(new_emoji))
                except Exception as e:
                    failed.append(name)

        result_text = []
        if added:
            result_text.append(f"✅ **Added ({len(added)}):** {' '.join(added)}")
        if failed:
            result_text.append(f"❌ **Failed ({len(failed)}):** {', '.join(failed)}")
        
        await msg.edit(content="\n".join(result_text))

    
    





    @commands.command(name="stealsticker")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    @commands.bot_has_permissions(manage_emojis_and_stickers=True)
    async def steal_sticker(self, ctx):
        """Copy a sticker from a replied message and add it to the server."""
        guild = ctx.guild


        if not ctx.message.reference:
            return await ctx.send(":x: You must reply to a message containing a sticker.")

        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not ref_msg.stickers:
            return await ctx.send(":x: That message has no stickers.")

        sticker = ref_msg.stickers[0]

        emoji_char = "🙂"


        async with aiohttp.ClientSession() as session:
            async with session.get(sticker.url) as resp:
                if resp.status != 200:
                    return await ctx.send(":x: Failed to fetch sticker.")
                sticker_bytes = await resp.read()

        try:

            new_sticker = await guild.create_sticker(
                name=sticker.name,
                description="Sticker",
                emoji=emoji_char,
                file=discord.File(fp=io.BytesIO(sticker_bytes), filename="sticker.png")
            )
            await ctx.send(f"✅ Added sticker: {new_sticker.name}")
        except Exception as e:
            await ctx.send(f":x: Failed to add sticker: {e}")





class Privacy(commands.Cog):
    """
    A simple cog that contains the bot's privacy policy command.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="privacy", aliases=["policy"])
    async def privacy(self, ctx):
        """Displays the bot's privacy policy."""
        

        privacy_policy_url = "https://www.collagebot.info/privacypolicy"
        
        embed = discord.Embed(
            title="Privacy Policy",
            description=f"The privacy of your data is important to us. You can view our full privacy policy by clicking the link below.\n\n[Click here to view our Privacy Policy]({privacy_policy_url})",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)



class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.coin_list = None

        self.priority_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "sol": "solana",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "shib": "shiba-inu",
            "dot": "polkadot",
            "matic": "matic-network",
            "link": "chainlink",
            "ltc": "litecoin",
            "bch": "bitcoin-cash",
            "usdt": "tether",
            "usdc": "usd-coin",
            "bnb": "binancecoin",
        }
        self.cache_task = self.bot.loop.create_task(self._cache_coin_list())

    async def _cache_coin_list(self):
        """Fetches and caches the list of all coins from CoinGecko."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                print("Caching CoinGecko coin list...")
                response = requests.get("https://api.coingecko.com/api/v3/coins/list")
                response.raise_for_status()
                self.coin_list = response.json()
                print("Successfully cached coin list.")

                await asyncio.sleep(86400)
            except requests.exceptions.RequestException as e:
                print(f"Error caching coin list: {e}. Retrying in 60 seconds.")
                await asyncio.sleep(60)

    def _find_coin_id(self, query: str) -> str | None:
        """Finds the CoinGecko ID for a given query, prioritizing common symbols."""
        query = query.lower()


        if query in self.priority_map:
            return self.priority_map[query]


        for coin in self.coin_list:
            if coin['id'] == query:
                return coin['id']
        

        for coin in self.coin_list:
            if coin['symbol'] == query:
                return coin['id']


        for coin in self.coin_list:
            if coin['name'].lower() == query:
                return coin['id']

        return None

    @commands.hybrid_command(name="price", description="Get a detailed price report for a cryptocurrency by name or symbol.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def price(self, ctx: commands.Context, *, crypto: str):
        """
        Provides a detailed price report for a given cryptocurrency.

        :param crypto: The name, symbol or ID of the cryptocurrency (e.g., bitcoin, btc, solana).
        """
        await ctx.defer()

        if not self.coin_list:
            embed = discord.Embed(
                title="Bot is Warming Up",
                description="The list of cryptocurrencies is still being cached. Please try again in a moment.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        coin_id = self._find_coin_id(crypto)

        if not coin_id:
            embed = discord.Embed(
                title="Cryptocurrency Not Found",
                description=f"Could not find data for '{crypto}'. Please check the name or symbol.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {'vs_currency': 'usd', 'ids': coin_id}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data:
                crypto_data = data[0]
                raw_ts = crypto_data['last_updated']
                safe_ts = raw_ts.replace("Z", "+00:00")
                embed = discord.Embed(
                    title=f"Report for {crypto_data['name']} ({crypto_data['symbol'].upper()})",
                    description="",
                    color=discord.Color.default(),
                    timestamp=datetime.fromisoformat(safe_ts)
                )
                embed.set_thumbnail(url=crypto_data['image'])
                embed.add_field(name="Current Price", value=f"**${crypto_data['current_price']:,.2f} USD**", inline=False)
                

                price_change_24h = crypto_data.get('price_change_percentage_24h')
                if price_change_24h is not None:
                    change_emoji = "📈" if price_change_24h >= 0 else "📉"
                    embed.add_field(name="24h Change", value=f"{change_emoji} {price_change_24h:.2f}%", inline=True)
                
                market_cap = crypto_data.get('market_cap')
                if market_cap is not None:
                    embed.add_field(name="Market Cap", value=f"${market_cap:,}", inline=True)
                
                total_volume = crypto_data.get('total_volume')
                if total_volume is not None:
                    embed.add_field(name="24h Volume", value=f"${total_volume:,}", inline=True)

                high_24h = crypto_data.get('high_24h')
                if high_24h is not None:
                    embed.add_field(name="24h High", value=f"${high_24h:,.2f}", inline=True)
                
                low_24h = crypto_data.get('low_24h')
                if low_24h is not None:
                    embed.add_field(name="24h Low", value=f"${low_24h:,.2f}", inline=True)

                ath = crypto_data.get('ath')
                if ath is not None:
                    embed.add_field(name="All-Time High", value=f"${ath:,.2f}", inline=True)
                
                circulating_supply = crypto_data.get('circulating_supply')
                if circulating_supply is not None:
                    embed.add_field(name="Circulating Supply", value=f"{circulating_supply:,.0f} {crypto_data['symbol'].upper()}", inline=True)
                
                embed.set_footer(text="Last Updated")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="Error", description=f"Found an ID for '{crypto}' but could not fetch its market data.", color=discord.Color.red())
                await ctx.send(embed=embed)

        except requests.exceptions.RequestException as e:
            print(f"An API error occurred: {e}")
            embed = discord.Embed(title="API Error", description="There was an issue connecting to the cryptocurrency service.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            embed = discord.Embed(title="An Unexpected Error Occurred", description="Something went wrong. Please try again.", color=discord.Color.dark_red())
            await ctx.send(embed=embed)





class SimplePaginator(discord.ui.View):
    def __init__(self, ctx, embeds):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.embeds = embeds
        self.current = 0
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = (self.current == 0)
        self.children[1].disabled = (self.current == len(self.embeds) - 1)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Not your menu.", ephemeral=True)
        self.current -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Not your menu.", ephemeral=True)
        self.current += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    async def start(self):
        await self.ctx.send(embed=self.embeds[0], view=self)

class HeistUtility(Cog):
    def __init__(self, bot):
        self.bot = bot


    async def get_color(self):
        """Returns the default information color"""
        return 0x2b2d31

    async def warn(self, ctx, message):
        """Standard warning message"""
        embed = Embed(description=f"⚠️ {message}", color=discord.Color.red())
        if hasattr(ctx, 'reply'):
            await ctx.reply(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed, ephemeral=True)

    async def neutral(self, ctx, description, title=None, image=None, footer=None):
        """Standard neutral/info message"""
        embed = Embed(description=description, color=await self.get_color())
        if title: embed.title = title
        if image: embed.set_image(url=image)
        if footer: embed.set_footer(text=footer)
        await ctx.send(embed=embed)

    async def paginate_text(self, ctx, entries, base_embed, per_page=10):
        """Splits a list of text lines into multiple embeds and paginates them"""
        embeds = []

        chunks = [entries[i:i + per_page] for i in range(0, len(entries), per_page)]
        
        for i, chunk in enumerate(chunks):

            embed = base_embed.copy()
            


            start_index = (i * per_page) + 1
            formatted_lines = []
            for idx, line in enumerate(chunk, start=start_index):
                formatted_lines.append(f"`{idx:02d}` {line}")
            
            embed.description = "\n".join(formatted_lines)
            

            footer_text = f"Page {i+1}/{len(chunks)}"
            if embed.footer.text:
                footer_text = f"{embed.footer.text} • {footer_text}"
            embed.set_footer(text=footer_text, icon_url=embed.footer.icon_url)
            
            embeds.append(embed)
        
        paginator = SimplePaginator(ctx, embeds)
        await paginator.start()



    @command(aliases=["perms"])
    async def permissions(self, ctx: Context):
        """View your permissions in the server"""
        member = ctx.author
        guild = ctx.guild
        

        user_perms = [perm for perm, value in member.guild_permissions if value]
        

        perm_names = [perm.replace('_', ' ').title() for perm in user_perms]
        entries = perm_names
        
        base_embed = Embed(color=await self.get_color())
        base_embed.set_author(
            name=f"Your permissions in {guild.name} ({len(entries)})",
            icon_url=ctx.author.display_avatar.url
        )

        if len(entries) > 10:
            await self.paginate_text(ctx, entries, base_embed, per_page=10)
        else:

            numbered_entries = [f"`{idx:02d}` {perm}" for idx, perm in enumerate(entries, start=1)]
            base_embed.description = "\n".join(numbered_entries)
            await ctx.send(embed=base_embed)
    
    @hybrid_command(aliases=["av", "pfp"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, ctx: Context, *, member: User = None):
        """View a user's avatar"""
        if not member:
            member = ctx.author
        
        await self.neutral(
            ctx,
            "",
            title=f"{member.display_name}'s avatar",
            image=member.display_avatar.url,
            footer=f"User ID: {member.id}"
        )
    
    @hybrid_command()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def banner(self, ctx: Context, *, member: User = None):
        """View a user's banner"""
        if not member:
            member = ctx.author
        

        user = await self.bot.fetch_user(member.id)
        
        if not user.banner:
            return await self.warn(ctx, f"{member.display_name} doesn't have a banner.")
        
        await self.neutral(
            ctx,
            "",
            title=f"{member.display_name}'s banner",
            image=user.banner.url,
            footer=f"User ID: {member.id}"
        )
    
    @command(aliases=["sav"])
    async def serveravatar(self, ctx: Context, *, member: Member = None):
        """View a user's server avatar"""
        if not member:
            member = ctx.author
        
        if not member.guild_avatar:
            return await self.warn(ctx, f"{member.display_name} doesn't have a server avatar.")
        
        await self.neutral(
            ctx,
            "",
            title=f"{member.display_name}'s server avatar",
            image=member.guild_avatar.url,
            footer=f"User ID: {member.id}"
        )
    
    @command(aliases=["sbanner"])
    async def serverbanner(self, ctx: Context):
        """View the server's banner"""
        guild = ctx.guild
        
        if not guild.banner:
            return await self.warn(ctx, f"{guild.name} doesn't have a banner.")
        
        await self.neutral(
            ctx,
            "",
            title=f"{guild.name}'s Banner",
            image=guild.banner.url,
            footer=f"Server ID: {guild.id}"
        )
    
    @command(aliases=["ci"])
    async def channelinfo(self, ctx: Context, channel=None):
        """View information about a channel"""
        if not channel:
            channel = ctx.channel
        else:

            try:
                channel = await commands.TextChannelConverter().convert(ctx, str(channel))
            except:
                try:

                    channel = ctx.bot.get_channel(int(channel))
                    if not channel:
                        return await self.warn(ctx, "Channel not found.")
                except:
                    return await self.warn(ctx, "Invalid channel ID.")
        
        channel_types = {
            TextChannel: "text",
            VoiceChannel: "voice", 
            CategoryChannel: "category",
            ForumChannel: "forum",
            StageChannel: "stage"
        }
        
        channel_type = channel_types.get(type(channel), "unknown")
        
        embed = Embed(
            color=await self.get_color(),
            title=channel.name
        )
        
        embed.add_field(name="Channel ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="Type", value=channel_type, inline=True)
        embed.add_field(name="Created At", value=f"<t:{int(channel.created_at.timestamp())}:F>", inline=True)
        embed.add_field(name="Guild", value=f"{channel.guild.name} (`{channel.guild.id}`)", inline=True)
        
        await ctx.send(embed=embed)
    
    @command()
    async def roles(self, ctx: Context):
        """View roles in the server"""
        guild = ctx.guild
        

        roles_with_members = [role for role in guild.roles if len(role.members) > 0 and role != guild.default_role]
        roles_with_members.sort(key=lambda r: len(r.members), reverse=True)
        
        if not roles_with_members:
            embed = Embed(
                color=await self.get_color(),
                title="Roles with Members (0)",
                description="No roles with members found."
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)
        
        entries = []
        for role in roles_with_members:
            entries.append(f"**<@&{role.id}>**")
        
        base_embed = Embed(
            color=await self.get_color(),
            title=f"Roles with Members ({len(roles_with_members)})"
        )
        base_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        if len(entries) > 10:
            await self.paginate_text(ctx, entries, base_embed, per_page=10)
        else:

            numbered_entries = [f"`{idx:02d}` {role}" for idx, role in enumerate(entries, start=1)]
            base_embed.description = "\n".join(numbered_entries)
            await ctx.send(embed=base_embed)

    @command(name="inviteinfo", aliases=["ii"])
    async def inviteinfo(self, ctx: Context, *, code: Invite):
        """View information about a guild using an invite code."""
        embed = Embed(title=f"Invite Code: {code.code}", color=await self.get_color())
        embed.add_field(
            name="Invite & Channel",
            value=f"**Name:** {code.channel.name} \n**ID:** {code.channel.id} \n**Created:** {format_dt(code.created_at, 'F') if code.created_at else 'Unknown'} \n**Expiration:** {format_dt(code.expires_at) if code.expires_at else 'Never'} \n**Inviter:** {code.inviter if code.inviter else 'Vanity URL'}", 
        )
        embed.add_field(
            name="Guild",
            value=f"**Name:** {code.guild.name} \n**Created:** {format_dt(code.guild.created_at, 'F')} \n**Members:** {code.approximate_member_count: ,} \n**Active:** {code.approximate_presence_count: ,} \n**Verification:** {code.guild.verification_level}",
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        if code.guild.icon:
            embed.set_thumbnail(url=code.guild.icon.url)
            
        await ctx.send(embed=embed)

    @command(name="banreason", description="Get a user's ban reason.")
    @commands.has_permissions(ban_members=True)
    async def banreason(self, ctx: Context, *, user: User):
        """View the reason why someone was banned."""

        entry = None
        async for ban in ctx.guild.bans():
            if ban.user.id == user.id:
                entry = ban
                break

        if not entry:
            return await self.warn(ctx, "This member is **not** banned.")


        timestamp_str = "unknown timestamp"
        async for log in ctx.guild.audit_logs(action=AuditLogAction.ban):
            if log.target.id == user.id:
                timestamp_str = f"<t:{int(log.created_at.timestamp())}:f>"
                break

        reason = entry.reason or 'No reason provided'
        await self.neutral(
            ctx,
            f"**{user.name}** was banned for **{reason}** at {timestamp_str}."
        )

    @command()
    @commands.has_permissions(manage_guild=True)
    async def invites(self, ctx: Context):
        """View server invites"""
        invites = await ctx.guild.invites()
        
        if not invites:
            return await self.warn(ctx, "No invites found")
        
        entries = []
        for invite in invites:
            inviter = invite.inviter.display_name if invite.inviter else "Unknown"
            inviter_id = invite.inviter.id if invite.inviter else "Unknown"
            entries.append(f"[{invite.code}](https://discord.gg/{invite.code}) by **{inviter}** (`{inviter_id}`)") 
        
        base_embed = Embed(
            color=await self.get_color(),
            title=f"{len(invites)} invites"
        )
        
        if len(entries) > 10:
            await self.paginate_text(ctx, entries, base_embed, per_page=10)
        else:

            numbered_entries = [f"`{idx:02d}` {line}" for idx, line in enumerate(entries, start=1)]
            base_embed.description = "\n".join(numbered_entries)
            await ctx.send(embed=base_embed)

    @command()
    async def inrole(self, ctx: Context, *, role: Role):
        """View members in a role"""
        members = role.members
        
        if not members:
            return await self.warn(ctx, f"No members found in {role.name}")
        
        entries = []
        for member in members:
            you_text = " - **you**" if member.id == ctx.author.id else ""
            entries.append(f"<@{member.id}> (`{member.id}`){you_text}")
        
        base_embed = Embed(
            color=await self.get_color(),
            title=f"{len(members)} members in {role.name}"
        )
        base_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        if len(entries) > 10:
            await self.paginate_text(ctx, entries, base_embed, per_page=10)
        else:
            numbered_entries = [f"`{idx:02d}` {line}" for idx, line in enumerate(entries, start=1)]
            base_embed.description = "\n".join(numbered_entries)
            await ctx.send(embed=base_embed)

    @command()
    async def boosters(self, ctx: Context):
        """View server boosters"""
        boosters = ctx.guild.premium_subscribers
        
        if not boosters:
            return await self.warn(ctx, "No boosters found")
        
        entries = []
        for member in boosters:
            you_text = " - **you**" if member.id == ctx.author.id else ""
            entries.append(f"<@{member.id}> (`{member.id}`){you_text}")
        
        base_embed = Embed(
            color=await self.get_color(),
            title=f"{len(boosters)} boosters"
        )
        base_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        if len(entries) > 10:
            await self.paginate_text(ctx, entries, base_embed, per_page=10)
        else:
            numbered_entries = [f"`{idx:02d}` {line}" for idx, line in enumerate(entries, start=1)]
            base_embed.description = "\n".join(numbered_entries)
            await ctx.send(embed=base_embed)

    @hybrid_command()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def getbotinvite(self, ctx: Context, *, user: User):
        """Get an invite for a bot"""
        if not user.bot:
            return await self.warn(ctx, "This is not a bot")

        invite_url = f"https://discord.com/oauth2/authorize?client_id={user.id}"
        await ctx.reply(f"Invite [{user}]({invite_url})")




INFO_COLOR = 0x2b2d31    


async def heisted_paginate(ctx, entries, embed_template, per_page=10):
    pages = [entries[i:i+per_page] for i in range(0, len(entries), per_page)]
    
    def get_page_embed(page_idx):
        e = embed_template.copy()
        e.description = "\n".join(pages[page_idx])
        e.set_footer(text=f"Page {page_idx + 1}/{len(pages)} ({len(entries)} entries)")
        return e

    if len(pages) == 1:
        return await ctx.send(embed=get_page_embed(0))

    class PaginatorView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.current = 0

        @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction, button):
            if interaction.user != ctx.author: return
            self.current = max(0, self.current - 1)
            await interaction.response.edit_message(embed=get_page_embed(self.current))

        @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary)
        async def next(self, interaction, button):
            if interaction.user != ctx.author: return
            self.current = min(len(pages) - 1, self.current + 1)
            await interaction.response.edit_message(embed=get_page_embed(self.current))

    await ctx.send(embed=get_page_embed(0), view=PaginatorView())


class HeistUtility2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="joins", description="View recent joins in the server")
    async def joins(self, ctx):
        guild = ctx.guild
        members = sorted(guild.members, key=lambda m: m.joined_at or datetime.min, reverse=True)
        now = datetime.now(timezone.utc)
        recent_joins = [m for m in members if m.joined_at and (now - m.joined_at).days < 1]
        
        if not recent_joins:
            embed = Embed(
                color=INFO_COLOR,
                title=f"0 joins in the last 1d in {guild.name}",
                description="No recent joins found."
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)
        
        entries = []
        for idx, member in enumerate(recent_joins, start=1):
            timestamp = int(member.joined_at.timestamp())
            entries.append(f"`{idx:02d}` {member.display_name} - <t:{timestamp}:R>")
        
        base_embed = Embed(
            color=INFO_COLOR,
            title=f"{len(recent_joins)} joins in the last 1d in {guild.name}"
        )
        base_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        await heisted_paginate(ctx, entries, base_embed, per_page=10)

    @commands.hybrid_command(name="bots", description="View bots in the server")
    async def bots(self, ctx):
        guild = ctx.guild
        bot_members = [m for m in guild.members if m.bot]
        
        if not bot_members:
            embed = Embed(color=INFO_COLOR, title="0 Bots", description="No bots found in this server.")
            return await ctx.send(embed=embed)
        
        entries = []
        for idx, bot in enumerate(bot_members, start=1):
            entries.append(f"`{idx:02d}` <@{bot.id}> (`{bot.id}`)")
        
        base_embed = Embed(color=INFO_COLOR, title=f"{len(bot_members)} Bots")
        
        if len(entries) > 10:
            await heisted_paginate(ctx, entries, base_embed, per_page=10)
        else:
            base_embed.description = "\n".join(entries)
            await ctx.send(embed=base_embed)

    @commands.hybrid_command(name="roleinfo", aliases=["ri"], description="View information about a role")
    async def roleinfo(self, ctx, role: discord.Role):
        dangerous_perms_list = [
            "administrator", "kick_members", "ban_members", "manage_guild",
            "manage_roles", "manage_channels", "manage_expressions",
            "manage_webhooks", "manage_nicknames", "mention_everyone"
        ]
        
        role_perms = [perm for perm, value in role.permissions if value and perm in dangerous_perms_list]
        
        embed = Embed(
            color=role.color if role.color.value != 0 else INFO_COLOR,
            title=role.name
        )
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Role color", value="No color" if role.color.value == 0 else f"#{role.color.value:06x}", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(role.created_at.timestamp())}:f> **{discord.utils.format_dt(role.created_at, 'R')}**", inline=False)
        
        member_count = len(role.members)
        if member_count == 0:
            member_text = "No members"
        else:
            sorted_members = sorted(role.members, key=lambda m: m.joined_at or datetime.now(timezone.utc), reverse=True)
            preview = sorted_members[:10]
            member_text = ", ".join([f"`{m.display_name}`" for m in preview])
            
            if member_count > 10:
                member_text += f"\n...and **{member_count - 10}** more."
            
        embed.add_field(name=f"{member_count} Member{'s' if member_count != 1 else ''}", value=member_text, inline=False)
        
        if role_perms:
            perm_names = [perm.replace('_', ' ').title() for perm in role_perms]
            embed.add_field(name="Dangerous Permissions", value=", ".join(perm_names), inline=False)
            
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)





async def setup(bot: commands.Bot):
    await bot.add_cog(TopDownloads(bot))
    await bot.add_cog(UtilityCog(bot))
    await bot.add_cog(UserInfoCog(bot))
    await bot.add_cog(EmbedCog(bot))
    await bot.add_cog(HelpCog(bot))
    await bot.add_cog(StatsCog(bot))
    await bot.add_cog(Copier(bot))
    await bot.add_cog(Privacy(bot))
    await bot.add_cog(Crypto(bot))
    await bot.add_cog(HeistUtility(bot))
    await bot.add_cog(HeistUtility2(bot))