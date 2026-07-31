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

    # Init the Bot
    intents = discord.Intents.all()
    client = commands.Bot(command_prefix=os.getenv("COMMAND_PREFIX"), intents=intents)

    @client.event
    async def on_ready():
        logger.info(f'Bot ready: {client.user} (ID: {client.user.id})')
        # Attempt to sync commands to each guild for immediate availability
        for guild in list(client.guilds):
            synced = False
            if hasattr(client, 'tree'):
                try:
                    await client.tree.sync(guild=guild)
                    logger.info(f'Synced commands to guild {guild.id} via tree.sync')
                    synced = True
                except Exception as e:
                    logger.warning(f'Guild tree sync failed for {guild.id}: {e}')
            if not synced:
                try:
                    await client.sync_commands(guild)
                    logger.info(f'Synced commands to guild {guild.id} via sync_commands(guild)')
                    synced = True
                except TypeError:
                    try:
                        await client.sync_commands(discord.Object(id=guild.id))
                        logger.info(f'Synced commands to guild {guild.id} via sync_commands(Object)')
                        synced = True
                    except Exception as e:
                        logger.error(f'Failed to sync commands to guild {guild.id}: {e}')
                except Exception as e:
                    logger.error(f'Failed to sync commands to guild {guild.id}: {e}')
            if not synced:
                logger.error(f'Unable to sync commands for guild {guild.id}')
        # Also attempt a global sync if supported
        if hasattr(client, 'tree'):
            try:
                await client.tree.sync()
                logger.info('Global command sync attempted via tree.sync')
            except Exception as e:
                logger.warning(f'Global command sync failed: {e}')
        else:
            try:
                await client.sync_commands()
                logger.info('Global command sync attempted via sync_commands')
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
