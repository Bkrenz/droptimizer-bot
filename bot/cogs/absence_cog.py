import datetime
import io
import logging
import os
import json
import discord
from discord import Embed
from discord.commands import SlashCommandGroup
from discord.ext import commands

from ..models.absence import Absence

from ..embeds import ItemColors, MIST_LOGO_URL, ISSUES_NOTE, FOOTER_DESC

class AbsenceCog(commands.Cog, name='Absences'):

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(AbsenceView())

    async def _resolve_player_display(self, ctx: commands.Context, player: str) -> str:
        if ctx.guild is None:
            return str(player)
        try:
            pid = int(player)
        except Exception:
            return str(player)

        member = ctx.guild.get_member(pid)
        if member is None:
            try:
                member = await ctx.guild.fetch_member(pid)
            except Exception:
                member = None
        return member.display_name if member is not None else str(player)

    async def _respond_embed_or_file(self, ctx: commands.Context, embed: discord.Embed, file_text: str = None, filename: str = 'output.txt', fallback_message: str = 'Output too large for embed; attached as a file.', ephemeral: bool = False, force_file: bool = False):
        def get_invoker():
            if getattr(ctx, 'author', None) is not None:
                return ctx.author
            if getattr(ctx, 'user', None) is not None:
                return ctx.user
            interaction = getattr(ctx, 'interaction', None)
            if interaction is not None:
                return getattr(interaction, 'user', None)
            return None

        async def send_file(channel_or_user, text, name):
            return await channel_or_user.send(content=fallback_message, file=discord.File(io.BytesIO(text.encode('utf-8')), filename=name))

        if force_file:
            if file_text is None:
                raise ValueError('force_file requires file_text')
            try:
                await ctx.respond(content=fallback_message, file=discord.File(io.BytesIO(file_text.encode('utf-8')), filename=filename), ephemeral=ephemeral)
                return
            except discord.HTTPException as file_error:
                logger = logging.getLogger('discord')
                logger.warning(f'File response failed in channel; attempting DM fallback: {file_error}')
                user = get_invoker()
                if user is None:
                    raise
                try:
                    await send_file(user, file_text, filename)
                    await ctx.respond(content='The output was too large for this channel, so I sent it to your DMs.', ephemeral=True)
                    return
                except discord.HTTPException as dm_error:
                    logger.error(f'Failed to send file fallback via DM: {dm_error}')
                    await ctx.respond(content='Unable to send fallback file in channel or DM.', ephemeral=True)
                    return

        try:
            await ctx.respond(embed=embed, ephemeral=ephemeral)
            return
        except discord.HTTPException as e:
            if file_text is None:
                raise
            logger = logging.getLogger('discord')
            logger.warning(f'Embed response failed with HTTPException, sending file fallback: {e}')
            try:
                await ctx.respond(content=fallback_message, file=discord.File(io.BytesIO(file_text.encode('utf-8')), filename=filename), ephemeral=ephemeral)
                return
            except discord.HTTPException as file_error:
                logger.warning(f'File response failed in channel; attempting DM fallback: {file_error}')
                user = get_invoker()
                if user is None:
                    raise
                try:
                    await send_file(user, file_text, filename)
                    await ctx.respond(content='The output was too large for this channel, so I sent it to your DMs.', ephemeral=True)
                    return
                except discord.HTTPException as dm_error:
                    logger.error(f'Failed to send file fallback via DM: {dm_error}')
                    await ctx.respond(content='Unable to send fallback file in channel or DM.', ephemeral=True)
                    return

    absence_group = SlashCommandGroup('absences', 'Raid Absence Commands')
    absence_admin = absence_group.create_subgroup('admin', 'Absence Admin commands.')

    TRACKED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'tracked_players.json'))

    @commands.slash_command(description='Setup this channel to support Raid Absences.')
    async def setup_absences(self, ctx: commands.Context):
        await ctx.respond("## Use this button to register a new Absence", view=AbsenceView())

    @commands.slash_command(description='Get all registered absences.')
    async def get_absences(self, ctx: commands.Context):
        absences = sorted(Absence.get_absences(), key=lambda x: x.date_begin)
        embed = Embed(title='Upcoming Absences', color=ItemColors.Common)
        embed.description = '```'
        for absence in absences:
            b = absence.date_begin.date()
            e = absence.date_end.date()
            d = f'{b.month}/{b.day} - {e.month}/{e.day}'
            display_name = await self._resolve_player_display(ctx, absence.player)
            embed.description += f'{absence.id} - {display_name} - {d}\n'

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.description += f'```\n{ISSUES_NOTE}'

        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        await ctx.respond(embed=embed)

    @absence_group.command(description='Calculate attendance percentage for a player since a start date.')
    async def attendance(self, ctx: commands.Context, start: str, player: str = None):
        """Compute attendance percentage assuming posted absences are absences and missing posts mean present.

        `start` accepts mm/dd/yy or mm/dd/yyyy. Events occur on Monday, Tuesday, and Thursday.
        If `player` is omitted, computes percentages for every player found in the database.
        """
        # parse start date
        date_fmts = ['%m/%d/%y', '%m/%d/%Y']
        start_date = None
        for fmt in date_fmts:
            try:
                start_date = datetime.datetime.strptime(start, fmt).date()
                break
            except:
                start_date = None

        if start_date is None:
            embed = Embed(title='Invalid Date Format', color=ItemColors.Common)
            embed.description = 'Start date format invalid. Use mm/dd/yy or mm/dd/yyyy.'
            await ctx.respond(embed=embed, ephemeral=True)
            return

        today = datetime.date.today()
        if start_date > today:
            embed = Embed(title='Invalid Start Date', color=ItemColors.Common)
            embed.description = 'Start date is in the future.'
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # count scheduled events (Mon=0, Tue=1, Thu=3)
        event_weekdays = {0, 1, 3}
        total_events = 0
        day = start_date
        event_dates = []
        while day <= today:
            if day.weekday() in event_weekdays:
                total_events += 1
                event_dates.append(day)
            day = day + datetime.timedelta(days=1)

        if total_events == 0:
            embed = Embed(title='No Scheduled Events', color=ItemColors.Common)
            embed.description = 'There are no scheduled events between the given start date and today.'
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # fetch absences overlapping the range for one player or all players
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(today, datetime.time.max)

        players = []
        if player is None:
            # Priority: tracked file -> guild roles -> DB
            try:
                if os.path.exists(self.TRACKED_FILE):
                    with open(self.TRACKED_FILE, 'r', encoding='utf-8') as f:
                        players = json.load(f)
                elif ctx.guild is not None:
                    # Fetch members with roles 'Mist Officer', 'Raiders', 'Trials'
                    role_names = {"Mist Officer", "Raiders", "Trials"}
                    players = []
                    try:
                        members = await ctx.guild.fetch_members(limit=None).flatten()
                    except Exception:
                        members = ctx.guild.members
                    for m in members:
                        if any(r.name in role_names for r in m.roles):
                            players.append(m.id)
                else:
                    players = Absence.get_all_players()
            except Exception:
                players = Absence.get_all_players()
        else:
            players = [player]

        # Resolve tracked IDs or names to display names used in the Absence.player field
        resolved = []
        for p in players:
            # numeric IDs stored as int or numeric strings
            player_keys = [str(p)]
            member_name = None
            try:
                pid = int(p)
            except Exception:
                pid = None

            if pid is not None and ctx.guild is not None:
                try:
                    member = ctx.guild.get_member(pid) or await ctx.guild.fetch_member(pid)
                    if member is not None:
                        member_name = member.display_name
                        player_keys = [str(pid), member.display_name]
                except Exception:
                    member_name = None

            if member_name is None:
                # fall back to using the raw value (likely a display name from old DB entries)
                member_name = str(p)

            resolved.append((player_keys, member_name))

        results = []
        for (orig_p, player_name) in resolved:
            absences = Absence.get_for_player_between(orig_p, start_dt, end_dt)
            absence_ranges = [(a.date_begin.date(), a.date_end.date()) for a in absences]

            missed = 0
            for ev in event_dates:
                covered = False
                for (b, e) in absence_ranges:
                    if b <= ev <= e:
                        covered = True
                        break
                if covered:
                    missed += 1

            present = total_events - missed
            pct = (present / total_events) * 100
            results.append((player_name, total_events, present, missed, pct, absence_ranges))

        # build response
        file_text = None
        if player is None:
            if len(results) > 25:
                file_text = 'Attendance Summary since ' + start_date.strftime('%m/%d/%Y') + '\n'
                for (player_name, tot, pres, missed, pct, _) in results:
                    file_text += f'{player_name}: {pres}/{tot} ({pct:.1f}%)\n'

                embed = Embed(title=f'Attendance Summary since {start_date.strftime("%m/%d/%Y")}', color=ItemColors.Common)
                embed.description = 'Too many players to display in an embed. See attached file.'
                await self._respond_embed_or_file(
                    ctx,
                    embed,
                    file_text=file_text,
                    filename='attendance_summary.txt',
                    force_file=True
                )
                return

            embed = Embed(title=f'Attendance Summary since {start_date.strftime("%m/%d/%Y")}', color=ItemColors.Common)
            file_text = 'Attendance Summary since ' + start_date.strftime('%m/%d/%Y') + '\n'
            for (player_name, tot, pres, missed, pct, _) in results:
                embed.add_field(name=player_name, value=f'{pres}/{tot} ({pct:.1f}%)', inline=True)
                file_text += f'{player_name}: {pres}/{tot} ({pct:.1f}%)\n'
        else:
            player_name, tot, pres, missed, pct, absence_ranges = results[0]
            missed_dates = []
            for ev in event_dates:
                for (b, e) in absence_ranges:
                    if b <= ev <= e:
                        missed_dates.append(ev.strftime('%m/%d/%Y'))
                        break

            embed = Embed(title=f'Attendance for {player_name}', color=ItemColors.Common)
            embed.add_field(name='Start Date', value=start_date.strftime('%m/%d/%Y'))
            embed.add_field(name='End Date', value=today.strftime('%m/%d/%Y'))
            embed.add_field(name='Total Scheduled Events', value=str(tot))
            embed.add_field(name='Present', value=f'{pres} ({pct:.1f}%)')
            embed.add_field(name='Missed', value=str(missed))
            if missed_dates:
                missed_text = '\n'.join(missed_dates)
                if len(missed_text) > 1024:
                    file_text = 'Missed Dates for ' + player_name + ' since ' + start_date.strftime('%m/%d/%Y') + '\n'
                    file_text += missed_text
                    embed.description = 'Missed dates are too large for an embed. See attached file.'
                    await self._respond_embed_or_file(
                        ctx,
                        embed,
                        file_text=file_text,
                        filename='attendance_missed_dates.txt'
                    )
                    return
                embed.add_field(name='Missed Dates', value=missed_text, inline=False)

            file_text = (
                f'Attendance for {player_name}\n'
                f'Start Date: {start_date.strftime("%m/%d/%Y")}\n'
                f'End Date: {today.strftime("%m/%d/%Y")}\n'
                f'Total Scheduled Events: {tot}\n'
                f'Present: {pres} ({pct:.1f}%)\n'
                f'Missed: {missed}\n'
            )
            if missed_dates:
                file_text += '\nMissed Dates:\n' + missed_text

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        await self._respond_embed_or_file(
            ctx,
            embed,
            file_text=file_text,
            filename='attendance.txt'
        )

    @commands.slash_command(description='Delete this absence.')
    async def delete_absence(self, ctx:commands.context, id: int):
        Absence.delete(id)
        embed = Embed(title='Deleted Absence', color=ItemColors.Common)

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.description = f'\n{ISSUES_NOTE}'

        embed.description += f'\nDeleted absence {id}.'

        await ctx.respond(embed=embed)

    @absence_admin.command(description='Delete all absences that end before the given cutoff date. Set confirm=True to execute.')
    @commands.has_permissions(administrator=True)
    async def reset_attendance(self, ctx: commands.Context, cutoff: str):
        """Administrative command to delete absences ending before `cutoff`.

        `cutoff` should be in `mm/dd/yy` or `mm/dd/yyyy` format. This command will
        present an interactive Confirm/Cancel dialog to the command invoker.
        """
        date_fmts = ['%m/%d/%y', '%m/%d/%Y']
        cutoff_dt = None
        for fmt in date_fmts:
            try:
                cutoff_dt = datetime.datetime.strptime(cutoff, fmt)
                break
            except:
                cutoff_dt = None

        if cutoff_dt is None:
            embed = Embed(title='Invalid Date Format', color=ItemColors.Common)
            embed.description = 'Cutoff date format invalid. Use mm/dd/yy or mm/dd/yyyy.'
            await ctx.respond(embed=embed, ephemeral=True)
            return

        embed = Embed(title='Confirm Reset', color=ItemColors.Common)
        embed.description = (f'About to delete absences that end before '
                             f'{cutoff_dt.date().strftime("%m/%d/%Y")}. Click Confirm to proceed or Cancel to abort.')

        view = ResetConfirmView(cutoff_dt=cutoff_dt, requester_id=ctx.author.id)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

    @absence_admin.command(description='Add a player to the tracked player list.')
    @commands.has_permissions(administrator=True)
    async def add_user(self, ctx: commands.Context, name: str):
        """Add a display name to the tracked players JSON file."""
        try:
            players = []
            if os.path.exists(self.TRACKED_FILE):
                with open(self.TRACKED_FILE, 'r', encoding='utf-8') as f:
                    players = json.load(f)
            # try to resolve a guild member to an id
            pid = None
            if ctx.guild is not None:
                # try as mention or id
                try:
                    pid = int(name.strip('<@!>'))
                except Exception:
                    pid = None
                if pid is None:
                    # try find by display name
                    member = discord.utils.get(ctx.guild.members, display_name=name)
                    if member:
                        pid = member.id

            if pid is None:
                await ctx.respond('Provide a Discord user mention, ID, or an exact display name in this guild.', ephemeral=True)
                return

            if pid in players:
                await ctx.respond(f'<@{pid}> is already tracked.', ephemeral=True)
                return
            players.append(pid)
            with open(self.TRACKED_FILE, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2)
            await ctx.respond(f'Added <@{pid}> to tracked players.', ephemeral=True)
        except Exception as e:
            await ctx.respond(f'Error adding user: {e}', ephemeral=True)

    @absence_admin.command(description='Remove a player from the tracked player list.')
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx: commands.Context, name: str):
        """Remove a display name from the tracked players JSON file."""
        try:
            if not os.path.exists(self.TRACKED_FILE):
                await ctx.respond('No tracked players file exists.', ephemeral=True)
                return
            with open(self.TRACKED_FILE, 'r', encoding='utf-8') as f:
                players = json.load(f)
            # resolve provided identifier to an ID
            pid = None
            try:
                pid = int(name.strip('<@!>'))
            except Exception:
                pid = None
            if pid is None and ctx.guild is not None:
                member = discord.utils.get(ctx.guild.members, display_name=name)
                if member:
                    pid = member.id

            if pid is None:
                await ctx.respond('Provide a Discord user mention, ID, or an exact display name in this guild.', ephemeral=True)
                return

            if pid not in players:
                await ctx.respond(f'<@{pid}> is not in tracked players.', ephemeral=True)
                return
            players = [p for p in players if p != pid]
            with open(self.TRACKED_FILE, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2)
            await ctx.respond(f'Removed <@{pid}> from tracked players.', ephemeral=True)
        except Exception as e:
            await ctx.respond(f'Error removing user: {e}', ephemeral=True)

    @absence_admin.command(description='Sync tracked players from Discord roles (Mist Officer, Raiders, Trials).')
    @commands.has_permissions(administrator=True)
    async def sync_users(self, ctx: commands.Context):
        """Populate the tracked players file with members from the configured roles."""
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return
        role_names = {"Mist Officer", "Raiders", "Trials"}
        players = []
        try:
            try:
                members = await ctx.guild.fetch_members(limit=None).flatten()
            except Exception:
                members = ctx.guild.members
            for m in members:
                if any(r.name in role_names for r in m.roles):
                    players.append(m.id)
            # write to file
            os.makedirs(os.path.dirname(self.TRACKED_FILE), exist_ok=True)
            with open(self.TRACKED_FILE, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2)
            await ctx.respond(f'Synced {len(players)} users to tracked players.', ephemeral=True)
        except Exception as e:
            await ctx.respond(f'Error syncing users: {e}', ephemeral=True)

    @absence_admin.command(description='Preview how many absences would be deleted before cutoff (no changes).')
    @commands.has_permissions(administrator=True)
    async def preview_reset(self, ctx: commands.Context, cutoff: str):
        """Return the number of absences that would be deleted for a given cutoff date."""
        date_fmts = ['%m/%d/%y', '%m/%d/%Y']
        cutoff_dt = None
        for fmt in date_fmts:
            try:
                cutoff_dt = datetime.datetime.strptime(cutoff, fmt)
                break
            except:
                cutoff_dt = None

        if cutoff_dt is None:
            embed = Embed(title='Invalid Date Format', color=ItemColors.Common)
            embed.description = 'Cutoff date format invalid. Use mm/dd/yy or mm/dd/yyyy.'
            await ctx.respond(embed=embed, ephemeral=True)
            return

        count = Absence.count_before(cutoff_dt)
        embed = Embed(title='Preview Reset', color=ItemColors.Common)
        embed.description = f'{count} absence(s) would be deleted that ended before {cutoff_dt.date().strftime("%m/%d/%Y")}. '
        await ctx.respond(embed=embed, ephemeral=True)


