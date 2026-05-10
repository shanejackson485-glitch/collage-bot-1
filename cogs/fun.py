import discord
import time
import random
import aiohttp
import asyncio
import io
import os
import secrets
import datetime
import math
import ast
import operator
import decimal
import regex as re
import urllib.parse
import unicodedata
import pyfiglet
import json
import logging

from io import BytesIO
from typing import Optional, Tuple
from decimal import Decimal
from functools import partial
from urllib.parse import quote
from datetime import datetime, timedelta


import uwuify
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog, hybrid_command
from pilmoji import Pilmoji
from PIL import Image, ImageDraw, ImageFont, ImageColor
from lyricsgenius import Genius



from config import GENIUS_KEY, whitelist, BALANCE_FILE


logger = logging.getLogger("combined_cog")
logger.setLevel(logging.DEBUG)

fonts = [
    "3d-ascii", "3d_diagonal", "5lineoblique", "avatar", "braced", 
    "cards", "computer", "drpepper", "fun_face", "keyboard", "konto_slant"
]

allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow
}

MAX_INPUT_LENGTH = 200
MAX_RECURSION_DEPTH = 20
MAX_EXECUTION_TIME = 2
MAX_NUMBER = Decimal('1e1000')



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

    async def start(self, message=None):
        if not message:
            self.message = await self.ctx.send(embed=self.embeds[0], view=self)
        else:
            self.message = message
            await self.message.edit(embed=self.embeds[0], view=self)

class SafeMathEvaluator:
    def __init__(self):
        self.start_time = None

    def evaluate_expression(self, expression):
        if len(expression) > MAX_INPUT_LENGTH:
            return "Error: Expression too long"

        expression = ''.join(c for c in expression if c.isprintable())
        expression = unicodedata.normalize("NFKC", expression)

        try:
            decimal.getcontext().prec = 50
            self.start_time = time.time()
            tree = ast.parse(expression, mode='eval')

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) or isinstance(node, ast.Attribute):
                    raise ValueError("Function calls and attribute access are not allowed")
                if isinstance(node, ast.BinOp) and type(node.op) not in allowed_operators:
                    raise ValueError("Unsupported operator")

            result = self._eval_ast(tree.body, 0)
            return str(result)

        except Exception as e:
            return str(e)

    def _eval_ast(self, node, depth):
        if depth > MAX_RECURSION_DEPTH:
            raise ValueError("Maximum recursion depth exceeded")
        if time.time() - self.start_time > MAX_EXECUTION_TIME:
            raise ValueError("Execution time limit exceeded")

        if isinstance(node, ast.Expression):
            return self._eval_ast(node.body, depth + 1)
        elif isinstance(node, ast.BinOp):
            left = self._eval_ast(node.left, depth + 1)
            right = self._eval_ast(node.right, depth + 1)
            op_func = allowed_operators[type(node.op)]

            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Division by zero")
            if isinstance(node.op, ast.Pow):
                if left == 0 and right < 0:
                    raise ValueError("Zero cannot be raised to a negative power")
                if abs(right) > 1000:
                    raise ValueError("Exponent too large")

            result = op_func(Decimal(str(left)), Decimal(str(right)))
            if abs(result) > MAX_NUMBER:
                raise ValueError("Result too large")
            return result

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_ast(node.operand, depth + 1)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            else:
                raise ValueError("Unsupported unary operator")
        elif isinstance(node, ast.Num):
            if abs(Decimal(str(node.n))) > MAX_NUMBER:
                raise ValueError("Number too large")
            return Decimal(str(node.n))
        else:
            raise ValueError("Unsupported AST node")



