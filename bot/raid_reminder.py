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
    return f'{raiders_mention} {trials_mention} it\'s raid time bitches'
