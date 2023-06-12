from enum import Enum

MIST_LOGO_URL = 'https://raw.githubusercontent.com/Bkrenz/droptimizer-bot/main/resources/images/mist_logo_192.png'
FOOTER_DESC = 'Mist Analytics'
ISSUES_NOTE = 'Issues? Report at [Github](https://github.com/Bkrenz/droptimizer-bot)'

class ItemColors:
    Poor = 0x889D9D
    Common = 0xFFFFFF
    Uncommon = 0x1EFF0C
    Rare = 0x0070FF
    Epic = 0xA335EE
    Legendary = 0xFF8000
    Heirloom = 0xE6CC80

    @staticmethod
    def get_by_difficulty(diff: str):
        if diff == 'Mythic':
            return ItemColors.Legendary
        elif diff == 'Heroic':
            return ItemColors.Epic
        elif diff == 'Normal':
            return ItemColors.Uncommon
        return ItemColors.Common

class ClassColors:
    DeathKnight = 0xC41E3A
    DemonHunter = 0xA330C9
    Druid = 0xFF7C0A
    Evoker = 0x33937F
    Hunter = 0xAAD372
    Mage = 0x3FC7EB
    Monk = 0x00FF98
    Paladin = 0xF48CBA
    Priest = 0xFFFFFF
    Rogue = 0xFFF468
    Shaman = 0x0070DD
    Warlock = 0x8788EE
    Warrior = 0xC69B6D

