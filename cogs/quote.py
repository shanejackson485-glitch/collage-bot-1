import discord
import aiohttp
import asyncio
import io
import os
from discord import app_commands, File
from discord.ui import Button, View, Select
from discord.ext import commands
from discord.ext.commands import Cog
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
from pilmoji import Pilmoji



def ListedFonts():
    """Lists available fonts in the local directory."""
    fonts = []
    if os.path.exists('heist/fonts/'):
        for file in os.listdir('heist/fonts/'):
            if (file.endswith('.ttf') or file.endswith('.otf')):
                fonts.append(file)
    return fonts

def get_font(size, filename=None):
    """Loads a font from heist/fonts/ or falls back to default."""
    try:
        font_path = f"heist/fonts/{filename}" if filename and filename != "Default" else None
        
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        
        for fallback in ["arial.ttf", "segoeui.ttf", "roboto.ttf"]:
            try:
                return ImageFont.truetype(fallback, size)
            except:
                continue
                
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()



def process_avatar_gradient(avatar, color_val, transparency, flip, new):
    if avatar.mode != 'RGBA':
        im = avatar.convert('RGBA')
    else:
        im = avatar

    width, height = im.size
    
    gradient = Image.new('L', (width, 1), color=0xFF)
    for x in range(width):
        val = max(0, min(255, transparency - int((x / width) * 255))) 
        gradient.putpixel((x, 0), int(max(0, transparency - x) if transparency > 255 else max(0, 255 - (x * (255/width)))))

    alpha = gradient.resize(im.size)
    black_im = Image.new('RGBA', (width, height), color=color_val)
    
    rotation = (180 if not flip else 0) if not new else 90
    black_im.putalpha(alpha.rotate(rotation))
    
    gradient_im = Image.alpha_composite(im, black_im)
    return gradient_im

def wrap_text(text, font, max_width, draw):
    words = text.split() 
    lines = []
    current_line = ""

    for word in words:
        test_line = (current_line + " " + word).strip() if current_line else word
        w = draw.textlength(test_line, font=font)
        
        if w <= max_width:
            current_line = test_line
            continue
            
        if current_line:
            lines.append(current_line)
            current_line = ""
            
        w_word = draw.textlength(word, font=font)
        if w_word <= max_width:
            current_line = word
            continue
            
        chunk = ""
        for char in word:
            test_chunk = chunk + char
            w_chunk = draw.textlength(test_chunk, font=font)
            if w_chunk <= max_width:
                chunk = test_chunk
            else:
                lines.append(chunk)
                chunk = char
        current_line = chunk

    if current_line:
        lines.append(current_line)

    return lines

def draw_quote_content(img, content, display_name, username, font_name, text_color, new, flip):
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    if new:
        wrap_width = 500
        center_x = width / 2
        center_y = height / 2
        max_text_h = 175
    else:
        wrap_width = 350
        center_y = height / 2
        max_text_h = 335
        
        if not flip:
            center_x = 640 
        else:
            center_x = 217 

    reserved_bottom_h = 150
    allowed_text_height = max_text_h - reserved_bottom_h
    if allowed_text_height < 50: allowed_text_height = 50

    font_size = 60 if not new else 70
    min_font_size = 12
    line_spacing = 1.1
    
    selected_font = get_font(font_size, font_name)
    lines = []

    while font_size >= min_font_size:
        selected_font = get_font(font_size, font_name)
        lines = wrap_text(content, selected_font, wrap_width, draw)

        ascent, descent = selected_font.getmetrics()
        single_line_h = ascent + descent
        
        total_h = (single_line_h * len(lines)) + \
                  (single_line_h * (line_spacing - 1) * max(0, len(lines)-1))

        max_line_w = 0
        for line in lines:
            w = draw.textlength(line, font=selected_font)
            if w > max_line_w: max_line_w = w

        if max_line_w <= (wrap_width + 5) and total_h <= allowed_text_height:
            break

        font_size -= 2

    ascent, descent = selected_font.getmetrics()
    single_line_h = ascent + descent
    
    total_text_height = (single_line_h * len(lines)) + \
                        (single_line_h * (line_spacing - 1) * max(0, len(lines)-1))
    
    text_y_start = center_y if not new else center_y + 200
    current_y = text_y_start - (total_text_height / 2)

    with Pilmoji(img) as pilmoji:
        for line in lines:
            line_w = draw.textlength(line, font=selected_font)
            line_x = center_x - (line_w / 2)

            pilmoji.text((int(line_x), int(current_y)), line, font=selected_font, fill=text_color)
            current_y += single_line_h * line_spacing

    name_size = max(16, int(font_size * (0.55 if not new else 0.60)))
    user_size = max(12, int(font_size * (0.42 if not new else 0.46)))

    name_font = get_font(name_size, font_name)
    name_text = f"- {display_name}" if not new else display_name

    name_w = draw.textlength(name_text, font=name_font)
    name_x = center_x - (name_w / 2)
    name_y = center_y + ((20 + total_text_height / 2) if not new else 330)

    min_name_y = text_y_start + (total_text_height / 2) + 15
    name_y = max(name_y, min_name_y)


    draw.text((int(name_x), int(name_y)), name_text, font=name_font, fill=text_color)

    user_font = get_font(user_size, font_name)
    user_text = f"@{username}"
    user_w = draw.textlength(user_text, font=user_font)
    user_x = center_x - (user_w / 2)
    user_y = name_y + name_size + 10
    
    dim_color = (180, 180, 180) if text_color[0] > 100 else (80, 80, 80)
    draw.text((int(user_x), int(user_y)), user_text, font=user_font, fill=dim_color)

    wm_font = get_font(12, font_name)
    wm_text = "collagebot.info"
    wm_w = draw.textlength(wm_text, font=wm_font)
    
    wm_color = (100, 100, 100) if text_color[0] > 100 else (160, 160, 160)
    
    if new:
        wm_x = center_x - (wm_w / 2)
        wm_y = center_y + 355
    else:
        wm_x = 815 if not flip else 70
        wm_x = wm_x - (wm_w / 2)
        wm_y = 420
    
    draw.text((int(wm_x), int(wm_y)), wm_text, font=wm_font, fill=wm_color)
    
    if new:
        q_font = get_font(225, font_name)
        q_w = draw.textlength('"', font=q_font)
        q_y = center_y + 135
        draw.text((int(center_x - (q_w/2)), int(q_y)), '"', font=q_font, fill=text_color)

