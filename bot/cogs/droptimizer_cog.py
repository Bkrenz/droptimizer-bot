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

    def _normalize_channel_name(self, name: str) -> str:
        normalized = name.lower().replace(' ', '-')
        normalized = re.sub(r'[^a-z0-9-]', '', normalized)
        return normalized.strip('-') or 'user'

    def _archive_channel_name(self, name: str) -> str:
        date_str = datetime.date.today().strftime('%Y-%m-%d')
        if name.endswith(f'-{date_str}'):
            return name
        return f'{name}-{date_str}'

    async def _ensure_archive_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        archive_category = discord.utils.get(guild.categories, name='Archive')
        if archive_category is None:
            archive_category = await guild.create_category(name='Archive')
        return archive_category

    def _find_forum_thread(self, forum: discord.ForumChannel, thread_name: str):
        if forum is None:
            return None
        return discord.utils.get(forum.threads, name=thread_name)

    async def _delete_forum_thread(self, forum: discord.ForumChannel, thread_name: str) -> bool:
        thread = self._find_forum_thread(forum, thread_name)
        if thread is None:
            return False
        await thread.delete()
        return True

    async def _delete_channel(self, guild: discord.Guild, channel_name: str) -> bool:
        channel = discord.utils.get(guild.channels, name=channel_name)
        if channel is None:
            return False
        await channel.delete()
        return True

    def _trial_channel_name(self, member: discord.Member) -> str:
        return f'trial-{self._normalize_channel_name(member.display_name)}'

    def _trial_feedback_thread_name(self, member: discord.Member) -> str:
        return f'{member.display_name} • Trial'

    def _team_feedback_thread_name(self, member: discord.Member) -> str:
        return f'{member.display_name} • Team Feedback'

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

    async def _set_read_only(self, channel: discord.abc.GuildChannel):
        overwrite = channel.overwrites_for(channel.guild.default_role)
        overwrite.view_channel = True
        overwrite.send_messages = False
        overwrite.create_public_threads = False
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)

    @commands.slash_command(description='Archive a channel or forum to the Archive category and make it read-only.')
    @commands.has_permissions(manage_channels=True)
    async def archive(self, ctx: commands.Context, target: discord.abc.GuildChannel):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        if isinstance(target, discord.CategoryChannel):
            await ctx.respond('Cannot archive a category. Please provide a text or forum channel.', ephemeral=True)
            return

        archive_category = await self._ensure_archive_category(ctx.guild)
        new_name = self._archive_channel_name(target.name)

        try:
            await target.edit(category=archive_category, name=new_name)
            await self._set_read_only(target)
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to archive that channel.', ephemeral=True)
            return

        await ctx.respond(f'Archived {target.mention} to {archive_category.name} and made it read-only.')

    @commands.slash_command(description='Create the team feedback forum and shared feedback channel for officers and raiders.')
    @commands.has_permissions(manage_channels=True)
    async def feedback(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        forum = discord.utils.get(ctx.guild.channels, name='team_feedback')
        if forum is None:
            try:
                forum = await ctx.guild.create_forum_channel(
                    name='team_feedback',
                    topic='Team feedback and discussion forum for Mist Officers, Raiders, and Trials.'
                )
            except discord.Forbidden:
                await ctx.respond('Bot does not have permission to create the team_feedback forum.', ephemeral=True)
                return

        if not isinstance(forum, discord.ForumChannel):
            await ctx.respond('A channel named team_feedback exists but is not a forum.', ephemeral=True)
            return

        feedback_channel = discord.utils.get(ctx.guild.channels, name='feedback')
        if feedback_channel is None:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
            for role_name in ('Mist Officer', 'Raiders', 'Trials'):
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if role is not None:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

            try:
                feedback_channel = await ctx.guild.create_text_channel(
                    name='feedback',
                    topic='Shared feedback channel for Mist Officers, Raiders, and Trials.',
                    overwrites=overwrites
                )
            except discord.Forbidden:
                await ctx.respond('Bot does not have permission to create the feedback channel.', ephemeral=True)
                return

        general_feedback = self._find_forum_thread(forum, 'General Feedback')
        if general_feedback is None:
            general_feedback = await forum.create_thread(
                name='General Feedback',
                content=('This is a place for us and you to express our concerns or triumphs regarding performance. '
                         'Please take it upon yourself to get ahead of the hammer if you have a bad night and highlight what was wrong and how you are going to fix it.')
            )

        secondary_message = (
            'Raid Date:\n'
            'Positive Takeaways:\n'
            'Errors/Challenges:\n'
            'General Thoughts:\n\n'
            'There is something conceptually that some of you have read about with all the recent Ian interviews I am sure but it is the concept of the fact that wow has turned into two different games.\n\n'
            '"There are two games being played in a raid group. There is game 1, which is the game that we built, which is beat the raid boss, clear the dungeon in the time limit. Then there’s game 2, which players have largely created for themselves, which is win DPS meters, beat my performance from last week, get a purple parse, get a gold parse, whatever else. We don’t create that game. But many people are playing it, and it is almost the primary motivation for them."\n\n'
            'The best guilds focus on Game #1. We want everyone to be playing Game #1. This isn\'t to say we don\'t want you to be excited when you are playing exceptionally, but the goal and primary focus should be "How can I play most effectively and not die to kill this boss". A lot of times Game 2 plays into Game 1 when people are playing well they typically perform better and parse looks better anyway. We want to be a Game #1 guild.'
        )

        try:
            secondary_post = await general_feedback.send(secondary_message)
            await secondary_post.pin()
        except discord.Forbidden:
            await ctx.respond('Could not send or pin the secondary feedback post. Permissions may be missing.', ephemeral=True)
            return

        result_embed = Embed(title='Feedback Setup Complete', color=0x00ff00)
        result_embed.add_field(name='Forum', value=forum.mention, inline=False)
        result_embed.add_field(name='Feedback Channel', value=feedback_channel.mention if feedback_channel else 'N/A', inline=False)
        result_embed.add_field(name='General Feedback Post', value=getattr(general_feedback, 'jump_url', getattr(general_feedback, 'url', 'N/A')), inline=False)
        await ctx.respond(embed=result_embed)

    @commands.slash_command(description='Create a raid forum and boss posts for the specified raid and season.')
    @commands.has_permissions(manage_channels=True)
    async def raid(self, ctx: commands.Context, raid_name: str, season: str, bosses: str):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        forum_name = self._normalize_channel_name(f'{raid_name}-{season}')
        existing = discord.utils.get(ctx.guild.channels, name=forum_name)
        if existing is not None:
            await ctx.respond('A channel or forum with that raid name already exists.', ephemeral=True)
            return

        raid_category = discord.utils.get(ctx.guild.categories, name='Raids')
        try:
            raid_forum = await ctx.guild.create_forum_channel(
                name=forum_name,
                topic=f'Raid forum for {raid_name} ({season})',
                category=raid_category
            )
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create the raid forum.', ephemeral=True)
            return

        boss_names = [boss.strip() for boss in bosses.split(',') if boss.strip()]
        created_threads = []
        template_content = (
            '**Composition:**\n'
            '- \n\n'
            '**Video Reference:**\n'
            '- \n\n'
            '**Raid plan:**\n'
            '- '
        )
        for boss_name in boss_names:
            thread = await raid_forum.create_thread(name=boss_name, content=template_content)
            created_threads.append(thread)

        result_embed = Embed(title='Raid Forum Created', color=0x00ff00)
        result_embed.add_field(name='Raid Forum', value=raid_forum.mention, inline=False)
        if created_threads:
            result_embed.add_field(name='Boss Threads', value='\n'.join(thread.name for thread in created_threads), inline=False)
        await ctx.respond(embed=result_embed)

    async def _get_thread_starter_message(self, thread: discord.Thread):
        starter = getattr(thread, 'starter_message', None)
        if starter is not None:
            return starter

        if hasattr(thread, 'fetch_message'):
            try:
                return await thread.fetch_message(thread.id)
            except (discord.NotFound, discord.Forbidden):
                pass

        async for message in thread.history(limit=1, oldest_first=True):
            return message
        return None

    @commands.slash_command(description='Update a boss thread template in a raid forum thread.')
    @commands.has_permissions(administrator=True)
    async def bossupdate(
        self,
        ctx: commands.Context,
        forum: discord.ForumChannel,
        thread_name: str,
        composition: str,
        video_reference: str,
        raid_plan: str
    ):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        if not isinstance(forum, discord.ForumChannel):
            await ctx.respond('Please provide a valid forum channel.', ephemeral=True)
            return

        thread = self._find_forum_thread(forum, thread_name)
        if thread is None:
            await ctx.respond(f'Could not find a thread named `{thread_name}` in {forum.mention}.', ephemeral=True)
            return

        starter_message = await self._get_thread_starter_message(thread)
        if starter_message is None:
            await ctx.respond('Unable to find the starter message for that thread.', ephemeral=True)
            return

        content = (
            f'**Composition:**\n{composition}\n\n'
            f'**Video Reference:**\n{video_reference}\n\n'
            f'**Raid plan:**\n{raid_plan}'
        )

        try:
            await starter_message.edit(content=content)
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to edit the starter message.', ephemeral=True)
            return

        await ctx.respond(f'Updated the template for {thread.mention}.')

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

        channel_name = self._trial_channel_name(member)
        mist_officer_role = discord.utils.get(ctx.guild.roles, name='Mist Officer')
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }
        if mist_officer_role is not None:
            overwrites[mist_officer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        try:
            trial_channel = await ctx.guild.create_text_channel(
                name=channel_name,
                category=officers_category,
                topic=f'Private officer channel for {member.display_name} trial',
                overwrites=overwrites,
                position=0
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
            application_posts = [thread for thread in application_forum.threads if str(member.id) in thread.name or member.display_name.lower() in thread.name.lower()]

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
        trial_post = await trial_feedback_forum.create_thread(
            name=trial_post_name,
            content=(f'Start date: {parsed_start.strftime("%m/%d/%Y")}\n'
                     f'Warcraft Logs: {warcraft_logs_url or "Not found from application."}')
        )

        team_post_name = f'{member.display_name} • Team Feedback'
        team_post = await team_feedback_forum.create_thread(
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

    @commands.slash_command(description='Promote a trial to Raiders and clean up trial artifacts.')
    @commands.has_permissions(manage_roles=True)
    async def promote(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        trial_channel_name = self._trial_channel_name(member)
        trial_feedback_name = self._trial_feedback_thread_name(member)

        trial_feedback_forum = discord.utils.get(ctx.guild.channels, name='trial_feedback')
        deleted_channel = await self._delete_channel(ctx.guild, trial_channel_name)
        deleted_feedback = await self._delete_forum_thread(trial_feedback_forum, trial_feedback_name) if isinstance(trial_feedback_forum, discord.ForumChannel) else False

        trials_role = discord.utils.get(ctx.guild.roles, name='Trials')
        raiders_role = discord.utils.get(ctx.guild.roles, name='Raiders')
        if trials_role and trials_role in member.roles:
            await member.remove_roles(trials_role, reason='Promoted from Trials to Raiders')
        if raiders_role:
            await member.add_roles(raiders_role, reason='Promoted from Trials to Raiders')

        result_embed = Embed(title='Trial Promoted', color=0x00ff00)
        result_embed.add_field(name='Member', value=member.mention, inline=False)
        result_embed.add_field(name='Trial Channel Deleted', value=str(deleted_channel), inline=False)
        result_embed.add_field(name='Trial Feedback Deleted', value=str(deleted_feedback), inline=False)
        await ctx.respond(embed=result_embed)

    @commands.slash_command(description='Retire a Raider to Not104 and delete their team feedback thread.')
    @commands.has_permissions(manage_roles=True)
    async def retire(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        team_feedback_name = self._team_feedback_thread_name(member)
        team_feedback_forum = discord.utils.get(ctx.guild.channels, name='team_feedback')
        deleted_team_feedback = await self._delete_forum_thread(team_feedback_forum, team_feedback_name) if isinstance(team_feedback_forum, discord.ForumChannel) else False

        raiders_role = discord.utils.get(ctx.guild.roles, name='Raiders')
        not104_role = discord.utils.get(ctx.guild.roles, name='Not104')
        if raiders_role and raiders_role in member.roles:
            await member.remove_roles(raiders_role, reason='Retired from Raiders')
        if not104_role:
            await member.add_roles(not104_role, reason='Retired to Not104')

        result_embed = Embed(title='Raider Retired', color=0xffa500)
        result_embed.add_field(name='Member', value=member.mention, inline=False)
        result_embed.add_field(name='Team Feedback Deleted', value=str(deleted_team_feedback), inline=False)
        await ctx.respond(embed=result_embed)

    @commands.slash_command(description='Fail a trial, clean up all trial artifacts, and remove all their roles.')
    @commands.has_permissions(manage_roles=True)
    async def fail(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        trial_channel_name = self._trial_channel_name(member)
        trial_feedback_name = self._trial_feedback_thread_name(member)
        team_feedback_name = self._team_feedback_thread_name(member)

        trial_feedback_forum = discord.utils.get(ctx.guild.channels, name='trial_feedback')
        team_feedback_forum = discord.utils.get(ctx.guild.channels, name='team_feedback')

        deleted_trial_channel = await self._delete_channel(ctx.guild, trial_channel_name)
        deleted_trial_feedback = await self._delete_forum_thread(trial_feedback_forum, trial_feedback_name) if isinstance(trial_feedback_forum, discord.ForumChannel) else False
        deleted_team_feedback = await self._delete_forum_thread(team_feedback_forum, team_feedback_name) if isinstance(team_feedback_forum, discord.ForumChannel) else False

        roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role]
        roles_removed = False
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason='Trial failed cleanup')
                roles_removed = True
            except discord.Forbidden:
                roles_removed = False

        result_embed = Embed(title='Trial Failed', color=0xff0000)
        result_embed.add_field(name='Member', value=member.mention, inline=False)
        result_embed.add_field(name='Trial Channel Deleted', value=str(deleted_trial_channel), inline=False)
        result_embed.add_field(name='Trial Feedback Deleted', value=str(deleted_trial_feedback), inline=False)
        result_embed.add_field(name='Team Feedback Deleted', value=str(deleted_team_feedback), inline=False)
        result_embed.add_field(name='Roles Removed', value=str(roles_removed), inline=False)
        await ctx.respond(embed=result_embed)


def setup(bot):
    bot.add_cog(DroptimizerCog(bot))
