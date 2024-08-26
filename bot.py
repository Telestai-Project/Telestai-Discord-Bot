import discord
from discord.ext import commands, tasks
import requests
import time
import os
from dotenv import load_dotenv

# Loan env variables
load_dotenv()

# Get Discord bot token
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Define intents to enable message events
intents = discord.Intents.default()
intents.messages = True

# Create a Discord bot instance
client = commands.Bot(command_prefix="!", intents=intents)

# Function to set a voice channel to private (disconnect for everyone)
async def set_channel_private(category, channel):
    try:
        if isinstance(channel, discord.VoiceChannel) and channel.category == category:
            await channel.set_permissions(channel.guild.default_role, connect=False)
    except Exception as e:
        print(f"An error occurred while setting channel to private: {e}")

# Function to get or create a voice channel within a category
async def get_or_create_channel(category, channel_name):
    for existing_channel in category.voice_channels:
        existing_name = existing_channel.name.lower().replace(" ", "")
        target_name = channel_name.lower().replace(" ", "")
        if existing_name.startswith(target_name):
            return existing_channel

    channel = await category.create_voice_channel(channel_name)
    time.sleep(0.5)
    return channel

# Function to create or update a voice channel's name with specific formatting
async def create_or_update_channel(guild, category, channel_name, stat_value):
    try:
        channel = await get_or_create_channel(category, channel_name)

        if channel_name.lower() == "supply:":
            formatted_value = "{:,.0f} TLS".format(stat_value)
        elif channel_name.lower() == "price: $":
            formatted_value = "{:.4f}".format(stat_value)
        elif channel_name.lower() == "hashrate":
            formatted_value = "{:,.3f}".format(round(stat_value))
        elif channel_name.lower() == "market cap:":
            formatted_value = "{:,.0f}".format(round(stat_value))
        elif channel_name.lower() in ["difficulty:", "block:"]:
            formatted_value = "{:.0f}".format(stat_value)
        else:
            formatted_value = stat_value

        await channel.edit(name=f"{channel_name} {formatted_value}")

    except Exception as e:
        print(f"An error occurred while updating channel name: {e}")

# Function to update all statistics channels within a guild
async def update_stats_channels(guild):
    try:
        # Fetch server statistics from the new APIs
        difficulty_data = requests.get("https://telestai.cryptoscope.io/api/getdifficulty").json()
        hashrate_data = requests.get("https://telestai.cryptoscope.io/api/getnetworkhashps").json()
        block_data = requests.get("https://telestai.cryptoscope.io/api/getblockcount").json()
        supply_data = requests.get("https://telestai.cryptoscope.io/api/getcoinsupply").json()
        price_data = requests.get("https://api.exbitron.digital/api/v1/cg/tickers").json()

        # Extract necessary values
        difficulty = difficulty_data["difficulty_raw"]
        hashrate = round(hashrate_data["hashrate_raw"] / 1e9, 3)  # Convert to GH/s
        block_count = block_data["blockcount"]
        supply = float(supply_data["coinsupply"])
        price = next(item for item in price_data if item["ticker_id"] == "TLS-USDT")["last_price"]

        # Define the category name for statistics channels
        category_name = "Telestai Server Stats"
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            print(f"Creating category '{category_name}'")
            category = await guild.create_category(category_name)

        time.sleep(0.5)

        # Update or create individual statistics channels
        await create_or_update_channel(guild, category, "Difficulty:", difficulty)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Hashrate: GH/s", hashrate)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Block:", block_count)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Supply:", supply)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Price: $", float(price))
        time.sleep(0.5)

        # Calculate market cap and update its channel
        market_cap = round(supply * float(price))
        await create_or_update_channel(guild, category, "Market Cap: $", market_cap)

        for channel in category.voice_channels:
            await set_channel_private(category, channel)

    except Exception as e:
        print(f"An error occurred while updating channels: {e}")

# Define a task to update statistics channels every 5 minutes
@tasks.loop(minutes=5)
async def update_stats_task():
    for guild in client.guilds:
        print(f"Updating stats for guild '{guild.name}'")
        await update_stats_channels(guild)

@client.event
async def on_ready():
    print("The bot is ready")
    update_stats_task.start()

# Run the bot with the provided token
client.run(TOKEN)
