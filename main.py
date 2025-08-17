import discord
from discord.ext import commands
from discord import option
import json
import os
import logging
from datetime import datetime

# --- CONFIG ---
from config import *

# --- Logging setup ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

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
    def __init__(self, author_id, message_id, title, description, overlay_json, image_url, private, status="📜 Planned"):
        self.author_id = author_id
        self.message_id = message_id
        self.title = title
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

# --- Events ---
@bot.event
async def on_ready():
    logging.info(f"Bot is online as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_application_command(ctx):
    selected_options = {opt['name']: opt['value'] for opt in ctx.selected_options}
    logging.info(
        f"User {ctx.author} (ID: {ctx.author.id}) executed command '{ctx.command.qualified_name}' "
        f"with options: {selected_options} "
        f"in guild {ctx.guild} (ID: {ctx.guild_id})"
    )

# --- Slash Commands ---
@bot.slash_command(guild_ids=[GUILD_ID], description="Create a new artwork post")
@option("title", str, description="Title of your artwork")
@option("description", str, description="Description of your artwork")
@option("overlay_json", str, description="Overlay Pro Import JSON string")
@option("image", discord.Attachment, description="Upload your artwork image")
@option("private", bool, description="Hide your name (private mode)?", required=False, default=False)
async def artwork_create(
    ctx: discord.ApplicationContext,
    title: str,
    description: str,
    overlay_json: str,
    image: discord.Attachment,
    private: bool = False,
):
    logging.info(f"Executing artwork_create for user {ctx.author} with title '{title}'")
    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    if not channel:
        await ctx.respond("Artworks channel not found.", ephemeral=True)
        return

    embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    embed.add_field(name="Overlay JSON", value=f"```json\n{overlay_json}\n```", inline=False)
    embed.add_field(name="Status", value="📜 Planned", inline=True)
    if not private:
        embed.set_footer(text=f"By {ctx.author.display_name}")
    embed.set_image(url=image.url)

    try:
        msg = await channel.send(embed=embed)
        await msg.add_reaction("👍")
        artworks[str(msg.id)] = Artwork(ctx.author.id, str(msg.id), title, description, overlay_json, image.url, private)
        save_artworks()
        await ctx.respond("Your artwork has been posted!", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in artwork_create: {e}")
        await ctx.respond("Failed to post artwork.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Delete one of your artworks")
@option("message_id", str, description="Message ID of the artwork")
async def artwork_delete(ctx: discord.ApplicationContext, message_id: str):
    logging.info(f"Executing artwork_delete for user {ctx.author} on message {message_id}")
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
    except Exception as e:
        logging.error(f"Error deleting artwork {message_id}: {e}")
        await ctx.respond("Failed to delete artwork.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Set the status of your artwork")
@option("message_id", str, description="Message ID of the artwork")
@option("status", str, description="New status", choices=["✅ Done", "🖌️ In progress", "📜 Planned"])
async def artwork_set_status(ctx: discord.ApplicationContext, message_id: str, status: str):
    logging.info(f"Executing artwork_set_status for user {ctx.author} on message {message_id} with status '{status}'")
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
    except Exception as e:
        logging.error(f"Error updating status for artwork {message_id}: {e}")
        await ctx.respond("Failed to update status.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Edit your artwork")
@option("message_id", str, description="Message ID of the artwork")
@option("title", str, description="New title", required=False)
@option("description", str, description="New description", required=False)
@option("overlay_json", str, description="New overlay JSON", required=False)
@option("image", discord.Attachment, description="New artwork image", required=False)
@option("private", bool, description="Hide your name (private mode)?", required=False)
async def artwork_edit(ctx: discord.ApplicationContext, message_id: str, title: str = None, description: str = None, overlay_json: str = None, image: discord.Attachment = None, private: bool = None):
    logging.info(f"Executing artwork_edit for user {ctx.author} on message {message_id} with options: title={title}, description={description}, overlay_json={overlay_json}, image={image}, private={private}")
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

        if title:
            embed.title = title
            art.title = title
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
            if private:
                embed.set_footer(text="")
            else:
                embed.set_footer(text=f"By {ctx.author.display_name}")

        await msg.edit(embed=embed)
        save_artworks()
        await ctx.respond("Artwork updated!", ephemeral=True)
    except Exception as e:
        logging.error(f"Error editing artwork {message_id}: {e}")
        await ctx.respond("Failed to edit artwork.", ephemeral=True)


bot.run(TOKEN)
