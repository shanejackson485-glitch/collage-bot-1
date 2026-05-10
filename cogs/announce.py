import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
import re
import os




CONFIG_PATH = "data/Developer/config.json"
ADMIN_ID = None

try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            ADMIN_ID = config.get("admin_user_id")
    else:
        print(f"[Announce] Config file not found at {CONFIG_PATH}")
except Exception as e:
    print(f"[Announce] Failed to load config: {e}")




def get_broadcast_channel(guild: discord.Guild, bot: discord.Client):

    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel


    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages and channel.name.lower() == "general":
            return channel


    chat_names = ["chat", "chats", "main-chat", "discussion", "announcements"]
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages and channel.name.lower() in chat_names:
            return channel


    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages and channel.name.lower() == guild.name.lower():
            return channel


    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel

    return None




class EditEmbedModal(discord.ui.Modal, title="Edit Announcement"):
    def __init__(self, embed: discord.Embed):
        super().__init__()

        self.initial_title = embed.title or ""
        self.initial_description = embed.description or ""
        self.initial_color = f"#{embed.color.value:06x}" if embed.color else ""
        self.initial_thumbnail = embed.thumbnail.url if embed.thumbnail and embed.thumbnail.url else ""

        self.title_input = discord.ui.TextInput(
            label="Embed Title",
            max_length=256,
            default=self.initial_title
        )
        self.add_item(self.title_input)

        self.description_input = discord.ui.TextInput(
            label="Embed Description",
            style=discord.TextStyle.long,
            max_length=4000,
            default=self.initial_description
        )
        self.add_item(self.description_input)

        self.color_input = discord.ui.TextInput(
            label="Embed Color (Hex)",
            required=False,
            default=self.initial_color
        )
        self.add_item(self.color_input)

        self.thumbnail_input = discord.ui.TextInput(
            label="Thumbnail URL",
            required=False,
            default=self.initial_thumbnail
        )
        self.add_item(self.thumbnail_input)

    async def on_submit(self, interaction: discord.Interaction):

        color = discord.Color.default()
        if self.color_input.value:

            hex_clean = self.color_input.value.lstrip('#').replace('0x', '')
            try:
                color = discord.Color(int(hex_clean, 16))
            except ValueError:
                pass


        updated_embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=color
        )
        if self.thumbnail_input.value:
            updated_embed.set_thumbnail(url=self.thumbnail_input.value)


        view = ConfirmAnnouncementView(updated_embed)

        await interaction.response.edit_message(
            content="Preview updated. Confirm or edit again.",
            embed=updated_embed,
            view=view
        )




class ConfirmAnnouncementView(discord.ui.View):
    def __init__(self, embed: discord.Embed):
        super().__init__(timeout=120)
        self.embed = embed

    @discord.ui.button(label="Send to All Servers", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Broadcast started... Sending to all servers.", view=self)

        sent = 0
        failed = 0


        for guild in interaction.client.guilds:
            channel = get_broadcast_channel(guild, interaction.client)
            if channel is None:
                failed += 1
                continue
            try:
                await channel.send(embed=self.embed)
                sent += 1
            except Exception as e:
                print(f"[Announce] Failed to send to {guild.name}: {e}")
                failed += 1
            
            await asyncio.sleep(1.5)

        await interaction.followup.send(
            f"✔️ Broadcast complete.\n**Sent:** {sent}\n**Failed:** {failed}",
            ephemeral=True
        )

    @discord.ui.button(label="Edit Embed", style=discord.ButtonStyle.blurple)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditEmbedModal(self.embed))




class AnnouncementModal(discord.ui.Modal, title="Global Announcement"):
    def __init__(self):
        super().__init__()
        self.title_input = discord.ui.TextInput(label="Embed Title", max_length=256)
        self.add_item(self.title_input)
        
        self.description_input = discord.ui.TextInput(label="Embed Description", style=discord.TextStyle.long, max_length=4000)
        self.add_item(self.description_input)
        
        self.color_input = discord.ui.TextInput(label="Embed Color (Hex)", required=False)
        self.add_item(self.color_input)
        
        self.thumbnail_input = discord.ui.TextInput(label="Thumbnail URL (Optional)", required=False)
        self.add_item(self.thumbnail_input)
        
        self.footer_input = discord.ui.TextInput(label="Footer (Optional)", required=False, placeholder="Enter footer text...")
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):

        color = discord.Color.default()
        if self.color_input.value:
            hex_clean = self.color_input.value.lstrip('#').replace('0x', '')
            try:
                color = discord.Color(int(hex_clean, 16))
            except ValueError:
                pass
        
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=color
        )
        
        if self.thumbnail_input.value:
            embed.set_thumbnail(url=self.thumbnail_input.value)
        if self.footer_input.value:
            embed.set_footer(text=self.footer_input.value)
        
        view = ConfirmAnnouncementView(embed)
        await interaction.response.send_message(
            "Preview your announcement below. Confirm or edit before sending.",
            embed=embed,
            view=view,
            ephemeral=True
        )




class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Send a server-wide announcement to ALL servers the bot is in.")
    async def announce(self, interaction: discord.Interaction):

        if not ADMIN_ID:
            return await interaction.response.send_message(
                "❌ Admin ID not loaded from config. Please check bot logs.",
                ephemeral=True
            )

        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
        await interaction.response.send_modal(AnnouncementModal())




async def setup(bot):
    await bot.add_cog(Announce(bot))