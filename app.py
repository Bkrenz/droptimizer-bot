import importlib
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
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'discord.log')
    handler = logging.FileHandler(filename=log_path, encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    logger.info(f'Starting app.py from {os.path.abspath(__file__)}')

    # Init the Bot
    intents = discord.Intents.all()
    client = commands.Bot(command_prefix=os.getenv("COMMAND_PREFIX"), intents=intents)

    @client.event
    async def on_ready():
        logger.info(f'Bot ready: {client.user} (ID: {client.user.id})')
        logger.info(f'discord version: {getattr(discord, "__version__", "unknown")}')
        logger.info(f'client has tree: {hasattr(client, "tree")}')
        if not hasattr(client, 'tree'):
            logger.warning('Discord client does not expose command tree; creating one manually.')
            try:
                app_commands = importlib.import_module('discord.app_commands')
            except ModuleNotFoundError:
                logger.error('discord.app_commands is unavailable in this runtime. Cannot create CommandTree.')
                return
            client.tree = app_commands.CommandTree(client)

        # Sync commands to each guild for immediate availability in guilds,
        # then sync globally as a fallback.
        for guild in client.guilds:
            try:
                await client.tree.sync(guild=guild)
                logger.info(f'Synced commands to guild {guild.id} via client.tree.sync')
            except Exception as e:
                logger.warning(f'Failed to sync commands to guild {guild.id}: {e}')

        try:
            await client.tree.sync()
            logger.info('Global command sync attempted via client.tree.sync')
        except Exception as e:
            logger.warning(f'Global command sync failed: {e}')

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
