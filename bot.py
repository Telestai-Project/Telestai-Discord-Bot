#bot.py
import discord
from discord.ext import commands, tasks
import aiohttp
import time
import os
from dotenv import load_dotenv
import json
import tweepy
import requests

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

# Global variables to store the last successful values
last_followers_count = 1503  # Initial value
last_difficulty = "N/A"
last_hashrate = "N/A"
last_block_count = "N/A"
last_supply = "N/A"
last_price = "N/A"
last_volume = "N/A"

# Add your Telegram bot token here
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Function to get Telegram followers count
def get_telegram_followers():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMembersCount?chat_id={TELEGRAM_CHAT_ID}"
        response = requests.get(url)
        data = response.json()
        if data["ok"]:
            return data["result"]
    except Exception as e:
        print(f"An error occurred while fetching Telegram followers: {e}")
    return "N/A"

# Function to get Twitter followers count
async def get_twitter_followers(username):
    global last_followers_count
    try:
        user = twitter_client.get_user(username=username, user_fields=['public_metrics'])
        if user.data:
            last_followers_count = user.data.public_metrics['followers_count']
            return last_followers_count
    except Exception as e:
        print(f"An error occurred while fetching Twitter followers: {e}")
    return last_followers_count

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
            if channel_name.lower() in ["x followers:", "telegram followers:", "members:"]:
                formatted_value = "{:,.0f}".format(stat_value)
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

# Function to get Lasko users count
async def get_lasko_users():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://testnetv1.telestai.io/api/v1/user/getAll") as response:
                users_data = await response.json()
                return len(users_data)
    except Exception as e:
        print(f"An error occurred while fetching Lasko users: {e}")
        return "N/A"

