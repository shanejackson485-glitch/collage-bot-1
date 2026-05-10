import discord
from discord.ext import commands
import json
import os
import asyncio
import re
import datetime
from datetime import timedelta
from collections import defaultdict
from typing import Union, Optional, List
import sys



def parse_time(time_str: str) -> int:
    """Converts a string like '1h 30m' into seconds."""
    if not time_str: return 0
    regex = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
    parts = regex.match(time_str)
    if not parts: return 0
    time_params = {name: int(param) for name, param in parts.groupdict().items() if param}
    return int(timedelta(**time_params).total_seconds())

def format_timespan(seconds: int) -> str:
    return str(timedelta(seconds=seconds))



class ModerationData:
    def __init__(self, file_path="data/Moderation/moderation.json"):
        self.file_path = file_path
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            self.data = {}
            self.save()
        else:
            try:
                with open(self.file_path, "r") as f:
                    self.data = json.load(f)
            except:
                self.data = {}

    def save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_guild(self, guild_id):
        gid = str(guild_id)
        if gid not in self.data:
            self.data[gid] = {
                "jail_config": None,
                "jailed": {},
                "hardbans": [],
                "forcenicks": {},
                "restore": {}
            }
            self.save()
        return self.data[gid]



class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = ModerationData()
        self.locks = defaultdict(asyncio.Lock)
        if not os.path.exists("data/Moderation"):
            os.makedirs("data/Moderation")


    
    async def send_success(self, ctx, title: str, description: str = None):
        embed = discord.Embed(title=f"✅ {title}", description=description, color=discord.Color.brand_green())
        await ctx.send(embed=embed)

    async def send_error(self, ctx, title: str, description: str = None):
        embed = discord.Embed(title=f"❌ {title}", description=description, color=discord.Color.brand_red())
        await ctx.send(embed=embed, delete_after=10)

    async def send_mod_log(self, ctx, action: str, target: Union[discord.Member, discord.User], reason: str, extra_info: str = None):
        """Creates a professional looking moderation log embed."""
        embed = discord.Embed(title=f"🛡️ Action: {action}", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Target", value=f"{target.mention} (`{target.id}`)", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        if extra_info:
            embed.add_field(name="Details", value=extra_info, inline=False)
        embed.set_footer(text=f"Server: {ctx.guild.name}")
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        g_data = self.db.get_guild(member.guild.id)
        

        if member.id in g_data.get("hardbans", []):
            try:
                await member.guild.ban(member, reason="[Auto] User is hardbanned")
                return
            except:
                pass


        if str(member.id) in g_data.get("jailed", {}):
            config = g_data.get("jail_config")
            if config:
                jail_role = member.guild.get_role(config["role_id"])
                if jail_role:
                    await member.add_roles(jail_role, reason="[Auto] Jail Evasion Prevention")


        saved_roles = g_data.get("restore", {}).get(str(member.id))
        if saved_roles:
            roles_to_add = []
            for r_id in saved_roles:
                role = member.guild.get_role(r_id)
                if role and role.is_assignable() and role != member.guild.default_role:
                    roles_to_add.append(role)
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Role Restore")
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        g_data = self.db.get_guild(member.guild.id)
        role_ids = [r.id for r in member.roles if r != member.guild.default_role]
        g_data["restore"][str(member.id)] = role_ids
        self.db.save()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick: return
        g_data = self.db.get_guild(before.guild.id)
        forced = g_data.get("forcenicks", {}).get(str(before.id))
        
        if forced and after.nick != forced:
            if after.guild.me.guild_permissions.manage_nicknames:
                try:
                    await after.edit(nick=forced, reason="Force Nickname Enforcement")
                except:
                    pass




    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        """Restarts the bot (Owner only)."""
        await self.send_success(ctx, "System", "Restarting bot process...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await self.send_error(ctx, "Permission Denied", "You cannot kick someone with an equal or higher role.")
        
        await ctx.guild.kick(user, reason=f"{ctx.author}: {reason}")
        await self.send_mod_log(ctx, "Kick", user, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        if isinstance(user, discord.Member):
            if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                return await self.send_error(ctx, "Permission Denied", "You cannot ban someone with an equal or higher role.")
        
        await ctx.guild.ban(user, reason=f"{ctx.author}: {reason}")
        await self.send_mod_log(ctx, "Ban", user, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User):
        try:
            await ctx.guild.unban(user)
            await self.send_success(ctx, f"Unbanned {user.name}")
        except:
            await self.send_error(ctx, "Action Failed", "User is not banned or not found.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, time: str = "1h", *, reason: str = "No reason"):
        if member.top_role >= ctx.author.top_role:
             return await self.send_error(ctx, "Permission Denied", "Role hierarchy prevents muting this user.")
        
        seconds = parse_time(time)
        if seconds == 0: seconds = 3600
        
        try:
            expiry = discord.utils.utcnow() + timedelta(seconds=seconds)
            await member.timeout(expiry, reason=f"Muted by {ctx.author}: {reason}")
            

            timestamp_str = f"<t:{int(expiry.timestamp())}:R>"
            await self.send_mod_log(ctx, "Timeout / Mute", member, reason, extra_info=f"Duration: {format_timespan(seconds)}\nExpires: {timestamp_str}")
        except Exception as e:
            await self.send_error(ctx, "Action Failed", str(e))

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        try:
            await member.timeout(None, reason=f"Unmuted by {ctx.author}")
            await self.send_success(ctx, f"Unmuted {member.mention}")
        except:
            await self.send_error(ctx, "Action Failed", "Could not remove timeout.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is False:
            return await self.send_error(ctx, "Already Locked", "This channel is already locked.")
        
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await self.send_success(ctx, "Channel Locked", f"{ctx.channel.mention} is now locked for the default role.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is None:
            return await self.send_error(ctx, "Already Unlocked", "This channel is not locked.")
        
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await self.send_success(ctx, "Channel Unlocked", f"{ctx.channel.mention} is now open.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await self.send_success(ctx, "Slowmode Disabled")
        else:
            await self.send_success(ctx, "Slowmode Updated", f"Delay set to {seconds} seconds.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Clones and deletes the current channel."""
        embed = discord.Embed(title="⚠️ Nuke Request", description="Are you sure you want to **delete** this channel and clone it?\nReply `yes` to confirm.", color=discord.Color.red())
        await ctx.send(embed=embed)
        
        try:
            check = lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"
            await self.bot.wait_for("message", check=check, timeout=15)
        except asyncio.TimeoutError:
            return await self.send_error(ctx, "Cancelled", "Nuke request timed out.")

        try:

            pos = ctx.channel.position
            new_channel = await ctx.channel.clone(reason="Channel Nuked")
            await new_channel.edit(position=pos)
            await ctx.channel.delete()
            
            nuke_embed = discord.Embed(title="💥 Channel Nuked", description=f"Performed by {ctx.author.mention}", color=discord.Color.dark_orange())
            nuke_embed.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
            await new_channel.send(embed=nuke_embed)
        except Exception as e:
            await ctx.send(f"Failed to nuke: {e}")



    @commands.group(invoke_without_command=True, aliases=["r"])
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, *, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role)
            await self.send_success(ctx, "Role Removed", f"Removed {role.mention} from {member.mention}")
        else:
            await member.add_roles(role)
            await self.send_success(ctx, "Role Added", f"Added {role.mention} to {member.mention}")

    @role.command(name="create")
    async def role_create(self, ctx, *, name: str):
        r = await ctx.guild.create_role(name=name)
        await self.send_success(ctx, "Role Created", f"{r.mention}")

    @role.command(name="delete")
    async def role_delete(self, ctx, *, role: discord.Role):
        name = role.name
        await role.delete()
        await self.send_success(ctx, "Role Deleted", f"Deleted role `{name}`")

    @role.command(name="humans")
    async def role_humans(self, ctx, *, role: discord.Role):
        """Give a role to all humans."""
        humans = [m for m in ctx.guild.members if not m.bot and role not in m.roles]
        if not humans: return await self.send_error(ctx, "No Targets", "No humans need this role.")
        
        await self.send_success(ctx, "Processing", f"Assigning {role.mention} to {len(humans)} humans. This may take a while...")
        
        count = 0
        for m in humans:
            try:
                await m.add_roles(role)
                count += 1
                await asyncio.sleep(0.5)
            except:
                pass
        await self.send_success(ctx, "Complete", f"Finished. Assigned to {count} members.")



    @commands.group(invoke_without_command=True, aliases=["clear", "c"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=amount)
        await self.send_success(ctx, "Purge Complete", f"🗑️ Deleted {len(deleted)} messages.")

    @purge.command(name="user")
    async def purge_user(self, ctx, member: discord.Member, amount: int = 20):
        await ctx.message.delete()
        def check(m): return m.author == member
        deleted = await ctx.channel.purge(limit=amount, check=check)
        await self.send_success(ctx, "User Purge Complete", f"🗑️ Deleted {len(deleted)} messages from {member.mention}.")

    @purge.command(name="bots")
    async def purge_bots(self, ctx, amount: int = 20):
        await ctx.message.delete()
        def check(m): return m.author.bot
        deleted = await ctx.channel.purge(limit=amount, check=check)
        await self.send_success(ctx, "Bot Purge Complete", f"🗑️ Deleted {len(deleted)} bot messages.")

    @purge.command(name="contains")
    async def purge_contains(self, ctx, string: str, amount: int = 20):
        await ctx.message.delete()
        def check(m): return string.lower() in m.content.lower()
        deleted = await ctx.channel.purge(limit=amount, check=check)
        await self.send_success(ctx, "Keyword Purge Complete", f"🗑️ Deleted {len(deleted)} messages containing '{string}'.")



    @commands.command(name="setup")
    @commands.has_permissions(manage_messages=True)
    async def mod_setup(self, ctx, role: discord.Role = None, channel: discord.TextChannel = None):
        """
        Sets up jail system.
        Usage:
        1. !setup (Creates new role + jail channel automatically)
        2. !setup @JailedRole #jail (Uses existing; DOES NOT change permissions)
        """
        g_data = self.db.get_guild(ctx.guild.id)
        bot_member = ctx.guild.me




        if role and channel:


            if not channel.permissions_for(bot_member).view_channel:
                return await self.send_error(
                    ctx, "Channel Error",
                    f"I cannot access {channel.mention}. Make sure I can view it."
                )


            if role >= bot_member.top_role:
                return await self.send_error(
                    ctx, "Hierarchy Error",
                    f"I cannot use {role.mention} because it is **higher than my top role**."
                )


            g_data["jail_config"] = {"role_id": role.id, "channel_id": channel.id}
            self.db.save()

            return await self.send_success(
                ctx, "Setup Updated",
                f"Jail system configured using:\n"
                f"• Role: {role.mention}\n"
                f"• Channel: {channel.mention}\n\n"
                "**No permissions were changed.**"
            )




        if g_data.get("jail_config"):
            return await self.send_error(
                ctx, "Already Setup",
                "Moderation is already set up.\nRun `!setup @role #channel` to overwrite."
            )




        await ctx.send("⚙️ Setting up Jail system automatically...")


        missing = []
        if not bot_member.guild_permissions.manage_roles:
            missing.append("Manage Roles")
        if not bot_member.guild_permissions.manage_channels:
            missing.append("Manage Channels")

        if missing:
            return await self.send_error(
                ctx, "Missing Permissions",
                f"I need the following permissions:\n- " + "\n- ".join(missing)
            )




        try:
            jail_role = await ctx.guild.create_role(name="Jailed", reason="Mod Setup")
        except Exception as e:
            return await self.send_error(ctx, "Setup Failed", f"Could not create role:\n```{e}```")


        for ch in ctx.guild.channels:
            perms = ch.permissions_for(bot_member)


            if not perms.manage_channels:
                continue

            try:
                await ch.set_permissions(jail_role, view_channel=False)
            except discord.Forbidden:
                continue
            except Exception:
                continue




        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        try:
            jail_channel = await ctx.guild.create_text_channel("jail", overwrites=overwrites)
        except Exception as e:
            return await self.send_error(ctx, "Setup Failed", f"Could not create channel:\n```{e}```")




        g_data["jail_config"] = {"role_id": jail_role.id, "channel_id": jail_channel.id}
        self.db.save()

        await self.send_success(
            ctx, "Setup Complete",
            f"Created jail system:\n"
            f"• {jail_role.mention}\n"
            f"• {jail_channel.mention}\n\n"
            "Automatic permissions applied."
        )

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def jail(self, ctx, member: discord.Member, *, reason="No reason"):
        g_data = self.db.get_guild(ctx.guild.id)
        config = g_data.get("jail_config")
        if not config: return await self.send_error(ctx, "Not Setup", "Run `setup` first.")
        
        jail_role = ctx.guild.get_role(config["role_id"])
        if not jail_role: return await self.send_error(ctx, "Config Error", "Jail role missing. Run setup again.")


        old_roles = [r.id for r in member.roles if r.is_assignable() and r != ctx.guild.default_role]
        g_data["jailed"][str(member.id)] = old_roles
        self.db.save()


        to_remove = [r for r in member.roles if r.is_assignable() and r != ctx.guild.default_role]
        await member.remove_roles(*to_remove)
        await member.add_roles(jail_role, reason=f"Jailed by {ctx.author}: {reason}")
        
        await self.send_mod_log(ctx, "Jailed", member, reason)
        
        jail_chan = ctx.guild.get_channel(config["channel_id"])
        if jail_chan:
            await jail_chan.send(f"🔒 {member.mention} has been jailed.\n**Reason:** {reason}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unjail(self, ctx, member: discord.Member):
        g_data = self.db.get_guild(ctx.guild.id)
        if str(member.id) not in g_data.get("jailed", {}):
            return await self.send_error(ctx, "Error", "Member is not jailed.")
        
        config = g_data.get("jail_config")
        jail_role = ctx.guild.get_role(config["role_id"]) if config else None
        

        saved_ids = g_data["jailed"][str(member.id)]
        to_add = [ctx.guild.get_role(rid) for rid in saved_ids if ctx.guild.get_role(rid)]
        
        if jail_role and jail_role in member.roles:
            await member.remove_roles(jail_role)
        
        if to_add:
            await member.add_roles(*to_add, reason="Unjailed")
        
        del g_data["jailed"][str(member.id)]
        self.db.save()
        await self.send_success(ctx, "Unjailed", f"Released {member.mention} and restored roles.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def hardban(self, ctx, user: Union[discord.Member, discord.User]):
        g_data = self.db.get_guild(ctx.guild.id)
        if user.id not in g_data["hardbans"]:
            g_data["hardbans"].append(user.id)
            self.db.save()
        
        await ctx.guild.ban(user, reason=f"Hardbanned by {ctx.author}")
        await self.send_mod_log(ctx, "Hardban", user, "Indefinite hardban triggered.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unhardban(self, ctx, user: discord.User):
        g_data = self.db.get_guild(ctx.guild.id)
        if user.id in g_data["hardbans"]:
            g_data["hardbans"].remove(user.id)
            self.db.save()
            try:
                await ctx.guild.unban(user)
            except:
                pass
            await self.send_success(ctx, "Hardban Removed", f"Allowed {user.mention} to rejoin.")
        else:
            await self.send_error(ctx, "Error", "User is not hardbanned.")

    @commands.command(aliases=["fn"])
    @commands.has_permissions(manage_nicknames=True)
    async def forcenick(self, ctx, member: discord.Member, *, nick: str = None):
        g_data = self.db.get_guild(ctx.guild.id)
        if not nick:
            if str(member.id) in g_data["forcenicks"]:
                del g_data["forcenicks"][str(member.id)]
                self.db.save()
                await member.edit(nick=None)
                await self.send_success(ctx, "Forcenick Removed", f"Restored nickname for {member.mention}")
            else:
                await self.send_error(ctx, "Error", "Member does not have a force nickname.")
        else:
            g_data["forcenicks"][str(member.id)] = nick
            self.db.save()
            await member.edit(nick=nick)
            await self.send_success(ctx, "Forcenick Applied", f"Locked {member.mention} to `{nick}`")




    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def channel(self, ctx):
        await ctx.send_help(ctx.command)

    @channel.command(name="create")
    async def ch_create(self, ctx, *, name: str):
        """
        Creates a channel.
        Usage:
        1. !channel create new-chat (Creates at top)
        2. !channel create 123456789012345678 new-chat (Creates in specific category)
        3. Reply to a message with an ID -> !channel create new-chat
        """

        name = name.replace("\n", " ").strip()
        
        category = None
        


        parts = name.split(" ", 1)
        
        if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) > 15:

            potential_category = ctx.guild.get_channel(int(parts[0]))
            if isinstance(potential_category, discord.CategoryChannel):
                category = potential_category
                name = parts[1]
        

        if ctx.message.reference and ctx.message.reference.resolved:
            ref_content = ctx.message.reference.resolved.content
            import re
            match = re.search(r'\d{17,20}', ref_content)
            if match:
                cat_id = int(match.group())
                found_category = ctx.guild.get_channel(cat_id)
                if isinstance(found_category, discord.CategoryChannel):
                    category = found_category

        if not name:
            return await self.send_error(ctx, "Error", "Please provide a channel name.")


        try:
            c = await ctx.guild.create_text_channel(name, category=category)
            
            location = f"inside **{category.name}**" if category else "at the top"
            await self.send_success(ctx, "Channel Created", f"{c.mention} created {location}.")
                
        except discord.HTTPException as e:
            if e.code == 50035:
                await self.send_error(ctx, "Invalid Name", "Discord rejected this name (special chars/newlines).")
            else:
                await self.send_error(ctx, "API Error", str(e))
        except Exception as e:
            await self.send_error(ctx, "Error", str(e))

    @channel.command(name="delete")
    async def ch_delete(self, ctx, channel: discord.TextChannel):
        name = channel.name
        await channel.delete()
        await self.send_success(ctx, "Channel Deleted", f"Deleted `#{name}`")

    @channel.command(name="hide")
    async def ch_hide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await self.send_success(ctx, "Channel Hidden", f"{channel.mention} is now hidden.")

    @channel.command(name="reveal")
    async def ch_reveal(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await self.send_success(ctx, "Channel Revealed", f"{channel.mention} is now visible.")

class WarningsCog(commands.Cog, name="Warning System"):
    """Commands for warning users."""
    def __init__(self, bot):
        self.bot = bot
        self.warnings_file = "data/Moderation/warnings.json"
        self.warnings = self.load_warnings()

    def load_warnings(self):
        if not os.path.exists(self.warnings_file): return {}
        with open(self.warnings_file, "r") as f:
            try: return json.load(f)
            except: return {}

    def save_warnings(self):
        with open(self.warnings_file, "w") as f:
            json.dump(self.warnings, f, indent=4)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        self.warnings.setdefault(guild_id, {}).setdefault(user_id, []).append({
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "moderator": str(ctx.author.id)
        })
        self.save_warnings()
        
        embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.gold())
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        user_warnings = self.warnings.get(guild_id, {}).get(user_id, [])
        
        if not user_warnings: 
            embed = discord.Embed(description=f"✅ {member.mention} has a clean record.", color=discord.Color.green())
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(title=f"📜 Warnings for {member.display_name}", color=discord.Color.orange())
        for i, w in enumerate(user_warnings, 1):
            date_str = w.get('timestamp', 'Unknown').split('T')[0]
            embed.add_field(name=f"Case #{i} ({date_str})", value=f"**Reason:** {w['reason']}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["delwarn"])
    @commands.has_permissions(manage_messages=True)
    async def removewarn(self, ctx, member: discord.Member, index: int):
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        user_warnings = self.warnings.get(guild_id, {}).get(user_id, [])
        
        if 1 <= index <= len(user_warnings):
            removed = user_warnings.pop(index - 1)
            self.save_warnings()
            embed = discord.Embed(description=f"✅ Removed warning **#{index}** from {member.mention}", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Invalid warning ID.", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, member: discord.Member):
        guild_id = str(ctx.guild.id)
        if str(member.id) in self.warnings.get(guild_id, {}):
            del self.warnings[guild_id][str(member.id)]
            self.save_warnings()
            embed = discord.Embed(description=f"✅ Cleared **all** warnings for {member.mention}", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            await ctx.send("User has no warnings.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(WarningsCog(bot))