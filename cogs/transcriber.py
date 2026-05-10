import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import io
from pydub import AudioSegment
from typing import Optional


GROQ_API_KEY = "" 
TRANSCRIPTION_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_DURATION_MS = 180000

class TranscribeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        
        self.ctx_menu = app_commands.ContextMenu(
            name="Transcribe",
            callback=self.transcribe_ctx_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
        asyncio.create_task(self.session.close())


    async def _process_transcription(self, ctx, interaction, attachment_url):
        if interaction:
            await interaction.response.defer(thinking=True, ephemeral=False)
        else:
            await ctx.typing()

        try:
            async with self.session.get(attachment_url) as response:
                if response.status != 200: raise Exception
                audio_data = await response.read()
        except:
            msg = "❌ Error downloading file."
            return await interaction.followup.send(msg) if interaction else await ctx.send(msg)

        def _convert(file_data):
            try:
                segment = AudioSegment.from_file(io.BytesIO(file_data))
            except: return None, None
            
            notice = ""
            if len(segment) > MAX_DURATION_MS:
                segment = segment[:MAX_DURATION_MS]
                notice = f"\n-# ⚠️ Audio trimmed to {int(MAX_DURATION_MS/1000)}s."

            out = io.BytesIO()
            segment.export(out, format='mp3')
            out.seek(0)
            return out, notice

        audio_file, warning = await asyncio.to_thread(_convert, audio_data)

        if not audio_file:
            msg = "❌ Invalid audio file."
            return await interaction.followup.send(msg) if interaction else await ctx.send(msg)

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        data = aiohttp.FormData()
        data.add_field('file', audio_file, filename='audio.mp3', content_type='audio/mpeg')
        data.add_field('model', 'whisper-large-v3')
        data.add_field('response_format', 'json')

        try:
            async with self.session.post(TRANSCRIPTION_API_URL, headers=headers, data=data) as r:
                if r.status != 200: raise Exception(f"Status: {r.status}")
                res = await r.json()
        except:
            msg = "❌ API Error."
            return await interaction.followup.send(msg) if interaction else await ctx.send(msg)

        text = res.get('text', '')
        if not text: text = "*(No speech detected)*"
        
        limit = 1990 - len(warning)
        if len(text) > limit: text = text[:limit] + "..."
        
        final = f"{text}{warning}"
        if interaction: await interaction.followup.send(final)
        else: await ctx.send(final)



    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def transcribe_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        if not message.attachments:
            return await interaction.response.send_message("❌ No attachment found.", ephemeral=True)
        await self._process_transcription(None, interaction, message.attachments[0].url)

    @commands.hybrid_command(name="transcribe", description="Transcribe an audio file.")
    @app_commands.describe(file="Upload a file to transcribe (Optional)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def transcribe_command(self, ctx, file: Optional[discord.Attachment] = None):
        url = None
        
        if file:
            url = file.url
            
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].url
            
        elif ctx.message.reference and ctx.message.reference.resolved:
            ref = ctx.message.reference.resolved
            if isinstance(ref, discord.Message) and ref.attachments:
                url = ref.attachments[0].url

        if not url:
            return await ctx.send("❌ Please upload a file or reply to a voice message.", ephemeral=True)
        interaction = ctx.interaction if ctx.interaction else None
        await self._process_transcription(ctx, interaction, url)

async def setup(bot):
    await bot.add_cog(TranscribeCog(bot))