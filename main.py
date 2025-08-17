import discord
from discord.ext import commands
from discord import option
import json
import os

# --- CONFIG ---
from config import *

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Persistence ---
def load_artworks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_artworks():
    with open(DATA_FILE, "w") as f:
        json.dump({k: v.__dict__ for k, v in artworks.items()}, f, indent=4)

# --- Artwork class ---
class Artwork:
    def __init__(self, author_id, message_id, description, overlay_json, image_url, private, status="📜 Planned"):
        self.author_id = author_id
        self.message_id = message_id
        self.description = description
        self.overlay_json = overlay_json
        self.image_url = image_url
        self.private = private
        self.status = status

# Load existing artworks
artworks = {}
raw_data = load_artworks()
for k, v in raw_data.items():
    artworks[k] = Artwork(**v)

# --- Slash Commands ---
@bot.slash_command(guild_ids=[GUILD_ID], description="Create a new artwork post")
@option("description", str, description="Description of your artwork")
@option("overlay_json", str, description="Overlay Pro Import JSON string")
@option("image", discord.Attachment, description="Upload your artwork image")
@option("private", bool, description="Hide your name (private mode)?", required=False, default=False)
async def artwork_create(
    ctx: discord.ApplicationContext,
    description: str,
    overlay_json: str,
    image: discord.Attachment,
    private: bool = False,
):
    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    if not channel:
        await ctx.respond("Artworks channel not found.", ephemeral=True)
        return

    embed = discord.Embed(title="🎨 New Artwork", description=description, color=discord.Color.blurple())
    embed.add_field(name="Overlay JSON", value=f"```json\n{overlay_json}\n```", inline=False)
    embed.add_field(name="Status", value="📜 Planned", inline=True)
    if not private:
        embed.set_footer(text=f"By {ctx.author.display_name}")
    embed.set_image(url=image.url)

    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")

    artworks[str(msg.id)] = Artwork(ctx.author.id, str(msg.id), description, overlay_json, image.url, private)
    save_artworks()

    await ctx.respond("Your artwork has been posted!", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="Delete one of your artworks")
@option("message_id", str, description="Message ID of the artwork")
async def artwork_delete(ctx: discord.ApplicationContext, message_id: str):
    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    art = artworks.get(message_id)

    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != ctx.author.id:
        await ctx.respond("You can only delete your own artworks.", ephemeral=True)
        return

    try:
        msg = await channel.fetch_message(int(message_id))
        await msg.delete()
        del artworks[message_id]
        save_artworks()
        await ctx.respond("Your artwork has been deleted.", ephemeral=True)
    except:
        await ctx.respond("Failed to delete artwork.", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="Set the status of your artwork")
@option("message_id", str, description="Message ID of the artwork")
@option("status", str, description="New status", choices=["✅ Done", "🖌️ In progress", "📜 Planned"])
async def artwork_set_status(ctx: discord.ApplicationContext, message_id: str, status: str):
    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    art = artworks.get(message_id)

    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != ctx.author.id:
        await ctx.respond("You can only update your own artworks.", ephemeral=True)
        return

    try:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0]
        embed.set_field_at(1, name="Status", value=status, inline=True)
        await msg.edit(embed=embed)
        art.status = status
        save_artworks()
        await ctx.respond(f"Status updated to {status}", ephemeral=True)
    except:
        await ctx.respond("Failed to update status.", ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="Edit your artwork")
@option("message_id", str, description="Message ID of the artwork")
@option("description", str, description="New description", required=False)
@option("overlay_json", str, description="New overlay JSON", required=False)
@option("image", discord.Attachment, description="New artwork image", required=False)
@option("private", bool, description="Set artwork private? (True/False)", required=False)
async def artwork_edit(
    ctx: discord.ApplicationContext,
    message_id: str,
    description: str = None,
    overlay_json: str = None,
    image: discord.Attachment = None,
    private: bool = None
):
    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    art = artworks.get(message_id)

    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != ctx.author.id:
        await ctx.respond("You can only edit your own artworks.", ephemeral=True)
        return

    try:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0]

        if description:
            embed.description = description
            art.description = description
        if overlay_json:
            embed.set_field_at(0, name="Overlay JSON", value=f"```json\n{overlay_json}\n```", inline=False)
            art.overlay_json = overlay_json
        if image:
            embed.set_image(url=image.url)
            art.image_url = image.url
        if private is not None:
            art.private = private
            if not private:
                embed.set_footer(text=f"By {ctx.author.display_name}")
            else:
                embed.set_footer(text="")

        await msg.edit(embed=embed)
        save_artworks()
        await ctx.respond("Artwork updated!", ephemeral=True)
    except:
        await ctx.respond("Failed to edit artwork.", ephemeral=True)

bot.run(TOKEN)
