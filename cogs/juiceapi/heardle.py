import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import os
import json
import re
import uuid
import shutil
import random
from .helpers import api_client





STATS_FILE = "data/Heardle/stats.json"


if not os.path.exists("data/Heardle"):
    os.makedirs("data/Heardle")

def load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_stats(data):


    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_heardle_stats(user_id: int, won: bool, guesses_taken: int):
    data = load_stats()
    uid = str(user_id)
    
    if uid not in data:
        data[uid] = {
            "wins": 0, "losses": 0, "games_played": 0,
            "current_streak": 0, "max_streak": 0,
            "total_guesses": 0
        }
    
    stats = data[uid]
    stats["games_played"] += 1
    
    if won:
        stats["wins"] += 1
        stats["current_streak"] += 1
        stats["total_guesses"] += guesses_taken
        if stats["current_streak"] > stats["max_streak"]:
            stats["max_streak"] = stats["current_streak"]
    else:
        stats["losses"] += 1
        stats["current_streak"] = 0
        
    save_stats(data)




active_heardle_games = {}





active_heardle_games = {}



class GuessModal(ui.Modal, title="Guess the Song"):
    name = ui.TextInput(
        label="Song Name",
        placeholder="Type your guess here...",
        min_length=1,
        max_length=100
    )

    def __init__(self, view_ref):
        super().__init__()
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        self.view_ref.user_guess = self.name.value
        self.view_ref.action = "guess"
        self.view_ref.stop()
        await interaction.response.defer()

class HeardleControls(ui.View):
    def __init__(self, author_id, timeout=45):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.user_guess = None
        self.action = "timeout"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
            return False
        return True

    @ui.button(label="📝 Guess", style=discord.ButtonStyle.success)
    async def guess_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(GuessModal(self))

    @ui.button(label="⏩ Skip", style=discord.ButtonStyle.primary)
    async def skip_btn(self, interaction: discord.Interaction, button: ui.Button):
        self.action = "skip"
        self.stop()
        await interaction.response.defer()

    @ui.button(label="🛑 Give Up", style=discord.ButtonStyle.danger)
    async def quit_btn(self, interaction: discord.Interaction, button: ui.Button):
        self.action = "quit"
        self.stop()
        await interaction.response.defer()



