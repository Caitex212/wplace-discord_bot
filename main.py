import discord
from discord.ext import commands
from discord import option
import sqlite3
import os
import logging
from datetime import datetime
import json

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
logging.getLogger('discord').setLevel(logging.ERROR)

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Database Setup ---
DB_FILE = "artworks.db"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS artworks (
    message_id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    overlay_json TEXT,
    image_url TEXT,
    private INTEGER,
    status TEXT,
    followers TEXT
)
""")
conn.commit()

# --- Artwork class ---
class Artwork:
    def __init__(self, author_id, message_id, title, description, overlay_json, image_url, private, status="📜 Planned", followers=None):
        self.author_id = author_id
        self.message_id = message_id
        self.title = title
        self.description = description
        self.overlay_json = overlay_json
        self.image_url = image_url
        self.private = private
        self.status = status
        self.followers = followers or []

    def save(self):
        cursor.execute("""
            INSERT OR REPLACE INTO artworks (message_id, author_id, title, description, overlay_json, image_url, private, status, followers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.message_id,
            self.author_id,
            self.title,
            self.description,
            self.overlay_json,
            self.image_url,
            int(self.private),
            self.status,
            json.dumps(self.followers)
        ))
        conn.commit()

    @staticmethod
    def load(message_id):
        cursor.execute("SELECT * FROM artworks WHERE message_id = ?", (message_id,))
        row = cursor.fetchone()
        if row:
            return Artwork(
                author_id=row[1],
                message_id=row[0],
                title=row[2],
                description=row[3],
                overlay_json=row[4],
                image_url=row[5],
                private=bool(row[6]),
                status=row[7],
                followers=json.loads(row[8] or "[]")
            )
        return None

    @staticmethod
    def all():
        cursor.execute("SELECT * FROM artworks")
        rows = cursor.fetchall()
        return [Artwork(
            author_id=row[1],
            message_id=row[0],
            title=row[2],
            description=row[3],
            overlay_json=row[4],
            image_url=row[5],
            private=bool(row[6]),
            status=row[7],
            followers=json.loads(row[8] or "[]")
        ) for row in rows]

    @staticmethod
    def delete(message_id):
        cursor.execute("DELETE FROM artworks WHERE message_id = ?", (message_id,))
        conn.commit()


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
async def artwork_create(ctx, title, description, overlay_json, image, private: bool = False):
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
        art = Artwork(ctx.author.id, str(msg.id), title, description, overlay_json, image.url, private)
        art.save()
        await msg.create_thread(name=f"Discussion - {title}")
        await ctx.respond("Your artwork has been posted!", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in artwork_create: {e}")
        await ctx.respond("Failed to post artwork.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Delete one of your artworks")
@option("message_id", str, description="Message ID of the artwork")
async def artwork_delete(ctx, message_id: str):
    art = Artwork.load(message_id)
    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != str(ctx.author.id):
        await ctx.respond("You can only delete your own artworks.", ephemeral=True)
        return

    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    try:
        msg = await channel.fetch_message(int(message_id))
        await msg.delete()
        Artwork.delete(message_id)
        await ctx.respond("Your artwork has been deleted.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error deleting artwork {message_id}: {e}")
        await ctx.respond("Failed to delete artwork.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Set the status of your artwork")
@option("message_id", str, description="Message ID of the artwork")
@option("status", str, description="New status", choices=["✅ Done", "🖌️ In progress", "📜 Planned"])
async def artwork_set_status(ctx, message_id: str, status: str):
    art = Artwork.load(message_id)
    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != str(ctx.author.id):
        await ctx.respond("You can only update your own artworks.", ephemeral=True)
        return

    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
    try:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0]
        embed.set_field_at(1, name="Status", value=status, inline=True)
        await msg.edit(embed=embed)
        art.status = status
        art.save()
        for follower_id in art.followers:
            user = await bot.fetch_user(follower_id)
            try:
                await user.send(f"Artwork '{art.title}' status updated to {status}.")
            except:
                pass
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
async def artwork_edit(ctx, message_id: str, title=None, description=None, overlay_json=None, image=None, private=None):
    art = Artwork.load(message_id)
    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if art.author_id != str(ctx.author.id):
        await ctx.respond("You can only edit your own artworks.", ephemeral=True)
        return

    channel = bot.get_channel(ARTWORKS_CHANNEL_ID)
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
        art.save()
        await ctx.respond("Artwork updated!", ephemeral=True)
    except Exception as e:
        logging.error(f"Error editing artwork {message_id}: {e}")
        await ctx.respond("Failed to edit artwork.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="List artworks with optional filters")
@option("status", str, description="Filter by status", required=False, choices=["✅ Done", "🖌️ In progress", "📜 Planned"])
@option("author", discord.Member, description="Filter by author", required=False)
async def artwork_list(ctx, status=None, author=None):
    results = []
    for art in Artwork.all():
        if status and art.status != status:
            continue
        if author and int(art.author_id) != author.id:
            continue
        results.append(art)

    if not results:
        await ctx.respond("No artworks found matching the criteria.", ephemeral=True)
        return

    for art in results:
        embed = discord.Embed(title=art.title, description=art.description, color=discord.Color.blurple())
        embed.add_field(name="Overlay JSON", value=f"```json\n{art.overlay_json}\n```", inline=False)
        embed.add_field(name="Status", value=art.status, inline=True)
        if not art.private:
            user = await bot.fetch_user(art.author_id)
            embed.set_footer(text=f"By {user.display_name}")
        embed.set_image(url=art.image_url)
        await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Follow an artwork to get status updates")
@option("message_id", str, description="Message ID of the artwork")
async def artwork_follow(ctx, message_id: str):
    art = Artwork.load(message_id)
    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if ctx.author.id == int(art.author_id):
        await ctx.respond("You cannot follow your own artwork.", ephemeral=True)
        return
    if ctx.author.id in art.followers:
        await ctx.respond("You are already following this artwork.", ephemeral=True)
        return

    art.followers.append(ctx.author.id)
    art.save()
    await ctx.respond(f"You are now following '{art.title}'. You will receive updates when the status changes.", ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Unfollow an artwork")
@option("message_id", str, description="Message ID of the artwork")
async def artwork_unfollow(ctx, message_id: str):
    art = Artwork.load(message_id)
    if not art:
        await ctx.respond("Artwork not found.", ephemeral=True)
        return
    if ctx.author.id not in art.followers:
        await ctx.respond("You are not following this artwork.", ephemeral=True)
        return

    art.followers.remove(ctx.author.id)
    art.save()
    await ctx.respond(f"You have unfollowed '{art.title}'.", ephemeral=True)


bot.run(TOKEN)
