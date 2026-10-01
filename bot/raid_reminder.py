import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')


def _is_raid_day(day: datetime.date) -> bool:
    """Raid nights are Monday, Tuesday, and Thursday."""
    return day.weekday() in (0, 1, 3)


def _next_raid_reminder_time_et(now: datetime.datetime | None = None) -> datetime.datetime:
    """Return the next Monday/Tuesday/Thursday 8:45 PM ET raid reminder time."""
    if now is None:
        now = datetime.datetime.now(ET)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=ET)

    if _is_raid_day(now.date()):
        next_reminder = now.replace(hour=20, minute=45, second=0, microsecond=0)
        if now < next_reminder:
            return next_reminder
        next_day = now.date() + datetime.timedelta(days=1)
    else:
        next_day = now.date()

    while not _is_raid_day(next_day):
        next_day += datetime.timedelta(days=1)

    return datetime.datetime.combine(next_day, datetime.time(20, 45, tzinfo=ET))


def _build_raid_reminder_message(raiders_mention: str = '@raiders', trials_mention: str = '@trials') -> str:
    jokes = [
        f'{raiders_mention} {trials_mention} time to spend three hours discovering which mechanic our feet have been standing in.',
        f'{raiders_mention} {trials_mention} Mythic raid tonight: where every pull is a learning experience and nobody learns the same lesson twice.',
        f'{raiders_mention} {trials_mention} come make the boss regret having a health bar and the healers regret having eyes.',
        f'{raiders_mention} {trials_mention} the loot is imaginary, the repair bill is real, and the confidence is completely unjustified.',
        f'{raiders_mention} {trials_mention} let\'s go practice the ancient Mythic art of blaming latency with total conviction.',
        f'{raiders_mention} {trials_mention} tonight\'s strategy is simple: dodge the swirls, press defensives, and pretend that pull was intentional.',
        f'{raiders_mention} {trials_mention} assemble for Mythic raiding, where the boss has mechanics and we have opinions.',
        f'{raiders_mention} {trials_mention} raid time: because apparently normal difficulty was not emotionally complicated enough.',
        f'{raiders_mention} {trials_mention} bring your best damage, your second-best excuse, and at least one cooldown you forgot existed.',
        f'{raiders_mention} {trials_mention} the boss is ready, the group is questionable, and someone has already called for a five-minute break.',
        f'{raiders_mention} {trials_mention} it is time to get this raid rolling before the tanks lose their bearings and the DPS lose their minds.',
        f'{raiders_mention} {trials_mention} tonight we are turning incoming damage into outgoing complaints.',
        f'{raiders_mention} {trials_mention} our raid leader has a plan, which means we have approximately eight minutes before improvisation.',
        f'{raiders_mention} {trials_mention} let\'s make some boss pulls and questionable life choices: it is a two-for-one special.',
        f'{raiders_mention} {trials_mention} keep calm and carry on, unless you are a tank, in which case keep aggro and carry everyone.',
        f'{raiders_mention} {trials_mention} Mythic raiding: the only place where standing still is a movement mechanic.',
        f'{raiders_mention} {trials_mention} we have the power, the numbers, and absolutely no idea where that debuff came from.',
        f'{raiders_mention} {trials_mention} come get your weekly dose of heroic effort at Mythic prices.',
        f'{raiders_mention} {trials_mention} tonight we are aiming for a clean kill, but we will accept a memorable wipe.',
        f'{raiders_mention} {trials_mention} the boss has phases, we have phases, and the raid leader has entered their final phase.',
        f'{raiders_mention} {trials_mention} bring your flasks and your flask excuses; tonight is going to be well-rounded.',
        f'{raiders_mention} {trials_mention} our strategy is looking solid, which is raid-speak for nobody has asked a follow-up question yet.',
        f'{raiders_mention} {trials_mention} let us make this encounter less of a boss fight and more of a boss flight.',
        f'{raiders_mention} {trials_mention} the only thing getting depleted faster than our mana is our optimism.',
        f'{raiders_mention} {trials_mention} it is time to show the boss who is in charge, right after we check the dungeon journal again.',
        f'{raiders_mention} {trials_mention} tonight\'s forecast is 100 percent chance of mechanics with scattered patches of panic.',
        f'{raiders_mention} {trials_mention} our DPS is making big hits, our tanks are taking big hits, and our excuses are critting.',
        f'{raiders_mention} {trials_mention} remember: every wipe is just the boss giving us a well-earned opportunity to repair.',
        f'{raiders_mention} {trials_mention} let\'s pull together, because pulling separately is how you accidentally invent a soft enrage.',
        f'{raiders_mention} {trials_mention} the raid is ready to pop off, preferably without popping a cooldown at the wrong time.',
        f'{raiders_mention} {trials_mention} tonight we will be making history, or at least making the combat log interesting.',
        f'{raiders_mention} {trials_mention} if at first you do not succeed, blame the assignment and pull again.',
        f'{raiders_mention} {trials_mention} we are fully geared for success and emotionally geared for a very long trash pack.',
        f'{raiders_mention} {trials_mention} the boss may be immune to reason, but fortunately we are immune to learning.',
        f'{raiders_mention} {trials_mention} it is time to turn teamwork into a group project nobody can drop.',
        f'{raiders_mention} {trials_mention} get ready to make the meters rise and the raid frames develop trust issues.',
        f'{raiders_mention} {trials_mention} tonight\'s pull has everything: action, suspense, and one person asking if lust is up.',
        f'{raiders_mention} {trials_mention} come raid where the mechanics are challenging and the explanations are aggressively optional.',
        f'{raiders_mention} {trials_mention} we are not wiping; we are conducting an extended group teleport.',
        f'{raiders_mention} {trials_mention} let\'s get this party started before the boss mistakes our confidence for competence.',
    ]
    return jokes[abs(hash(datetime.date.today().isoformat())) % len(jokes)]
