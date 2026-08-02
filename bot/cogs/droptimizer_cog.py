import os
import re
import datetime
import discord
from discord import Embed
from discord.commands import SlashCommandGroup
from discord.ext import commands

from sqlalchemy import delete, select

from ..models.discord.saved_channels import SavedChannel
from ..apis.raidbots import RaidBots
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

    @commands.slash_command(description='Accept a trial and create the required trial workflow.')
    @commands.has_permissions(manage_roles=True)
    async def trial(self, ctx: commands.Context, member: discord.Member, start_date: str):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        date_fmts = ['%m/%d/%y', '%m/%d/%Y']
        parsed_start = None
        for fmt in date_fmts:
            try:
                parsed_start = datetime.datetime.strptime(start_date, fmt).date()
                break
            except ValueError:
                parsed_start = None

        if parsed_start is None:
            await ctx.respond('Start date must be in mm/dd/yy or mm/dd/yyyy format.', ephemeral=True)
            return

        trials_role = discord.utils.get(ctx.guild.roles, name='Trials')
        if trials_role is None:
            await ctx.respond('Could not find a role named `Trials` in this guild.', ephemeral=True)
            return

        try:
            await member.add_roles(trials_role, reason='Trial accepted via /trial command')
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to assign the Trials role.', ephemeral=True)
            return

        officers_category = discord.utils.get(ctx.guild.categories, name='officers')
        if officers_category is None:
            await ctx.respond('Could not find a category named `officers`.', ephemeral=True)
            return

        channel_name = f'trial-{member.display_name.lower().replace(" ", "-")}'
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }
        try:
            trial_channel = await ctx.guild.create_text_channel(
                name=channel_name,
                category=officers_category,
                topic=f'Private officer channel for {member.display_name} trial',
                overwrites=overwrites
            )
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create the trial channel.', ephemeral=True)
            return

        trial_feedback_forum = discord.utils.get(ctx.guild.channels, name='trial_feedback')
        if trial_feedback_forum is None or not isinstance(trial_feedback_forum, discord.ForumChannel):
            await ctx.respond('Could not find a forum named `trial_feedback`.', ephemeral=True)
            return

        team_feedback_forum = discord.utils.get(ctx.guild.channels, name='team_feedback')
        if team_feedback_forum is None or not isinstance(team_feedback_forum, discord.ForumChannel):
            await ctx.respond('Could not find a forum named `team_feedback`.', ephemeral=True)
            return

        application_forum = discord.utils.get(ctx.guild.channels, name='applications')
        application_posts = []
        if isinstance(application_forum, discord.ForumChannel):
            application_posts = [thread for thread in application_forum.threads if str(member.id) in thread.name]

        warcraft_logs_url = None
        for thread in application_posts:
            async for message in thread.history(limit=50):
                content = message.content or ''
                lower_content = content.lower()
                if 'warcraftlogs' in lower_content or 'warcraftlogs.com' in lower_content:
                    urls = re.findall(r'https?://\S+', content)
                    if urls:
                        warcraft_logs_url = urls[0]
                        break
            if warcraft_logs_url:
                break

        trial_post_name = f'{member.display_name} • Trial'
        trial_post = await trial_feedback_forum.create_post(
            name=trial_post_name,
            content=(f'Start date: {parsed_start.strftime("%m/%d/%Y")}\n'
                     f'Warcraft Logs: {warcraft_logs_url or "Not found from application."}')
        )

        team_post_name = f'{member.display_name} • Team Feedback'
        team_post = await team_feedback_forum.create_post(
            name=team_post_name,
            content=('This is a place for us and you to express our concerns or triumphs regarding performance. '
                     'Please take it upon yourself to get ahead of the hammer if you have a bad night and highlight what was wrong and how you are going to fix it.')
        )

        result_embed = Embed(title='Trial Accepted', color=0x00ff00)
        result_embed.add_field(name='Member', value=member.mention, inline=False)
        result_embed.add_field(name='Trial Channel', value=trial_channel.mention, inline=False)
        result_embed.add_field(name='Trial Feedback Post', value=getattr(trial_post, 'jump_url', getattr(trial_post, 'url', 'N/A')), inline=False)
        result_embed.add_field(name='Team Feedback Post', value=getattr(team_post, 'jump_url', getattr(team_post, 'url', 'N/A')), inline=False)
        await ctx.respond(embed=result_embed)


def setup(bot):
    bot.add_cog(DroptimizerCog(bot))