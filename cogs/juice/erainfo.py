import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class EraInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.era_file = os.path.join(os.getcwd(), "data", "JuiceWRLD", "erainfo.json")

    @commands.hybrid_command(
        name="erainfo",
        with_app_command=True,
        description="Displays information about a specified Juice WRLD era, including aliases and details."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def erainfo(self, ctx: commands.Context, *, era_name: str):
        """Displays information about a specified era, including aliases and custom embed color."""
        
        if ctx.interaction:
            await ctx.defer()

        if not os.path.exists(self.era_file):
            await ctx.send("❌ Era data file not found! Please check `data/JuiceWRLD/erainfo.json`.")
            return
        
        try:
            with open(self.era_file, "r", encoding="utf-8") as f:
                eras = json.load(f)
        except Exception as e:
            await ctx.send(f"❌ Error loading era file: {e}")
            return

        era_key = None
        era_name_lower = era_name.lower()


        for key, data in eras.items():
            if key.lower() == era_name_lower:
                era_key = key
                break
            aliases = data.get("aliases", [])
            if any(alias.lower() == era_name_lower for alias in aliases):
                era_key = key
                break
        
        if not era_key:
            await ctx.send(f"❌ Era **{era_name}** not found. Please check your spelling.")
            return

        era_data = eras[era_key]


        color_value = era_data.get("color", "#9b59b6")
        try:
            if isinstance(color_value, str):
                color_value = color_value.replace("#", "")
                color = discord.Color(int(color_value, 16))
            else:
                color = discord.Color(int(color_value))
        except:
            color = discord.Color.purple()


        embed = discord.Embed(
            title=f"{era_key} Era Information",
            color=color
        )

        if image_url := era_data.get("image_url"):
            embed.set_thumbnail(url=image_url)

        embed.add_field(name="Total Leaked Sessions", value=era_data.get("total_leaked_sessions", 0), inline=True)
        embed.add_field(name="Total Leaked Songs", value=era_data.get("total_leaked_songs", 0), inline=True)
        embed.add_field(name="Unsurfaced Songs", value=era_data.get("unsurfaced_songs", 0), inline=True)
        
        start_date = era_data.get("era_start", "Unknown")
        end_date = era_data.get("era_end", "Unknown")
        
        embed.add_field(name="Era Timeline", value=f"**Start:** {start_date}\n**End:** {end_date}", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EraInfo(bot))