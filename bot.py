#bot.py
import discord
from discord.ext import commands, tasks
import aiohttp
import time
import os
from dotenv import load_dotenv

# Import the extract.py script
import extract

# Load env variables
load_dotenv()

# Get Discord bot token
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Define intents to enable message events
intents = discord.Intents.default()
intents.messages = True

# Create a Discord bot instance
client = commands.Bot(command_prefix="!", intents=intents)

# Define a global variable to store the previous XeggeX value
previous_xeggex_value = 0
last_notification_time = 0

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
                formatted_value = "{:.4f}".format(stat_value)
            elif channel_name.lower() == "hashrate: gh/s":
                formatted_value = "{:,.3f}".format(round(stat_value))
            elif channel_name.lower() == "market cap:":
                formatted_value = "{:,.0f}".format(round(stat_value))
            elif channel_name.lower() in ["difficulty:", "block:"]:
                formatted_value = "{:.0f}".format(stat_value)
            elif channel_name.lower() == "xeggex:":
                formatted_value = "{:.2f} / 5K".format(stat_value)
            else:
                formatted_value = stat_value

        await channel.edit(name=f"{channel_name} {formatted_value}")

    except Exception as e:
        print(f"An error occurred while updating channel name: {e}")

# Function to update all statistics channels within a guild
async def update_stats_channels(guild):
    global previous_xeggex_value, last_notification_time

    try:
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
                    hashrate = round(hashrate_data["hashrate_raw"] / 1e9, 3)  # Convert to GH/s
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
                async with session.get("https://api.exbitron.digital/api/v1/cg/tickers") as response:
                    price_data = await response.json()
                    price = next(item for item in price_data if item["ticker_id"] == "TLS-USDT")["last_price"]
            except Exception:
                price = "N/A"

        balances = await extract.get_balances()
        if "error" in balances:
            xeggex_formatted = "N/A"
        else:
            xeggex = balances["totalRaisedInUsd"]
            xeggex_formatted = "{:.2f} / 5K".format(xeggex)

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
        await create_or_update_channel(guild, category, "Members:", member_count)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Difficulty:", difficulty)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Hashrate: GH/s", hashrate)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Block:", block_count)
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Supply:", supply)
        time.sleep(0.5)
        if price != "N/A":
            await create_or_update_channel(guild, category, "Price: $", float(price))
        time.sleep(0.5)

        # Calculate market cap and update its channel
        if supply != "N/A" and price != "N/A":
            market_cap = round(supply * float(price))
            await create_or_update_channel(guild, category, "Market Cap: $", market_cap)
        time.sleep(0.5)

        # Update XeggeX channel with the formatted value
        await create_or_update_channel(guild, category, "XeggeX: $", xeggex_formatted)
        time.sleep(0.5)

        # Notify if XeggeX value has increased or if it's the first run
        current_time = time.time()
        print(f"Current time: {current_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}), "
              f"Last notification time: {last_notification_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_notification_time))})")
        if xeggex > previous_xeggex_value and (current_time - last_notification_time >= 3600):
            print("Sending notification message...")
            channel = guild.get_channel(1187867994404175933)
            if channel:
                await channel.send(
                    f":dart: **We're Getting Closer to Xeggex!** :dart:\n\n"
                    f":moneybag: **New Amount:** `${xeggex_formatted}` **Goal**\n\n"
                    f":link: Keep pushing forward—let's hit that target together! :muscle::rocket:"
                )
            last_notification_time = current_time
        else:
            print("Notification not sent. Either XeggeX value did not increase or 6 minutes have not passed.")

        previous_xeggex_value = xeggex

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
