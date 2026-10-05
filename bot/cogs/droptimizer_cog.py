import os
import re
import asyncio
import datetime
from zoneinfo import ZoneInfo

import discord
from discord import Embed
from discord.ext import commands

if not hasattr(commands, 'slash_command'):
    def _compat_slash_command(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    commands.slash_command = _compat_slash_command

try:
    from discord.commands import SlashCommandGroup
except ImportError:
    class SlashCommandGroup:
        def __init__(self, *args, **kwargs):
            pass

        def command(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def create_subgroup(self, *args, **kwargs):
            return self

from sqlalchemy import delete, select

from ..models.discord.saved_channels import SavedChannel
from ..models.discord.deprioritized_character import DeprioritizedCharacter
from ..apis.raidbots import RaidBots
from ..apis.wowaudit import WowAudit
from ..apis.loot_optimizer import MAX_ROSTER_SIZE, MYTHIC_DIFFICULTY, ROLE_QUOTAS, format_roster_recommendation_rows, get_boss_item_needs, get_boss_item_upgrade_scores, get_character_role, recommend_roster_with_allocations

ET = ZoneInfo('America/New_York')
FEEDBACK_NAG_TOPIC_MARKER = '[mistbot-feedback-nags:{status}]'
BOSS_AUTOCOMPLETE_CACHE_SECONDS = 900


async def _boss_name_autocomplete(context):
    cog = getattr(context, 'cog', None)
    if cog is None:
        return []
    try:
        boss_names = await cog._get_available_bosses()
    except Exception:
        return []

    query = (getattr(context, 'value', '') or '').casefold()
    matches = [name for name in boss_names if query in name.casefold()]
    option_choice = getattr(discord, 'OptionChoice', None)
    if option_choice is not None:
        return [option_choice(name=name, value=name) for name in matches[:25]]
    return matches[:25]


if hasattr(discord, 'Option'):
    _BOSS_NAME_OPTION = discord.Option(
        str,
        description='Choose a boss from the current Mythic season',
        autocomplete=_boss_name_autocomplete,
    )
else:
    _BOSS_NAME_OPTION = str


def _feedback_nags_enabled(topic: str | None) -> bool:
    if topic is None:
        return True
    match = re.search(r'^\[mistbot-feedback-nags:(on|off)\]$', topic, re.MULTILINE)
    return match is None or match.group(1) == 'on'


def _feedback_nag_topic(topic: str | None, enabled: bool) -> str:
    topic = topic or ''
    topic = re.sub(r'\n?\[mistbot-feedback-nags:(?:on|off)\]$', '', topic).rstrip()
    marker = FEEDBACK_NAG_TOPIC_MARKER.format(status='on' if enabled else 'off')
    return f'{topic}\n{marker}' if topic else marker


def _feedback_nag_message(member_mention: str) -> str:
    messages = [
        'Your feedback thread is feeling lonely. Give it a performance comment before it starts talking to itself.',
        'The raid logs have spoken, and they would like a tiny review from their favorite main character.',
        'Please post your weekly performance comment. Even the combat log is tired of being the only one doing the writing.',
        'Your feedback thread called. It says it has seen your parses and would like to discuss them calmly.',
        'One weekly performance comment, coming right up. It pairs nicely with cooldowns and questionable confidence.',
        'Please update your performance comment before your thread gets marked absent from its own attendance sheet.',
        'The raid may be over, but your feedback assignment has respawned.',
        'Your logs are ready for their character development arc. Please add this week\'s performance comment.',
        'Time to tell us how you performed before the boss gets to write the review first.',
        'Your feedback thread has more empty space than a raid leader\'s five-minute break. Please fill it in.',
        'Please leave your weekly performance comment. The meters are not going to explain themselves.',
        'Your thread is waiting patiently, which is more than we can say for some people waiting on lust.',
        'A weekly performance comment keeps the raid team informed and the accountability goblin unemployed.',
        'Please update your performance notes before your best parse becomes ancient raid history.',
        'Your feedback thread is currently doing zero DPS. Help it contribute with a weekly comment.',
        'The raid has cleared, the loot is distributed, and your performance comment remains the final boss.',
        'Please post your weekly review. It is a low-mechanics encounter with a guaranteed clear.',
        'Your combat log has questions, and this feedback thread is the designated answer box.',
        'Time for your weekly performance comment: dodge the excuses, press submit, and collect zero repair costs.',
        'Your thread is ready for a fresh pull. This one only requires words instead of defensives.',
        'Please add your weekly performance comment before the logs start filing a missing-person report.',
        'The bosses have been analyzed. Now it is your turn to provide the director\'s commentary.',
        'Your performance thread is waiting for content, much like a raid group waiting for the last DPS.',
        'One small comment for you, one giant leap for raid accountability.',
        'Please update your weekly performance comment. The only thing missing from the recap is, well, the recap.',
        'Your logs are not judging you. They are simply taking notes. Please add your thoughts.',
        'This is your friendly reminder to turn last week\'s wipefest into this week\'s thoughtful reflection.',
        'Your feedback thread has survived another reset. Reward it with a performance comment.',
        'Please write up your weekly performance before the raid leader invents a creative interpretation of it.',
        'Your thread is at 0 percent completion and 100 percent potential. The math says it is your turn.',
        'The meters have numbers, the raid has memories, and your feedback thread has an appointment with you.',
        'Please post your weekly performance comment. It is the only encounter where overthinking is extra credit.',
        'Your raid performance deserves a recap, even if it starts with a weird pull.',
        'The feedback boss has entered phase two: politely asking again for your weekly comment.',
        'Please update your thread before it gets a heroic achievement for surviving another empty week.',
        'Your logs are loaded, your excuses are ready, and your weekly performance comment is still in queue.',
        'A fresh week, a fresh comment, and the same heroic commitment to pretending that mechanic was unavoidable.',
        'Please give your feedback thread some attention. It has been standing in the same empty space for a week.',
        'Your weekly comment is ready to be pulled. Remember to bring your best insight and a healthstone.',
        'The raid review is not a mythic boss. One focused attempt should be enough to clear it.',
        'Please post your weekly performance comment before the thread starts asking the raid leader for help.',
        'Beep boop. This bot has detected an empty feedback thread and recommends one comment.',
        'My circuits have reviewed the logs. They recommend adding your perspective before I overheat.',
        'I ran the numbers, and they say your feedback thread is due for a fresh comment.',
        'Beep boop. Your weekly review is ready; no firmware update required.',
        'My reminder subroutine says it is your turn to write. It is very persistent for a few lines of code.',
        'I am a bot, so I cannot parse feelings. I can, however, parse an empty feedback thread.',
    ]
    index = datetime.date.today().toordinal() % len(messages)
    return f'{member_mention} {messages[index]}'


def _detect_thread_owner_from_history(messages, bot_id: int):
    for message in messages:
        if not _is_real_thread_post(message):
            continue
        if getattr(message.author, 'id', None) != bot_id:
            if not getattr(message.author, 'bot', False):
                return getattr(message.author, 'id', None)
            continue
        for user in getattr(message, 'mentions', []):
            if getattr(user, 'id', None) != bot_id:
                return user.id
    return None


def _is_real_thread_post(message) -> bool:
    message_type = getattr(message, 'type', None)
    if message_type is None:
        return True
    type_name = getattr(message_type, 'name', str(message_type).rsplit('.', 1)[-1])
    return type_name in {'default', 'reply', 'thread_starter_message'}


def _has_recent_owner_post(messages, member_id: int, now: datetime.datetime) -> bool:
    latest_post = None
    for message in messages:
        if not _is_real_thread_post(message):
            continue
        if getattr(getattr(message, 'author', None), 'id', None) != member_id:
            continue
        created_at = getattr(message, 'created_at', None)
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=ET)
        else:
            created_at = created_at.astimezone(ET)
        if latest_post is None or created_at > latest_post:
            latest_post = created_at
    return latest_post is not None and now - latest_post < datetime.timedelta(days=7)


def _next_feedback_nag_time_et(now: datetime.datetime | None = None) -> datetime.datetime:
    if now is None:
        now = datetime.datetime.now(ET)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=ET)

    next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now > next_run:
        next_run += datetime.timedelta(days=1)
    return next_run