async def generate_quote_locally(avatar_bytes, content, display_name, username, style_options):
    font_name = style_options.get('font', 'Default')
    dark_mode = style_options.get('color', True)
    save_as_gif = style_options.get('gif', False)

    if dark_mode: 
        bg_color = (0, 0, 0, 255)
        text_color = (255, 255, 255) 
        transparency = 280 
    else: 
        bg_color = (255, 255, 255, 255)
        text_color = (0, 0, 0)
        transparency = 255

    flip = style_options.get('flip', False)
    new = style_options.get('new', False)
    
    canvas_w = 857 if not new else 592
    canvas_h = 450 if not new else 743
    paste_pos = (0, 0) if not flip else (round(canvas_w / 2 - 20), 0)
    target_size = (450, 450) if not new else (592, 743)

    try:
        avatar_source = Image.open(io.BytesIO(avatar_bytes))
        if getattr(avatar_source, "is_animated", False):
            avatar_source.seek(0)
        avatar_source = avatar_source.convert("RGBA")
    except:
        avatar_source = Image.new("RGBA", (512, 512), (128, 128, 128, 255))

    def process_frame(frame_img):
        frame = frame_img.convert("RGBA")
        frame = ImageOps.fit(frame, target_size, method=Image.Resampling.LANCZOS)
        gradient_im = process_avatar_gradient(frame, bg_color, transparency, flip, new)
        
        if style_options.get('contrast'):
            gradient_im = gradient_im.convert('L').convert('RGBA')
        if style_options.get('blur'):
            gradient_im = gradient_im.filter(ImageFilter.GaussianBlur(10))
        if style_options.get('brightness'):
            gradient_im = ImageEnhance.Brightness(gradient_im).enhance(1.5)
        if style_options.get('pixelate'):
            w, h = gradient_im.size
            gradient_im = gradient_im.resize((w//10, h//10), Image.NEAREST).resize((w, h), Image.NEAREST)
        if style_options.get('solarize'):
            gradient_im = ImageOps.solarize(gradient_im)
            
        base = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
        base.paste(gradient_im, paste_pos, gradient_im)
        
        flat_base = Image.new("RGB", base.size, bg_color[:3])
        flat_base.paste(base, mask=base.split()[3])
        
        draw_quote_content(flat_base, content, display_name, username, font_name, text_color, new, flip)
        
        return flat_base

    loop = asyncio.get_running_loop()
    final_image = await loop.run_in_executor(None, process_frame, avatar_source)
    
    output = io.BytesIO()
    
    if save_as_gif:
        try:
            gif_image = final_image.quantize(colors=256, method=2, dither=Image.NONE)
        except:
            gif_image = final_image.quantize(colors=256, method=1, dither=Image.NONE)
            
        gif_image.save(output, format="GIF", optimize=True)
    else:
        final_image.save(output, format="PNG")
        
    output.seek(0)
    return output



class Buttons(discord.ui.View):
    EMOJIS = {
        "color": "<:color:1316896978931683408>",
        "contrast": "<:contrast:1316896854956314755>",
        "flip": "<:flip:1316896847096315954>",
        "gif": "<:gif:1325499192097116201>",
        "new": "<:new:1316896960917016607>",
        "blur": "<:blur:1316897646480461885>",
        "brightness": "<:brightness:1316897642114187324>",
        "pixelate": "<:pixel:1316897638620336148>",
        "solarize": "<:solarize:1316896942382387231>",
        "remove": "<:trash:1316896912372400201>"
    }

    def __init__(self, ctx, author):
        super().__init__(timeout=240)
        self.ctx = ctx
        self.author = author
        self.font = 'Default'
        self.style_options = {
            'color': True, 
            'contrast': False, 
            'flip': False, 
            'blur': False, 
            'pixelate': False, 
            'solarize': False,
            'brightness': False,
            'new': False,
            'gif': False
        }
        self._update_font_select()

    def _update_font_select(self):
        fonts = ListedFonts()
        if not fonts:
            fonts = ["Default"]
        self.select_font.options = [
            discord.SelectOption(
                label=f, value=f, default=(f == self.font)
            ) for f in fonts[:25]
        ]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("Not your menu.", ephemeral=True)
            return False
        return True

    async def update_image(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(str(self.message.author.display_avatar.url)) as resp:
                avatar_bytes = await resp.read()

        self.style_options['font'] = self.font

        img_buffer = await generate_quote_locally(
            avatar_bytes,
            self.message.clean_content,
            self.message.author.display_name,
            self.message.author.name,
            self.style_options
        )

        ext = 'gif' if self.style_options['gif'] else 'png'
        file = discord.File(img_buffer, filename=f'quote.{ext}')
        await interaction.edit_original_response(attachments=[file], view=self)

    @discord.ui.select(placeholder="Select a font...", options=[])
    async def select_font(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.font = select.values[0]
        self._update_font_select()
        await self.update_image(interaction)
    
    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["color"])
    async def color(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['color'] = not self.style_options['color']
        button.style = discord.ButtonStyle.blurple if self.style_options['color'] else discord.ButtonStyle.grey
        await self.update_image(interaction)
        
    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["gif"])
    async def gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['gif'] = not self.style_options['gif']
        button.style = discord.ButtonStyle.blurple if self.style_options['gif'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["contrast"])
    async def contrast(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['contrast'] = not self.style_options['contrast']
        button.style = discord.ButtonStyle.blurple if self.style_options['contrast'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["flip"])
    async def flip(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['flip'] = not self.style_options['flip']
        button.style = discord.ButtonStyle.blurple if self.style_options['flip'] else discord.ButtonStyle.grey
        await self.update_image(interaction)
    
    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["new"])
    async def new(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['new'] = not self.style_options['new']
        button.style = discord.ButtonStyle.blurple if self.style_options['new'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["blur"])
    async def blur(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['blur'] = not self.style_options['blur']
        button.style = discord.ButtonStyle.blurple if self.style_options['blur'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["brightness"])
    async def brightness(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['brightness'] = not self.style_options['brightness']
        button.style = discord.ButtonStyle.blurple if self.style_options['brightness'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["pixelate"])
    async def pixelate(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['pixelate'] = not self.style_options['pixelate']
        button.style = discord.ButtonStyle.blurple if self.style_options['pixelate'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=EMOJIS["solarize"])
    async def solarize(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style_options['solarize'] = not self.style_options['solarize']
        button.style = discord.ButtonStyle.blurple if self.style_options['solarize'] else discord.ButtonStyle.grey
        await self.update_image(interaction)

    @discord.ui.button(emoji=EMOJIS["remove"], style=discord.ButtonStyle.grey)
    async def remove_quote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()



class HeistQuote(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        

        self.ctx_quote = app_commands.ContextMenu(
            name='Quote Message',
            callback=self.quotemessage_context,
        )
        self.bot.tree.add_command(self.ctx_quote)

    async def cog_unload(self):

        self.bot.tree.remove_command(self.ctx_quote.name, type=self.ctx_quote.type)
        if self.session:
            await self.session.close()

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def quotemessage_context(self, interaction: discord.Interaction, message: discord.Message):

        ctx = await self.bot.get_context(interaction)
        await self._process_quote(ctx, message)

    async def _process_quote(self, ctx, message):
        if not message.content:
            return await ctx.send("Message has no content or I cannot read it.")

        view = Buttons(ctx, author=ctx.author)
        view.message = message
        
        await ctx.typing()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(message.author.display_avatar.url)) as resp:
                    avatar_bytes = await resp.read()

            img_buffer = await generate_quote_locally(
                avatar_bytes,
                message.clean_content,
                message.author.display_name,
                message.author.name,
                view.style_options
            )
            
            file = discord.File(img_buffer, filename='quote.png')
            await ctx.send(file=file, view=view)
        except Exception as e:
            await ctx.send(f"Failed to generate quote: {e}")

async def setup(bot):
    await bot.add_cog(HeistQuote(bot))