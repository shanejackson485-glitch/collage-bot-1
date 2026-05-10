import discord
from discord.ext import commands
import json
import os
import asyncio


DIR_PATH = 'data/BoosterRoles'
CONFIG_FILE = f'{DIR_PATH}/br_config.json'
USER_ROLES_FILE = f'{DIR_PATH}/br_user_roles.json'

class BoosterRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._ensure_files_exist()

        self.config = self.load_json_sync(CONFIG_FILE)
        self.user_roles = self.load_json_sync(USER_ROLES_FILE)

    def _ensure_files_exist(self):
        """Creates the folder and empty JSON files if they don't exist."""
        if not os.path.exists(DIR_PATH):
            os.makedirs(DIR_PATH)
        
        for file in [CONFIG_FILE, USER_ROLES_FILE]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    json.dump({}, f)

    def load_json_sync(self, file):
        """Loads JSON synchronously (only used on startup)."""
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def save_json_async(self, file, data):
        """Saves JSON in a background thread to stop the bot from freezing."""
        def write_file():
            with open(file, 'w') as f:
                json.dump(data, f, indent=4)
        await self.bot.loop.run_in_executor(None, write_file)


    def get_booster_role_id(self, guild_id):
        return self.config.get(str(guild_id))

    def get_user_booster_role(self, guild_id, user_id):
        return self.user_roles.get(str(guild_id), {}).get(str(user_id))

    async def set_user_booster_role(self, guild_id, user_id, role_id):
        gid = str(guild_id)
        uid = str(user_id)
        if gid not in self.user_roles:
            self.user_roles[gid] = {}
        self.user_roles[gid][uid] = role_id

        await self.save_json_async(USER_ROLES_FILE, self.user_roles)

    async def remove_user_booster_role_data(self, guild_id, user_id):
        gid = str(guild_id)
        uid = str(user_id)
        if gid in self.user_roles and uid in self.user_roles[gid]:
            del self.user_roles[gid][uid]

            await self.save_json_async(USER_ROLES_FILE, self.user_roles)

    async def save_config(self):
        await self.save_json_async(CONFIG_FILE, self.config)


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Removes custom role if the user stops boosting."""
        guild_id_str = str(before.guild.id)
        booster_role_id = self.get_booster_role_id(guild_id_str)
        
        if not booster_role_id:
            return


        had_booster = any(role.id == booster_role_id for role in before.roles)
        has_booster = any(role.id == booster_role_id for role in after.roles)


        if had_booster and not has_booster:
            user_role_id = self.get_user_booster_role(after.guild.id, after.id)
            
            if user_role_id:
                role = after.guild.get_role(user_role_id)
                if role:
                    try:
                        await role.delete(reason="User stopped boosting.")
                        await after.send(f"💔 You stopped boosting **{after.guild.name}**, so your custom booster role was removed.")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        print(f"Could not delete role for {after.name}: {e}")
                

                await self.remove_user_booster_role_data(guild_id_str, after.id)


    @commands.group(invoke_without_command=True)
    async def br(self, ctx):
        await ctx.send("Use a valid subcommand: `create`, `name`, `color`, `icon`, `config role`.")

    @br.command()
    @commands.has_permissions(manage_roles=True)
    async def config(self, ctx, subcommand: str, role: discord.Role):
        if subcommand.lower() == 'role':
            self.config[str(ctx.guild.id)] = role.id
            await self.save_config()
            await ctx.send(f"✅ Booster role configured as {role.mention}")
        else:
            await ctx.send("Unknown subcommand. Usage: `br config role @RoleName`")

    @br.command()
    async def create(self, ctx):

        booster_role_id = self.get_booster_role_id(ctx.guild.id)
        if booster_role_id is None:
            return await ctx.send("❌ Booster role not configured in this server.")


        if booster_role_id not in [role.id for role in ctx.author.roles]:
            return await ctx.send("❌ You do not have the server booster role.")


        existing_role_id = self.get_user_booster_role(ctx.guild.id, ctx.author.id)
        if existing_role_id and ctx.guild.get_role(existing_role_id):
            return await ctx.send("❌ You already have a booster role.")


        role_name = f"{ctx.author.name}'s booster role"
        try:
            new_role = await ctx.guild.create_role(name=role_name, color=discord.Color.random(), reason="Booster role creation")
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to create roles.")


        await ctx.author.add_roles(new_role)
        await self.set_user_booster_role(ctx.guild.id, ctx.author.id, new_role.id)


        main_booster_role = ctx.guild.get_role(booster_role_id)
        if main_booster_role:
            try:
                if ctx.guild.me.top_role.position > main_booster_role.position:
                    await new_role.edit(position=main_booster_role.position)
            except Exception:
                pass

        await ctx.send(f"✅ Created and assigned booster role: {new_role.mention}")

    @br.command()
    async def name(self, ctx, *, new_name: str):
        role_id = self.get_user_booster_role(ctx.guild.id, ctx.author.id)
        if not role_id: return await ctx.send("❌ You don't have a booster role yet.")

        role = ctx.guild.get_role(role_id)
        if role:
            await role.edit(name=new_name)
            await ctx.send(f"✅ Role name updated to **{new_name}**")
        else:
            await ctx.send("❌ Role not found.")

    @br.command()
    async def color(self, ctx, hex_color: str):
        role_id = self.get_user_booster_role(ctx.guild.id, ctx.author.id)
        if not role_id: return await ctx.send("❌ You don't have a booster role yet.")

        role = ctx.guild.get_role(role_id)
        if role:
            try:

                hex_val = hex_color.lstrip('#').replace('0x', '')
                color = discord.Color(int(hex_val, 16))
                await role.edit(color=color)
                await ctx.send(f"✅ Role color updated.")
            except ValueError:
                await ctx.send("❌ Invalid hex code.")
        else:
            await ctx.send("❌ Role not found.")

    @br.command()
    async def icon(self, ctx):
        if ctx.guild.premium_tier < 2:
            return await ctx.send("❌ Server must be Level 2+ for role icons.")

        role_id = self.get_user_booster_role(ctx.guild.id, ctx.author.id)
        if not role_id: return await ctx.send("❌ You don't have a booster role yet.")

        role = ctx.guild.get_role(role_id)
        if not role: return await ctx.send("❌ Role not found.")

        if not ctx.message.attachments:
            return await ctx.send("❌ Please attach an image.")

        attachment = ctx.message.attachments[0]
        if not attachment.content_type.startswith("image"):
            return await ctx.send("❌ Attachment must be an image.")

        try:
            img_bytes = await attachment.read()
            await role.edit(display_icon=img_bytes)
            await ctx.send("✅ Role icon updated.")
        except Exception as e:
            await ctx.send(f"❌ Failed to update icon: {e}")

async def setup(bot):
    await bot.add_cog(BoosterRole(bot))