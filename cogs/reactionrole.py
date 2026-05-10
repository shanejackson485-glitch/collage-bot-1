import discord
from discord.ext import commands
import json
import os
import shlex
import re

REACTION_ROLES_FILE = "reaction_roles.json"

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = self.load_reaction_roles()


    def load_reaction_roles(self):
        if os.path.exists(REACTION_ROLES_FILE):
            with open(REACTION_ROLES_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_reaction_roles(self):
        with open(REACTION_ROLES_FILE, "w") as f:
            json.dump(self.reaction_roles, f, indent=4)


    def parse_flags(self, text: str):
        """
        Manually parse flags from text without using shlex, to avoid quoting issues.
        Supports: --flag "value", --flag value, --flag
        """
        flags = {}




        pattern = r'--([\w-]+)\s+(?:"([^"]*)"|([^\s]+))'
        
        while True:
            match = re.search(pattern, text)
            if not match:
                break
            
            flag_name = match.group(1)
            flag_value = match.group(2) or match.group(3)
            flags[flag_name] = flag_value
            

            text = text[:match.start()] + text[match.end():]
        
        return text.strip(), flags


    @commands.hybrid_group(name="rr", description="Manage reaction roles.")
    @commands.has_permissions(manage_roles=True)
    async def rr(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @rr.command(name="create", description="Create a new reaction role message.")
    async def rr_create(
        self,
        ctx,
        emoji: str,
        role: discord.Role,
        *,
        text: str = "",
        title: str | None = None,
        color: str | None = None,
        thumbnail: str | None = None
    ):
        """
        Slash version: /rr create emoji: 🎄 role: @Role text: blah
        """

        if ctx.prefix:
            description, flags = self.parse_flags(text)


            title = flags.get("title", title)
            color = flags.get("color", color)
            thumbnail = flags.get("thumbnail", thumbnail)
        else:

            description = text

        embed_title = title or "Reaction Role"
        embed_color = discord.Color.blurple()

        if color:
            try:
                embed_color = discord.Color(int(color.lstrip("#"), 16))
            except:
                pass

        embed = discord.Embed(
            title=embed_title,
            description=description,
            color=embed_color
        )

        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        msg = await ctx.send(embed=embed)

        try:
            await msg.add_reaction(emoji)
        except Exception as e:
            await msg.delete()
            return await ctx.send(f"⚠️ Invalid emoji: {emoji}\n`{e}`")


        emoji_str = str(emoji)
        self.reaction_roles.setdefault(str(msg.id), {})
        self.reaction_roles[str(msg.id)][emoji_str] = role.id
        self.save_reaction_roles()

        await ctx.send(
            f"✅ Reaction role set for {role.mention} with {emoji_str}",
            delete_after=5
        )

    @rr.command(name="add", description="Add a reaction role to an EXISTING message.")
    async def rr_add(self, ctx, message_link_or_id: str, emoji: str, role: discord.Role):

        try:
            if "/" in message_link_or_id:
                msg_id = int(message_link_or_id.split("/")[-1])
            else:
                msg_id = int(message_link_or_id)
        except ValueError:
            return await ctx.send("❌ Invalid message ID or link.")


        msg = None
        try:
            msg = await ctx.channel.fetch_message(msg_id)
        except:

            for channel in ctx.guild.text_channels:
                try:
                    msg = await channel.fetch_message(msg_id)
                    if msg: break
                except:
                    continue
        
        if not msg:
            return await ctx.send("❌ Could not find that message. Make sure the ID is correct and I have permission to see it.")


        try:
            await msg.add_reaction(emoji)
        except Exception as e:
            return await ctx.send(f"⚠️ Invalid emoji: {emoji}\n`{e}`")


        emoji_str = str(emoji)
        self.reaction_roles.setdefault(str(msg_id), {})
        self.reaction_roles[str(msg_id)][emoji_str] = role.id
        self.save_reaction_roles()

        await ctx.send(f"✅ Added {role.mention} to {emoji_str} on message `{msg_id}`", delete_after=5)

    @rr.command(name="remove", description="Remove a reaction role from a message.")
    async def rr_remove(self, ctx, message_link_or_id: str, emoji: str):
        try:
            if "/" in message_link_or_id:
                msg_id = int(message_link_or_id.split("/")[-1])
            else:
                msg_id = int(message_link_or_id)
        except ValueError:
            return await ctx.send("❌ Invalid message ID.")

        str_id = str(msg_id)
        if str_id not in self.reaction_roles or emoji not in self.reaction_roles[str_id]:
            return await ctx.send("❌ No role configured for that emoji on that message.")


        del self.reaction_roles[str_id][emoji]
        if not self.reaction_roles[str_id]:
            del self.reaction_roles[str_id]
        self.save_reaction_roles()


        try:
            msg = None
            for channel in ctx.guild.text_channels:
                try:
                    msg = await channel.fetch_message(msg_id)
                    if msg:
                        await msg.clear_reaction(emoji)
                        break
                except: pass
        except:
            pass

        await ctx.send(f"🗑️ Removed reaction role for {emoji} on message `{msg_id}`")

    @rr.command(name="list", description="List all reaction roles on a message.")
    async def rr_list(self, ctx, message_link_or_id: str):
        try:
            if "/" in message_link_or_id:
                msg_id = int(message_link_or_id.split("/")[-1])
            else:
                msg_id = int(message_link_or_id)
        except ValueError:
            return await ctx.send("❌ Invalid message ID.")

        str_id = str(msg_id)
        if str_id not in self.reaction_roles:
            return await ctx.send("ℹ️ No reaction roles set up for this message.")

        data = self.reaction_roles[str_id]
        desc_lines = []
        for em, rid in data.items():
            r = ctx.guild.get_role(rid)
            r_mention = r.mention if r else f"`Deleted Role ({rid})`"
            desc_lines.append(f"{em} -> {r_mention}")
        
        embed = discord.Embed(title=f"Reaction Roles for {msg_id}", description="\n".join(desc_lines), color=discord.Color.gold())
        await ctx.send(embed=embed)

    @rr.command(name="bulkcreate", description="Create an RR message from a text list of emojis and roles.")
    async def rr_bulkcreate(self, ctx, title: str, *, text: str):
        """
        Creates an embed with the provided text, then scans the text for Emojis and Role Mentions.
        Supports flags anywhere in the text: --thumbnail url --color #hex
        
        Usage: 
        !rr bulkcreate "My Title" --color #FF0000 --thumbnail http://image.com
        🐣 = @Role1
        🎅 = @Role2
        """
        

        try:
            description, flags = self.parse_flags(text)
        except Exception as e:
            return await ctx.send(f"⚠️ Error parsing arguments: `{e}`")
        
        color_str = flags.get("color")
        thumbnail = flags.get("thumbnail")
        
        embed_color = discord.Color.blurple()
        if color_str:
            try:
                embed_color = discord.Color(int(color_str.lstrip("#"), 16))
            except:
                pass


        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        msg = await ctx.send(embed=embed)
        self.reaction_roles.setdefault(str(msg.id), {})


        lines = description.split('\n')
        added_count = 0
        ignored_count = 0

        for line in lines:

            role_match = re.search(r"<@&(\d+)>", line)
            if not role_match:
                continue

            role_id = int(role_match.group(1))
            role = ctx.guild.get_role(role_id)
            if not role:
                continue



            custom_emoji_match = re.search(r"(<a?:\w+:(\d+)>)", line)
            
            emoji_to_use = None
            
            if custom_emoji_match:

                emoji_to_use = custom_emoji_match.group(1)
            else:

                name_match = re.search(r":([\w~-]+):", line)
                if name_match:
                    found = discord.utils.get(ctx.guild.emojis, name=name_match.group(1))
                    if found:
                        emoji_to_use = found

                if not emoji_to_use:



                    cleaned = line.replace(role_match.group(0), "")
                    cleaned = re.sub(r"[=\-\:]", " ", cleaned).strip()
                    parts = cleaned.split()
                    if parts:
                        emoji_to_use = parts[0]

            if emoji_to_use:
                try:
                    await msg.add_reaction(emoji_to_use)

                    self.reaction_roles[str(msg.id)][str(emoji_to_use)] = role_id
                    added_count += 1
                except Exception as e:
                    print(f"[RR Bulk Error] Could not add {emoji_to_use}: {e}")

                    ignored_count += 1
            
        self.save_reaction_roles()
        
        summary = f"✅ Bulk setup complete! Added {added_count} roles."
        if ignored_count > 0:
            summary += f" ({ignored_count} emojis failed/ignored)"
            
        await ctx.send(summary, delete_after=5)



    async def handle_reaction(self, payload, add=True):
        data = self.reaction_roles.get(str(payload.message_id))
        if not data:
            return

        emoji_str = str(payload.emoji)
        role_id = data.get(emoji_str)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except:
            return

        role = guild.get_role(role_id)
        if not role or role >= guild.me.top_role:
            return

        try:
            if add:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)


        except Exception as e:
            print(f"[RR ERROR] {e}")


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id != self.bot.user.id:
            await self.handle_reaction(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id != self.bot.user.id:
            await self.handle_reaction(payload, False)


async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
