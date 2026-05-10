import discord
from discord.ext import commands, tasks
import json
from datetime import datetime
import time
import itertools
import asyncio
from config import BOOSTER_ROLE_ID



BLACKLIST_PATH = "data/Developer/blacklist.json"
SERVERS_PATH = "data/Developer/servers.json"
COMMANDS_PATH = "data/Developer/commands.json"
PREMIUM_PATH = "data/Developer/premium_whitelist.json"

DISABLED_CMDS_PATH = "data/Developer/disabled_commands.json"


class CommandDisabled(commands.CheckFailure):
    pass

class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.sent_dm_warnings = set()
        


        self.blacklist_cache = self.load_json(BLACKLIST_PATH, {"guilds": {}, "users": {}})
        self.premium_cache = self.load_json(PREMIUM_PATH, {"whitelisted_ids": []})

        self.disabled_cache = self.load_json(DISABLED_CMDS_PATH, {})
        

        cmd_data = self.load_json(COMMANDS_PATH, {"command_count": 0})
        self.command_count = cmd_data.get("command_count", 0)


        self.status_index = 0
        self.status_cycle = itertools.cycle([])
        self.rotate_status.start()
        self.auto_save_data.start()


        self.bot.add_check(self.disabled_commands_check)

    def cog_unload(self):
        self.rotate_status.cancel()
        self.auto_save_data.cancel()

        self.bot.remove_check(self.disabled_commands_check)

        self.save_json_sync(COMMANDS_PATH, {"command_count": self.command_count})
        self.save_json_sync(DISABLED_CMDS_PATH, self.disabled_cache)



    async def disabled_commands_check(self, ctx):
        """Logic to prevent commands from running in specific channels."""
        if not ctx.guild:
            return True
        
        chan_id = str(ctx.channel.id)
        if chan_id in self.disabled_cache:
            if ctx.command.name in self.disabled_cache[chan_id]:
                raise CommandDisabled()
        return True



    def load_json(self, path, default):
        """Loads JSON synchronously (only used on startup)."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def save_json_sync(self, path, data):
        """Saves JSON synchronously (used on unload)."""
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    async def save_json_async(self, path, data):
        """Saves JSON in a separate thread to prevent bot lag."""
        def write():
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        await self.bot.loop.run_in_executor(None, write)



    @tasks.loop(minutes=5)
    async def auto_save_data(self):
        """Periodically saves the command count to disk."""
        await self.save_json_async(COMMANDS_PATH, {"command_count": self.command_count})
        await self.save_json_async(DISABLED_CMDS_PATH, self.disabled_cache)

    @tasks.loop(seconds=30)
    async def rotate_status(self):
        """Rotates the bot’s status every 30 seconds."""
        try:

            if self.status_index % 10 == 0 or self.status_cycle is None:
                await self.set_status_cycle()


            next_activity = next(self.status_cycle)


            await self.bot.change_presence(
                status=discord.Status.online,
                activity = next_activity
            )

            self.status_index += 1

        except Exception as e:
            print(f"[Status Rotation Error] {e}")

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.bot.wait_until_ready()





    async def set_status_cycle(self):
        """Refreshes and rebuilds the activity rotation cycle."""
        total_users = sum(g.member_count for g in self.bot.guilds)

        self.status_cycle = itertools.cycle([
            discord.Streaming(name="collagebot.info", url="https://twitch.tv/collage"),

            
            discord.Streaming(name="@collage help", url="https://twitch.tv/collage"),
        ])



    @commands.Cog.listener()
    async def on_ready(self):
        print("-" * 30)
        print(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        print(f"Bot is ready in {len(self.bot.guilds)} servers.")
        print("-" * 30)


        servers = {}
        for guild in self.bot.guilds:
            servers[str(guild.id)] = {
                "name": guild.name,
                "owner_id": guild.owner_id,
                "member_count": guild.member_count,
            }
        await self.save_json_async(SERVERS_PATH, servers)

        await self.set_status_cycle()
        



        try:
            synced = await self.bot.tree.sync()
            print(f"🌍 Globally synced {len(synced)} commands.")
        except Exception as e:
            print(f"Sync failed: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return



        if str(message.author.id) in self.blacklist_cache.get("users", {}):

            if message.content.startswith(tuple(await self.bot.get_prefix(message))):
                reason = self.blacklist_cache["users"][str(message.author.id)]["message"]
                embed = discord.Embed(
                    title="⛔ Blacklisted",
                    description=f"You are blacklisted from using the bot.\n**Reason:** {reason}",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Contact support if you believe this is a mistake.")
                await message.channel.send(embed=embed)
                return 


        if message.guild is None and message.author.id not in self.sent_dm_warnings:
            embed = discord.Embed(
                title="**Hey There!**",
                description="I work best in servers. DM commands might be unstable.",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)
            self.sent_dm_warnings.add(message.author.id)


        filter_cog = self.bot.get_cog("Filter")
        if filter_cog and await filter_cog.check_message_for_filter(message):
            return

        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"✅ Joined new server: {guild.name} ({guild.id})")
        

        if str(guild.id) in self.blacklist_cache.get("guilds", {}):
            print(f"🚫 Server {guild.name} is blacklisted. Leaving.")
            await guild.leave()
            return


        servers = self.load_json(SERVERS_PATH, {})
        servers[str(guild.id)] = {
            "name": guild.name,
            "owner_id": guild.owner_id,
            "member_count": guild.member_count,
        }
        await self.save_json_async(SERVERS_PATH, servers)


        admin_id = self.bot.config.get('admin_user_id')
        if admin_id:
            admin = await self.bot.fetch_user(admin_id)
            if admin:
                await admin.send(f"✅ **Joined a new server:** {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):

        self.command_count += 1
        

        guild_name = ctx.guild.name if ctx.guild else "DM"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {ctx.author} executed '{ctx.command.name}' in {guild_name}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Global Error Handler.
        Silences errors for users trying to run Dev/Admin commands.
        """
        

        if isinstance(error, commands.CommandNotFound):
            return


        if isinstance(error, CommandDisabled):
            embed = discord.Embed(
                title="🚫 Command Disabled",
                description=f"The command `{ctx.command.name}` is disabled in this channel.",
                color=discord.Color.red()
            )
            return await ctx.send(content=f"{ctx.author.mention}", embed=embed)



        if isinstance(error, (commands.NotOwner, commands.CheckFailure)):

            if ctx.command and ctx.command.hidden:
                return
            

            if isinstance(error, commands.MissingPermissions):
                pass
            else:
                return

        embed = discord.Embed(title="Command Error", color=discord.Color.red())


        if isinstance(error, commands.MissingPermissions):
            missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
            embed.description = f"❌ You do not have the required permissions: **{', '.join(missing)}**"
        
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"❌ Missing argument: `{error.param.name}`\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"

        elif isinstance(error, commands.BadArgument):
            embed.description = "❌ Invalid argument provided."

        elif isinstance(error, commands.CommandOnCooldown):
            embed.title = "⏳ Cooldown"
            embed.description = f"Try again in **{error.retry_after:.2f}s**"

        else:

            embed.description = "⚠️ An unexpected error occurred."
            print(f"Error in {ctx.command}: {error}")

            try:
                with open("logs/collage.log", "a") as f:
                    f.write(f"[{datetime.now()}] {ctx.command}: {error}\n")
            except:
                pass

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Efficiently handles Booster Role updates."""

        whitelisted_ids = set(self.premium_cache.get("whitelisted_ids", []))
        

        had_role = before.get_role(BOOSTER_ROLE_ID) is not None
        has_role = after.get_role(BOOSTER_ROLE_ID) is not None

        changed = False

        if not had_role and has_role:
            whitelisted_ids.add(str(after.id))
            print(f"✅ Added {after} to premium (booster).")
            changed = True
        elif had_role and not has_role:
            if str(after.id) in whitelisted_ids:
                whitelisted_ids.remove(str(after.id))
                print(f"🚫 Removed {after} from premium (lost boost).")
                changed = True

        if changed:
            self.premium_cache["whitelisted_ids"] = list(whitelisted_ids)
            await self.save_json_async(PREMIUM_PATH, self.premium_cache)

    @commands.command()
    @commands.is_owner()
    async def debug_listeners(self, ctx):
        listeners = self.bot.extra_events.get('on_message', [])
        await ctx.send(f"Found {len(listeners)} `on_message` listener(s).")

    @commands.command()
    async def syncboosters(self, ctx):
        admin_id = self.bot.config.get("admin_user_id")
        if ctx.author.id != admin_id:

            return 

        role = ctx.guild.get_role(BOOSTER_ROLE_ID)
        if not role:
            return await ctx.send("❌ Booster role not found.")

        members_with_role = [str(m.id) for m in ctx.guild.members if role in m.roles]
        
        if not members_with_role:
            return await ctx.send("⚠️ No boosters found.")

        self.premium_cache["whitelisted_ids"] = members_with_role
        await self.save_json_async(PREMIUM_PATH, self.premium_cache)

        await ctx.send(f"✅ Synced {len(members_with_role)} boosters.")

    @commands.command(name="channelcommand", aliases=["ccmd"])
    @commands.has_permissions(manage_guild=True)
    async def toggle_channel_command(self, ctx, command_name: str, channel: discord.TextChannel = None):
        """Disables or Enables a command in a specific channel."""
        channel = channel or ctx.channel
        chan_id = str(channel.id)

        cmd = self.bot.get_command(command_name)
        if not cmd:
            return await ctx.send(f"❌ Command `{command_name}` not found.")

        if cmd.name == "channelcommand":
            return await ctx.send("❌ You cannot disable this command.")

        if chan_id not in self.disabled_cache:
            self.disabled_cache[chan_id] = []

        if cmd.name in self.disabled_cache[chan_id]:
            self.disabled_cache[chan_id].remove(cmd.name)
            action = "Enabled"
            color = discord.Color.green()
        else:
            self.disabled_cache[chan_id].append(cmd.name)
            action = "Disabled"
            color = discord.Color.red()

        await self.save_json_async(DISABLED_CMDS_PATH, self.disabled_cache)
        
        embed = discord.Embed(
            description=f"✅ **{action}** `{cmd.name}` in {channel.mention}.",
            color=color
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Listeners(bot))