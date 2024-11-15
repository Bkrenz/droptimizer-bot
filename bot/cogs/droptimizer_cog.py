import os
import discord
from discord import Embed
from discord.commands import SlashCommandGroup
from discord.ext import commands

from sqlalchemy import delete, select

from ..models.discord.saved_channels import SavedChannel
from ..apis.wowaudit import WowAudit

class DroptimizerCog(commands.Cog, name='Droptimizer'):

    def __init__(self, bot):
        self.bot = bot

    droptimizer = SlashCommandGroup('droptimizer', 'Droptimizer Commands')
    dropadmin = droptimizer.create_subgroup('admin', 'Droptimizer Administrative Commands')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        '''
        This listener is setup to find all Droptimizer Reports submitted to the specified channel
        in the Environment Variables, label DROPTIMIZER_CHANNEL_ID. Multiple reports may be submitted
        in the same message, spaced apart.
        '''
        # Check if the message was from this bot, and ignore if so
        if message.author.id == self.bot.user.id:
            return

        # Parse all the reports included in the message
        if SavedChannel.check_channel_registered(message.channel.id):
            # Get a list of all reports
            raidbots_reports = [x.split('/')[5] for x in message.content.split() if 'raidbots.com/simbot/report' in x]
            qe_live_reports = [x.split('/')[-1] for x in message.content.split() if 'questionablyepic.com/live/upgradereport' in x]
            if (len(qe_live_reports) + len(raidbots_reports)) == 0:
                return

            # Process the Reports
            embed_list = []
            for report in raidbots_reports:
                embed_list.append(await WowAudit.upload_raidbots_report(report))
            for report in qe_live_reports:
                embed_list.append(await WowAudit.upload_qe_live_report(report))

            # Create the Embed
            for em in embed_list:
                await message.author.send(embed=em)
            await message.delete()


    @dropadmin.command(description='Register this channel to listen for droptimizer reports from this discord.')
    async def register(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        SavedChannel.save_channel(guild_id, channel_id, 'Droptimizer')
        reg_embed = Embed(title='Registered Channel')
        reg_embed.description = 'Successfully registered this channel to watch for Droptimizer Reports for this Guild Discord.'
        await ctx.respond(embed=reg_embed)


def setup(bot):
    bot.add_cog(DroptimizerCog(bot))