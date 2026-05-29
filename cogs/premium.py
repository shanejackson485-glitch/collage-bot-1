import os
import sys
import discord
from discord.ext import commands
import json
from datetime import datetime
from discord import Embed
from pathlib import Path
import logging
from datetime import datetime, time, timezone
from discord.ext import tasks
import random 
import discord
from discord.ext import commands, tasks
import asyncio
from difflib import get_close_matches
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from mutagen.mp4 import MP4Cover
from mutagen.flac import Picture
from PIL import Image
import io
from datetime import time
from datetime import datetime  
import time  
import difflib
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from discord.ui import Button
from discord import ui
import discord
from discord.ext import commands
import asyncio
from config import premium_role, whitelist, era_sort_order, era_mapping, GUNNA_LEAK_PATH, CARTI_LEAK_PATH
from discord.ui import Select, View
import re
from discord.ext import commands
import discord
from datetime import datetime
import asyncio
import os
import sys
from discord import Embed
import yt_dlp
import math
import subprocess
import uuid
import shutil
import functools
import string
import eyed3
import re
import string
from discord import app_commands

with open('data/JuiceWRLD/track_data.json', 'r') as file:
    track_data = json.load(file)









class LeakTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_id = 971471008185851955
        self.server_id = 963632067856437300

    @commands.Cog.listener()
    async def on_ready(self):
        """Runs once when the bot is fully connected and ready."""
        
        

        try:
            with open("premium_whitelist.json", "r", encoding="utf-8") as file:
                data = json.load(file)
                whitelisted_ids = data.get("whitelisted_ids", [])
        except FileNotFoundError:
            whitelisted_ids = []


        guild = self.bot.get_guild(self.server_id)
        if guild:

            for member in guild.members:

                if self.role_id in [role.id for role in member.roles] and str(member.id) not in whitelisted_ids:

                    whitelisted_ids.append(str(member.id))
                    

            data["whitelisted_ids"] = whitelisted_ids
            with open("premium_whitelist.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print(f"Checked all members in {guild.name}, updated whitelist.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Triggered when a member's information changes, including role changes."""
        if after.guild.id != self.server_id:
            return


        try:
            with open("premium_whitelist.json", "r", encoding="utf-8") as file:
                data = json.load(file)
                whitelisted_ids = data.get("whitelisted_ids", [])
        except FileNotFoundError:
            whitelisted_ids = []


        if self.role_id in [role.id for role in after.roles] and str(after.id) not in whitelisted_ids:

            whitelisted_ids.append(str(after.id))
            data["whitelisted_ids"] = whitelisted_ids


            with open("premium_whitelist.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print(f"Added {after.id} to the premium whitelist.")

        elif self.role_id not in [role.id for role in after.roles] and str(after.id) in whitelisted_ids:

            whitelisted_ids.remove(str(after.id))
            data["whitelisted_ids"] = whitelisted_ids


            with open("premium_whitelist.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print(f"Removed {after.id} from the premium whitelist.")

    def is_premium_user(self, user_id):
        """Check if the user is in either premium_whitelist.json or manual_whitelist.json."""
        whitelists = ["data/Developer/premium_whitelist.json", "data/Developer/manual_whitelist.json"]
        for file in whitelists:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if str(user_id) in data.get("whitelisted_ids", []):
                        return True
            except FileNotFoundError:
                continue
        return False

    @commands.command()
    async def leaktracker(self, ctx):
        """Sends leak tracker information to premium users."""
        if self.is_premium_user(ctx.author.id):
            await ctx.send("Check your DMs!")

            try:
                with open("leaktracker.txt", "r", encoding="utf-8") as file:
                    leaks = file.readlines()

                if not leaks:
                    await ctx.author.send("No leaks found.")
                    return

                embeds = []
                current_embed = discord.Embed(title="**All leaks**", color=discord.Color.blue())
                embed_content = ""

                for line in leaks:
                    if len(embed_content) + len(line) > 2000:
                        current_embed.description = embed_content
                        embeds.append(current_embed)
                        current_embed = discord.Embed(color=discord.Color.blue())
                        embed_content = ""

                    embed_content += line

                if embed_content:
                    current_embed.description = embed_content
                    embeds.append(current_embed)

                for embed in embeds:
                    await ctx.author.send(embed=embed)

            except FileNotFoundError:
                await ctx.send("Leaks file not found.")
        else:
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by using the `@collage premium` command.",
                color=discord.Color.gold(),
            )
            await ctx.send(embed=embed)


class PremiumCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_whitelist(self, file_name):
        """Loads a whitelist JSON file, returns a dictionary."""
        if not os.path.exists(file_name):
            return {"whitelisted_ids": []}

        with open(file_name, "r", encoding="utf-8") as file:
            return json.load(file)

    def save_whitelist(self, file_name, data):
        """Saves data to a whitelist JSON file."""
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    @commands.command()
    async def addpremium(self, ctx, user_id: int):
        allowed_users = [715354423706124359, 987654321098765432]

        if ctx.author.id not in allowed_users:
            await ctx.send("You do not have permission to execute this command.")
            return

        manual_whitelist = self.load_whitelist("data/Developer/manual_whitelist.json")
        whitelisted_ids = manual_whitelist.get("whitelisted_ids", [])

        if str(user_id) not in whitelisted_ids:
            whitelisted_ids.append(str(user_id))
            manual_whitelist["whitelisted_ids"] = whitelisted_ids
            self.save_whitelist("data/Developer/manual_whitelist.json", manual_whitelist)
            await ctx.send(f"User {user_id} has been **manually** added to the premium whitelist.")
        else:
            await ctx.send(f"User {user_id} is **already** in the manual whitelist.")

    @commands.command()
    async def removepremium(self, ctx, user_id: int):
        allowed_users = [715354423706124359, 987654321098765432]

        if ctx.author.id not in allowed_users:
            await ctx.send("You do not have permission to execute this command.")
            return

        manual_whitelist = self.load_whitelist("data/Developer/manual_whitelist.json")
        whitelisted_ids = manual_whitelist.get("whitelisted_ids", [])

        if str(user_id) in whitelisted_ids:
            whitelisted_ids.remove(str(user_id))
            manual_whitelist["whitelisted_ids"] = whitelisted_ids
            self.save_whitelist("data/Developer/manual_whitelist.json", manual_whitelist)
            await ctx.send(f"User {user_id} has been **manually removed** from the premium whitelist.")
        else:
            await ctx.send(f"User {user_id} is **not** in the manual whitelist.")



def setup(bot):
    bot.add_cog(LeakTracker(bot))






class Comp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_premium_user(self, user_id: int):
        """Checks if a user is in either premium_whitelist.json or manual_whitelist.json"""
        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")

        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    @commands.command()
    async def comp(self, ctx):

        if await self.is_premium_user(ctx.author.id):
            await ctx.send("Check your DMs!")

            embed = discord.Embed(
                title="Comps:", 
                description="Thanks for supporting us!\nChoose a comp from the dropdown below:", 
                color=discord.Color.red()
            )


            select = Select(
                placeholder="Choose a comp...",
                options=[
                    discord.SelectOption(label="Juice Comp", description="Juice WRLD Comp", value="juice_comp"),
                    discord.SelectOption(label="Uzi Comp", description="Lil Uzi Vert Comp", value="uzi_comp"),
                    discord.SelectOption(label="Carti Comp", description="Playboi Carti Comp", value="carti_comp"),
                    discord.SelectOption(label="Gunna Comp", description="Gunna Comp", value="gunna_comp")
                ]
            )

            async def select_callback(interaction):
                comp_choice = select.values[0]
                
                if comp_choice == "juice_comp":

                    embed1 = discord.Embed(
                        title="Juice WRLD Comp Part 1",
                        description="Thanks for supporting us!",
                        color=discord.Color.red()
                    )
                    embed1.add_field(name="**Last updated**", value="August 21, 2025", inline=False)
                    embed1.add_field(name="**Amount of files**", value="`unknown`", inline=False)
                    embed1.add_field(name="**Comp size**", value="`18.32 GB`", inline=False)
                    embed1.set_thumbnail(url="https://i.ibb.co/zHV5Ykqg/mega.png")
                    button1 = Button(label="Mega Comp Part 1", url="https://mega.nz/folder/tZBmiJ6Q#lXyfhor14P54loxDYbjjOA")
                    view1 = View()
                    view1.add_item(button1)
                    await interaction.response.send_message(embed=embed1, view=view1)


                    embed2 = discord.Embed(
                        title="Juice WRLD Comp Part 2",
                        description="More files from the comp!",
                        color=discord.Color.red()
                    )
                    embed2.add_field(name="**Last updated**", value="August 21, 2025", inline=False)
                    embed2.add_field(name="**Amount of files**", value="`unknown`", inline=False)
                    embed2.add_field(name="**Comp size**", value="`5.83 GB`", inline=False)
                    embed2.set_thumbnail(url="https://i.ibb.co/zHV5Ykqg/mega.png")
                    button2 = Button(label="Mega Comp Part 2", url="https://mega.nz/folder/ABAFBDJL#lGiWeELhZNItj1jZsR__LQ")
                    view2 = View()
                    view2.add_item(button2)
                    await interaction.followup.send(embed=embed2, view=view2)

                elif comp_choice == "uzi_comp":
                    embed = discord.Embed(
                        title="Lil Uzi Vert Comp", 
                        description="Thanks for supporting us!", 
                        color=discord.Color.default()
                    )
                    embed.add_field(name="**Last updated**", value="April 4, 2025", inline=False)
                    embed.add_field(name="**Amount of files**", value="`1072`", inline=False)
                    embed.add_field(name="**Comp size**", value="`8.28 GB`", inline=False)
                    embed.add_field(name="**Password**", value="`WOTP`", inline=False)
                    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/Xs3uz5aHbVNCYb08GNJEZigwFG0H3xf_WchElr9bY_8/https/i.ibb.co/F4GrRhpL/filen.png?format=webp&quality=lossless&width=1216&height=1216")
                    button = Button(label="Filen Comp", url="https://app.filen.io/#/f/c5794afd-bd85-41d0-a8ab-9862584da253%23DmHMuZmi9D5PewEzdJRbv0g6hJeYS3pa")
                    view = View()
                    view.add_item(button)
                    await interaction.response.send_message(embed=embed, view=view)

                elif comp_choice == "carti_comp":
                    embed = discord.Embed(
                        title="Playboi Carti Comp", 
                        description="Thanks for supporting us!", 
                        color=discord.Color.default()
                    )
                    embed.add_field(name="**Last updated**", value="April 3, 2025", inline=False)
                    embed.add_field(name="**Amount of files**", value="`400`", inline=False)
                    embed.add_field(name="**Comp size**", value="`3.6 GB`", inline=False)
                    embed.add_field(name="**Password**", value="`WOTP`", inline=False)
                    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/Xs3uz5aHbVNCYb08GNJEZigwFG0H3xf_WchElr9bY_8/https/i.ibb.co/F4GrRhpL/filen.png?format=webp&quality=lossless&width=1216&height=1216")
                    button = Button(label="Filen Comp", url="https://app.filen.io/#/f/9ac91bd6-b626-46b0-8186-554c7f1942e8%23pzNd7LqJO5NBx9BDgJleQGghHF6cX2h3")
                    view = View()
                    view.add_item(button)
                    await interaction.response.send_message(embed=embed, view=view)

                elif comp_choice == "gunna_comp":
                    embed = discord.Embed(
                        title="Gunna Comp", 
                        description="Thanks for supporting us!", 
                        color=discord.Color.default()
                    )
                    embed.add_field(name="**Last updated**", value="April 3, 2025", inline=False)
                    embed.add_field(name="**Amount of files**", value="`177`", inline=False)
                    embed.add_field(name="**Comp size**", value="`1.1 GB`", inline=False)
                    embed.add_field(name="**Password**", value="`WOTP`", inline=False)
                    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/Xs3uz5aHbVNCYb08GNJEZigwFG0H3xf_WchElr9bY_8/https/i.ibb.co/F4GrRhpL/filen.png?format=webp&quality=lossless&width=1216&height=1216")
                    button = Button(label="Filen Comp", url="https://app.filen.io/#/f/6189351b-1ba7-46b3-9efa-fb99911ead83%23ISboIqYKhxaBO0e3sCvmxmXrjIJ4vi10")
                    view = View()
                    view.add_item(button)
                    await interaction.response.send_message(embed=embed, view=view)

            select.callback = select_callback
            view = View()
            view.add_item(select)


            try:
                await ctx.author.send(embed=embed, view=view)
            except discord.Forbidden:
                await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")

        else:
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by doing the `@collage premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Comp(bot))





class LeakDate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_premium_user(self, user_id: int):
        """Checks if a user is in either premium_whitelist.json or manual_whitelist.json"""
        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")

        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    def normalize_date(self, user_date):
        months = {
            'january': '1', 'february': '2', 'march': '3', 'april': '4', 'may': '5',
            'june': '6', 'july': '7', 'august': '8', 'september': '9', 'october': '10',
            'november': '11', 'december': '12'
        }

        user_date = user_date.lower()

        for month, month_num in months.items():
            if month in user_date:
                user_date = user_date.replace(month, month_num)
                break

        user_date = re.sub(r'(st|nd|rd|th)', '', user_date)
        user_date = re.sub(r'(\d{1,2})[./]([0-9]{1,2})[./]([0-9]{2})', r'\1 / \2 / \3', user_date)
        user_date = re.sub(r'(\d{1,2})\s*(\d{1,2})\s*(\d{4})', r'\1 / \2 / \3', user_date)
        user_date = re.sub(r'(\d{1}) / (\d{1}) / (\d{2})', r'0\1 / 0\2 / \3', user_date)
        user_date = re.sub(r'(\d{1,2}) / (\d{1,2}) / (\d{4})', r'\1 / \2 / \3', user_date)
        user_date = re.sub(r'(\d{1,2}) / (\d{1,2}) / (\d{2})', lambda m: f'{m.group(1)} / {m.group(2)} / {str(int(m.group(3))):02}', user_date)

        return user_date.strip()

    @commands.command()
    async def date(self, ctx, *, user_date: str):

        if await self.is_premium_user(ctx.author.id):
            normalized_date = self.normalize_date(user_date)

            if normalized_date in track_data:
                embed = discord.Embed(
                    title=f"Leaks for {normalized_date}", 
                    description="Here are the song(s) that leaked on this day:", 
                    color=discord.Color.default()
                )

                for track in track_data[normalized_date]:
                    embed.add_field(name=" ", value=track, inline=False)

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Sorry, no tracks found for {user_date}.")
        else:
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by doing the `@collage premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(LeakDate(bot))






class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def premium(self, ctx):
        embed = discord.Embed(
            title="**__What Is Premium?__**",
            description="Premium is a service we offer that gives access to commands and exclusive features that regular users do not have access to.",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url="https://i.ibb.co/Zzz1j0PW/c41579327c01906016b3ade2c1308656.webp")  

        embed.add_field(name="• **_leaktracker_**", value="This command sends every single known leak with dates to the user's DMs.", inline=False)
        embed.add_field(name="• *_date_*", value="This allows the user to specify a date, and the bot will look for every leak on the specified date.", inline=False)
        embed.add_field(name="• **_comp_**", value="This command provides the user with comps from 4 different artists, including Juice WRLD, Playboi Carti, Gunna, and Lil Uzi Vert", inline=False)
        embed.add_field(name="• **_convert_**", value="Convert's the users inputted Youtube link into a MP3.", inline=False)
        embed.add_field(name="• **_cartileak_**", value="Get any leak from Playboi Carti.", inline=False)
        embed.add_field(name="• **_gunnaleak_**", value="Get any leak from Gunna.", inline=False)
        embed.add_field(name="• **_uzileak_**", value="Get any leak from Lil Uzi Vert.", inline=False)
        embed.add_field(name="• **_repost_**", value="Repost a TikTok, Instagram, or Twitter video into a discord channel.", inline=False)
        embed.add_field(name="• **_protools_**", value="Get any leaked Pro Tools session. **This feature is still a work in progress.**", inline=False)
        embed.add_field(name="• **_convertfile_**", value="Convert a user inputted audio file into a different format.", inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="**__How can I get Premium?__**", value="Premium can be accessed by boosting our server, WRLD of the Perced or by sending 7$ USD for lifetime premium to our PayPal.", inline=False)
        embed.add_field(name="**• PayPal**:", value="[Click Here For PayPal](https://paypal.me/xigbotic)", inline=False)
        embed.add_field(name=" ", value="**__Please send your money as Friends & Family and put your discord tag in the payment message. If you do not do this, you will not be given premium and your money will be sent back.\n\n If it has been longer than 16 hours and you still not have received premium on your account, please contact @4nbx or @xbox360s on discord through our support server.__**", inline=False)
        embed.set_footer(text="Made by xbox360s on discord | Support Server: discord.gg/wotp")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Premium(bot))





class Credits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def credits(self, ctx):
        embed = discord.Embed(
            title="Credits",
            description=" ",
            color=discord.Color.default(),
        )

        embed.set_thumbnail(url="https://i.ibb.co/Zzz1j0PW/c41579327c01906016b3ade2c1308656.webp")

        embed.add_field(
            name="Developer",
            value="`@xbox360s` & `@houndswrldd`",
            inline=False
        )

        embed.add_field(
            name="Special Thanks",
            value=(
                "`@merikaaaaa` — extremely skilled developer, contributed to this entire project. Check out his FH5 Trainer [Here.](https://www.merika.dev/)\n"
                "`@VerzeHxD` — provided the database for the snippet command.\n"
                "`@gabedoesntgaf` — created the Juice WRLD groupbuy spreadsheet.\n"
                "`@192kbps` — compiled the Juice WRLD information spreadsheet.\n"
                "`@WRLDOverlord` — compiled the Lil Uzi Vert information spreadsheet.\n"
                "`@juicewrldapi` — provided the [JuiceWRLDAPI.](https://juicewrldapi.com/)"
            ),
            inline=False
        )

        embed.add_field(
            name="Testers",
            value=(
                "`@sharkky999`, `@angzyjr`, `@999ashton`, `@nick1616`, "
                "`@truesecurity`, `@jo097951`, `@squiregilligan`, `@kfjaf`, `@aussigirl2`, `@blxssedfr`\n\n"
                "_Your feedback, ideas, and patience helped shape this bot into what it is today. "
                "Thank you for your continued support._"
            ),
            inline=False
        )

        embed.set_footer(text="discord.gg/wotp")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Credits(bot))