class HeardleGame:
    def __init__(self, ctx, bot, song_data, full_audio_path):
        self.ctx = ctx
        self.bot = bot
        self.song_data = song_data
        self.full_audio_remote_path = full_audio_path
        self.guesses = 0
        self.segment_length = 1
        self.max_segments = 6
        self.is_active = True
        
        self.game_id = str(uuid.uuid4())
        self.base_filename = f"heardle_{self.game_id}"
        
        self.temp_files = [] 
        self.local_audio_path = f"{self.base_filename}_full.mp3"
        self.temp_avatar_file = f"{self.base_filename}_avatar.png"
        self.game_messages = []
        
        self.valid_answers = self.generate_valid_answers(song_data)

    def normalize_text(self, text):
        if not text: return ""
        return re.sub(r'[^a-z0-9]', '', text.lower())

    def generate_valid_answers(self, song_data):
        answers = set()
        sources = []
        if 'name' in song_data: sources.append(song_data['name'])
        if 'track_titles' in song_data and isinstance(song_data['track_titles'], list):
            sources.extend(song_data['track_titles'])

        for source in sources:
            if not isinstance(source, str): continue
            answers.add(source)

            clean_name = re.sub(r"[\(\[].*?[\)\]]", "", source).strip()
            if clean_name and clean_name != source: answers.add(clean_name)

            if "feat" in source.lower() or "ft." in source.lower():
                no_feat = re.split(r"feat\.?|ft\.?", source, flags=re.IGNORECASE)[0].strip()
                if no_feat: answers.add(no_feat)

        return list(answers)

    def register_temp_file(self, path):
        if path not in self.temp_files: self.temp_files.append(path)
        return path

    def cleanup(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

    async def delete_clips(self):
        """Waits 5 seconds and deletes all video messages."""
        await asyncio.sleep(5)
        for msg in self.game_messages:
            try:
                await msg.delete()
            except:
                pass

    async def download_resources(self):
        avatar = self.ctx.author.avatar or self.ctx.author.default_avatar
        await avatar.save(self.temp_avatar_file)
        self.register_temp_file(self.temp_avatar_file)


        audio_url = api_client.get_download_url(self.full_audio_remote_path)
        
        if not audio_url:
            raise ValueError("Could not get audio URL from API.")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", audio_url, "-c:a", "libmp3lame", self.local_audio_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        if not os.path.exists(self.local_audio_path):
            raise ValueError("FFmpeg failed to download audio file.")
            
        self.register_temp_file(self.local_audio_path)

    async def generate_clip(self, duration):
        output_file = f"{self.base_filename}_clip_{duration}s.mp4"

        start_offset = 30 

        command = [
            "ffmpeg", "-y",
            "-ss", str(start_offset),
            "-i", self.local_audio_path,
            "-i", self.temp_avatar_file,
            "-filter_complex",
            "[1:v]scale=640:640, crop=640:360, loop=loop=-1:size=1:start=0[v]",
            "-map", "[v]",
            "-map", "0:a",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            output_file
        ]

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            print(f"FFmpeg Error: {stderr.decode()}")
            raise Exception("Video generation failed.")

        self.register_temp_file(output_file)
        return output_file

    async def start_game(self):
        try:
            await self.ctx.send(f"🎧 **Heardle Loading...** Downloading assets.")
            await self.download_resources()
            
            while self.is_active and self.guesses < self.max_segments:
                clip_path = await self.generate_clip(self.segment_length)
                view = HeardleControls(self.ctx.author.id, timeout=45)
                
                file = discord.File(clip_path, filename="heardle.mp4")
                msg = await self.ctx.send(
                    content=f"🎵 **Round {self.guesses + 1}/{self.max_segments}** - Clip length: `{self.segment_length}s`",
                    file=file, view=view
                )

                self.game_messages.append(msg)

                timed_out = await view.wait()
                for child in view.children: child.disabled = True
                await msg.edit(view=view)

                if timed_out:
                    await self.ctx.send("⏰ Time's up for this round!")
                    self.guesses += 1; self.segment_length += 1; continue

                if view.action == "quit":
                    update_heardle_stats(self.ctx.author.id, False, self.guesses + 1)
                    await self.ctx.send(f"🛑 Game ended. The song was **{self.song_data['name']}**.")
                    return 
                elif view.action == "skip":
                    await self.ctx.send("⏩ Skipped this round.")
                    self.guesses += 1; self.segment_length += 1; continue
                elif view.action == "guess":
                    guess = view.user_guess
                    if any(self.normalize_text(guess) == self.normalize_text(a) for a in self.valid_answers):
                        update_heardle_stats(self.ctx.author.id, True, self.guesses + 1)
                        await self.ctx.send(f"🎉 **CORRECT!** The song was **{self.song_data['name']}**.\nYou got it in {self.guesses + 1} tries!")
                        self.is_active = False
                        return
                    else:
                        await self.ctx.send(f"❌ `{guess}` is incorrect.")
                        self.guesses += 1; self.segment_length += 1

            if self.is_active:
                update_heardle_stats(self.ctx.author.id, False, self.max_segments)
                await self.ctx.send(f"💔 **Game Over!** You ran out of guesses.\nThe song was **{self.song_data['name']}**.")

        except Exception as e:
            print(f"Heardle Crash: {e}")
            await self.ctx.send(f"⚠️ An error occurred: `{e}`")
        finally:
            self.cleanup()
            await self.delete_clips()
            key = (self.ctx.guild.id, self.ctx.author.id)
            if key in active_heardle_games: del active_heardle_games[key]



class HeardleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not shutil.which("ffmpeg"):
            print("⚠️ WARNING: FFmpeg is missing. Heardle will not work.")

    @commands.hybrid_command(name="heardle", description="Play Juice WRLD Heardle!")
    async def heardle(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else 0
        key = (ctx.guild.id, ctx.author.id)
        if key in active_heardle_games:
            return await ctx.send("❌ You already have a Heardle game running!", ephemeral=True)

        await ctx.defer()
        
        song = None
        full_audio_path = None


        for _ in range(5):
            s = await api_client.get_random_song()
            if not s: continue


            raw_name = s.get("name", "")
            search_query = re.sub(r"[\(\[].*?[\)\]]", "", raw_name).strip()




            try:
                data = await api_client.get("files/browse", params={"search": search_query})
            except Exception:
                data = None

            if data and data.get("items"):
                for item in data["items"]:
                    if item["type"] == "file" and item["path"].lower().endswith(('.mp3', '.m4a', '.wav', '.flac')):
                        full_audio_path = item["path"]
                        break
            
            if full_audio_path:
                song = s
                break

        if not song:
            return await ctx.send("❌ Couldn't find a playable song (API did not return valid files).")

        game = HeardleGame(ctx, self.bot, song, full_audio_path)
        active_heardle_games[key] = game
        await game.start_game()



class LeaderboardView(ui.View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pages = pages
        self.current = 0
        self.update_buttons()

    def update_buttons(self):
        self.prev.disabled = self.current == 0
        self.next.disabled = self.current == len(self.pages) - 1

    @ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        self.current -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        self.current += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.ctx.author.id

class HeardleStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_bar(self, percentage):
        """Creates a visual progress bar [🟩🟩🟩⬜⬜]"""
        length = 10
        filled = int((percentage / 100) * length)
        bar = "🟩" * filled + "⬛" * (length - filled)
        return bar

    @commands.hybrid_command(name="hstats", description="View your Heardle statistics.")
    async def hstats(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        data = load_stats()
        uid = str(user.id)

        if uid not in data:
            return await ctx.send(f"❌ {user.display_name} has not played Heardle yet.", ephemeral=True)

        s = data[uid]
        wins = s.get("wins", 0)
        losses = s.get("losses", 0)
        streak = s.get("current_streak", 0)
        max_streak = s.get("max_streak", 0)
        total = wins + losses
        

        win_rate = (wins / total * 100) if total > 0 else 0
        bar = self.create_bar(win_rate)

        embed = discord.Embed(title=f"📊 Heardle Stats: {user.display_name}", color=0x1DB954)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="🏆 Wins", value=f"**{wins}**", inline=True)
        embed.add_field(name="💀 Losses", value=f"{losses}", inline=True)
        embed.add_field(name="Total Games", value=f"{total}", inline=True)
        
        embed.add_field(name="🔥 Current Streak", value=f"**{streak}**", inline=True)
        embed.add_field(name="⚡ Best Streak", value=f"{max_streak}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(name=f"Win Rate ({round(win_rate, 1)}%)", value=f"`{bar}`", inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="htop", aliases=["hleaderboard"], description="Global Heardle Leaderboard.")
    async def htop(self, ctx):
        data = load_stats()
        if not data:
            return await ctx.send("No stats recorded yet.")



        leaderboard = []
        for uid, s in data.items():
            wins = s.get("wins", 0)
            losses = s.get("losses", 0)
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            leaderboard.append((uid, wins, win_rate, s.get("current_streak", 0)))


        leaderboard.sort(key=lambda x: (x[1], x[2]), reverse=True)

        pages = []
        chunk_size = 10
        
        for i in range(0, len(leaderboard), chunk_size):
            chunk = leaderboard[i:i + chunk_size]
            embed = discord.Embed(title="🏆 Global Heardle Leaderboard", color=0xFFD700)
            
            desc = ""
            for idx, entry in enumerate(chunk):
                uid, wins, rate, streak = entry
                rank = i + idx + 1
                

                if rank == 1: badge = "🥇"
                elif rank == 2: badge = "🥈"
                elif rank == 3: badge = "🥉"
                else: badge = f"`#{rank}`"


                user = self.bot.get_user(int(uid))
                name = user.name if user else "Unknown User"
                

                desc += f"{badge} **{name}**\n└ 🏆 {wins} Wins • {round(rate)}% WR • 🔥 {streak}\n\n"

            embed.description = desc
            embed.set_footer(text=f"Page {len(pages) + 1} • Top 100 Players")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            view = LeaderboardView(ctx, pages)
            await ctx.send(embed=pages[0], view=view)

async def setup(bot):
    await bot.add_cog(HeardleCog(bot))
    await bot.add_cog(HeardleStatsCog(bot))