# Function to update all statistics channels within a guild
async def update_stats_channels(guild):
    global last_notification_time, last_difficulty, last_hashrate, last_block_count, last_supply, last_price, last_volume

    try:
        # Fetch Twitter followers count using the username from the environment variable
        followers_count = await get_twitter_followers(TWITTER_USERNAME)

        # Fetch Telegram followers count
        telegram_followers_count = get_telegram_followers()

        # Fetch server statistics from the APIs
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://telestai.cryptoscope.io/api/getdifficulty") as response:
                    difficulty_data = await response.json()
                    last_difficulty = difficulty_data["difficulty_raw"]
            except Exception:
                pass

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getnetworkhashps") as response:
                    hashrate_data = await response.json()
                    last_hashrate = hashrate_data["hashrate_raw"] / 1e9  # Convert to GH/s
            except Exception:
                pass

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getblockcount") as response:
                    block_data = await response.json()
                    last_block_count = block_data["blockcount"]
            except Exception:
                pass

            try:
                async with session.get("https://telestai.cryptoscope.io/api/getcoinsupply") as response:
                    supply_data = await response.json()
                    last_supply = float(supply_data["coinsupply"])
            except Exception:
                pass

            # Fetch Lasko users count
            try:
                async with session.get("https://testnetv1.telestai.io/api/v1/user/getAll") as response:
                    users_data = await response.json()
                    lasko_users_count = len(users_data)
            except Exception as e:
                print(f"An error occurred while fetching Lasko users: {e}")
                lasko_users_count = "N/A"

            try:
                async with session.get("https://api.xeggex.com/api/v2/market/getbysymbol/tls_usdt") as response:
                    price_data = await response.json()
                    last_price_xeggex = price_data["lastPrice"]
                    volume_tls = price_data["volume"]
                    volume_xeggex = float(volume_tls) * float(last_price_xeggex)
                    price_change_xeggex = price_data.get("changePercent", "N/A")
            except Exception:
                volume_xeggex = "N/A" # Set volume to "N/A" if there's an error
                price_change_xeggex = "N/A"
                last_price_xeggex = "N/A"
                
            try:
                async with session.get("https://tradeogre.com/api/v1/ticker/tls-usdt") as response:
                    text_data = await response.text()
                    volume_data = json.loads(text_data)
                    volume_tradeogre = float(volume_data["volume"])
                    last_price_tradeogre = volume_data["price"]
                    # Calculate price change manually using initialprice and current price
                    initial_price = float(volume_data["initialprice"])
                    current_price = float(volume_data["price"])
                    price_change_tradeogre = ((current_price - initial_price) / initial_price) * 100
            except Exception:
                volume_tradeogre = 0  # Set volume to 0 if there's an error
                last_price_tradeogre = "N/A"
                price_change_tradeogre = "N/A"

            volume_coinmetro = "N/A"
            last_price_coinmetro = "N/A"
            price_change_coinmetro = "N/A"

            try:
                async with session.get("https://api.coinmetro.com/exchange/prices") as response:
                    coinmetro_data = await response.json()
                    # Find TLS price from latestPrices
                    for price in coinmetro_data["latestPrices"]:
                        if price["pair"] == "TLSUSDT":
                            last_price_coinmetro = price["price"]
                            break
                    
                    # Find TLS volume and price change from 24hInfo
                    for info in coinmetro_data["24hInfo"]:
                        if info["pair"] == "TLSUSDT":
                            volume_coinmetro = float(info["v"]) * float(last_price_coinmetro)
                            # Calculate price change using delta
                            price_change_coinmetro = float(info["delta"]) * 100
                            break
            except Exception as e:
                print(f"Error fetching CoinMetro data: {e}")
                last_price_coinmetro = "N/A"
                volume_coinmetro = "N/A" 
                price_change_coinmetro = "N/A"

            # Calculate last price using volume-weighted average
            available_exchanges = []
            if last_price_xeggex != "N/A" and volume_xeggex != "N/A":
                available_exchanges.append({
                    "price": float(last_price_xeggex),
                    "volume": float(volume_xeggex),
                    "change": price_change_xeggex
                })
            if last_price_coinmetro != "N/A" and volume_coinmetro != "N/A":
                available_exchanges.append({
                    "price": float(last_price_coinmetro),
                    "volume": float(volume_coinmetro),
                    "change": price_change_coinmetro
                })
            if last_price_tradeogre != "N/A" and volume_tradeogre != "N/A":
                available_exchanges.append({
                    "price": float(last_price_tradeogre),
                    "volume": float(volume_tradeogre),
                    "change": price_change_tradeogre
                })

            # Print which exchanges are being used
            print("\nExchanges being used:")
            if last_price_xeggex != "N/A" and volume_xeggex != "N/A":
                print(f"XeggeX - Price: ${float(last_price_xeggex):.6f}, Volume: ${float(volume_xeggex):,.2f}")
            if last_price_coinmetro != "N/A" and volume_coinmetro != "N/A":
                print(f"CoinMetro - Price: ${float(last_price_coinmetro):.6f}, Volume: ${float(volume_coinmetro):,.2f}")
            if last_price_tradeogre != "N/A" and volume_tradeogre != "N/A":
                print(f"TradeOgre - Price: ${float(last_price_tradeogre):.6f}, Volume: ${float(volume_tradeogre):,.2f}")
            print(f"Total exchanges used: {len(available_exchanges)}\n")

            if available_exchanges:
                total_volume = sum(exchange["volume"] for exchange in available_exchanges)
                last_price = sum(exchange["price"] * (exchange["volume"] / total_volume) for exchange in available_exchanges)

                # Calculate weighted average of price change if all available exchanges have price change data
                available_changes = [exchange["change"] for exchange in available_exchanges if exchange["change"] != "N/A"]
                if available_changes:
                    price_change = sum(
                        float(exchange["change"]) * (exchange["volume"] / total_volume)
                        for exchange in available_exchanges
                        if exchange["change"] != "N/A"
                    )
                    if price_change >= 0:
                        price_display = f"${last_price:.6f} (▲ +{price_change:.2f}% 24h)"
                    else:
                        price_display = f"${last_price:.6f} (▼ {price_change:.2f}% 24h)"
                else:
                    price_display = f"${last_price:.6f}"
            else:
                last_price = "N/A"
                price_display = "N/A"

            # Calculate total volume
            try:
                if volume_xeggex != "N/A" and volume_coinmetro != "N/A":
                    last_volume = float(volume_xeggex) + float(volume_coinmetro) + volume_tradeogre
                elif volume_xeggex != "N/A":
                    last_volume = float(volume_xeggex) + volume_tradeogre
                elif volume_coinmetro != "N/A":
                    last_volume = float(volume_coinmetro) + volume_tradeogre
                else:
                    last_volume = volume_tradeogre
            except Exception as e:
                print(f"Error calculating total volume: {e}")
                last_volume = "N/A"

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
        print(f"Telegram Followers '{telegram_followers_count}'")
        await create_or_update_channel(guild, category, "Telegram Followers:", telegram_followers_count)
        time.sleep(0.5)
        print(f"Lasko Users '{lasko_users_count}'")
        await create_or_update_channel(guild, category, "Lasko Users:", lasko_users_count)
        time.sleep(0.5)
        print(f"Members '{member_count}'")
        await create_or_update_channel(guild, category, "Members:", member_count)
        time.sleep(0.5)
        print(f"Difficulty '{last_difficulty}'")
        await create_or_update_channel(guild, category, "Difficulty:", last_difficulty)
        time.sleep(0.5)
        print(f"Hashrate '{last_hashrate}'")
        await create_or_update_channel(guild, category, "Hashrate: GH/s", last_hashrate)
        time.sleep(0.5)
        print(f"Block '{last_block_count}'")
        await create_or_update_channel(guild, category, "Block:", last_block_count)
        time.sleep(0.5)
        print(f"Supply '{last_supply}'")
        await create_or_update_channel(guild, category, "Supply:", last_supply)
        time.sleep(0.5)
        print(f"Price '{price_display}'")
        await create_or_update_channel(guild, category, "Price:", price_display)
        time.sleep(0.5)
        
        # Ensure volume is formatted correctly
        if last_volume != "N/A":
            formatted_volume = "{:,.0f}".format(last_volume)
        else:
            formatted_volume = "N/A"
        print(f"24h Volume '{formatted_volume}'")
        await create_or_update_channel(guild, category, "24h Volume: $", formatted_volume)
        time.sleep(0.5)

        # Calculate market cap and ensure it's formatted correctly
        if last_supply != "N/A" and last_price != "N/A":
            market_cap = round(last_supply * float(last_price))
            formatted_market_cap = "{:,.0f}".format(market_cap)
        else:
            formatted_market_cap = "N/A"
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