def _get_team_feedback_forum(guild: discord.Guild):
    raid_category = discord.utils.get(guild.categories, name='Raid Things')
    if raid_category is None:
        return None

    forum = discord.utils.get(raid_category.channels, name='team_feedback')
    return forum if isinstance(forum, discord.ForumChannel) else None


class DroptimizerCog(commands.Cog, name='Droptimizer'):

    def __init__(self, bot):
        self.bot = bot
        self._weekly_nag_sent = {}
        self._boss_names_cache = []
        self._boss_names_cache_at = None
        self._boss_names_cache_lock = asyncio.Lock()
        try:
            self._weekly_nag_task = self.bot.loop.create_task(self._weekly_feedback_nag_loop())
        except Exception:
            self._weekly_nag_task = None

    def cog_unload(self):
        if getattr(self, '_weekly_nag_task', None):
            self._weekly_nag_task.cancel()

    async def _get_available_bosses(self):
        loop = asyncio.get_running_loop()
        if (
            self._boss_names_cache_at is not None
            and loop.time() - self._boss_names_cache_at < BOSS_AUTOCOMPLETE_CACHE_SECONDS
        ):
            return self._boss_names_cache

        async with self._boss_names_cache_lock:
            if (
                self._boss_names_cache_at is not None
                and loop.time() - self._boss_names_cache_at < BOSS_AUTOCOMPLETE_CACHE_SECONDS
            ):
                return self._boss_names_cache
            overview = await WowAudit.get_wishlist_overview()
            character_ids = list(dict.fromkeys(
                character.get('id') for character in overview.get('characters', [])
                if character.get('id') is not None
            ))
            details_by_id = await WowAudit.get_character_wishlists(character_ids)
            boss_names = set()
            for detail in details_by_id.values():
                for instance in detail.get('instances', []):
                    for difficulty_entry in instance.get('difficulties', []):
                        if difficulty_entry.get('difficulty', '').casefold() != MYTHIC_DIFFICULTY.casefold():
                            continue
                        wishlist = difficulty_entry.get('wishlist') or {}
                        boss_names.update(
                            encounter.get('name', '').strip()
                            for encounter in wishlist.get('encounters', [])
                            if encounter.get('name', '').strip()
                        )
            self._boss_names_cache = sorted(boss_names, key=str.casefold)
            self._boss_names_cache_at = loop.time()
            return self._boss_names_cache

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

    async def _delete_forum_thread(self, forum: discord.ForumChannel, thread_name: str, *, member: discord.Member | None = None) -> bool:
        thread = self._find_forum_thread(forum, thread_name)
        if thread is None and member is not None:
            thread = await self._find_forum_thread_for_member(forum, member)
        if thread is None:
            return False
        await thread.delete()
        return True

    async def _delete_channel(self, guild: discord.Guild, channel_name: str, *, member: discord.Member | None = None) -> bool:
        channel = discord.utils.get(guild.channels, name=channel_name)
        if channel is None and member is not None:
            channel = await self._find_channel_for_member(guild, member, category_name='officers')
        if channel is None:
            return False
        await channel.delete()
        return True

    def _trial_channel_name(self, member: discord.Member) -> str:
        return self._normalize_channel_name(member.display_name)

    def _trial_feedback_thread_name(self, member: discord.Member) -> str:
        return f'{member.display_name}'

    def _team_feedback_thread_name(self, member: discord.Member) -> str:
        return f'{member.display_name}'

    async def _find_channel_for_member(self, guild: discord.Guild, member: discord.Member, *, category_name: str | None = None):
        expected_name = self._trial_channel_name(member)
        channel = discord.utils.get(guild.channels, name=expected_name)
        if channel is not None:
            return channel

        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            if category_name is not None and getattr(channel.category, 'name', None) not in {category_name, category_name.lower()}:
                continue
            topic = channel.topic or ''
            if member.display_name.lower() in topic.lower():
                return channel
            if self._normalize_channel_name(member.display_name) in channel.name.lower():
                return channel
        return None

    async def _find_forum_thread_for_member(self, forum: discord.ForumChannel, member: discord.Member):
        if forum is None:
            return None

        expected_names = {self._trial_feedback_thread_name(member), self._team_feedback_thread_name(member)}
        for thread in forum.threads:
            if thread.name in expected_names:
                return thread
            if getattr(thread, 'owner_id', None) == member.id:
                return thread

        for thread in forum.threads:
            starter = await self._get_thread_starter_message(thread)
            if starter is None:
                continue
            if getattr(starter, 'author', None) is not None and starter.author.id == member.id:
                return thread
            if any(getattr(user, 'id', None) == member.id for user in getattr(starter, 'mentions', [])):
                return thread
            content = getattr(starter, 'content', '') or ''
            if member.display_name.lower() in content.lower() or f'<@{member.id}>' in content:
                return thread
        return None

    droptimizer = SlashCommandGroup('droptimizer', 'Droptimizer Commands')
    dropadmin = droptimizer.create_subgroup('admin', 'Droptimizer Administrative Commands')
    loot = SlashCommandGroup('loot', 'Loot roster optimization commands')

    @loot.command(name='deprioritize', description='Blacklist a WoWAudit character from roster recommendations.')
    @commands.has_permissions(manage_roles=True)
    async def deprioritize_character(self, ctx: commands.Context, character_name: str):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        added = DeprioritizedCharacter.add(ctx.guild.id, character_name)
        if added:
            await ctx.respond(f'{character_name} is now blacklisted from roster recommendations.', ephemeral=True)
        else:
            await ctx.respond(f'{character_name} is already deprioritized.', ephemeral=True)

    @loot.command(name='prioritize', description='Remove a character from the roster blacklist.')
    @commands.has_permissions(manage_roles=True)
    async def prioritize_character(self, ctx: commands.Context, character_name: str):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        removed = DeprioritizedCharacter.remove(ctx.guild.id, character_name)
        if removed:
            await ctx.respond(f'{character_name} is eligible for roster recommendations again.', ephemeral=True)
        else:
            await ctx.respond(f'{character_name} was not on the deprioritized list.', ephemeral=True)

    @loot.command(name='deprioritized', description='Show characters blacklisted from roster recommendations.')
    @commands.has_permissions(manage_roles=True)
    async def list_deprioritized_characters(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        names = sorted(DeprioritizedCharacter.get_for_guild(ctx.guild.id))
        message = ', '.join(names) if names else 'No characters are blacklisted.'
        await ctx.respond(message, ephemeral=True)

    @loot.command(name='optimize', description='Recommend a 2-tank, 4-healer, 14-DPS roster for a boss.')
    @commands.has_permissions(manage_roles=True)
    async def optimize_loot(self, ctx: commands.Context, boss_name: _BOSS_NAME_OPTION):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        try:
            overview, character_roster = await asyncio.gather(
                WowAudit.get_wishlist_overview(),
                WowAudit.get_characters(),
            )
            roster_by_id = {character['id']: character for character in character_roster}
            roster_records = []
            seen_character_ids = set()
            for character in overview.get('characters', []):
                character_id = character.get('id')
                if character_id is None or character_id in seen_character_ids or not character.get('name'):
                    continue
                roster_records.append(character)
                seen_character_ids.add(character_id)

            if not roster_records:
                await ctx.followup.send('No WoWAudit characters were found in the roster.', ephemeral=True)
                return

            name_counts = {}
            for character in roster_records:
                normalized_name = character['name'].strip().casefold()
                name_counts[normalized_name] = name_counts.get(normalized_name, 0) + 1

            names_by_id = {}
            records_by_id = {}
            for character in roster_records:
                character_id = character['id']
                name = character['name'].strip()
                if name_counts[name.casefold()] > 1:
                    realm = character.get('realm') or character.get('realm_name')
                    if isinstance(realm, dict):
                        realm = realm.get('name')
                    name = f'{name} ({realm or character_id})'
                names_by_id[character_id] = name
                records_by_id[character_id] = character

            candidate_names = list(names_by_id.values())
            details_by_id = await WowAudit.get_character_wishlists(list(names_by_id))
            needs_by_character = {}
            upgrade_scores_by_character = {}
            roles_by_character = {}
            available_bosses = set()

            for character_id, detail in details_by_id.items():
                character_name = names_by_id[character_id]
                needs_by_character[character_name] = get_boss_item_needs(detail, boss_name)
                upgrade_scores_by_character[character_name] = get_boss_item_upgrade_scores(detail, boss_name)
                character_role = get_character_role(roster_by_id.get(character_id, {}))
                character_role = character_role or get_character_role(records_by_id[character_id]) or get_character_role(detail)
                if character_role is None and isinstance(detail.get('character'), dict):
                    character_role = get_character_role(detail['character'])
                if character_role is not None:
                    roles_by_character[character_name] = character_role
                for instance in detail.get('instances', []):
                    for difficulty_entry in instance.get('difficulties', []):
                        if difficulty_entry.get('difficulty', '').casefold() != MYTHIC_DIFFICULTY.casefold():
                            continue
                        wishlist = difficulty_entry.get('wishlist') or {}
                        available_bosses.update(
                            encounter.get('name', '') for encounter in wishlist.get('encounters', [])
                            if encounter.get('name')
                        )

            if not any(name.casefold() == boss_name.strip().casefold() for name in available_bosses):
                available = ', '.join(sorted(available_bosses)) or 'none found in Mythic wishlists'
                await ctx.followup.send(f'Boss `{boss_name}` was not found in Mythic wishlists. Available: {available}', ephemeral=True)
                return

            self._boss_names_cache = sorted(available_bosses, key=str.casefold)
            self._boss_names_cache_at = asyncio.get_running_loop().time()
            deprioritized = DeprioritizedCharacter.get_for_guild(ctx.guild.id)
            selected, excluded, allocated_items_by_character = recommend_roster_with_allocations(
                candidate_names,
                needs_by_character,
                deprioritized,
                roles_by_character=roles_by_character,
                upgrade_scores_by_character=upgrade_scores_by_character,
            )
            blacklisted_normalized = {name.casefold() for name in deprioritized}
            selected_by_role = {
                role: [name for name in selected if roles_by_character.get(name) == role]
                for role in ROLE_QUOTAS
            }

            result = Embed(title=f'{boss_name} Roster Recommendation', color=0x00a86b)
            role_summary = ', '.join(
                f'{len(selected_by_role[role])}/{target} {role}'
                for role, target in ROLE_QUOTAS.items()
            )
            result.description = f'Mythic | {len(selected)}/{MAX_ROSTER_SIZE} selected from {len(candidate_names)} WoWAudit characters | {role_summary}'
            recommendation_rows = format_roster_recommendation_rows(
                selected,
                roles_by_character,
                needs_by_character,
                upgrade_scores_by_character,
                allocated_items_by_character,
            )
            field_header = 'Player | Role | Loot needs'
            field_rows = []
            field_index = 1
            for row in recommendation_rows:
                candidate_rows = field_rows + [row]
                candidate_value = f'{field_header}\n' + '\n'.join(candidate_rows)
                if len(candidate_value) > 1024 and field_rows:
                    result.add_field(
                        name='Recommended' if field_index == 1 else f'Recommended (continued {field_index})',
                        value=f'{field_header}\n' + '\n'.join(field_rows),
                        inline=False,
                    )
                    field_rows = [row]
                    field_index += 1
                else:
                    field_rows = candidate_rows
            if field_rows:
                result.add_field(
                    name='Recommended' if field_index == 1 else f'Recommended (continued {field_index})',
                    value=f'{field_header}\n' + '\n'.join(field_rows),
                    inline=False,
                )
            if excluded:
                selected_role_counts = {role: len(selected_by_role[role]) for role in ROLE_QUOTAS}
                exclusion_reasons = []
                for name, item_names in excluded.items():
                    role = roles_by_character.get(name)
                    if name.casefold() in blacklisted_normalized:
                        reason = 'blacklisted'
                    elif role is None:
                        reason = 'role unavailable in WoWAudit data'
                    elif item_names:
                        reason = f'item cap ({", ".join(item_names)})'
                    elif selected_role_counts[role] >= ROLE_QUOTAS[role]:
                        reason = f'{role} slots filled'
                    else:
                        reason = 'roster optimization'
                    exclusion_reasons.append(f'{name}: {reason}')
                exclusion_text = '\n'.join(exclusion_reasons)
                result.add_field(name='Not selected', value=exclusion_text[:1024], inline=False)
            await ctx.followup.send(embed=result, ephemeral=True)
        except Exception:
            await ctx.followup.send('Could not retrieve or process the WoWAudit wishlists. Check the API configuration and try again.', ephemeral=True)

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

    @commands.slash_command(description='Create the team feedback forum for officers and raiders.')
    @commands.has_permissions(manage_channels=True)
    async def feedback(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        raid_category = discord.utils.get(ctx.guild.categories, name='Raid Things')
        if raid_category is None:
            await ctx.respond('Could not find a category named `Raid Things`.', ephemeral=True)
            return

        forum = discord.utils.get(ctx.guild.channels, name='team_feedback')
        position = None
        raid_discussion = discord.utils.get(raid_category.channels, name='raid-discussion')
        if raid_discussion is not None:
            position = raid_discussion.position + 1

        forum_kwargs = {
            'name': 'team_feedback',
            'topic': 'Team feedback and discussion forum for Mist Officers, Raiders, and Trials.',
            'category': raid_category
        }
        if position is not None:
            forum_kwargs['position'] = position

        if forum is None:
            try:
                forum = await ctx.guild.create_forum_channel(**forum_kwargs)
            except discord.Forbidden:
                await ctx.respond('Bot does not have permission to create the team_feedback forum.', ephemeral=True)
                return
        else:
            if not isinstance(forum, discord.ForumChannel):
                await ctx.respond('A channel named team_feedback exists but is not a forum.', ephemeral=True)
                return
            if forum.category != raid_category or position is not None:
                try:
                    await forum.edit(category=raid_category, position=position)
                except discord.Forbidden:
                    await ctx.respond('Bot does not have permission to move the team_feedback forum.', ephemeral=True)
                    return

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        role_names = ('Mist Officers', 'Raiders', 'Trials')
        for role_name in role_names:
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role is not None:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_messages=True,
                    create_public_threads=True
                )

        try:
            await forum.edit(overwrites=overwrites)
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to set permissions on the forum.', ephemeral=True)
            return

        general_feedback = self._find_forum_thread(forum, 'General Feedback')
        general_content = (
            'There is something conceptually that some of you have read about with all the recent Ian interviews I am sure but it is the concept of the fact that wow has turned into two different games.\n\n'
            '"There are two games being played in a raid group. There is game 1, which is the game that we built, which is beat the raid boss, clear the dungeon in the time limit. Then there’s game 2, which players have largely created for themselves, which is win DPS meters, beat my performance from last week, get a purple parse, get a gold parse, whatever else. We don’t create that game. But many people are playing it, and it is almost the primary motivation for them."\n\n'
            'The best guilds focus on Game #1. We want everyone to be playing Game #1. This isn\'t to say we don\'t want you to be excited when you are playing exceptionally, but the goal and primary focus should be "How can I play most effectively and not die to kill this boss". A lot of times Game 2 plays into Game 1 when people are playing well they typically perform better and parse looks better anyway. We want to be a Game #1 guild.'
        )

        if general_feedback is None:
            general_feedback = await forum.create_thread(
                name='General Feedback',
                content=general_content
            )

        starter_message = await self._get_thread_starter_message(general_feedback)
        if starter_message is not None:
            try:
                await starter_message.pin()
            except discord.Forbidden:
                await ctx.respond('Could not pin the General Feedback starter message. Permissions may be missing.', ephemeral=True)
                return

        member_template = (
            'This is a place for us and you to express our concerns or triumphs regarding performance. '
            'Please take it upon yourself to get ahead of the hammer if you have a bad night and highlight what was wrong and how you are going to fix it.\n\n'
            'Raid Date:\n'
            'Positive Takeaways:\n'
            'Errors/Challenges:\n'
            'General Thoughts:'
        )

        member_roles = [discord.utils.get(ctx.guild.roles, name=name) for name in role_names]
        member_set = {member for role in member_roles if role is not None for member in role.members}

        created_threads = []
        for member in sorted(member_set, key=lambda m: m.display_name.lower()):
            thread_name = f'{member.display_name}'
            if self._find_forum_thread(forum, thread_name) is not None:
                continue

            thread = await forum.create_thread(
                name=thread_name,
                content=f'{member.mention}\n\n{member_template}'
            )
            created_threads.append(thread)
            starter = await self._get_thread_starter_message(thread)
            if starter is not None:
                try:
                    await starter.pin()
                except discord.Forbidden:
                    pass

        result_embed = Embed(title='Feedback Setup Complete', color=0x00ff00)
        result_embed.add_field(name='Forum', value=forum.mention, inline=False)
        result_embed.add_field(name='General Feedback Post', value=getattr(general_feedback, 'jump_url', getattr(general_feedback, 'url', 'N/A')), inline=False)
        result_embed.add_field(name='Feedback Threads Created', value=str(len(created_threads)), inline=False)
        await ctx.respond(embed=result_embed)

    @commands.slash_command(description='Create a raid forum and boss posts for the specified raid.')
    @commands.has_permissions(manage_channels=True)
    async def raid(self, ctx: commands.Context, raid_name: str, bosses: str):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        forum_name = self._normalize_channel_name(f'{raid_name}')
        existing = discord.utils.get(ctx.guild.channels, name=forum_name)
        if existing is not None:
            await ctx.respond('A channel or forum with that raid name already exists.', ephemeral=True)
            return

        raid_category = discord.utils.get(ctx.guild.categories, name='Raid Things')
        if raid_category is None:
            await ctx.respond('Could not find a category named `Raid Things`.', ephemeral=True)
            return

        position = None
        team_feedback = discord.utils.get(raid_category.channels, name='team_feedback')
        if team_feedback is not None:
            position = team_feedback.position + 1

        try:
            raid_forum = await ctx.guild.create_forum_channel(
                name=forum_name,
                topic=f'Raid forum for {raid_name}',
                category=raid_category,
                position=position
            )
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create the raid forum.', ephemeral=True)
            return

        boss_names = [boss.strip() for boss in bosses.split(',') if boss.strip()]
        created_threads = []

        # Create a shared resources thread that contains the raid template
        resources_template = (
            '```\n'
            'Composition:\n'
            'Video Reference:\n'
            'Raid plan:\n'
            '```'
        )
        try:
            resources_thread = await raid_forum.create_thread(name='raid-resources', content=resources_template)
            created_threads.append(resources_thread)
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create threads in the raid forum.', ephemeral=True)
            return

        # Create a thread per boss; initial content simply repeats the boss name
        for boss_name in boss_names:
            thread = await raid_forum.create_thread(name=boss_name, content=boss_name)
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

    async def _resolve_member_for_thread(self, thread: discord.Thread):
        if thread is None:
            return None

        starter = await self._get_thread_starter_message(thread)
        member = self._member_mentioned_in_message(thread, starter)
        if member is not None:
            return member

        try:
            async for message in thread.history(limit=50, oldest_first=True):
                if not _is_real_thread_post(message):
                    continue
                if getattr(message.author, 'bot', False):
                    member = self._member_mentioned_in_message(thread, message)
                    if member is not None:
                        return member
                    continue
                return thread.guild.get_member(message.author.id) or message.author
        except Exception:
            pass

        return None

    def _member_mentioned_in_message(self, thread: discord.Thread, message):
        if message is None:
            return None

        bot_id = getattr(getattr(self.bot, 'user', None), 'id', None)
        for user in getattr(message, 'mentions', []):
            if getattr(user, 'id', None) == bot_id:
                continue
            member = thread.guild.get_member(user.id)
            if member is not None:
                return member

        content = getattr(message, 'content', '') or ''
        for user_id in re.findall(r'<@!?(\d+)>', content):
            if int(user_id) == bot_id:
                continue
            member = thread.guild.get_member(int(user_id))
            if member is not None:
                return member
        return None

    async def _send_weekly_feedback_nag(self, thread: discord.Thread):
        if thread is None or thread.archived:
            return

        member = await self._resolve_member_for_thread(thread)
        if member is None:
            return

        now = datetime.datetime.now(ET)
        last_sent = self._weekly_nag_sent.get(thread.id)
        if last_sent is not None and now - last_sent < datetime.timedelta(days=7):
            return

        try:
            messages = [message async for message in thread.history(limit=None, oldest_first=False)]
        except Exception:
            messages = []

        if _has_recent_owner_post(messages, member.id, now):
            return

        try:
            await thread.send(_feedback_nag_message(member.mention))
            self._weekly_nag_sent[thread.id] = now
        except Exception:
            pass

    async def _weekly_feedback_nag_loop(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

        while True:
            now = datetime.datetime.now(ET)
            next_run = _next_feedback_nag_time_et(now)
            await asyncio.sleep(max(0, (next_run - now).total_seconds()))
            try:
                for guild in self.bot.guilds:
                    forum = _get_team_feedback_forum(guild)
                    if forum is None or not _feedback_nags_enabled(forum.topic):
                        continue
                    for thread in list(forum.threads):
                        if thread.archived or thread.name.casefold() == 'general feedback':
                            continue
                        await self._send_weekly_feedback_nag(thread)
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    @commands.slash_command(description='Start or stop weekly team feedback reminders for this season.')
    @commands.has_permissions(manage_channels=True)
    async def feedback_nags(self, ctx: commands.Context, enabled: bool):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        forum = _get_team_feedback_forum(ctx.guild)
        if forum is None:
            await ctx.respond('Could not find the `team_feedback` forum in `Raid Things`.', ephemeral=True)
            return

        try:
            await forum.edit(topic=_feedback_nag_topic(forum.topic, enabled))
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to update the team feedback forum.', ephemeral=True)
            return

        state = 'started' if enabled else 'stopped'
        await ctx.respond(f'Weekly team feedback reminders {state}.')

    @commands.slash_command(description='Create the wipefest forum and resources post.')
    @commands.has_permissions(manage_channels=True)
    async def wipefest(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.respond('This command must be run in a guild.', ephemeral=True)
            return

        raid_category = discord.utils.get(ctx.guild.categories, name='Raid Things')
        if raid_category is None:
            await ctx.respond('Could not find a category named `Raid Things`.', ephemeral=True)
            return

        # Position under team_feedback when possible
        position = None
        team_feedback = discord.utils.get(raid_category.channels, name='team_feedback')
        if team_feedback is not None:
            position = team_feedback.position + 1

        try:
            wipe_forum = await ctx.guild.create_forum_channel(
                name='wipefest',
                topic='Wipefest aggregated reports and discussion.',
                category=raid_category,
                position=position
            )
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create the wipefest forum.', ephemeral=True)
            return

        wipe_content = (
            'These reports should be taken with a grain of salt and will never tell the full story but I do think there\'s value in seeing the aggregated data. '
            'Please use these reports to enhance/ give a starting point for your personal feedback channel. Everything is filtered to show up until first 2 deaths unless otherwise stated.'
        )

        try:
            wipe_thread = await wipe_forum.create_thread(name='wipefest-resources', content=wipe_content)
        except discord.Forbidden:
            await ctx.respond('Bot does not have permission to create threads in wipefest forum.', ephemeral=True)
            return

        result = Embed(title='Wipefest Created', color=0x00ff00)
        result.add_field(name='Forum', value=wipe_forum.mention, inline=False)
        result.add_field(name='Resources Thread', value=getattr(wipe_thread, 'jump_url', getattr(wipe_thread, 'url', 'N/A')), inline=False)
        await ctx.respond(embed=result)

    

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

        trial_post_name = f'{member.display_name}'
        trial_post = await trial_feedback_forum.create_thread(
            name=trial_post_name,
            content=(f'Start date: {parsed_start.strftime("%m/%d/%Y")}\n'
                     f'Warcraft Logs: {warcraft_logs_url or "Not found from application."}')
        )

        team_post_name = f'{member.display_name}'
        team_post = await team_feedback_forum.create_thread(
            name=team_post_name,
            content=(f'{member.mention}\n\nThis is a place for us and you to express our concerns or triumphs regarding performance. '
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
        deleted_channel = await self._delete_channel(ctx.guild, trial_channel_name, member=member)
        deleted_feedback = await self._delete_forum_thread(trial_feedback_forum, trial_feedback_name, member=member) if isinstance(trial_feedback_forum, discord.ForumChannel) else False

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
        deleted_team_feedback = await self._delete_forum_thread(team_feedback_forum, team_feedback_name, member=member) if isinstance(team_feedback_forum, discord.ForumChannel) else False

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

        deleted_trial_channel = await self._delete_channel(ctx.guild, trial_channel_name, member=member)
        deleted_trial_feedback = await self._delete_forum_thread(trial_feedback_forum, trial_feedback_name, member=member) if isinstance(trial_feedback_forum, discord.ForumChannel) else False
        deleted_team_feedback = await self._delete_forum_thread(team_feedback_forum, team_feedback_name, member=member) if isinstance(team_feedback_forum, discord.ForumChannel) else False

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
