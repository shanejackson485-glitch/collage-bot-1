import discord
import os
import io
import asyncio
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TPE2, TRCK, TCON, APIC, ID3NoHeaderError
import json


COVER_PATHS = {
    "jute_sessions": r"D:\Covers\Sessions\.JUTE era.jpg",
    "aff_sessions": r"D:\Covers\Sessions\.AFF Era.png",
    "hih999_sessions": r"D:\Covers\Sessions\.HIH999 Era.png",
    "jw999_sessions": r"D:\Covers\Sessions\.JW999 Era.png",
    "bdm_sessions": r"D:\Covers\Sessions\.BDM Era.jpg",
    "nd_sessions": r"D:\Covers\Sessions\.ND Era.jpg",
    "gbgr_sessions": r"D:\Covers\Sessions\gbgr.xig.jpg",
    "wod_sessions": r"D:\Covers\Sessions\.WOD.png",
    "drfl_sessions": r"D:\Covers\Sessions\.DRFL.png",
    "out_sessions": r"D:\Covers\Sessions\outsiders.xig.jpg",
    "post_sessions": r"D:\Covers\Sessions\.Legends Never Die.png",
    "jute_era": r"D:\Covers\Era\.JUTE era.jpg",
    "aff_era": r"D:\Covers\Era\.AFF Era.png",
    "hih999_era": r"D:\Covers\Era\.HIH999 Era.png",
    "jw999_era": r"D:\Covers\Era\.JW999 Era.png",
    "bdm_era": r"D:\Covers\Era\.BDM Era.jpg",
    "nd_era": r"D:\Covers\Era\.ND Era.jpg",
    "gbgr_era": r"D:\Covers\Era\.GBGR.jpg",
    "wod_era": r"D:\Covers\Era\.WOD.png",
    "drfl_era": r"D:\Covers\Era\.DRFL.png",
    "out_era": r"D:\Covers\Era\.JTK era.png",
    "post_era": r"D:\Covers\Era\.Legends Never Die.png",
}


PRESETS = {

    "jute_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "JUICED UP THE EP (Sessions)",
        "year": 2014,
        "genre": "Hip-Hop/Rap",
        "cover": "jute_sessions"
    },
    "aff_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "affliction (Sessions)",
        "year": 2016,
        "genre": "Hip-Hop/Rap",
        "cover": "aff_sessions"
    },
    "hih999_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Heartbroken In Hollywood 9 9 9 (Sessions)",
        "year": 2016,
        "genre": "Hip-Hop/Rap",
        "cover": "hih999_sessions"
    },
    "jw999_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "JuiceWRLD 9 9 9 (Sessions)",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "jw999_sessions"
    },
    "bdm_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "BINGEDRINKINGMUSIC (Sessions)",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "bdm_sessions"
    },
    "nd_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "NOTHING'S DIFFERENT </3 (Sessions)",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "nd_sessions"
    },
    "gbgr_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Goodbye & Good Riddance (Sessions)",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "gbgr_sessions"
    },
    "wod_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "WRLD ON DRUGS (Sessions)",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "wod_sessions"
    },
    "drfl_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Death Race For Love (Sessions)",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "drfl_sessions"
    },
    "out_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Outsiders (Sessions)",
        "year": 2019,
        "genre": "Hip-Hop/Rap",
        "cover": "out_sessions"
    },
    "post_sessions": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Posthumous (Sessions)",
        "year": 2020,
        "genre": "Hip-Hop/Rap",
        "cover": "post_sessions"
    },

    "jute_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "JUICED UP THE EP Era",
        "year": 2014,
        "genre": "Hip-Hop/Rap",
        "cover": "jute_era"
    },
    "aff_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "affliction Era",
        "year": 2016,
        "genre": "Hip-Hop/Rap",
        "cover": "aff_era"
    },
    "hih999_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Heartbroken In Hollywood 9 9 9 Era",
        "year": 2016,
        "genre": "Hip-Hop/Rap",
        "cover": "hih999_era"
    },
    "jw999_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "JuiceWRLD 9 9 9 Era",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "jw999_era"
    },
    "bdm_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "BINGEDRINKINGMUSIC Era",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "bdm_era"
    },
    "nd_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "NOTHING'S DIFFERENT </3 Era",
        "year": 2017,
        "genre": "Hip-Hop/Rap",
        "cover": "nd_era"
    },
    "gbgr_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Goodbye & Good Riddance Era",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "gbgr_era"
    },
    "wod_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "WRLD ON DRUGS Era",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "wod_era"
    },
    "drfl_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Death Race For Love Era",
        "year": 2018,
        "genre": "Hip-Hop/Rap",
        "cover": "drfl_era"
    },
    "out_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Outsiders Era",
        "year": 2019,
        "genre": "Hip-Hop/Rap",
        "cover": "out_era"
    },
    "post_era": {
        "artist": "Juice WRLD",
        "album_artist": "Juice WRLD",
        "album": "Posthumous Era",
        "year": 2020,
        "genre": "Hip-Hop/Rap",
        "cover": "post_era"
    }
}

