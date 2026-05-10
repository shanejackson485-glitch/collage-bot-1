import discord
from discord.ext import commands
import time
import platform
import psutil
from datetime import datetime, timedelta, timezone
import os
import shutil
import zipfile
import sqlite3
import json 
import io
import textwrap
import traceback
import contextlib
from discord import ui
import asyncio
from typing import Optional, Union


DIR_PATH = "data/Developer"
BLACKLIST_FILE = f"{DIR_PATH}/blacklist.json"
SERVERS_FILE = f"{DIR_PATH}/servers.json"
CONFIG_FILE = f"{DIR_PATH}/config.json"
ERROR_LOG_FILE = "logs/collage.log"


if not os.path.exists(DIR_PATH):
    os.makedirs(DIR_PATH)

def load_json_sync(path):
    try:
        with open(path, "r") as f: 
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def save_json_async(bot, path, data):
    def write():
        with open(path, "w") as f: json.dump(data, f, indent=4)
    await bot.loop.run_in_executor(None, write)

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = time.time()
        

        self.config = load_json_sync(CONFIG_FILE)
        self.admin_id = self.config.get("admin_user_id")
        self.whitelisted_users = self.config.get("whitelisted_users", [])
        
        if not self.admin_id:
            print(f"⚠️ Developer Cog: 'admin_user_id' missing in {CONFIG_FILE}. Commands may be inaccessible.")


        self.blacklist_data = load_json_sync(BLACKLIST_FILE)
        self.servers_data = load_json_sync(SERVERS_FILE)

    def is_user_whitelisted(self, user_id):

        return user_id == self.admin_id or user_id in self.whitelisted_users or user_id == self.bot.owner_id

    async def cog_check(self, ctx):

        if not self.is_user_whitelisted(ctx.author.id):
            return False
        return True


    async def send_success(self, ctx, title, description):
        embed = discord.Embed(title=f"✅ {title}", description=description, color=discord.Color.green())
        await ctx.send(embed=embed)

    async def send_error(self, ctx, title, description):
        embed = discord.Embed(title=f"❌ {title}", description=description, color=discord.Color.red())
        await ctx.send(embed=embed)

    async def send_info(self, ctx, title, description):
        embed = discord.Embed(title=f"ℹ️ {title}", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)




    @commands.command(name="blacklist")
    async def blacklist(self, ctx, target_type: str, target_id: int, *, reason: str = "No reason provided."):
        """Blacklist a server or a user."""
        target_type = target_type.lower()
        
        if target_type not in ["guild", "user"]:
             return await self.send_error(ctx, "Invalid Type", "Use `guild` or `user`.")

        key = "guilds" if target_type == "guild" else "users"
        
        if str(target_id) in self.blacklist_data.get(key, {}):
            return await self.send_error(ctx, "Already Blacklisted", f"{target_type.title()} {target_id} is already blacklisted.")


        if key not in self.blacklist_data: self.blacklist_data[key] = {}
        
        self.blacklist_data[key][str(target_id)] = {"message": reason, "date": str(datetime.now())}
        await save_json_async(self.bot, BLACKLIST_FILE, self.blacklist_data)

        listeners = self.bot.get_cog("Listeners")
        if listeners:
            listeners.blacklist_cache = self.blacklist_data
        
        await self.send_success(ctx, "Blacklisted", f"🚫 **{target_type.title()}**: `{target_id}`\n📝 **Reason**: {reason}")


        if target_type == "guild":
            guild = self.bot.get_guild(target_id)
            if guild:
                await guild.leave()

    @commands.command(name="unblacklist")
    async def unblacklist(self, ctx, target_type: str, target_id: int):
        target_type = target_type.lower()
        target_id_str = str(target_id)
        key = "guilds" if target_type == "guild" else "users"

        if target_id_str in self.blacklist_data.get(key, {}):
            del self.blacklist_data[key][target_id_str]
            await save_json_async(self.bot, BLACKLIST_FILE, self.blacklist_data)

            
            listeners = self.bot.get_cog("Listeners")
            if listeners:
                listeners.blacklist_cache = self.blacklist_data
            await self.send_success(ctx, "Unblacklisted", f"Allowed `{target_id}` access again.")
        else:
            await self.send_error(ctx, "Not Found", "Target is not in the blacklist.")




    @commands.command(name="leave")
    async def leave_server(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await self.send_error(ctx, "Not Found", "I am not in a server with that ID.")
        
        try:
            await guild.leave()
            await self.send_success(ctx, "Left Server", f"Successfully left **{guild.name}** ({guild.id}).")
        except Exception as e:
            await self.send_error(ctx, "Failed", f"Could not leave: {e}")

    @commands.command()
    async def addrole(self, ctx, member: Union[discord.Member, str], *, role: discord.Role):
        """Adds a role to a specific user or 'all' users."""
        

        if isinstance(member, str) and member.lower() == "all":
            await self.send_info(ctx, "Mass Role Add", f"⏳ Assigning {role.mention} to **{ctx.guild.member_count}** members.\nThis will take time to avoid API limits.")
            
            count = 0
            failed = 0
            start_time = time.time()
            
            for m in ctx.guild.members:
                if m.bot: continue
                if role in m.roles: continue
                
                try:
                    await m.add_roles(role, reason="Mass Role Add by Dev")
                    count += 1

                    if count % 5 == 0:
                        await asyncio.sleep(1.5)
                except:
                    failed += 1
            
            duration = str(timedelta(seconds=int(time.time() - start_time)))
            await self.send_success(ctx, "Task Complete", f"✅ Added to: {count}\n❌ Failed: {failed}\n⏱️ Time: {duration}")
            return


        if isinstance(member, discord.Member):
            try:
                await member.add_roles(role)
                await self.send_success(ctx, "Role Added", f"Added {role.mention} to {member.mention}.")
            except discord.Forbidden:
                await self.send_error(ctx, "Forbidden", "I don't have permission to add roles to that user (Hierarchy check).")


    class ServerListView(ui.View):
        def __init__(self, ctx, pages):
            super().__init__(timeout=60)
            self.ctx = ctx
            self.pages = pages
            self.current_page = 0
            self.update_buttons()

        def update_buttons(self):
            self.first_page.disabled = (self.current_page == 0)
            self.prev_page.disabled = (self.current_page == 0)
            self.next_page.disabled = (self.current_page == len(self.pages) - 1)
            self.last_page.disabled = (self.current_page == len(self.pages) - 1)

        async def update_message(self, interaction):
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

        async def interaction_check(self, interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("❌ This menu is not for you.", ephemeral=True)
                return False
            return True

        @ui.button(label="⏮", style=discord.ButtonStyle.secondary)
        async def first_page(self, interaction, button):
            self.current_page = 0
            await self.update_message(interaction)

        @ui.button(label="⬅", style=discord.ButtonStyle.secondary)
        async def prev_page(self, interaction, button):
            self.current_page = max(self.current_page - 1, 0)
            await self.update_message(interaction)

        @ui.button(label="➡", style=discord.ButtonStyle.secondary)
        async def next_page(self, interaction, button):
            self.current_page = min(self.current_page + 1, len(self.pages) - 1)
            await self.update_message(interaction)

        @ui.button(label="⏭", style=discord.ButtonStyle.secondary)
        async def last_page(self, interaction, button):
            self.current_page = len(self.pages) - 1
            await self.update_message(interaction)

    @commands.command(name="listservers")
    async def listservers(self, ctx):
        guilds = list(self.bot.guilds)
        if not guilds: return await ctx.send("I am in no servers.")
        
        pages = []
        chunk_size = 5

        for i in range(0, len(guilds), chunk_size):
            chunk = guilds[i:i + chunk_size]
            embed = discord.Embed(title=f"🤖 Server List ({len(guilds)} Total)", color=discord.Color.blurple())
            
            for g in chunk:
                desc = f"🆔 `{g.id}`\n👥 **Members:** {g.member_count}\n👑 **Owner:** {g.owner}"
                embed.add_field(name=g.name, value=desc, inline=False)
            
            embed.set_footer(text=f"Page {len(pages)+1} of {(len(guilds)+chunk_size-1)//chunk_size}")
            pages.append(embed)

        view = self.ServerListView(ctx, pages)
        await ctx.send(embed=pages[0], view=view)

    @commands.command(name="createinvite")
    async def createinvite(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild: return await self.send_error(ctx, "Error", "Guild not found.")
        

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                try:
                    invite = await channel.create_invite(max_age=300, max_uses=1, reason="Dev Force Invite")
                    return await self.send_success(ctx, f"Invite for {guild.name}", f"🔗 [Click to Join]({invite.url})")
                except:
                    continue
        
        await self.send_error(ctx, "Failed", "Could not create invite (Missing permissions in all channels).")




    @commands.command(name="debug")
    async def debug(self, ctx):
        uptime_seconds = time.time() - self.bot_start_time
        uptime = str(timedelta(seconds=int(uptime_seconds)))
        
        embed = discord.Embed(title="🔧 System Diagnostics", color=discord.Color.dark_grey())
        embed.add_field(name="💻 Platform", value=platform.system(), inline=True)
        embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📚 Discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="🧠 CPU Usage", value=f"{psutil.cpu_percent()}%", inline=True)
        embed.add_field(name="💾 RAM Usage", value=f"{psutil.virtual_memory().percent}%", inline=True)
        embed.add_field(name="📶 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    async def reload_cog(self, ctx, extension: str):
        """Reloads a cog. Tries standard paths."""
        try:

            await self.bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            try:

                await self.bot.reload_extension(f"cogs.{extension}")
            except Exception as e:
                return await self.send_error(ctx, "Load Error", f"Could not find/load `{extension}`.\nError: `{e}`")
        except Exception as e:
            return await self.send_error(ctx, "Syntax Error", f"Failed to reload `{extension}`.\nError: `{e}`")

        await self.send_success(ctx, "Reloaded", f"🔄 `{extension}` has been reloaded.")

    @commands.command(name="logs")
    async def logs(self, ctx, lines: int = 15):
        if not os.path.exists(ERROR_LOG_FILE):
            return await self.send_error(ctx, "Missing File", "Error log file does not exist.")
            
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as file:
                content = file.readlines()
            
            if not content:
                return await self.send_success(ctx, "Clean Logs", "Log file is empty.")

            last_lines = "".join(content[-lines:])
            
            if len(last_lines) > 1900:

                file = discord.File(io.BytesIO(last_lines.encode()), filename="logs.txt")
                await ctx.send("📄 **Log Output (Too long for embed):**", file=file)
            else:
                await ctx.send(f"```prolog\n{last_lines}\n```")
        except Exception as e:
            await self.send_error(ctx, "Read Error", str(e))

    @commands.command(name="clear_logs")
    async def clear_logs(self, ctx):
        with open(ERROR_LOG_FILE, "w") as file: file.truncate(0)
        await self.send_success(ctx, "Logs Cleared", "The error log has been wiped.")

    @commands.command(name="sync")
    async def sync(self, ctx):
        msg = await ctx.send("⏳ Syncing slash commands...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            await msg.edit(content=f"❌ Sync failed: {e}")

    @commands.command(name="backup")
    async def create_backup(self, ctx):
        """Zips the 'data' folder and sends it."""
        msg = await ctx.send("📦 Creating backup...")
        try:
            if not os.path.exists("data"):
                return await msg.edit(content="❌ No data folder to backup.")

            shutil.make_archive("backup", 'zip', "data")
            
            file_size = os.path.getsize("backup.zip")
            if file_size > 8 * 1024 * 1024:
                await msg.edit(content=f"❌ Backup is too large to send ({round(file_size/1024/1024, 2)}MB).")
            else:
                await ctx.send(file=discord.File("backup.zip"))
                await msg.delete()
            
            os.remove("backup.zip")
        except Exception as e:
            await ctx.send(f"Backup failed: {e}")

    @commands.command(name="shutdown")
    async def shutdown(self, ctx):
        await self.send_error(ctx, "System", "🔌 Shutting down bot...")
        await self.bot.close()

    @commands.command(name="eval")
    async def eval_code(self, ctx, *, code: str):
        """
        Executes raw Python code. 
        Supports await, multi-line, and stdout capture.
        """

        code = code.strip("`")
        if code.startswith("py\n"):
            code = code[3:]
        elif code.startswith("python\n"):
            code = code[7:]

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': None
        }


        stdout = io.StringIO()


        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        try:
            with contextlib.redirect_stdout(stdout):
                exec(to_compile, env)
                func = env['func']
                result = await func()
        except Exception:

            return await ctx.send(f"❌ **Error:**\n```py\n{traceback.format_exc()}\n```")


        output = stdout.getvalue()
        if result is not None:
            output += f"\n[Returned]: {result}"

        if not output:
            await ctx.message.add_reaction("✅")
        elif len(output) > 1900:
            file = discord.File(io.BytesIO(output.encode()), filename="eval_output.txt")
            await ctx.send("📝 Output too long:", file=file)
        else:
            await ctx.send(f"```py\n{output}\n```")

    @commands.command(name="sql")
    async def database_query(self, ctx, *, query: str):
        """Runs a raw SQL query on database.db"""
        if not os.path.exists("database.db"):
            return await self.send_error(ctx, "No Database", "database.db file not found.")

        try:
            connection = sqlite3.connect("database.db")
            cursor = connection.cursor()
            cursor.execute(query)
            

            if query.lower().startswith(("insert", "update", "delete", "create", "drop")):
                connection.commit()
                await self.send_success(ctx, "SQL Executed", f"Query executed successfully.\nRows affected: {cursor.rowcount}")
            else:

                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                result = cursor.fetchall()
                
                if not result:
                    await self.send_info(ctx, "SQL Result", "Query returned no rows.")
                else:

                    output = f"Columns: {columns}\n\n"
                    for row in result:
                        output += f"{row}\n"
                    
                    if len(output) > 1900:
                        file = discord.File(io.BytesIO(output.encode()), filename="sql_result.txt")
                        await ctx.send(file=file)
                    else:
                        await ctx.send(f"```py\n{output}\n```")
            
            connection.close()
        except sqlite3.Error as e:
            await self.send_error(ctx, "SQL Error", f"```\n{e}\n```")

    @commands.command(name="reset")
    async def reset(self, ctx, filename: str):
        """Resets a JSON file to {}."""
        if not filename.endswith('.json'):
            return await self.send_error(ctx, "Invalid File", "Only .json files allowed.")
        

        target_path = os.path.join(DIR_PATH, filename)
        if not os.path.exists(target_path):
            target_path = filename
        
        if not os.path.exists(target_path):
            return await self.send_error(ctx, "Not Found", f"File `{filename}` not found.")
        
        try:

            with open(target_path, "w") as file: 
                file.write("{}")
            await self.send_success(ctx, "Reset Complete", f"File `{filename}` has been reset to `{{}}`.")
        except Exception as e:
            await self.send_error(ctx, "Write Error", str(e))


    class CmdPaginator(ui.View):
        def __init__(self, ctx, pages):
            super().__init__(timeout=120)
            self.ctx = ctx
            self.pages = pages
            self.current_page = 0
            self.update_buttons()

        def update_buttons(self):
            self.first_page.disabled = (self.current_page == 0)
            self.prev_page.disabled = (self.current_page == 0)
            self.next_page.disabled = (self.current_page == len(self.pages) - 1)
            self.last_page.disabled = (self.current_page == len(self.pages) - 1)

        async def update_message(self, interaction):
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

        async def interaction_check(self, interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("❌ This menu is not for you.", ephemeral=True)
                return False
            return True

        @ui.button(label="⏮", style=discord.ButtonStyle.secondary)
        async def first_page(self, interaction, button):
            self.current_page = 0
            await self.update_message(interaction)

        @ui.button(label="⬅", style=discord.ButtonStyle.secondary)
        async def prev_page(self, interaction, button):
            self.current_page = max(self.current_page - 1, 0)
            await self.update_message(interaction)

        @ui.button(label="➡", style=discord.ButtonStyle.secondary)
        async def next_page(self, interaction, button):
            self.current_page = min(self.current_page + 1, len(self.pages) - 1)
            await self.update_message(interaction)

        @ui.button(label="⏭", style=discord.ButtonStyle.secondary)
        async def last_page(self, interaction, button):
            self.current_page = len(self.pages) - 1
            await self.update_message(interaction)


    @commands.command(name="cmd_map", aliases=["cogs_inspect", "list_cmds"])
    async def cmd_map(self, ctx):
        """Lists commands grouped by Cog with descriptions (Paginated)."""
        
        cogs_map = {}
        total_commands = 0


        for cog_name, cog in self.bot.cogs.items():
            cmds = cog.get_commands()
            if cmds:
                cogs_map[cog_name] = cmds
                total_commands += len(cmds)


        standalone_cmds = [c for c in self.bot.commands if c.cog is None]
        if standalone_cmds:
            cogs_map["[Main / No Cog]"] = standalone_cmds
            total_commands += len(standalone_cmds)


        sorted_cogs = sorted(cogs_map.items(), key=lambda x: x[0])



        pages = []
        CHUNK_SIZE = 3
        
        for i in range(0, len(sorted_cogs), CHUNK_SIZE):
            chunk = sorted_cogs[i:i + CHUNK_SIZE]
            
            embed = discord.Embed(
                title=f"🔌 Command Map (Total: {total_commands})", 
                description="List of loaded commands and their descriptions.",
                color=discord.Color.teal()
            )
            
            for cog_name, cmd_list in chunk:

                cmd_list.sort(key=lambda x: x.name)
                
                field_text = ""
                lines_added = 0
                
                for cmd in cmd_list:

                    desc = cmd.short_doc if cmd.short_doc else "No description"
                    line = f"• **{cmd.name}**: {desc}\n"
                    

                    if len(field_text) + len(line) > 1000:
                        remaining = len(cmd_list) - lines_added
                        field_text += f"... *({remaining} more)*"
                        break
                    
                    field_text += line
                    lines_added += 1
                
                embed.add_field(name=f"📂 {cog_name}", value=field_text, inline=False)
            
            embed.set_footer(text=f"Page {len(pages) + 1} / {(len(sorted_cogs) + CHUNK_SIZE - 1) // CHUNK_SIZE}")
            pages.append(embed)

        if not pages:
            return await ctx.send("❌ No commands found.")


        view = self.CmdPaginator(ctx, pages)
        await ctx.send(embed=pages[0], view=view)



whitelist = []
banned_user_ids = []

def is_whitelisted():
    async def predicate(ctx):
        return ctx.author.id in whitelist
    return commands.check(predicate)

def is_whitelisted():
    async def predicate(ctx):
        return ctx.author.id in whitelist
    return commands.check(predicate)

def perms_to_str(permissions: discord.Permissions) -> str:
    perms = []
    if permissions.administrator:
        perms.append("Administrator")
    else:
        checks = {
            "Manage Server": permissions.manage_guild,
            "Manage Roles": permissions.manage_roles,
            "Manage Channels": permissions.manage_channels,
            "Kick Members": permissions.kick_members,
            "Ban Members": permissions.ban_members,
            "View Audit Log": permissions.view_audit_log,
            "Send Messages": permissions.send_messages,
            "Manage Messages": permissions.manage_messages,
            "Embed Links": permissions.embed_links,
            "Attach Files": permissions.attach_files,
            "Connect (Voice)": permissions.connect,
            "Speak (Voice)": permissions.speak,
            "Use Slash Commands": permissions.use_application_commands,
        }
        for name, val in checks.items():
            if val:
                perms.append(name)
    return ", ".join(perms) if perms else "No permissions"

class ServerFetch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverfetch")
    @is_whitelisted()
    async def server_fetch(self, ctx, guild_id: int):
        cached_guild = self.bot.get_guild(guild_id)
        if not cached_guild:
            return await ctx.send("❌ I'm not in a server with that ID or it's invalid.")

        try:
            guild = await self.bot.fetch_guild(guild_id)
        except:
            guild = cached_guild

        text_channels = [c for c in cached_guild.channels if isinstance(c, discord.TextChannel)]
        voice_channels = [c for c in cached_guild.channels if isinstance(c, discord.VoiceChannel)]
        categories = [c for c in cached_guild.channels if isinstance(c, discord.CategoryChannel)]
        stickers = await cached_guild.fetch_stickers()
        roles = sorted(cached_guild.roles, key=lambda r: r.position, reverse=True)
        emojis = cached_guild.emojis
        bot_member = cached_guild.me
        bot_permissions = bot_member.guild_permissions if bot_member else discord.Permissions.none()

        online_members = len([m for m in cached_guild.members if m.status != discord.Status.offline])
        bots = len([m for m in cached_guild.members if m.bot])
        boosters = len([m for m in cached_guild.members if m.premium_since])


        try:
            bans = []
            async for ban_entry in cached_guild.bans():
                bans.append(ban_entry)
            banned_found = [b.user for b in bans if b.user.id in banned_user_ids]
        except discord.Forbidden:
            banned_found = None

        embed = discord.Embed(
            title=f"Server Info: {guild.name}",
            description=f"Owned by {guild.owner} ({guild.owner_id})",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text=f"Guild ID: {guild.id}")
        embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        embed.add_field(name="Total Members", value=cached_guild.member_count, inline=True)
        embed.add_field(name="Online Members", value=online_members, inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boosters", value=boosters, inline=True)
        embed.add_field(name="Roles", value=len(roles), inline=True)
        embed.add_field(name="Emojis", value=len(emojis), inline=True)
        embed.add_field(name="Stickers", value=len(stickers), inline=True)
        embed.add_field(name="Text Channels", value=len(text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(voice_channels), inline=True)
        embed.add_field(name="Categories", value=len(categories), inline=True)
        embed.add_field(name="Verification Level", value=str(guild.verification_level).capitalize(), inline=True)
        embed.add_field(name="NSFW Level", value=str(guild.nsfw_level).capitalize(), inline=True)
        embed.add_field(name="Default Locale", value=guild.preferred_locale, inline=True)

        embed.add_field(name="System Channel", value=cached_guild.system_channel.mention if cached_guild.system_channel else "None", inline=True)
        embed.add_field(name="Rules Channel", value=cached_guild.rules_channel.mention if cached_guild.rules_channel else "None", inline=True)
        embed.add_field(name="Public Updates", value=cached_guild.public_updates_channel.mention if cached_guild.public_updates_channel else "None", inline=True)
        embed.add_field(name="AFK Channel", value=cached_guild.afk_channel.mention if cached_guild.afk_channel else "None", inline=True)
        embed.add_field(name="AFK Timeout", value=f"{cached_guild.afk_timeout // 60} min", inline=True)

        features = ", ".join(guild.features) if guild.features else "None"
        embed.add_field(name="Features", value=features, inline=False)

        try:
            welcome_screen = await cached_guild.fetch_welcome_screen()
            if welcome_screen:
                if welcome_screen.description:
                    embed.add_field(name="Welcome Screen Description", value=welcome_screen.description, inline=False)
                if welcome_screen.welcome_channels:
                    ws_channels = "\n".join(f"• {c.channel.name}" for c in welcome_screen.welcome_channels)
                    embed.add_field(name="Welcome Channels", value=ws_channels, inline=False)
        except:
            pass

        if "VANITY_URL" in guild.features:
            try:
                vanity = await cached_guild.vanity_invite()
                vanity_str = f"https://discord.gg/{vanity.code} (uses: {vanity.uses})"
            except:
                vanity_str = "Available, but could not fetch"
            embed.add_field(name="Vanity URL", value=vanity_str, inline=False)

        if guild.banner:
            embed.set_image(url=guild.banner.url)
        elif guild.splash:
            embed.set_image(url=guild.splash.url)

        if bot_member:
            bot_roles = [r for r in bot_member.roles if r != cached_guild.default_role]
            if bot_roles:
                roles_info = []
                for r in bot_roles:
                    roles_info.append(f"**{r.name}** ({r.id}): {perms_to_str(r.permissions)}")
                roles_str = "\n".join(roles_info)
            else:
                roles_str = "No roles"
            embed.add_field(name="Bot Roles and Permissions", value=roles_str, inline=False)
        else:
            embed.add_field(name="Bot Roles and Permissions", value="Bot member not found", inline=False)

        permissions_list = [
            ("Administrator", bot_permissions.administrator),
            ("Manage Server", bot_permissions.manage_guild),
            ("Manage Roles", bot_permissions.manage_roles),
            ("Manage Channels", bot_permissions.manage_channels),
            ("Kick Members", bot_permissions.kick_members),
            ("Ban Members", bot_permissions.ban_members),
            ("View Audit Log", bot_permissions.view_audit_log),
            ("Send Messages", bot_permissions.send_messages),
            ("Manage Messages", bot_permissions.manage_messages),
            ("Embed Links", bot_permissions.embed_links),
            ("Attach Files", bot_permissions.attach_files),
            ("Use Slash Commands", bot_permissions.use_application_commands),
        ]
        perm_text = "\n".join(f"{'✅' if value else '❌'} {name}" for name, value in permissions_list)
        embed.add_field(name="Bot Permissions (Guild-wide)", value=perm_text, inline=False)

        channel_list = []
        for ch in cached_guild.channels:
            if isinstance(ch, discord.TextChannel):
                display_name = f"#{ch.name}"
                can_send = ch.permissions_for(bot_member).send_messages
            elif isinstance(ch, discord.VoiceChannel):
                display_name = f"🔊 {ch.name}"
                can_send = ch.permissions_for(bot_member).connect
            elif isinstance(ch, discord.CategoryChannel):
                display_name = f"📁 {ch.name}"
                can_send = None
            else:
                display_name = ch.name
                can_send = None

            if can_send is True:
                perm_marker = "✅"
            elif can_send is False:
                perm_marker = "❌"
            else:
                perm_marker = "—"

            channel_list.append(f"{perm_marker} {ch.id} — {display_name}")

        channels_text = "\n".join(channel_list)

        max_len = 1024
        if len(channels_text) > max_len:
            chunks = []
            current = ""
            for line in channel_list:
                if len(current) + len(line) + 1 > max_len:
                    chunks.append(current)
                    current = ""
                current += line + "\n"
            if current:
                chunks.append(current)

            await ctx.send(embed=embed)

            for i, chunk in enumerate(chunks, 1):
                e = discord.Embed(
                    title=f"Channels List (Part {i}/{len(chunks)}) — (✅ bot can send/connect)",
                    description=chunk,
                    color=discord.Color.blurple()
                )
                await ctx.send(embed=e)
        else:
            embed.add_field(name="Channels (ID — Name with Send Permission)", value=channels_text, inline=False)
            await ctx.send(embed=embed)

        if banned_found is not None:
            if banned_found:
                names = ", ".join(f"{u} ({u.id})" for u in banned_found)
                await ctx.send(f"⚠️ Found {len(banned_found)} banned user(s) from the monitored list:\n{names}")
            else:
                await ctx.send("✅ No banned users from the monitored list found in this server.")
        else:
            await ctx.send("⚠️ Unable to fetch banned users. Missing permissions?")

async def setup(bot):
    await bot.add_cog(Developer(bot))
    await bot.add_cog(ServerFetch(bot))
