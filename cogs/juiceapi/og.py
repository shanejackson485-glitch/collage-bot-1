import discord
from discord.ext import commands
from discord import app_commands
import re
from datetime import datetime, timedelta


from .helpers import api_client, rate_limiter, ERA_MAPPING





class OGSelectView(discord.ui.View):
    def __init__(self, music_cog, ctx, results):
        super().__init__()
        self.music_cog = music_cog
        self.ctx = ctx
        
        options = []
        for i, song in enumerate(results[:25]):
            era_code = None
            era_raw = song.get('era')
            
            if era_raw:
                if isinstance(era_raw, dict):
                    era_code = era_raw.get('name') 
                elif isinstance(era_raw, str):
                    era_code = era_raw
            
            description_text = f"Type: {song.get('type', 'N/A')}"
            
            if era_code:
                clean_code = str(era_code).strip().upper() 
                
                if clean_code in ERA_MAPPING:
                    era_name = ERA_MAPPING[clean_code]['name_long']
                    description_text = f"Era: {era_name}"
                else:
                    description_text = f"Era: {clean_code}" 

            alt_titles_part = (
                f" [{', '.join(song.get('track_titles', [])[1:])}]" 
                if len(song.get('track_titles', [])) > 1 else ""
            )
            
            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {song['name']}{alt_titles_part}"[:100],
                    value=song['public_id'],
                    description=description_text
                )
            )

        select = discord.ui.Select(
            placeholder="Choose which song's OG link to send...",
            options=options 
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):

        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return

        selected_id = interaction.data['values'][0]
        

        try:
            rate_limiter.check(interaction.user.id)
        except commands.CommandOnCooldown as e:
            await self.music_cog.getog_error(self.ctx, e)
            return


        await interaction.response.defer()


        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass

        full_song = await api_client.get_song_by_id(selected_id)
        og_paths = await self.music_cog.resolve_full_path_og(full_song)

        track_titles = full_song.get('track_titles', [])
        main_title = track_titles[0] if track_titles else full_song['name']
        alt_titles = track_titles[1:]

        if alt_titles:
            alt_title_string = " | ".join(alt_titles)
            description_content = (
                f"**{alt_title_string}**\n\nDownload links are provided via individual buttons below."
            )
        else:
            description_content = "Download links are provided via individual buttons below."

        era_display = None
        embed_color = discord.Color.from_rgb(44, 47, 51)
        era_cover_url = None

        era_raw = full_song.get('era')
        era_code = None

        if era_raw:
            if isinstance(era_raw, dict):
                era_code = era_raw.get('name')
            elif isinstance(era_raw, str):
                era_code = era_raw

            if era_code:
                clean_code = str(era_code).strip().upper()

                if clean_code in ERA_MAPPING:
                    era_data = ERA_MAPPING[clean_code]
                    era_display = era_data['name_long']
                    embed_color = era_data['color']
                    era_cover_url = era_data.get('cover_url')
                else:
                    era_display = clean_code
                    embed_color = discord.Color.from_rgb(100, 100, 100)

        link_view = discord.ui.View()
        all_files_list = []

        embed = discord.Embed(
            title=f"{main_title}",
            description=description_content,
            color=embed_color
        )

        if era_display:
            embed.add_field(name="Era", value=era_display, inline=True)
        if full_song.get('length'):
            embed.add_field(name="Length", value=full_song['length'], inline=True)
        if full_song.get('producers'):
            embed.add_field(name="Producers", value=full_song['producers'], inline=True)

        if full_song.get('record_dates'):
            record_date_val = self.music_cog.format_record_date(full_song['record_dates'])
            if record_date_val:
                embed.add_field(name="Record Date", value=record_date_val, inline=False)

        if full_song.get('date_leaked'):
            surfaced_date_val = self.music_cog.format_surfaced_date(full_song['date_leaked'])
            if surfaced_date_val:
                embed.add_field(name="Surfaced", value=surfaced_date_val, inline=False)

        for path in og_paths:
            download_url = api_client.get_download_url(path)
            ext = path.split('.')[-1].upper()
            fname = path.rsplit("/", 1)[-1]

            button_label = f"[{ext}] {fname.rsplit('.', 1)[0]}"

            link_view.add_item(
                discord.ui.Button(
                    label=button_label,
                    url=download_url,
                    style=discord.ButtonStyle.link
                )
            )

            all_files_list.append(f"`{fname}`")

        if all_files_list:
            embed.add_field(
                name="Included Files",
                value=(
                    '\n'.join(all_files_list[:20]) +
                    ('\n...' if len(all_files_list) > 20 else '')
                ),
                inline=False
            )

        embed.set_footer(
            text=f"Requested by {self.ctx.author.display_name}",
            icon_url=self.ctx.author.display_avatar.url
        )

        if era_cover_url:
            embed.set_thumbnail(url=era_cover_url)
        elif img := full_song.get('image_url'):
            embed.set_thumbnail(url=f"https://juicewrldapi.com{img}")


        await self.ctx.send(embed=embed, view=link_view)

        self.stop()

class OriginalFiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    def format_record_date(self, record_dates_str):
        if not record_dates_str:
            return None
            
        lines = []
        

        normalized_str = record_dates_str.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
        

        parts = re.split(r'(File Exported|Exported)', normalized_str, flags=re.IGNORECASE, maxsplit=1)
        

        record_date = parts[0].strip()
        

        record_date = re.sub(r'^Recorded\s*', '', record_date, flags=re.IGNORECASE).strip().strip('.')
        
        if record_date:
            lines.append(f"Recorded: **{record_date}**")
            

        if len(parts) >= 3:
            export_content = parts[2].strip()
            export_date = export_content.strip().strip('.')
            export_line = f"{parts[1].strip()}: **{export_date}**"
            lines.append(export_line)
                
        return '\n'.join(lines) if lines else None


    def format_surfaced_date(self, date_leaked_str):
        if not date_leaked_str:
            return None
            
        surfaced_date = date_leaked_str.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
        surfaced_date = re.sub(r'^Surfaced\s*/*\s*', '', surfaced_date, flags=re.IGNORECASE).strip()
        surfaced_date = surfaced_date.strip('.').strip()
        
        return f"**{surfaced_date}**" if surfaced_date else None

    async def resolve_full_path_og(self, song, AUDIO_EXTENSIONS=('.mp3', '.wav', '.flac', '.m4a')):
        """
        Finds the OG file by matching against the JuiceWRLD API 'file_names' field.
        Only returns files inside the 'Original Files' directory.
        """
        if not song:
            return []

        STRICT_OG_PREFIX = "Original Files"


        expected = song.get("file_names", "")
        

        if isinstance(expected, list):
            if expected:

                expected = expected[0]
            else:
                expected = ""


        if not expected:

            expected = song.get("name", "")



        if isinstance(expected, str) and '\n' in expected:

            if "File Name:" in expected:
                try:
                    file_name_line = [line for line in expected.split('\n') if "File Name:" in line][0]
                    expected = file_name_line.replace("File Name:", "").strip()
                except IndexError:
                    expected = song.get("name", "")
            else:
                expected = song.get("name", "")
        


        expected = str(expected)
        expected_norm = expected.lower().strip()
        expected_norm = re.sub(r'\s+', ' ', expected_norm)
        expected_compact = re.sub(r'[\s\-–—‐‒―]', '', expected_norm)




        search_query_parts = expected_norm.split()[:3]
        search_query = ' '.join(search_query_parts)

        data = await api_client.browse_files(params={
            'search': search_query  
        })

        if not data or "items" not in data:

            return []

        matches = []
        
        ALLOWED_COMPACT_SUFFIXES = ('', '.l', '.r')


        for item in data["items"]:
            if item["type"] != "file":
                continue

            path = item["path"]


            if not path.startswith(STRICT_OG_PREFIX):
                continue

            fname = path.rsplit("/", 1)[-1]


            if not fname.lower().endswith(AUDIO_EXTENSIONS):
                continue


            actual = re.sub(r'\.(mp3|wav|flac|m4a)$', '', fname, flags=re.IGNORECASE)
            actual_norm = actual.lower().strip()
            actual_norm = re.sub(r'\s+', ' ', actual_norm)
            actual_compact = re.sub(r'[\s\-–—‐‒―]', '', actual_norm)


            if actual_norm == expected_norm:
                matches.append(path)
                continue


            if actual_compact.startswith(expected_compact):
                suffix_part = actual_compact[len(expected_compact):]
                

                if suffix_part in ALLOWED_COMPACT_SUFFIXES:
                    matches.append(path)
                    continue


        return matches




    @commands.hybrid_command(name="ogfile", description="Sends the direct download link(s) for the Original File version(s) of a track.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def getog(self, ctx, *, query: str):
        


        try:
            rate_limiter.check(ctx.author.id) 
        except commands.CommandOnCooldown as e:

            await self.getog_error(ctx, e)
            return


        await ctx.defer()
        

        data = await api_client.search_songs(query)
        
        if not data:
            await ctx.send(f"❌ No songs found for '{query}'.")
            return


        if isinstance(data, dict):
            song_list = data.get('results', [])
        else:
            song_list = data

        if not song_list:
            await ctx.send(f"❌ No songs found in results for '{query}'.")
            return


        eligible_songs = [] 
        for song in song_list:
            paths = await self.resolve_full_path_og(song)
            if paths:
                eligible_songs.append((song, paths))
        
        eligible_results = [s[0] for s in eligible_songs]


        if not eligible_results:
            await ctx.send(f"❌ No 'Original Files' found for '{query}' (checked {len(song_list)} results).")
            return

        if len(eligible_results) > 1:


            view = OGSelectView(self, ctx, eligible_results)
            await ctx.send(f"Found {len(eligible_results)} songs with OG files. Please select one:", view=view)
            return


        single_result_tuple = eligible_songs[0]
        first_result = single_result_tuple[0] 
        og_paths = single_result_tuple[1]
        

        track_titles = first_result.get('track_titles', [])
        main_title = track_titles[0] if track_titles else first_result.get('name', 'Unknown Title')
        
        alt_titles = track_titles[1:]
        if alt_titles:
            alt_title_string = " | ".join(alt_titles)
            description_content = f"**{alt_title_string}**\n\nDownload links are provided via individual buttons below."
        else:
            description_content = "Download links are provided via individual buttons below."


        era_display = None
        embed_color = discord.Color.from_rgb(44, 47, 51)
        era_cover_url = None 
        
        era_raw = first_result.get('era')
        era_code = None
        
        if era_raw:
            if isinstance(era_raw, dict):
                era_code = era_raw.get('name') 
            elif isinstance(era_raw, str):
                era_code = era_raw

            if era_code:
                clean_code = str(era_code).strip().upper() 

                if clean_code in ERA_MAPPING:
                    era_data = ERA_MAPPING[clean_code] 
                    era_display = era_data['name_long']
                    embed_color = era_data['color']
                    era_cover_url = era_data.get('cover_url') 
                else:
                    era_display = clean_code
                    embed_color = discord.Color.from_rgb(100, 100, 100)


        embed = discord.Embed(
            title=f"{main_title}",
            description=description_content,
            color=embed_color
        )
        
        if era_display:
             embed.add_field(name="Era", value=era_display, inline=True)

        if first_result.get('length'):
            embed.add_field(name="Length", value=first_result['length'], inline=True)
            
        if first_result.get('producers'):
            embed.add_field(name="Producers", value=first_result['producers'], inline=True)
            
        if first_result.get('record_dates'):
            record_date_val = self.format_record_date(first_result['record_dates'])
            if record_date_val:
                embed.add_field(name="Record Date", value=record_date_val, inline=False)
            
        if first_result.get('date_leaked'):
            surfaced_date_val = self.format_surfaced_date(first_result['date_leaked'])
            if surfaced_date_val:
                embed.add_field(name="Surfaced", value=surfaced_date_val, inline=False)
        

        link_view = discord.ui.View()
        all_files_list = []
        
        for path in og_paths:
            download_url = api_client.get_download_url(path)
            ext = path.split('.')[-1].upper()
            fname = path.rsplit("/", 1)[-1]
            button_label = f"[{ext}] {fname.rsplit('.', 1)[0]}"
            
            link_view.add_item(
                discord.ui.Button(
                    label=button_label,
                    url=download_url,
                    style=discord.ButtonStyle.link
                )
            )
            all_files_list.append(f"`{fname}`")

        if all_files_list:
            embed.add_field(
                name="Included Files", 
                value='\n'.join(all_files_list[:20]) + ('\n...' if len(all_files_list) > 20 else ''),
                inline=False
            )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        if era_cover_url:
            embed.set_thumbnail(url=era_cover_url)
        elif img := first_result.get('image_url'):
            embed.set_thumbnail(url=f"https://juicewrldapi.com{img}")
        
        await ctx.send(embed=embed, view=link_view)


    @getog.error
    async def getog_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):

            time_left = str(timedelta(seconds=int(error.retry_after)))
            
            reset_message = rate_limiter.get_reset_msg(ctx.author.id)

            embed = discord.Embed(
                title="⭐ You've discovered a premium feature!",
                description=(
                    f"You have used this command **10 times** (non-premium limit).\n"
                    f"Time remaining until reset: `{time_left}`\n\n"
                    f"{reset_message}\n"
                    f"To get **unlimited access** and bypass this restriction, "
                    f"you can learn more about premium by using the `@collage premium` command."
                ),
                color=discord.Color.gold(),
            )

            if ctx.interaction:
                try:
                    await ctx.send(embed=embed, ephemeral=True)
                except discord.HTTPException:
                    await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
                
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f"❌ Check failed: {error}")
            
        else:
            print(f"Unhandled error in getog: {error}")

async def setup(bot):
    await bot.add_cog(OriginalFiles(bot))