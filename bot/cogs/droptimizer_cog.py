import os
import discord
from discord import Embed
from discord.commands import SlashCommandGroup
from discord.ext import commands

from sqlalchemy import delete, select

from ..embeds.report_list_embed import create_report_list_embed
from ..embeds.successful_reports_embed import create_successful_reports_embed
from ..embeds.droptimizer_search_embed import create_player_search_embed
from ..embeds.droptimizer_search_embed import create_item_search_embed
from ..embeds.difficulty_summary_embed import DifficultySummaryEmbed
from ..droptimizer.droptimizer_summary import DroptimizerSummary
from ..droptimizer.droptimizer_service import DroptimizerService
from ..models.sim_report import SimReport
from ..models.sim_item import SimItem
from ..models.item import Item
from ..models.player import Player
from ..models.discord.saved_channels import SavedChannel
from ..models import session

class DroptimizerCog(commands.Cog, name='Droptimizer'):

    def __init__(self, bot):
        self.bot = bot

    droptimizer = SlashCommandGroup('droptimizer', 'Droptimizer Commands')
    dropsearch = droptimizer.create_subgroup('search', 'Droptimizer Search Commands')
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
            reports = [x for x in message.content.split() if 'https://www.raidbots.com/simbot/report' in x]
            if len(reports) == 0:
                return
            
            # Process the Reports
            success, failed = await DroptimizerService.add_reports(reports)

            # Create the Embed
            embed = create_successful_reports_embed(success, failed)
            
            await message.author.send(embed=embed)
            await message.delete()


    @dropadmin.command(description='Get a list of players who submitted reports in the last two weeks.')
    async def reports(self, ctx: commands.Context, days: discord.Option(int) =14):
        '''
        This command displays a list of all reports that have been submitted.
        '''
        reports = SimReport.get_reports(days)
        embed = create_report_list_embed(reports, days)
        await ctx.respond(embed=embed)


    @dropadmin.command(description='Register this channel to listen for droptimizer reports from this discord.')
    async def register(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        SavedChannel.save_channel(guild_id, channel_id, 'Droptimizer')
        reg_embed = Embed(title='Registered Channel')
        reg_embed.description = 'Successfully registered this channel to watch for Droptimizer Reports for this Guild Discord.'
        await ctx.respond(embed=reg_embed)


    @dropadmin.command(description='Get a summary of available upgrades for the specified difficulty.')
    async def summary(self, ctx: commands.Context, difficulty: discord.Option(str, required=True, choices=['Mythic', 'Heroic', 'Normal']), min_val: discord.Option(int) =500):
        data = await DroptimizerSummary.get_difficulty_summary(difficulty, min_val)
        embed = DifficultySummaryEmbed.get_difficulty_summary_embed(difficulty, data)
        await ctx.respond(embed=embed)

    
    @dropsearch.command(description='Get the list of players with upgrades for a specific item.')
    async def player(self, ctx: commands.Context, player: str, difficulty: discord.Option(str, required=True, choices=['Mythic', 'Heroic', 'Normal'])):
        embed = create_player_search_embed(player, difficulty)
        await ctx.respond(embed=embed)
    

    @dropsearch.command(description='Get the list of players that benefit from this item.')
    async def item(self, ctx: commands.Context, item: str, difficulty: discord.Option(str, required=True, choices=['Mythic', 'Heroic', 'Normal']) ='Normal'):
        embed = create_item_search_embed(item, difficulty)
        await ctx.respond(embed=embed)


    @dropsearch.command(description='Get a list of items that match the input.')
    async def items(self, ctx: commands.Context, item:str):
        items = Item.get_items_by_partial_name(item)
        embed=discord.Embed(title=f'Search: {item}')
        embed.description='```'
        for it in items:
            embed.description += f'({it.item_id}) {it.name}\n'
        embed.description += '```'
        await ctx.respond(embed=embed)


    @dropadmin.command(description='Delete a player and its associated data.')
    async def delete_player(self, ctx: commands.Context, name: str):
        player = Player.get_player_by_name(name)
        if player is None:
            await ctx.respond(f'No data available for {name}.')
            return
        
        for diff in ['Mythic', 'Heroic', 'Normal']:
            items = SimItem.get_sim_items_for_player(player.id, diff)
            for item in items:
                session.delete(item)
        
        stmt = select(SimReport).where(SimReport.player_id.is_(player.id))
        reports = session.scalars(stmt).all()
        for report in reports:
            session.delete(report)

        session.delete(player)
        session.commit()

        await ctx.respond(f'Deleted data for {name}.')


def setup(bot):
    bot.add_cog(DroptimizerCog(bot))