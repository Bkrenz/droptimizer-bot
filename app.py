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

    @client.event
    async def on_ready():
        # Informative log
        print(f'Bot ready: {client.user} (ID: {client.user.id})')
        # Attempt to sync commands to each guild for immediate availability
        for guild in list(client.guilds):
            try:
                await client.tree.sync(guild=guild)
                print(f'Synced commands to guild {guild.id}')
            except Exception as e:
                try:
                    # Some forks expose a different sync API; try fallback
                    await client.sync_commands(guild=discord.Object(id=guild.id))
                    print(f'Synced (fallback) commands to guild {guild.id}')
                except Exception as e2:
                    print(f'Failed to sync commands to guild {guild.id}: {e} / {e2}')
        # Also attempt a global sync (may be slow to propagate)
        try:
            await client.tree.sync()
            print('Global command sync attempted')
        except Exception:
            pass

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
