from discord import Embed

from ..models.player import Player
from ..models.sim_item import SimItem
from ..models.item import Item
from ..models.encounter import Encounter


def create_player_search_embed(player_name, difficulty):
    # Get the Player
    player: Player = Player.get_player_by_name(player_name)

    # Get a list of the SimItems for the player
    items = SimItem.get_sim_items_for_player(player.id, difficulty)
    items = sorted(items, reverse=True)

    # Setup the Embed
    embed = Embed(title=f'{player.name} \u2022 {player.spec} \u2022 {difficulty}')
    embed.description = 'Simulated Items: \n```'
    for sim_item in items:
        item = Item.get_item_by_id(sim_item.item)
        embed.description += f'{item.name:20.20} \u2022 {sim_item.value if sim_item.value > 0 else 0:>6d}\n'
    embed.description += '```'

    return embed


def create_item_search_embed(item_name, difficulty):
    #Get the Item
    item = Item.get_item_by_name(item_name)

    # Get the list of SimItems for the Item
    sim_items = SimItem.get_sim_items_for_item(item.id, difficulty)
    sim_items = sorted(sim_items, reverse=True)

    # Setup the Embed
    embed = Embed(title=f'{item.name} \u2022 {difficulty}')
    embed.set_thumbnail(url=item.icon_url)
    embed.description = f'[{item.name}](https://www.wowhead.com/item={item.item_id}) ```'
    for sim_item in sim_items:
        player = Player.get_player_by_id(sim_item.player)
        embed.description += f'{player.name:15} \u2022 {sim_item.value if sim_item.value > 0 else 0:>6d}\n'
    embed.description += '```'

    return embed
