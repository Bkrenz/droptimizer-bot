import functools
import json
import logging
import os

from blizzardapi import BlizzardApi


class Blizzard:

    api_client = BlizzardApi(os.getenv('BLIZZ_CLIENT'), os.getenv('BLIZZ_SECRET'))
    boss_list = dict()
    item_list = dict()
    tier_map = dict()

    def load_cache_before(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # update boss list and item list
            with open('resources/blizz_cache.json', 'r') as f:
                cache = json.loads(f.read())
            args[0].boss_list = cache['boss']
            args[0].item_list = cache['item']

            # update tier map
            with open('resources/tier_map.json', 'r') as f:
                args[0].tier_map = json.loads(f.read())
            return func(*args, **kwargs)

        return wrapper

    @classmethod
    @load_cache_before
    def get_boss_from_id(cls, boss_id):
        """ Retrieves boss information from the Blizzard WoW GameData API using the encounter id. """
        if boss_id not in cls.boss_list:
            if boss_id == '-49':
                cls.boss_list[boss_id] = ['Trash', '']
            else:
                boss = cls.api_client.wow.game_data.get_journal_encounter('us', 'en_US', boss_id)
                media = cls.api_client.wow.game_data.get_journal_instance_media('us', 'en_US', boss['instance']['id'])
                cls.boss_list[boss_id] = [boss['name'], media['assets'][0]['value']]
            Blizzard.save_cache(cls.boss_list, cls.item_list)
        return cls.boss_list[boss_id]

    @classmethod
    @load_cache_before
    def get_item_from_id(cls, item_id):
        """ Retrieves item information from the Blizzard WoW GameData API using the item id. """
        if item_id in cls.tier_map:
            item_id = cls.tier_map[item_id]
        if item_id not in cls.item_list:
            item = cls.api_client.wow.game_data.get_item('us', 'en_US', item_id)
            media = cls.api_client.wow.game_data.get_item_media('us', 'en_US', item_id)
            cls.item_list[item_id] = [item['name'], media['assets'][0]['value']]
            Blizzard.save_cache(cls.boss_list, cls.item_list)
            logging.info(
                'Item {0} was retrieved from the Blizzard API and has been added to cache.'.format(item['name']))
        return cls.item_list[item_id]

    @classmethod
    @load_cache_before
    def get_icon_from_item_name(cls, item_name):
        """ Retrieves item icon from blizzard cache. """
        for item in cls.item_list.values():
            if item[0] == item_name:
                return item[1]

    @classmethod
    @load_cache_before
    def get_icon_from_boss_name(cls, boss_name):
        """ Retrieves item icon from blizzard cache. """
        for boss in cls.boss_list.values():
            if boss[0] == boss_name:
                return boss[1]

    @staticmethod
    def save_cache(boss_list, item_list):
        cache = {
            'boss': boss_list,
            'item': item_list
        }
        with open('resources/blizz_cache.json', 'w') as f:
            f.write(json.dumps(cache, indent=4))
