import os
import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from ..embeds.report_list_embed import create_report_list_embed
from ..droptimizer.droptimizer_service import DroptimizerService
from ..models.sim_report import SimReport

class DroptimizerCog(commands.Cog, name='Droptimizer'):

    def __init__(self, bot):
        self.bot = bot
        self.droptimizer_channel = int(os.getenv('DROPTIMIZER_CHANNEL_ID'))

    droptimizer = SlashCommandGroup('droptimizer', 'Droptimizer Commands')


    @commands.Cog.listener()
    async def on_message(self, message):
        # Check if the message was from this bot, and ignore if so
        if message.author.id == self.bot.user.id:
            return
        
        # Parse all the reports included in the message
        if message.channel.id == self.droptimizer_channel:
            DroptimizerService.add_reports([x for x in message.content.split() if 'https://www.raidbots.com/simbot/report' in x])


    @droptimizer.command(description='Get a list of timestamped player reports.')
    async def reports(self, ctx: commands.Context):
        reports = SimReport.get_reports()
        embed = create_report_list_embed(reports)
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(DroptimizerCog(bot))