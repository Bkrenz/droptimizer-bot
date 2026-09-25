import sys
import types
from datetime import datetime
from zoneinfo import ZoneInfo


discord = types.ModuleType('discord')
discord.Embed = object
discord.Message = object
discord.Guild = object
discord.File = object
discord.HTTPException = Exception
discord.Forbidden = Exception
discord.Member = object
discord.PermissionOverwrite = object
discord.Interaction = object
discord.ButtonStyle = types.SimpleNamespace(primary=1, secondary=2, danger=3)
discord.utils = types.SimpleNamespace(get=lambda *args, **kwargs: None)
discord.abc = types.SimpleNamespace(GuildChannel=object)

discord_ui = types.ModuleType('discord.ui')

class _DummyView:
    def __init__(self, *args, **kwargs):
        self.children = []

class _DummyModal:
    def __init__(self, *args, **kwargs):
        self.children = []

class _DummyInputText:
    def __init__(self, *args, **kwargs):
        self.value = None
        self.label = kwargs.get('label', '')


discord_ui.View = _DummyView
discord_ui.Modal = _DummyModal
discord_ui.InputText = _DummyInputText
discord_ui.button = lambda *args, **kwargs: (lambda func: func)
discord.ui = discord_ui

commands_mod = types.ModuleType('discord.ext.commands')

class _DummyCogMeta(type):
    def __new__(mcls, clsname, bases, namespace, **kwargs):
        namespace.setdefault('__init__', lambda self, *args, **kwargs: None)
        return super().__new__(mcls, clsname, bases, namespace)


class _DummyCog(metaclass=_DummyCogMeta):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def listener(cls, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class _DummyContext:
    pass


class _DummySlashCommandGroup:
    def __init__(self, *args, **kwargs):
        pass

    def command(self, *args, **kwargs):
        return lambda func: func

    def create_subgroup(self, *args, **kwargs):
        return self


def _command_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

commands_mod.Cog = _DummyCog
commands_mod.Context = _DummyContext
commands_mod.slash_command = _command_decorator
commands_mod.has_permissions = lambda *args, **kwargs: _command_decorator()
commands_mod.command = _command_decorator

# Stub the discord.commands namespace used by the project.
discord_commands = types.ModuleType('discord.commands')
discord_commands.SlashCommandGroup = _DummySlashCommandGroup

# Attach the fake modules before importing the bot code.
sys.modules['discord'] = discord
sys.modules['discord.ext'] = types.ModuleType('discord.ext')
sys.modules['discord.ext.commands'] = commands_mod
sys.modules['discord.commands'] = discord_commands

from bot.cogs.absence_cog import _next_refresh_time_et

ET = ZoneInfo('America/New_York')


def test_next_refresh_time_is_tomorrow_7am_when_after_7am():
    now = datetime(2026, 9, 24, 18, 0, tzinfo=ET)
    expected = datetime(2026, 9, 25, 7, 0, tzinfo=ET)

    assert _next_refresh_time_et(now) == expected


def test_next_refresh_time_is_today_7am_when_before_7am():
    now = datetime(2026, 9, 24, 6, 59, tzinfo=ET)
    expected = datetime(2026, 9, 24, 7, 0, tzinfo=ET)

    assert _next_refresh_time_et(now) == expected
