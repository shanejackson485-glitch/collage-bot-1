import discord
from discord.ext import commands
import os

from .helpers import load_data, save_data

GRAILS_FILE = os.path.join("data", "JuiceWRLD", "grails.json")
GIFS_FILE = os.path.join("data", "JuiceWRLD", "gifs.json")

class Grail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.user_grails = load_data(GRAILS_FILE)
        self.user_gifs = load_data(GIFS_FILE)

    @commands.group(invoke_without_command=True)
    async def grail(self, ctx, *, user: discord.Member = None):
        """View your grail list or the grail list of another user."""
        target_user = user or ctx.author
        user_id = str(target_user.id)

        if user_id not in self.user_grails or not self.user_grails[user_id]:
            message = "Your grail list is empty. Use `-grail add <item>` to add something."
            if user:
                message = f"{target_user.display_name}'s grail list is empty."
            return await ctx.send(message)


        embed = discord.Embed(
            title=f"{target_user.display_name}'s Grail List",
            description="\n".join(f"- {item}" for item in self.user_grails[user_id]),
            color=target_user.color
        )
        embed.set_author(name=target_user.name, icon_url=target_user.display_avatar.url)


        if user_id in self.user_gifs:
            embed.set_thumbnail(url=self.user_gifs[user_id])

        await ctx.send(embed=embed)

    @grail.command(name="add")
    async def grail_add(self, ctx, *, grail_item: str):
        """Add an item to your grail list."""
        user_id = str(ctx.author.id)
        
        if user_id not in self.user_grails:
            self.user_grails[user_id] = []
        
        self.user_grails[user_id].append(grail_item)

        save_data(self.user_grails, GRAILS_FILE)
        await ctx.send(f"✅ Added `{grail_item}` to your grail list!")

    @grail.command(name="update")
    async def grail_update(self, ctx, *, new_grails: str):
        """Replace your entire grail list with a new, comma-separated list."""
        user_id = str(ctx.author.id)
        self.user_grails[user_id] = [item.strip() for item in new_grails.split(",")]
        save_data(self.user_grails, GRAILS_FILE)
        await ctx.send("✅ Your grail list has been updated!")

    @grail.command(name="clear")
    async def grail_clear(self, ctx):
        """Clear your entire grail list."""
        user_id = str(ctx.author.id)
        if user_id in self.user_grails:
            self.user_grails[user_id] = []
            save_data(self.user_grails, GRAILS_FILE)
        await ctx.send("✅ Your grail list has been cleared!")

    @grail.command(name="gifadd")
    async def grail_gif_add(self, ctx, gif_url: str = None):
        """Adds or updates your grail GIF. Provide a URL or upload a file."""
        user_id = str(ctx.author.id)


        if ctx.message.attachments:
            gif_url = ctx.message.attachments[0].url
        
        if not gif_url:
            return await ctx.send("❌ Please provide a direct GIF URL or upload a GIF with the command.")


        if gif_url.lower().endswith(('.gif', '.gifv', '.mp4')):
            self.user_gifs[user_id] = gif_url
            save_data(self.user_gifs, GIFS_FILE)
            await ctx.send("✅ Your grail GIF has been set!")
        else:
            await ctx.send("❌ That doesn't look like a valid GIF or MP4 URL. Please provide a direct link.")

    @grail.command(name="gifremove")
    async def grail_gif_remove(self, ctx):
        """Removes your grail GIF."""
        user_id = str(ctx.author.id)
        if user_id in self.user_gifs:
            del self.user_gifs[user_id]
            save_data(self.user_gifs, GIFS_FILE)
            await ctx.send("✅ Your grail GIF has been removed!")
        else:
            await ctx.send("You don't have a grail GIF to remove.")

async def setup(bot):
    await bot.add_cog(Grail(bot))