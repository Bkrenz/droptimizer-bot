import os
import logging
import asyncio

import bot.models

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

async def main():

    # Setup Logging
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # Init the Bot
    intents = discord.Intents.all()
    client = commands.Bot(command_prefix=os.getenv("COMMAND_PREFIX"), intents=intents)

    # Load Cog Extensions
    for file in os.listdir("/home/bkrenz/droptimizer-bot/bot/cogs"):
        if file.startswith("__pycache__"):
            continue
        client.load_extension(f"bot.cogs.{file[:-3]}")

    # Initialize the Database Models
    bot.models.init()

    # Start the Bot
    await client.start(os.getenv("DISCORD_BOT_TOKEN"))



if __name__ == '__main__':
    asyncio.run(main())