class ResetConfirmView(discord.ui.View):
    def __init__(self, cutoff_dt: datetime.datetime, requester_id: int):
        super().__init__(timeout=120)
        self.cutoff_dt = cutoff_dt
        self.requester_id = requester_id

    @discord.ui.button(label='Confirm Reset', style=discord.ButtonStyle.danger, custom_id='confirm-reset')
    async def confirm(self, button, interaction: discord.Interaction):
        # Only allow the original requester to confirm
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message('Only the command invoker may confirm this action.', ephemeral=True)
            return

        deleted = Absence.delete_before(self.cutoff_dt)

        # Disable buttons after action
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(title='Reset Complete', color=ItemColors.Common)
        embed.description = f'Deleted {deleted} absence(s) that ended before {self.cutoff_dt.date().strftime("%m/%d/%Y")}. '
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary, custom_id='cancel-reset')
    async def cancel(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message('Only the command invoker may cancel this action.', ephemeral=True)
            return

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(title='Reset Cancelled', color=ItemColors.Common)
        embed.description = 'No changes were made.'
        await interaction.response.edit_message(embed=embed, view=self)


class AbsenceView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Add Absence', style=discord.ButtonStyle.primary, custom_id='button-add-absence')
    async def button_callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(AbsenceModal(title='Add Absence'))

class AbsenceModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label='Begin Date (mm/dd/yy or mm/dd/yyyy)'))
        self.add_item(discord.ui.InputText(label='End Date (mm/dd/yy or mm/dd/yyyy)'))
        self.add_item(discord.ui.InputText(label='Note', max_length=50))

    async def callback(self, interaction: discord.Interaction):
        # Accept two common formats: mm/dd/yy and mm/dd/yyyy
        date_fmts = ['%m/%d/%y', '%m/%d/%Y']
        submitter = interaction.user.display_name
        user_id = interaction.user.id
        try:
            embed = discord.Embed(title='Added Absence', color=ItemColors.Common)
            embed.description = ''
            begin_date = None
            end_date = None
            begin_val = self.children[0].value
            end_val = self.children[1].value
            for fmt in date_fmts:
                if begin_date is None:
                    try:
                        begin_date = datetime.datetime.strptime(begin_val, fmt)
                    except:
                        begin_date = None
                if end_date is None:
                    try:
                        end_date = datetime.datetime.strptime(end_val, fmt)
                    except:
                        end_date = None
            if begin_date is None or end_date is None:
                raise ValueError('Invalid date format')

            today = datetime.datetime.now().date()
            if begin_date.date() < today or end_date.date() < today:
                raise ValueError('You cannot post an abcense in the past.')

            # Always store the actual Discord user ID for the submitting user.
            player_id = str(interaction.user.id)
            absence = Absence(player=player_id,
                            date_begin=begin_date,
                            date_end=end_date,
                            note=self.children[2].value)
            absence.save()

            embed.add_field(name='ID', value=absence.id)
            embed.add_field(name='Player', value=interaction.user.display_name)
            embed.add_field(name='Begin', value=begin_date.date().strftime('%m/%d/%Y'))
            embed.add_field(name='End', value=end_date.date().strftime('%m/%d/%Y'))
            embed.add_field(name='Note', value=self.children[2].value)
        except ValueError as e:
            embed = discord.Embed(title='Error in Absence Submission', color=ItemColors.Common)
            if str(e) == 'You cannot post an abcense in the past.':
                embed.description = str(e)
            else:
                embed.description = ''
                embed.description += 'Error in data entry, please try again. The most likely cause is wrong format of Date — use mm/dd/yy or mm/dd/yyyy. For example, 09/11/01 or 09/11/2001.\n```'
                embed.description += f'Player: {submitter}\n'
                for val in self.children:
                    embed.description += f'{val.label} - {val.value}\n'
                embed.description += '```'
        except:
            embed = discord.Embed(title='Error in Absence Submission', color=ItemColors.Common)
            embed.description = ''
            embed.description += 'Error in data entry, please try again. The most likely cause is wrong format of Date — use mm/dd/yy or mm/dd/yyyy. For example, 09/11/01 or 09/11/2001.\n```'
            embed.description += f'Player: {submitter}\n'
            for val in self.children:
                embed.description += f'{val.label} - {val.value}\n'
            embed.description += '```'

        embed.description += f'Thank you for submission, {submitter} (<@{user_id}>).\n'

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')

        embed.description += f'\n\n{ISSUES_NOTE}'

        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        await interaction.response.send_message(embeds=[embed], view=AbsenceView())


def setup(bot):
    bot.add_cog(AbsenceCog(bot))