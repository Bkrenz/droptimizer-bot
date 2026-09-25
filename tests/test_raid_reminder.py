from datetime import datetime
from zoneinfo import ZoneInfo

from bot.raid_reminder import _next_raid_reminder_time_et, _build_raid_reminder_message

ET = ZoneInfo('America/New_York')


def test_next_raid_reminder_time_et_before_reminder():
    now = datetime(2026, 9, 24, 20, 44, 0, tzinfo=ET)
    assert _next_raid_reminder_time_et(now) == datetime(2026, 9, 24, 20, 45, 0, tzinfo=ET)


def test_next_raid_reminder_time_et_after_reminder():
    now = datetime(2026, 9, 24, 20, 46, 0, tzinfo=ET)
    assert _next_raid_reminder_time_et(now) == datetime(2026, 9, 28, 20, 45, 0, tzinfo=ET)


def test_next_raid_reminder_time_et_skips_non_raid_days():
    now = datetime(2026, 9, 25, 21, 0, 0, tzinfo=ET)  # Friday
    assert _next_raid_reminder_time_et(now) == datetime(2026, 9, 28, 20, 45, 0, tzinfo=ET)


def test_build_raid_reminder_message_mentions_both_roles():
    message = _build_raid_reminder_message('raiders', 'trials')
    assert 'raiders' in message.lower()
    assert 'trials' in message.lower()
    assert "it's raid time bitches" in message.lower()