class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def warn(self, ctx, message):
        embed = discord.Embed(description=f"⚠️ {message}", color=discord.Color.red())
        if hasattr(ctx, 'reply'):
            await ctx.reply(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed, ephemeral=True)
    
    async def edit_warn(self, ctx, message, msg_to_edit):
        embed = discord.Embed(description=f"⚠️ {message}", color=discord.Color.red())
        await msg_to_edit.edit(embed=embed)

    async def get_color(self, user_id):
        guild = self.bot.get_guild(self.bot.guilds[0].id) if self.bot.guilds else None
        if guild:
            member = guild.get_member(user_id)
            if member and member.color != discord.Color.default():
                return member.color
        return discord.Color.blurple()

    @app_commands.command()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str, freaky: bool = False, uwu: bool = False, reverse: bool = False):
        try:
            if reverse:
                message = message[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
            if uwu:
                flags = uwuify.STUTTER
                message = uwuify.uwu(message, flags=flags)
            if freaky:
                def to_freaky(text):
                    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                    freaky_font = "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓿𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃"
                    translation_table = str.maketrans(normal, freaky_font)
                    translated_text = text.translate(translation_table)
                    wrapped_text = re.sub(r'[^𝓐-𝔃 *]+', lambda match: f"*{match.group(0)}*", translated_text)
                    return wrapped_text
                message = to_freaky(message)

            await interaction.response.send_message(message, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            await interaction.response.send_message("`Command 'say' was blocked by AutoMod.`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    @hybrid_command(name="urban", description="Search Urban Dictionary")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
    async def urban(self, ctx: commands.Context, *, search: str):
        await ctx.typing()
        try:
            async with self.session.get(f"https://api.urbandictionary.com/v0/define?term={search}") as r:
                if not r.ok:
                    return await self.warn(ctx, "I think the API broke..")
                data = await r.json()
                if not data["list"]:
                    return await self.warn(ctx, "Couldn't find your search in the dictionary...")
                definitions = sorted(data["list"], reverse=True, key=lambda g: int(g["thumbs_up"]))
                if not definitions:
                    return await self.warn(ctx, "No definitions found.")

                color = await self.get_color(ctx.author.id)
                pages_embeds = []
                for definition_data in definitions:
                    definition = definition_data['definition']
                    word = definition_data['word']
                    url = definition_data['permalink']
                    if len(definition) >= 1000:
                        definition = definition[:1000].rsplit(" ", 1)[0] + "..."
                    embed = discord.Embed(title=word, url=url, description=definition, color=color)
                    if definition_data['example']:
                        embed.add_field(name="Example", value=definition_data['example'], inline=False)
                    embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
                    embed.set_footer(text=f"{definition_data['thumbs_up']} 👍 • {definition_data['thumbs_down']} 👎")
                    pages_embeds.append(embed)
                await SimplePaginator(ctx, pages_embeds).start()
        except Exception as e:
            await self.warn(ctx, str(e))

    @commands.hybrid_command(name="lyrics", description="Search for song lyrics")
    async def lyrics(self, ctx: commands.Context, *, song: str):
        loading_embed = discord.Embed(
            description=f"-# {ctx.author.mention}: fetching lyrics for: **{song}**",
            color=await self.get_color(ctx.author.id)
        )
        message = await ctx.send(embed=loading_embed)
        result = None
        try:
            loop = asyncio.get_running_loop()
            genius = Genius(GENIUS_KEY)
            genius.remove_section_headers = True
            genius.skip_non_songs = True
            song_obj = await loop.run_in_executor(None, genius.search_song, song)
            if song_obj and song_obj.lyrics and song_obj.lyrics.strip():
                lyrics_text = song_obj.lyrics
                if "Lyrics" in lyrics_text:
                    lyrics_index = lyrics_text.find("Lyrics")
                    lyrics_text = lyrics_text[lyrics_index + len("Lyrics"):].strip()
                lines = [line.strip() for line in lyrics_text.split("\n") if line.strip()]
                lines_per_page = 15
                pages_content = ["\n".join(lines[i:i+lines_per_page]) for i in range(0, len(lines), lines_per_page)]
                track_info = {"title": song_obj.title, "author": song_obj.artist, "albumArt": song_obj.song_art_image_url}
                result = {"text": lyrics_text, "track": track_info, "lines": pages_content, "source": "Genius"}
        except Exception:
            await self.edit_warn(ctx, "Lyrics not found (Check Genius API Key).", message)
            return

        if not result or not result.get("text"):
            await self.edit_warn(ctx, "Lyrics not found.", message)
            return

        track_info = result.get("track", {})
        title = track_info.get("title", song)
        artist = track_info.get("author", "Unknown Artist")
        album_art = track_info.get("albumArt")
        source = result.get("source", "Genius")
        color = await self.get_color(ctx.author.id)
        pages_embeds = []
        for content in result["lines"]:
            embed = discord.Embed(title=f"{title} - {artist}", description=f"```yaml\n{content}```", color=color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=source)
            if album_art:
                embed.set_thumbnail(url=album_art)
            pages_embeds.append(embed)
        paginator = SimplePaginator(ctx, pages_embeds)
        await paginator.start(message=message)

    @lyrics.autocomplete("song")
    async def lyrics_autocomplete(self, interaction: discord.Interaction, current: str):
        if not current:
            return [app_commands.Choice(name="Not Like Us - Kendrick Lamar", value="Not Like Us - Kendrick Lamar")]
        try:
            loop = asyncio.get_running_loop()
            genius = Genius(GENIUS_KEY)
            search_results = await loop.run_in_executor(None, genius.search_songs, current)
            hits = search_results.get("hits", [])[:25]
            choices = []
            for hit in hits:
                title = hit["result"]["title"]
                artist = hit["result"]["artist_names"]
                name = f"{title} - {artist}"[:100]
                choices.append(app_commands.Choice(name=name, value=name))
            return choices
        except:
            return []

    @hybrid_command(name="fakemessage", description="Create a fake Discord message", aliases=["fake", "fakemsg", "fmsg"])
    @app_commands.describe(user="The user to impersonate", text="The message content")
    @app_commands.choices(theme=[app_commands.Choice(name="Ash", value="ash"), app_commands.Choice(name="Dark", value="dark")])
    async def fakemessage(self, ctx: commands.Context, user: Optional[discord.User] = None, *, text: str, theme: Optional[app_commands.Choice[str]] = None):
        if user is None:
            user = ctx.author
        if text is None:
            return await ctx.send_help(ctx.command)
        await ctx.typing()
        theme_value = theme.value if theme else "ash"

        async def create_fake_discord_msg(display_name, pfp_data, message, decoration_data=None):
            def sync_create():
                try:
                    font_username = ImageFont.truetype("heist/fonts/gg sans semibold.ttf", 16)
                    font_timestamp = ImageFont.truetype("heist/fonts/gg sans medium.ttf", 12)
                    font_message = ImageFont.truetype("heist/fonts/gg sans medium.ttf", 16)
                except OSError:
                    font_username = ImageFont.load_default()
                    font_timestamp = ImageFont.load_default()
                    font_message = ImageFont.load_default()

                max_text_width = 500
                padding = 65
                wrapped_lines = []
                words = message.split(" ")
                line = ""
                for word in words:
                    test_line = line + word + " "
                    try:
                        line_len = font_message.getlength(test_line)
                    except AttributeError:
                        line_len = font_message.getsize(test_line)[0]
                    if line_len <= max_text_width:
                        line = test_line
                    else:
                        if line.strip(): wrapped_lines.append(line.strip())
                        line = word + " "
                if line.strip(): wrapped_lines.append(line.strip())
                
                try:
                    text_width = max(font_message.getlength(line) for line in wrapped_lines)
                except AttributeError:
                    text_width = max(font_message.getsize(line)[0] for line in wrapped_lines)
                
                width = min(800, max(400, int(text_width) + padding))
                height = 75 + (len(wrapped_lines) - 1) * 20
                bg_color = "#1a1b1e" if theme_value == "dark" else "#323339"
                image = Image.new("RGB", (width, height), bg_color)
                draw = ImageDraw.Draw(image, "RGBA")

                with Image.open(io.BytesIO(pfp_data)) as pfp_original:
                    pfp = pfp_original.convert("RGBA").resize((40, 40), Image.LANCZOS)
                large_mask = Image.new("L", (80, 80), 0)
                draw_large = ImageDraw.Draw(large_mask)
                draw_large.ellipse((0, 0, 80, 80), fill=255)
                mask = large_mask.resize((40, 40), Image.LANCZOS)
                pfp.putalpha(mask)
                image.paste(pfp, (13, 18), pfp)

                if decoration_data:
                    with Image.open(io.BytesIO(decoration_data)).convert("RGBA") as decor:
                        decor = decor.resize((50, 50), Image.LANCZOS)
                        image.paste(decor, (8, 13), decor)

                with Pilmoji(image) as pilmoji:
                    pilmoji.text((65, 15), display_name, (255, 255, 255), font=font_username, emoji_position_offset=(0, 3))
                
                try:
                    timestamp_x = int(65 + font_username.getlength(display_name) + 7)
                except AttributeError:
                    timestamp_x = int(65 + font_username.getsize(display_name)[0] + 7)
                
                hour = random.randint(1, 12)
                minute = random.randint(0, 59)
                ampm = random.choice(["AM", "PM"])
                timestamp_str = f"{hour}:{minute:02d} {ampm}"
                draw.text((timestamp_x, 18), timestamp_str, font=font_timestamp, fill=(163, 166, 170))

                with Pilmoji(image) as pilmoji:
                    extra_space = 2
                    y_offset = 36
                    for line in wrapped_lines:
                        x_offset = 65
                        words_in_line = line.split()
                        for word in words_in_line:
                            if re.fullmatch(r'@[\w]+', word):
                                mention_color = ImageColor.getrgb("#a5b5f9")
                                overlay_color = (41, 44, 80, 180)
                                try:
                                    mention_width = int(font_message.getlength(word + " "))
                                    mention_height = font_message.size + 2
                                except AttributeError:
                                    mention_width = int(font_message.getsize(word + " ")[0])
                                    mention_height = 18 
                                mention_y_offset = y_offset + 2
                                draw.rounded_rectangle([x_offset - 2, mention_y_offset, x_offset + mention_width, mention_y_offset + mention_height], radius=4, fill=overlay_color)
                                pilmoji.text((x_offset, y_offset), word + " ", mention_color, font_message, emoji_position_offset=(0, 3))
                                x_offset += mention_width + extra_space
                            else:
                                pilmoji.text((x_offset, y_offset), word + " ", ImageColor.getrgb("#e3e5e8"), font_message, emoji_position_offset=(0, 3))
                                try:
                                    x_offset += int(font_message.getlength(word + " "))
                                except AttributeError:
                                    x_offset += int(font_message.getsize(word + " ")[0])
                        y_offset += 20
                return image
            return await asyncio.to_thread(sync_create)

        try:
            pfp_url = user.display_avatar.url
            async with self.session.get(pfp_url) as resp:
                if resp.status != 200: return await self.warn(ctx, "Couldn't fetch profile picture")
                pfp_bytes = await resp.read()
            decoration_bytes = None
            if hasattr(user, "avatar_decoration") and user.avatar_decoration:
                async with self.session.get(user.avatar_decoration.url) as resp:
                    if resp.status == 200: decoration_bytes = await resp.read()
            mention_pattern = r'<@!?(\d+)>'
            mention_matches = list(re.finditer(mention_pattern, text))
            for match in mention_matches:
                user_id = int(match.group(1))
                try:
                    mentioned_user = await self.bot.fetch_user(user_id)
                    mention_text = f"@{mentioned_user.display_name or mentioned_user.name}"
                except:
                    mention_text = "@unknown"
                text = text.replace(match.group(0), mention_text, 1)
            img = await create_fake_discord_msg(user.display_name or user.name, pfp_bytes, text, decoration_bytes)
            with io.BytesIO() as image_binary:
                await asyncio.to_thread(img.save, image_binary, 'PNG')
                image_binary.seek(0)
                file = discord.File(fp=image_binary, filename='fakemessage.png')
                await ctx.send(file=file)
                img.close()
        except Exception as e:
            await self.warn(ctx, f"Failed to generate message: {str(e)}")

    @hybrid_command(name="math", description="Calculate mathematical expressions")
    async def math(self, ctx: commands.Context, expression: str):
        evaluator = SafeMathEvaluator()
        result = evaluator.evaluate_expression(expression)
        await ctx.send(f"{result}")

    @hybrid_command(name="asciify", description="Convert text to ASCII art")
    async def asciify(self, ctx: commands.Context, text: str, font: str = "3d-ascii"):
        if font not in fonts:
            return await self.warn(ctx, f"Invalid font. Available: {', '.join(fonts[:5])}...")
        try:
            ascii_art = await asyncio.to_thread(pyfiglet.figlet_format, text, font=font)
            await ctx.send(f"```fix\n{ascii_art}\n```")
        except Exception:
            await self.warn(ctx, "Text too long or error occurred.")

class BalanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.balances_file = BALANCE_FILE if 'BALANCE_FILE' in globals() else "balances.json"
        self.load_balances()

    def shorten_number(self, num):  
        suffixes = [
            (10**33, 'd'), (10**30, 'n'), (10**27, 'o'), (10**24, 's'),
            (10**21, 'se'), (10**18, 'qt'), (10**15, 'qd'), (10**12, 't'),
            (10**9,  'b'), (10**6,  'm'), (10**3,  'k'),
        ]
        for value, suffix in suffixes:
            if num >= value:
                shortened = num / value
                return f"{shortened:.1f}{suffix}" if shortened < 100 else f"{shortened:.0f}{suffix}"
        return str(num)

    def load_balances(self):
        try:
            with open(self.balances_file, "r") as f:
                self.balances = json.load(f)
        except FileNotFoundError:
            self.balances = {}
        

        for user_id, data in self.balances.items():
            if 'balance' not in data: data['balance'] = 0
            if 'bank' not in data: data['bank'] = 0
            if 'cooldowns' not in data: data['cooldowns'] = {}
            

            for key, val in data['cooldowns'].items():
                if isinstance(val, str):
                    try:
                        data['cooldowns'][key] = datetime.fromisoformat(val)
                    except ValueError:
                        pass

    def save_balances(self):

        data_to_save = {}
        for user_id, user_data in self.balances.items():
            user_copy = user_data.copy()
            cooldowns_copy = user_data.get('cooldowns', {}).copy()

            for k, v in cooldowns_copy.items():
                if isinstance(v, datetime):
                    cooldowns_copy[k] = v.isoformat()
            user_copy['cooldowns'] = cooldowns_copy
            data_to_save[user_id] = user_copy

        with open(self.balances_file, "w") as f:
            json.dump(data_to_save, f, indent=4)

    def get_balance(self, user_id):
        user_id = str(user_id)
        if user_id not in self.balances:
            self.balances[user_id] = {"balance": 0, "bank": 0, "cooldowns": {}}
        return self.balances[user_id]

    def update_balance(self, user_id, amount):
        user_id = str(user_id)
        if user_id not in self.balances:
            self.balances[user_id] = {"balance": 0, "bank": 0, "cooldowns": {}}
        self.balances[user_id]["balance"] += amount
        self.save_balances()

    @commands.command(aliases=["bal"])
    async def balance(self, ctx):
        """Shows the user's wallet and bank balance."""
        user_id = ctx.author.id
        data = self.get_balance(user_id)

        embed = discord.Embed(title=f"{ctx.author.name}'s Balance", color=discord.Color.green())
        embed.add_field(name="🪙 Wallet", value=f"{self.shorten_number(data['balance'])} coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"{self.shorten_number(data['bank'])} coins", inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def setbal(self, ctx, member: discord.Member, amount: int):
        if ctx.author.id not in whitelist:
            return await ctx.send("Denied.")
        user_id = str(member.id)
        if user_id not in self.balances:
            self.balances[user_id] = {"balance": 0, "bank": 0, "cooldowns": {}}
        self.balances[user_id]["balance"] = amount
        self.save_balances()
        shortened = self.shorten_number(amount)
        await ctx.send(f"Successfully set {member.name}'s balance to {shortened} coins.")

    @commands.command(aliases=["dep"])
    async def deposit(self, ctx, amount: str):
        user_id = ctx.author.id
        data = self.get_balance(user_id)

        if amount.lower() == "all":
            amount_val = data["balance"]
        else:
            try:
                amount_val = int(amount)
            except ValueError:
                return await ctx.send("❌ Invalid amount!")

        if amount_val <= 0 or amount_val > data["balance"]:
            return await ctx.send("❌ You don't have enough money!")

        data["balance"] -= amount_val
        data["bank"] += amount_val
        self.save_balances()
        await ctx.send(f"✅ Deposited {amount_val:,} coins into your bank!")

    @commands.command(aliases=["with"])
    async def withdraw(self, ctx, amount: str):
        user_id = ctx.author.id
        data = self.get_balance(user_id)

        if amount.lower() == "all":
            amount_val = data["bank"]
        else:
            try:
                amount_val = int(amount)
            except ValueError:
                return await ctx.send("❌ Invalid amount!")

        if amount_val <= 0 or amount_val > data["bank"]:
            return await ctx.send("❌ You don't have enough money in your bank!")

        data["balance"] += amount_val
        data["bank"] -= amount_val
        self.save_balances()
        await ctx.send(f"✅ Withdrawn {amount_val:,} coins from your bank!")

class RewardsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def balance_cog(self):
        return self.bot.get_cog("BalanceCog")

    def check_cooldown(self, user_id, reward_type, cooldown_time):
        user_data = self.balance_cog.get_balance(user_id)
        last_claim = user_data["cooldowns"].get(reward_type)

        if last_claim:
            if isinstance(last_claim, datetime):

                now = datetime.now()
                delta = (now - last_claim).total_seconds()
                if delta < cooldown_time:
                     return int(cooldown_time - delta)
            elif isinstance(last_claim, (int, float)):
                 if time.time() - last_claim < cooldown_time:
                    return int(cooldown_time - (time.time() - last_claim))
        return None

    def set_cooldown(self, user_id, reward_type):
        user_data = self.balance_cog.get_balance(user_id)
        user_data["cooldowns"][reward_type] = datetime.now()
        self.balance_cog.save_balances()

    @commands.command()
    async def daily(self, ctx):
        if not self.balance_cog: return await ctx.send("❌ Balance system offline.")
        cooldown = self.check_cooldown(ctx.author.id, "daily", 86400)
        if cooldown:
            return await ctx.send(f"❌ You can claim daily again in **{cooldown//3600}h {cooldown%3600//60}m**.")
        reward = random.randint(1000, 25000)
        self.balance_cog.update_balance(ctx.author.id, reward)
        self.set_cooldown(ctx.author.id, "daily")
        await ctx.send(f"✅ {ctx.author.mention}, you received **{reward}** coins as your daily reward!")

    @commands.command()
    async def weekly(self, ctx):
        if not self.balance_cog: return await ctx.send("❌ Balance system offline.")
        cooldown = self.check_cooldown(ctx.author.id, "weekly", 604800)
        if cooldown:
            return await ctx.send(f"❌ You can claim weekly again in **{cooldown//86400}d {cooldown%86400//3600}h**.")
        reward = random.randint(50000, 100000)
        self.balance_cog.update_balance(ctx.author.id, reward)
        self.set_cooldown(ctx.author.id, "weekly")
        await ctx.send(f"✅ {ctx.author.mention}, you received **{reward}** coins as your weekly reward!")

    @commands.command()
    async def monthly(self, ctx):
        if not self.balance_cog: return await ctx.send("❌ Balance system offline.")
        cooldown = self.check_cooldown(ctx.author.id, "monthly", 2592000)
        if cooldown:
            return await ctx.send(f"❌ You can claim monthly again in **{cooldown//86400}d {cooldown%86400//3600}h**.")
        reward = random.randint(150000, 1000000)
        self.balance_cog.update_balance(ctx.author.id, reward)
        self.set_cooldown(ctx.author.id, "monthly")
        await ctx.send(f"✅ {ctx.author.mention}, you received **{reward}** coins as your monthly reward!")

class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def hand_value(self, hand):
        value = sum(hand)
        aces = hand.count(11)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    @commands.command()
    async def blackjack(self, ctx, bet: str):
        balance_cog = self.bot.get_cog("BalanceCog")
        if not balance_cog: return await ctx.send("❌ Balance system is unavailable!")
        user_data = balance_cog.get_balance(ctx.author.id)
        balance = user_data["balance"]

        if bet.lower() == 'all':
            bet_val = balance
        else:
            try:
                bet_val = int(bet)
            except ValueError:
                return await ctx.send("❌ Invalid bet amount!")

        if bet_val <= 0 or bet_val > balance:
            return await ctx.send("❌ Invalid bet amount!")

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        def get_embed(show_dealer=False):
            if show_dealer:
                dealer_display = f"{dealer_hand} ({self.hand_value(dealer_hand)})"
            else:
                dealer_display = f"[{dealer_hand[0]}, '???']"
            embed = discord.Embed(title="Blackjack", color=discord.Color.blurple())
            embed.add_field(name="Your Hand", value=f"{player_hand} ({self.hand_value(player_hand)})", inline=False)
            embed.add_field(name="Dealer's Hand", value=dealer_display, inline=False)
            return embed

        class BlackjackButtons(discord.ui.View):
            def __init__(self, hand_value_func):
                super().__init__()
                self.hand_value = hand_value_func  

            @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
            async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
                player_hand.append(deck.pop())
                player_total = self.hand_value(player_hand)
                if player_total > 21:
                    self.stop()
                    balance_cog.update_balance(ctx.author.id, -bet_val)
                    await interaction.response.edit_message(content=f"💀 You busted! You lost {bet_val} coins.", view=None)
                else:
                    await interaction.response.edit_message(embed=get_embed(), view=self)

            @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
            async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
                self.stop()
                while self.hand_value(dealer_hand) < 17:
                    dealer_hand.append(deck.pop())
                dealer_total = self.hand_value(dealer_hand)
                player_total = self.hand_value(player_hand)
                if dealer_total > 21 or player_total > dealer_total:
                    balance_cog.update_balance(ctx.author.id, bet_val)
                    result = f"🎉 You win! You gained {bet_val} coins!"
                elif player_total < dealer_total:
                    balance_cog.update_balance(ctx.author.id, -bet_val)
                    result = f"💀 Dealer wins! You lost {bet_val} coins."
                else:
                    result = "😐 It's a tie! Your bet has been returned."
                await interaction.response.edit_message(embed=get_embed(show_dealer=True), content=result, view=None)

        await ctx.send(embed=get_embed(), view=BlackjackButtons(self.hand_value))

class GambleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def gamble(self, ctx, bet: str):
        balance_cog = self.bot.get_cog("BalanceCog")
        if not balance_cog: return await ctx.send("❌ Balance system is unavailable!")
        user_data = balance_cog.get_balance(ctx.author.id)
        balance = user_data["balance"]

        if bet.lower() == 'all':
            bet_val = balance
        else:
            try:
                bet_val = int(bet)
            except ValueError:
                return await ctx.send("❌ Invalid bet amount!")
        if bet_val <= 0 or bet_val > balance:
            return await ctx.send("❌ Invalid bet amount!")

        result = random.choice(["win", "lose"])
        if result == "win":
            balance_cog.update_balance(ctx.author.id, bet_val)
            result_message = f"🎉 You won! You gained {bet_val} coins!"
        else:
            balance_cog.update_balance(ctx.author.id, -bet_val)
            result_message = f"💀 You lost! You lost {bet_val} coins."
        await ctx.send(result_message)

class RobCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def balance_cog(self):
        return self.bot.get_cog("BalanceCog")

    @commands.command()
    async def rob(self, ctx, target: discord.Member):
        if not self.balance_cog: return await ctx.send("❌ Balance system unavailable.")
        
        user_data = self.balance_cog.get_balance(ctx.author.id)
        cooldown = user_data.get("cooldowns", {}).get("rob", None)

        if cooldown:
            time_left = cooldown - datetime.now()
            if time_left > timedelta(0):
                embed = discord.Embed(title="❌ Robbery Cooldown", description=f"Wait {time_left} before robbing again.", color=discord.Color.red())
                return await ctx.send(embed=embed)

        user_data["cooldowns"]["rob"] = datetime.now() + timedelta(minutes=30)
        self.balance_cog.save_balances()

        target_data = self.balance_cog.get_balance(target.id)
        if target_data["balance"] <= 0:
            return await ctx.send("❌ The target has no coins to rob!")

        stolen_amount = random.randint(50, 1000)
        if target_data["balance"] < stolen_amount:
            stolen_amount = target_data["balance"]


        target_data["balance"] -= stolen_amount
        user_data["balance"] += stolen_amount
        self.balance_cog.save_balances()

        embed = discord.Embed(title=f"💰 Robbery Successful!", description=f"You successfully robbed {target.name} and stole {stolen_amount:,} coins!", color=discord.Color.green())
        embed.add_field(name="Target's Remaining Balance", value=f"{target_data['balance']:,} coins", inline=True)
        embed.add_field(name="Your New Balance", value=f"{user_data['balance']:,} coins", inline=True)
        await ctx.send(embed=embed)

class BegCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def balance_cog(self):
        return self.bot.get_cog("BalanceCog")

    @commands.command()
    async def beg(self, ctx):
        if not self.balance_cog: return await ctx.send("❌ Balance system unavailable.")
        
        data = self.balance_cog.get_balance(ctx.author.id)
        cooldown = data.get("cooldowns", {}).get("beg", None)

        if cooldown:
            time_left = cooldown - datetime.now()
            if time_left > timedelta(0):
                embed = discord.Embed(title="❌ Begging Cooldown", description=f"Wait {time_left.seconds // 60}m {time_left.seconds % 60}s.", color=discord.Color.red())
                return await ctx.send(embed=embed)

        data["cooldowns"]["beg"] = datetime.now() + timedelta(minutes=5)
        self.balance_cog.save_balances()

        win = random.choice([True, False])

        
        if win:
            amount = random.randint(100, 25000)
            characters = {
                "lil bibby": f"Lil Bibby feels generous and gives you {amount:,} coins.",
                "pete": f"Pete hands you {amount:,} coins with a smile!",
                "juice wrld": f"Juice WRLD blesses you with {amount:,} coins.",
                "googly": f"Googly throws {amount:,} coins your way.",
                "dennis": f"Dennis feels sorry for you and gives you {amount:,} coins.",
                "daniel": f"Daniel gives you {amount:,} coins because you asked nicely.",
                "owner": f"Owner decides you're worthy and gives you {amount:,} coins.",
                "hounds": f"hounds gives you {amount:,} coins, but don't get used to it!",
                "arson": f"arson gives you {amount:,} coins out of pure kindness."
            }
            character = random.choice(list(characters.keys()))
            message = characters[character]
            self.balance_cog.update_balance(ctx.author.id, amount)

            embed = discord.Embed(title="💰 Begging Successful!", description=f"{message}", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            loss_message = random.choice([
                "Sorry, no one was willing to help you today.",
                "No coins for you today. Try again later!",
                "Better luck next time, no one gave you coins.",
                "It seems like you're out of luck today!"
            ])
            embed = discord.Embed(title="❌ Begging Unsuccessful", description=f"{ctx.author.name}, {loss_message}", color=discord.Color.red())
            await ctx.send(embed=embed)

class FunStuff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.responses = {
            'weed': [
                "BOMBOCLAT!!! {user} smoked some great pack with Jamaican homies and then ate some legendary street food!",
                "The OG Kush was too strong... {user} greened out and demanded a nap!",
                "You copped a $5 gram off your plug. Sadly it was laced with... fent??? RIP {user}.",
                "You took a rip off the bong but the glass exploded into your face. Skill issue, {user}.",
                "{user} hit a friend’s bong but the water tasted like baby oil? Wow, weird.",
                "{user} rolled a blunt so fat it could be used as a canoe paddle.",
                "{user} got couch‑locked and is now performing a lap dance for their sofa.",
                "{user} tried a ghost hit and forgot how to breathe for a solid minute.",
                "{user} smoked a joint thinking it was a cigar and is now in 5 fps.",
                "You hit a massive dab and coughed up an entire lung??? Wow no more breathing for {user}."
            ],
            'vape': [
                "{user} exhaled so much vape clouds the local weather report issued a fog warning.",
                "{user} tried to blow smoke rings but instead made a giant cloud dick. This dick desided that their ass was a great place to be.",
                "{user} took a hit and realized that they never liked nicotine. Why did you hit it?",
                "{user} realized their vape was empty and died of withdrawals.",
                "{user} discovered vape juice that tastes like cotton candy and is now diabetic af.",
                "{user} replaced the coil too late and just inhaled pure technology.",
                "{user} tried nic for the first time and now there lungs sound like a steam engine.",
                "{user} modded their vape to have pulse-pulse-pulse-pulse-pulse mode and now they got nic sick."
            ],
            'crack': [
                "{user} found a crack pipe in their aunt’s garage and immediately regretted it.",
                "{user} Googled “What is crack?” and got addicted before even trying it.",
                "{user} discovered fast money and even faster trips to regret.",
                "{user} tried a quick hit and ended up chasing the high for the rest of there life. Kids don't be like {user}",
                "{user} heard crack is a fun thing to try once and is now a meth-crack-heroin addicted junkie.",
                "{user} ended up watching hentai because they lost track of everything else."
            ],
            'salvia': [
                "{user} got teleported to Candyland and is bargaining with gingerbread men.",
                "{user} spoke fluent whale for a full minute.",
                "{user} thought they were a fish and tried to breathe underwater.",
                "{user} googled “Am I a chair?” and still isn’t sure.",
                "{user} saw the floor breathing and joined in.",
                "{user} hugged a lamp believing it was their long‑lost pet.",
                "{user} tasted colors and now prefers blueberry over red.",
                "{user} forgot they even had a body and asked their girlfriend if they were still tripping. You don't have a girlfriend, retard.",
                "{user} took a quick trip to Mars and forgot to return now you are forever fucked."
            ],
            'fent': [
                "{user} nodded off mid‑sentence and woke up in 2069.",
                "Fent hit so hard {user} levitated... straight into a trash can. Fuck ass fent user, kids stay away.",
                "{user} thought they were a vampire after one hit now {user} is afraid of sunlight and garlic bread.",
                "Fent made {user} fluent in the language of addiction.",
                "One tiny fent crumb and {user} achieved a god-like state then promptly forgot how to breathe. Well atleast he gets to meet god now..."
            ],
            'meth': [
                "{user} did meth and now thinks they can bench‑press a small country.",
                "Five minutes into meth, {user} reorganized their sock drawer by how gay the socks look.",
                "{user} on meth tried to cook breakfast and accidently made a nuke???",
                "{user} jittered so hard they single‑handedly made a small fucking earthquake.",
                "Meth had {user} convinced that they unraveled the stream of time. Marvel Loki type shi"
            ],
            'dmt': [
                "{user} smoked DMT and made friends with a talking kale chip. Hate those fucking vegans.",
                "DMT had {user} convinced their dog was a cosmic overlord who wanted to peg them.",
                "{user} melted into the couch and discovered the true meaning of spoons. When they came back they felt a spoon deep in their ass. How... just how???",
                "DMT took {user} to a dimension where gravity is optional and logic is a myth. Wait now your just retarded, sucks to suck.",
                "{user} punched through the veil of reality and found it was made of glitter... and baby oil, lots of it!"
            ],
            'default': [
                "Usage: `@collage smoke` `DMT` `Meth` `weed` `fent` `salvia` `crack` `vape`",
            ]
        }

    @commands.command(name='smoke')
    async def smoke(self, ctx, type: str):
        """Simulates smoking various substances with humorous outcomes."""
        key = type.lower() if type.lower() in self.responses else 'default'
        template = random.choice(self.responses[key])
        description = template.format(user=ctx.author.mention)
        embed = discord.Embed(title=" ", description=description, color=discord.Color.default() if key != 'default' else discord.Color.red())
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['8ball'])
    async def eightball(self, ctx, *, question: str):
        """Ask the magic 8ball a question."""
        responses = [
            "Yes", "No", "Maybe", "Definitely", "I don't know", "Ask again later",
            'It is certain', 'As I see it, yes', 'Cannot predict now',
            'My sources say no', 'Outlook not so good', 'Outlook good',
            'Do not count on it'
        ]
        response = random.choice(responses)
        embed = discord.Embed(title="🎱 8Ball", color=discord.Color.purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        embed.set_footer(text=f"Asked by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))
    await bot.add_cog(BalanceCog(bot))
    await bot.add_cog(RewardsCog(bot))
    await bot.add_cog(BlackjackCog(bot))
    await bot.add_cog(GambleCog(bot))
    await bot.add_cog(RobCog(bot))
    await bot.add_cog(BegCog(bot))
    await bot.add_cog(FunStuff(bot))