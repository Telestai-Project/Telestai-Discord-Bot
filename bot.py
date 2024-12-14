#bot.py
import discord
from discord.ext import commands, tasks
import aiohttp
import time
import os
from dotenv import load_dotenv
import json
import tweepy

# Load env variables
load_dotenv()

# Get Discord bot token
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Define intents to enable message and member events
intents = discord.Intents.default()
intents.messages = True
intents.members = True

# Create a Discord bot instance
client = commands.Bot(command_prefix="!", intents=intents)

# Define a global variable to store the previous XeggeX value
last_notification_time = 0

# Twitter API credentials and username from .env
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET_KEY = os.getenv("TWITTER_API_SECRET_KEY")
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")

# Authenticate with the Twitter API
twitter_client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Function to get Twitter followers count
async def get_twitter_followers(username):
    try:
        user = twitter_client.get_user(username=username, user_fields=['public_metrics'])
        if user.data:
            return user.data.public_metrics['followers_count']
    except Exception as e:
        print(f"An error occurred while fetching Twitter followers: {e}")
    return "N/A"

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

        if isinstance(stat_value, str) and stat_value == "N/A":
            formatted_value = stat_value
        else:
            if channel_name.lower() == "members:":
                formatted_value = "{:.0f}".format(stat_value)
            elif channel_name.lower() == "supply:":
                formatted_value = "{:,.0f} TLS".format(stat_value)
            elif channel_name.lower() == "price: $":
                formatted_value = "{:.6f}".format(stat_value)
            elif channel_name.lower() == "hashrate: gh/s":
                formatted_value = "{:,.3f}".format(stat_value)
            elif channel_name.lower() == "market cap:":
                formatted_value = "{:,.0f}".format(round(stat_value))
            elif channel_name.lower() in ["difficulty:", "block:"]:
                formatted_value = "{:,.0f}".format(stat_value)
            elif channel_name.lower() == "24h volume:":
                formatted_value = "{:,.0f}".format(stat_value)
            else:
                formatted_value = stat_value

        await channel.edit(name=f"{channel_name} {formatted_value}")

    except Exception as e:
        print(f"An error occurred while updating channel name: {e}")

# Function to update all statistics channels within a guild
async def update_stats_channels(guild):
    global last_notification_time

    try:
        # Fetch Twitter followers count using the username from the environment variable
        followers_count = await get_twitter_followers(TWITTER_USERNAME)

        # Fetch server statistics from the APIs
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://telestai.cryptoscope.io/api/getdifficulty") as response:
                    difficulty_data = await response.json()
                    difficulty = difficulty_data["difficulty_raw"]
            except Exception:
                difficulty = "N/A"

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getnetworkhashps") as response:
                    hashrate_data = await response.json()
                    hashrate = hashrate_data["hashrate_raw"] / 1e9  # Convert to GH/s
            except Exception:
                hashrate = "N/A"

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getblockcount") as response:
                    block_data = await response.json()
                    block_count = block_data["blockcount"]
            except Exception:
                block_count = "N/A"

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getcoinsupply") as response:
                    supply_data = await response.json()
                    supply = float(supply_data["coinsupply"])
            except Exception:
                supply = "N/A"

            try:
                async with session.get("https://api.xeggex.com/api/v2/market/getbysymbol/tls_usdt") as response:
                    price_data = await response.json()
                    #price_data = json.loads(text_data)
                    price = price_data["lastPrice"]
                    volume_tls = price_data["volume"]
                    volume_xeggex = float(volume_tls) * float(price)
                    print(volume_xeggex)
            except Exception:
                price = "N/A"
                volume = 0

            try:
                async with session.get("https://tradeogre.com/api/v1/ticker/tls-usdt") as response:
                    text_data = await response.text()
                    volume_data = json.loads(text_data)
                    volume_tradeogre = volume_data["volume"]
                    print(volume_tradeogre)
            except Exception:
                price = 0

            volume = float(volume_xeggex) + float(volume_tradeogre)


        try:
            member_count = guild.member_count
        except Exception:
            member_count = "N/A"

        # Define the category name for statistics channels
        category_name = "Telestai Server Stats"
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            print(f"Creating category '{category_name}'")
            category = await guild.create_category(category_name)

        time.sleep(0.5)

        # Update or create individual statistics channels
        print(f"Followers '{followers_count}'")
        await create_or_update_channel(guild, category, "X Followers:", followers_count)
        time.sleep(0.5)
        print(f"Members '{member_count}'")
        await create_or_update_channel(guild, category, "Members:", member_count)
        time.sleep(0.5)
        print(f"Difficulty '{difficulty}'")
        await create_or_update_channel(guild, category, "Difficulty:", difficulty)
        time.sleep(0.5)
        print(f"Hashrate '{hashrate}'")
        await create_or_update_channel(guild, category, "Hashrate: GH/s", hashrate)
        time.sleep(0.5)
        print(f"Block '{block_count}'")
        await create_or_update_channel(guild, category, "Block:", block_count)
        time.sleep(0.5)
        print(f"Supply '{supply}'")
        await create_or_update_channel(guild, category, "Supply:", supply)
        time.sleep(0.5)
        print(f"Price '{price}'")
        await create_or_update_channel(guild, category, "Price: $", float(price))
        time.sleep(0.5)
        
        # Ensure volume is formatted correctly
        formatted_volume = "{:,.0f}".format(volume)
        print(f"24h Volume '{formatted_volume}'")
        await create_or_update_channel(guild, category, "24h Volume: $", formatted_volume)
        time.sleep(0.5)

        # Calculate market cap and ensure it's formatted correctly
        if supply != "N/A" and price != "N/A":
            market_cap = round(supply * float(price))
            formatted_market_cap = "{:,.0f}".format(market_cap)
            print(f"Market Cap '{formatted_market_cap}'")
            await create_or_update_channel(guild, category, "Market Cap: $", formatted_market_cap)
        time.sleep(0.5)

        # Set all channels to private
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