class YT2MP3(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_premium_user(self, user_id: int):

        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")

        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    def sanitize_filename(self, filename):

        return re.sub(r'[\\/*?:"<>|]', "", filename)


    def download_and_get_path(self, url, ydl_opts):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                filename = ydl.prepare_filename(info)

                mp3_filepath = os.path.splitext(filename)[0] + '.mp3'
                return mp3_filepath, None
        except Exception as e:
            return None, e


    @commands.hybrid_command(  
        name='yt2mp3',
        with_app_command=True,
        description="Converts a YouTube video to MP3 and sends it via DM."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def yt2mp3(self, ctx: commands.Context, url: str):
        """Converts a YouTube video to MP3 and sends it via DM."""
        

        if not await self.is_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by using the `@collage premium` command.",
                color=discord.Color.gold()
            )

            await ctx.send(embed=embed, ephemeral=True)
            return


        embed_start = discord.Embed(
            title="<a:GTALoading:1348124710394662995> Processing your request...",
            description=f"Downloading and converting video... This might take a moment. Check your DMs soon, {ctx.author.mention}",
            color=discord.Color.default()
        )
        
        if ctx.interaction:

            await ctx.defer()


            await ctx.interaction.edit_original_response(embed=embed_start)
            message = await ctx.interaction.original_response()
        else:

            message = await ctx.send(embed=embed_start)
            

        ydl_opts = {

            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        }


        blocking_task = functools.partial(self.download_and_get_path, url, ydl_opts)
        mp3_file, error = await self.bot.loop.run_in_executor(None, blocking_task)


        if error:
            embed_error = discord.Embed(
                title="❌ An Error Occurred",
                description=f"Could not process your request. Error: {str(error)}",
                color=discord.Color.red()
            )

            if ctx.interaction:
                await ctx.interaction.edit_original_response(embed=embed_error)
            else:
                await message.edit(embed=embed_error)
            return


        if mp3_file and os.path.exists(mp3_file):
            embed_success = discord.Embed(
                title="<a:checkdone:1353058188877889647> Conversion Complete",
                description=f"Your file has been successfully converted. It's been sent to your DMs, {ctx.author.mention}",
                color=discord.Color.green()
            )
            

            if ctx.interaction:
                await ctx.interaction.edit_original_response(embed=embed_success)
            else:
                await message.edit(embed=embed_success)

            try:

                file_size = os.path.getsize(mp3_file)
                if file_size > 8 * 1024 * 1024:
                    await ctx.author.send("The converted file is too large to be sent over Discord (over 8MB).")
                else:
                    await ctx.author.send(file=discord.File(mp3_file))
                    
            except discord.Forbidden:
                embed_error_dm = discord.Embed(
                    title="❌ DM Error",
                    description=f"I couldn't DM you, {ctx.author.mention}. Please enable DMs from server members and try again.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed_error_dm)
                
            finally:

                os.remove(mp3_file)
                if ctx.message:
                    await ctx.message.delete()
        else:
            embed_error = discord.Embed(
                title="❌ Conversion Error",
                description="The file could not be created or found after conversion. Please try again.",
                color=discord.Color.red()
            )
            if ctx.interaction:
                await ctx.interaction.edit_original_response(embed=embed_error)
            else:
                await message.edit(embed=embed_error)





class ProducerSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_premium_user(self, user_id: int):
        """Checks if a user is in either premium_whitelist.json or manual_whitelist.json"""
        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")

        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    def parse_info(self, content):
        info = {}
        lines = content.splitlines()

        for line in lines:
            if line.strip():
                if line.startswith("Track Title(s):"):
                    info["Track Title"] = line.split(":", 1)[1].strip()
                elif line.startswith("ERA:"):
                    era_short = line.split(":", 1)[1].strip()
                    info["Era"] = era_mapping.get(era_short, era_short)
                elif line.startswith("Producer(s):"):
                    info["Producer"] = line.split(":", 1)[1].strip()

        return info

    def search_for_text_files(self, directory, producer_name):
        results = []

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)

                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    parsed_info = self.parse_info(content)

                    if "Producer" in parsed_info:
                        producers = re.split(r',\s*|\s*&\s*', parsed_info["Producer"])
                        if producer_name.lower() in [p.lower() for p in producers]:
                            parsed_info["File Name"] = file
                            results.append(parsed_info)


        results.sort(key=lambda x: era_sort_order.index(x["Era"]) if x["Era"] in era_sort_order else len(era_sort_order))

        return results

    @commands.command(aliases=["prod"])
    async def producer(self, ctx, *, producer_name: str):
        """Searches for tracks produced by the specified producer."""


        if not await self.is_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by using the `@collage premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return

        directory = r"D:\JBDB\juiceinfo (full names)"
        results = self.search_for_text_files(directory, producer_name)

        if not results:
            await ctx.send(f"No tracks found for producer: {producer_name}")
            return

        items_per_page = 10
        total_pages = math.ceil(len(results) / items_per_page)
        current_page = 0

        def create_embed(page):
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            page_results = results[start_idx:end_idx]

            embed = discord.Embed(
                title=f"Tracks produced by {producer_name}:",
                color=discord.Color.default()
            )

            for track in page_results:
                embed.add_field(
                    name=f"🎵 {track.get('Track Title', 'N/A')}",
                    value=f"**Era:** {track.get('Era', 'N/A')}\n"
                          f"**Producers:** {track.get('Producer', 'N/A')}",
                    inline=False
                )

            embed.set_footer(text=f"Page {page + 1} of {total_pages}")
            return embed

        message = await ctx.send(embed=create_embed(current_page))

        if total_pages > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ["⬅️", "➡️"]

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=120.0, check=check)

                    if str(reaction.emoji) == "➡️" and current_page < total_pages - 1:
                        current_page += 1
                        await message.edit(embed=create_embed(current_page))
                    elif str(reaction.emoji) == "⬅️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=create_embed(current_page))

                    await message.remove_reaction(reaction, user)

                except:
                    break


AUDIO_FORMATS = ["m4a", "mp3", "wav", "flac"]

class ConvertFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_premium_user(self, user_id: int):
        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")
        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    def get_max_upload_size(self, guild):
        if not guild:
            return 8 * 1024 * 1024
        return {
            0: 10 * 1024 * 1024,
            1: 10 * 1024 * 1024,
            2: 50 * 1024 * 1024,
            3: 100 * 1024 * 1024,
        }.get(guild.premium_tier, 8 * 1024 * 1024)

    def get_bitrate(self, file_path):
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                 'stream=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            bitrate = result.stdout.strip()
            return f"{int(bitrate)}" if bitrate else None
        except Exception as e:
            print(f"Failed to get bitrate: {e}")
            return None

    def extract_cover_art(self, file_path, cover_art_path="5jio4j8098g9g9g9nn.jpg"):
        try:
            command = ['ffmpeg', '-i', file_path, '-an', '-vcodec', 'png', cover_art_path]
            subprocess.run(command, check=True)
            return cover_art_path
        except subprocess.CalledProcessError:
            print("Error extracting cover art.")
            return None

    def add_cover_art_to_file(self, file_path, cover_art_path):
        try:
            if file_path.lower().endswith('.mp3'):
                audio = ID3(file_path)
                with open(cover_art_path, 'rb') as f:
                    audio.add(APIC(3, 'image/jpeg', 3, 'Front cover', f.read()))
                audio.save()
            elif file_path.lower().endswith('.m4a'):
                audio = MP4(file_path)
                with open(cover_art_path, 'rb') as f:
                    audio.tags["covr"] = [MP4Cover(f.read(), MP4Cover.FORMAT_JPEG)]
                audio.save()
        except Exception as e:
            print(f"Error tagging cover art: {e}")

    async def convert_file(self, input_path, output_path):
        input_ext = input_path.split('.')[-1].lower()
        output_ext = output_path.split('.')[-1].lower()
        command = ["ffmpeg", "-y", "-i", input_path, "-map", "0:a"]

        original_bitrate = self.get_bitrate(input_path)

        if input_ext in AUDIO_FORMATS and output_ext in AUDIO_FORMATS:
            if output_ext == "mp3":
                command += ["-c:a", "libmp3lame"]
            elif output_ext == "m4a":
                command += ["-c:a", "aac"]
            elif output_ext == "flac":
                command += ["-c:a", "flac"]
            elif output_ext == "wav":
                command += ["-c:a", "pcm_s16le"]

            if original_bitrate:
                command += ["-b:a", original_bitrate]
        else:
            return False

        command.append(output_path)

        try:
            subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[FFmpeg Error] {e}")
            return False

    @commands.command()
    async def convertfile(self, ctx):
        if not await self.is_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by doing the `@collage premium` command.",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        await ctx.send("🎵 Select the **current format** of your file:", view=FormatSelector(ctx, self.bot, self))


class FormatSelector(discord.ui.View):
    def __init__(self, ctx, bot, cog):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        self.cog = cog
        for fmt in AUDIO_FORMATS:
            self.add_item(FormatButton(fmt, ctx, bot, cog))


class FormatButton(discord.ui.Button):
    def __init__(self, fmt, ctx, bot, cog):
        super().__init__(label=fmt.upper(), style=discord.ButtonStyle.primary)
        self.fmt = fmt
        self.ctx = ctx
        self.bot = bot
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your session.", ephemeral=True)

        await interaction.response.edit_message(
            content=f"💿 What do you want to convert your **{self.fmt.upper()}** file into?",
            view=TargetFormatSelector(self.ctx, self.fmt, self.bot, self.cog)
        )


class TargetFormatSelector(discord.ui.View):
    def __init__(self, ctx, source_fmt, bot, cog):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.source_fmt = source_fmt
        self.bot = bot
        self.cog = cog

        for fmt in AUDIO_FORMATS:
            if fmt != source_fmt:
                self.add_item(TargetFormatButton(fmt, source_fmt, ctx, bot, cog))


class TargetFormatButton(discord.ui.Button):
    def __init__(self, target_fmt, source_fmt, ctx, bot, cog):
        super().__init__(label=target_fmt.upper(), style=discord.ButtonStyle.success)
        self.target_fmt = target_fmt
        self.source_fmt = source_fmt
        self.ctx = ctx
        self.bot = bot
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your session.", ephemeral=True)

        await interaction.response.edit_message(
            content=f"📎 Upload your **{self.source_fmt.upper()}** file to convert it to **{self.target_fmt.upper()}**.",
            view=None
        )

        def check(m):
            return m.author == self.ctx.author and m.attachments and m.channel == self.ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)


            file = msg.attachments[0]
            original_name = os.path.splitext(file.filename)[0]
            input_path = f"{original_name}.{self.source_fmt}"
            output_path = f"{original_name}.{self.target_fmt}"

            await file.save(fp=input_path)
            await msg.delete()
            await self.ctx.send(embed=discord.Embed(
            description="🗑️ Your uploaded file was deleted after conversion for **copyright & privacy** reasons.",
            color=discord.Color.orange()
            ))
            cover_art_path = self.cog.extract_cover_art(input_path)

            result = await self.cog.convert_file(input_path, output_path)

            if not result:
                return await self.ctx.send("❌ Conversion failed. Check if your file type is supported.")

            if cover_art_path:
                self.cog.add_cover_art_to_file(output_path, cover_art_path)
                os.remove(cover_art_path)

            file_size = os.path.getsize(output_path)
            max_size = self.cog.get_max_upload_size(self.ctx.guild)

            if file_size > max_size:
                return await self.ctx.send(
                    f"⚠️ Converted file is too large (**{file_size // 1024 ** 2}MB**). "
                    f"Your server limit is **{max_size // 1024 ** 2}MB** based on boost level."
                )

            embed = discord.Embed(
                title="🎶 Conversion Complete",
                description=f"Your **{self.source_fmt.upper()}** file has been successfully converted to **{self.target_fmt.upper()}**.",
                color=discord.Color.green()
            )
            sent_message = await self.ctx.send(embed=embed, file=discord.File(output_path))

            async def delete_after_delay():
                await asyncio.sleep(60)
                try:
                    await sent_message.delete()
                except:
                    pass
                if os.path.exists(output_path):
                    os.remove(output_path)

            self.bot.loop.create_task(delete_after_delay())

        except asyncio.TimeoutError:
            await self.ctx.send("⏰ You took too long to upload a file.")
        finally:

            for file_path in [input_path, output_path]:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Failed to remove {file_path}: {e}")



class GunnaLeakView(View):
    def __init__(self, folder_map, send_leak_func, user_avatar, bot_avatar):
        super().__init__(timeout=30)
        self.folder_map = folder_map
        self.send_leak = send_leak_func
        self.user_avatar = user_avatar
        self.bot_avatar = bot_avatar

        options = [
            discord.SelectOption(label=os.path.basename(fpath)[:100], value=safe_value)
            for safe_value, fpath in folder_map.items()
        ]
        
        self.select_menu = Select(options=options, placeholder="Select a file")
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True) 

        selected_value = self.select_menu.values[0]
        file_path = self.folder_map[selected_value]
        


        await self.send_leak(interaction, file_path, self.user_avatar, self.bot_avatar)
        

        self.select_menu.disabled = True
        try:
            await interaction.edit_original_response(view=self)
        except Exception:
             pass


class Gunnaleak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}


    async def is_premium_user(self, user_id: int):
        """Checks if a user is in either premium_whitelist.json or manual_whitelist.json"""
        def load_whitelist(file_name):
            if not os.path.exists(file_name):
                return {"whitelisted_ids": []}
            with open(file_name, "r", encoding="utf-8") as file:
                return json.load(file).get("whitelisted_ids", [])

        premium_whitelist = load_whitelist("data/Developer/premium_whitelist.json")
        manual_whitelist = load_whitelist("data/Developer/manual_whitelist.json")

        return str(user_id) in premium_whitelist or str(user_id) in manual_whitelist

    @commands.hybrid_command(
        name="gunnaleak",
        with_app_command=True,
        description="Search for and send Gunna leaks by name (Premium)."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def gunnaleak(self, ctx: commands.Context, *, query: str = None):
        
        user_avatar = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else ctx.bot.user.default_avatar.url


        if not await self.is_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ Premium Feature!",
                description="You can learn more about premium by using the `/premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return


        if ctx.interaction:
            await ctx.defer()
            
        if not query:
            embed = discord.Embed(
                title="Missing File Name",
                description="Provide a file name to search.\nExample: `/gunnaleak drip too hard`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        def normalize(text):
            text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            return re.sub(rf"[{re.escape(string.punctuation)}]", "", text.lower())

        normalized_query = normalize(query)


        matching_files = []

        if not os.path.isdir(GUNNA_LEAK_PATH):
            print(f"ERROR: GUNNA_LEAK_PATH '{GUNNA_LEAK_PATH}' not found or is not a directory.")
            await ctx.send("❌ The leak directory is not configured correctly. Please contact the bot owner.", ephemeral=True)
            return
            
        for era_folder in os.listdir(GUNNA_LEAK_PATH):
            era_path = os.path.join(GUNNA_LEAK_PATH, era_folder)
            if not os.path.isdir(era_path):
                continue
            for f in os.listdir(era_path):
                file_path = os.path.join(era_path, f)
                if os.path.isfile(file_path) and normalized_query in normalize(f) and f.lower().endswith(".mp3"):
                    matching_files.append(file_path)

        if not matching_files:
            embed = discord.Embed(
                title=":x: No Leaks Found",
                description=f"No leaks matching '{query}' found!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return


        if len(matching_files) == 1:

            await self.send_leak(ctx, matching_files[0], user_avatar, bot_avatar)
            return


        folder_map = {}
        for i, fpath in enumerate(matching_files[:25]):
            safe_value = f"leak_option_{i}"
            folder_map[safe_value] = fpath
        

        view = GunnaLeakView(folder_map, self.send_leak, user_avatar, bot_avatar) 

        await ctx.send(embed=discord.Embed(
            description=f"**{len(matching_files)} Leaks Found**\nSelect one from the dropdown.",
            color=discord.Color.default()
        ), view=view)

    async def send_leak(self, ctx_or_interaction, file_path, user_avatar, bot_avatar):
        if not os.path.exists(file_path):
            return await self.send_message(ctx_or_interaction, ":x: File not found.")

        audiofile = eyed3.load(file_path)
        title = audiofile.tag.title if audiofile and audiofile.tag and audiofile.tag.title else "Unknown"
        artist = audiofile.tag.artist if audiofile and audiofile.tag and audiofile.tag.artist else "Unknown"
        album = audiofile.tag.album if audiofile and audiofile.tag and audiofile.tag.album else "Unknown"
        length = audiofile.info.time_secs if audiofile and audiofile.info else 0
        formatted_length = f"{int(length//60)}:{int(length%60):02d}"

        cover_file = None
        if audiofile.tag and audiofile.tag.frame_set.get(b'APIC'):
            image_data = audiofile.tag.frame_set.get(b'APIC')[0].image_data
            cover_file = discord.File(io.BytesIO(image_data), filename="cover.jpg")

        embed = discord.Embed(
            title=title,
            description=f"**Artist:** `{artist}`\n**Album:** `{album}`\n**Length:** `{formatted_length}`",
            color=discord.Color.default()
        )
        embed.set_footer(text="File will be deleted after 60 seconds.")
        if cover_file:
            embed.set_thumbnail(url="attachment://cover.jpg")

        await self.send_message(ctx_or_interaction, embed=embed, file=cover_file)


        button = discord.ui.Button(label="Download", style=discord.ButtonStyle.green)
        async def button_callback(interaction: discord.Interaction):
            now = asyncio.get_event_loop().time()
            last_used = self.cooldowns.get(interaction.user.id, 0)
            if now - last_used < 30:
                return await interaction.response.send_message(
                    f"⏳ Wait {int(30 - (now - last_used))}s before downloading again.", ephemeral=True)
            self.cooldowns[interaction.user.id] = now

            file = discord.File(file_path, filename=os.path.basename(file_path))
            await interaction.response.send_message("📦 Preparing your file...", ephemeral=True)
            await interaction.followup.send(file=file, ephemeral=True)

        button.callback = button_callback
        view = discord.ui.View()
        view.add_item(button)
        await self.send_message(ctx_or_interaction, embed=None, view=view)

    async def send_message(self, ctx_or_interaction, *args, **kwargs):
        if isinstance(ctx_or_interaction, discord.Interaction):
            if not ctx_or_interaction.response.is_done():
                return await ctx_or_interaction.response.send_message(*args, **kwargs)
            return await ctx_or_interaction.followup.send(*args, **kwargs)
        return await ctx_or_interaction.send(*args, **kwargs)








async def setup(bot):
    await bot.add_cog(Comp(bot))
    await bot.add_cog(LeakDate(bot))
    await bot.add_cog(LeakTracker(bot))
    await bot.add_cog(Premium(bot))
    await bot.add_cog(Credits(bot))
    await bot.add_cog(PremiumCommands(bot))
    await bot.add_cog(YT2MP3(bot))
    await bot.add_cog(ProducerSearch(bot))
    await bot.add_cog(ConvertFile(bot))