def check_premium_user(user_id):
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

class MetaTag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def apply_metadata_mp3(self, filepath: str, metadata: dict, artwork: Optional[bytes] = None):
        """Apply metadata to MP3 files using ID3 tags."""
        try:
            try:
                audio = ID3(filepath)
            except ID3NoHeaderError:
                audio = ID3()

            if metadata.get('title'):
                audio['TIT2'] = TIT2(encoding=3, text=metadata['title'])
            if metadata.get('artist'):
                audio['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
            if metadata.get('album'):
                audio['TALB'] = TALB(encoding=3, text=metadata['album'])
            if metadata.get('year'):
                audio['TDRC'] = TDRC(encoding=3, text=str(metadata['year']))
            if metadata.get('album_artist'):
                audio['TPE2'] = TPE2(encoding=3, text=metadata['album_artist'])
            if metadata.get('track_number'):
                audio['TRCK'] = TRCK(encoding=3, text=str(metadata['track_number']))
            if metadata.get('genre'):
                audio['TCON'] = TCON(encoding=3, text=metadata['genre'])
            

            audio.delall('APIC')
            
            if artwork:
                audio['APIC'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=artwork
                )

            audio.save(filepath, v2_version=3)
            return True, None
        except Exception as e:
            return False, str(e)

    def apply_metadata_m4a(self, filepath: str, metadata: dict, artwork: Optional[bytes] = None):
        """Apply metadata to M4A/MP4 files."""
        try:
            audio = MP4(filepath)

            if metadata.get('title'):
                audio['\xa9nam'] = metadata['title']
            if metadata.get('artist'):
                audio['\xa9ART'] = metadata['artist']
            if metadata.get('album'):
                audio['\xa9alb'] = metadata['album']
            if metadata.get('year'):
                audio['\xa9day'] = str(metadata['year'])
            if metadata.get('album_artist'):
                audio['aART'] = metadata['album_artist']
            if metadata.get('track_number'):
                audio['trkn'] = [(int(metadata['track_number']), 0)]
            if metadata.get('genre'):
                audio['\xa9gen'] = metadata['genre']
            

            if 'covr' in audio:
                del audio['covr']
            
            if artwork:
                audio['covr'] = [MP4Cover(artwork, imageformat=MP4Cover.FORMAT_JPEG)]

            audio.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def apply_metadata_flac(self, filepath: str, metadata: dict, artwork: Optional[bytes] = None):
        """Apply metadata to FLAC files."""
        try:
            audio = FLAC(filepath)

            if metadata.get('title'):
                audio['title'] = metadata['title']
            if metadata.get('artist'):
                audio['artist'] = metadata['artist']
            if metadata.get('album'):
                audio['album'] = metadata['album']
            if metadata.get('year'):
                audio['date'] = str(metadata['year'])
            if metadata.get('album_artist'):
                audio['albumartist'] = metadata['album_artist']
            if metadata.get('track_number'):
                audio['tracknumber'] = str(metadata['track_number'])
            if metadata.get('genre'):
                audio['genre'] = metadata['genre']


            audio.clear_pictures()
            

            if artwork:
                from mutagen.flac import Picture
                picture = Picture()
                picture.type = 3
                picture.mime = 'image/jpeg'
                picture.desc = 'Cover'
                picture.data = artwork
                audio.add_picture(picture)

            audio.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def apply_metadata(self, filepath: str, metadata: dict, artwork: Optional[bytes] = None):
        """Auto-detect file type and apply appropriate metadata."""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext in ['.mp3']:
            return self.apply_metadata_mp3(filepath, metadata, artwork)
        elif ext in ['.m4a', '.mp4']:
            return self.apply_metadata_m4a(filepath, metadata, artwork)
        elif ext in ['.flac']:
            return self.apply_metadata_flac(filepath, metadata, artwork)
        else:
            return False, f"Unsupported file format: {ext}"

    @commands.hybrid_command(
        name='metatag',
        with_app_command=True,
        description="Tag audio file metadata with Juice WRLD era presets."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(
        preset="Apply a Juice WRLD era preset",
        file="Audio file to tag (MP3, M4A, or FLAC)",
        title="Song title (leave empty to use filename)",
        track_number="Track number",
        rename_file="Rename the output file to match the title"
    )
    async def metatag(
        self,
        ctx: commands.Context,
        preset: Literal[
            'jute_sessions', 'aff_sessions', 'hih999_sessions', 'jw999_sessions', 
            'bdm_sessions', 'nd_sessions', 'gbgr_sessions', 'wod_sessions', 
            'drfl_sessions', 'out_sessions', 'post_sessions',
            'jute_era', 'aff_era', 'hih999_era', 'jw999_era', 
            'bdm_era', 'nd_era', 'gbgr_era', 'wod_era', 
            'drfl_era', 'out_era', 'post_era'
        ],
        file: discord.Attachment,
        title: Optional[str] = None,
        track_number: Optional[int] = None,
        rename_file: bool = False
    ):
        """Tag audio file metadata with Juice WRLD era presets. Attach an MP3/M4A/FLAC file to tag it."""
        

        if not check_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by using the `@collage premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return


        attachment = file if file else (ctx.message.attachments[0] if ctx.message.attachments else None)

        if not attachment:
            embed = discord.Embed(
                title="❌ No Audio File Attached",
                description="Please attach an audio file (MP3, M4A, or FLAC) to tag.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Available Presets",
                value="**Sessions:** `jute_sessions`, `aff_sessions`, `hih999_sessions`, `jw999_sessions`, `bdm_sessions`, `nd_sessions`, `gbgr_sessions`, `wod_sessions`, `drfl_sessions`, `out_sessions`, `post_sessions`\n\n**Era:** `jute_era`, `aff_era`, `hih999_era`, `jw999_era`, `bdm_era`, `nd_era`, `gbgr_era`, `wod_era`, `drfl_era`, `out_era`, `post_era`",
                inline=False
            )
            embed.add_field(
                name="Example",
                value="Attach a file and use: `/metatag preset:gbgr_sessions title:\"Righteous\" track_number:5`",
                inline=False
            )
            await ctx.send(embed=embed, ephemeral=True)
            return


        file_ext = os.path.splitext(attachment.filename)[1].lower()
        if file_ext not in ['.mp3', '.m4a', '.mp4', '.flac']:
            embed = discord.Embed(
                title="❌ Unsupported File Format",
                description=f"The file format `{file_ext}` is not supported. Please use MP3, M4A, or FLAC.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return


        await ctx.defer()


        if preset not in PRESETS:
            embed = discord.Embed(
                title="❌ Invalid Preset",
                description=f"The preset `{preset}` is not valid.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        metadata = PRESETS[preset].copy()
        cover_key = metadata.pop('cover', None)
        

        if title:
            base_title = title
        else:

            base_title = os.path.splitext(attachment.filename)[0]
        

        metadata['title'] = base_title
        

        if rename_file:
            final_filename = f"{base_title}{file_ext}"
        else:
            final_filename = attachment.filename
        

        if track_number:
            metadata['track_number'] = track_number

        try:

            file_data = await attachment.read()
            temp_filepath = f"temp_media/{attachment.filename}"
            

            os.makedirs("temp_media", exist_ok=True)
            

            with open(temp_filepath, 'wb') as f:
                f.write(file_data)


            artwork_data = None
            if cover_key and COVER_PATHS.get(cover_key):
                cover_path = COVER_PATHS[cover_key]
                if os.path.exists(cover_path):
                    with open(cover_path, 'rb') as cover_file:
                        artwork_data = cover_file.read()


            success, error = self.apply_metadata(temp_filepath, metadata, artwork_data)

            if not success:
                embed = discord.Embed(
                    title="❌ Failed to Apply Metadata",
                    description=f"An error occurred: {error}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                os.remove(temp_filepath)
                return


            embed = discord.Embed(
                title="✅ Metadata Applied Successfully",
                description=f"**Preset:** `{preset}`\n**Output File:** `{final_filename}`",
                color=discord.Color.green()
            )
            

            metadata_display = {
                "Title": metadata.get('title'),
                "Artist": metadata.get('artist'),
                "Album": metadata.get('album'),
                "Year": metadata.get('year'),
                "Genre": metadata.get('genre'),
            }
            if metadata.get('track_number'):
                metadata_display["Track #"] = metadata.get('track_number')
            
            metadata_text = "\n".join([f"**{key}:** {value}" for key, value in metadata_display.items() if value])
            embed.add_field(name="📝 Applied Tags", value=metadata_text, inline=False)
            
            if artwork_data:
                embed.add_field(name="🎨 Cover Art", value="✅ Applied from preset", inline=False)
            else:
                embed.add_field(name="🎨 Cover Art", value="⚠️ No cover art configured for this preset", inline=False)


            with open(temp_filepath, 'rb') as f:
                file = discord.File(f, filename=final_filename)
                await ctx.send(embed=embed, file=file)


            os.remove(temp_filepath)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Processing File",
                description=f"An unexpected error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

    @commands.hybrid_command(
        name='metatag_presets',
        with_app_command=True,
        description="View all available Juice WRLD era presets."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def metatag_presets(self, ctx: commands.Context):
        """View all available Juice WRLD era presets."""
        
        if not check_premium_user(ctx.author.id):
            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description="You can learn more about premium by using the `@collage premium` command.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🎵 Juice WRLD Era Metadata Presets",
            description="All presets include: **Artist:** Juice WRLD | **Genre:** Hip-Hop/Rap",
            color=0x9B59B6
        )


        sessions_text = (
            "🎧 `jute_sessions` - JUICED UP THE EP (2014)\n"
            "🎧 `aff_sessions` - affliction (2016)\n"
            "🎧 `hih999_sessions` - Heartbroken In Hollywood 9 9 9 (2016)\n"
            "🎧 `jw999_sessions` - JuiceWRLD 9 9 9 (2017)\n"
            "🎧 `bdm_sessions` - BINGEDRINKINGMUSIC (2017)\n"
            "🎧 `nd_sessions` - NOTHING'S DIFFERENT </3 (2017)\n"
            "🎧 `gbgr_sessions` - Goodbye & Good Riddance (2018)\n"
            "🎧 `wod_sessions` - WRLD ON DRUGS (2018)\n"
            "🎧 `drfl_sessions` - Death Race For Love (2018)\n"
            "🎧 `out_sessions` - Outsiders (2019)\n"
            "🎧 `post_sessions` - Posthumous (2020)"
        )
        embed.add_field(
            name="📀 Sessions Presets",
            value=sessions_text,
            inline=False
        )


        era_text = (
            "⏳ `jute_era` - JUICED UP THE EP Era (2014)\n"
            "⏳ `aff_era` - affliction Era (2016)\n"
            "⏳ `hih999_era` - Heartbroken In Hollywood 9 9 9 Era (2016)\n"
            "⏳ `jw999_era` - JuiceWRLD 9 9 9 Era (2017)\n"
            "⏳ `bdm_era` - BINGEDRINKINGMUSIC Era (2017)\n"
            "⏳ `nd_era` - NOTHING'S DIFFERENT </3 Era (2017)\n"
            "⏳ `gbgr_era` - Goodbye & Good Riddance Era (2018)\n"
            "⏳ `wod_era` - WRLD ON DRUGS Era (2018)\n"
            "⏳ `drfl_era` - Death Race For Love Era (2018)\n"
            "⏳ `out_era` - Outsiders Era (2019)\n"
            "⏳ `post_era` - Posthumous Era (2020)"
        )
        embed.add_field(
            name="🕰️ Era Presets",
            value=era_text,
            inline=False
        )

        embed.add_field(
            name="📝 Usage",
            value=(
                "Attach an audio file and use:\n"
                "`/metatag preset:<preset_name> title:\"Song Name\"`\n\n"
                "**Options:**\n"
                "• `title` - Set song title (or leave blank to use filename)\n"
                "• `track_number` - Set track number\n"
                "• `rename_file` - Rename output file to match title"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📎 Examples",
            value=(
                "`/metatag preset:gbgr_sessions title:\"Righteous\"`\n"
                "`/metatag preset:drfl_era title:\"Robbery\" track_number:3`\n"
                "`/metatag preset:post_sessions title:\"Life's A Mess\" rename_file:True`"
            ),
            inline=False
        )
        
        embed.set_footer(text="🎨 Cover art automatically applied when configured")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MetaTag(bot))
