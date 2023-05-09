from discord import Embed
from ..models.player import Player

MIST_LOGO_URL = 'https://raw.githubusercontent.com/Bkrenz/mist-bot/main/resources/images/mist_logo_192.png'

def create_report_list_embed(reports: list, days):
    # Setup the Basic Info for the Embed
    embed = Embed(title='Droptimizer Reports')
    embed.set_thumbnail(url=MIST_LOGO_URL)

    # Build the main body
    body = ''
    player_set = set()
    for report in reports:
        player = Player.get_player_by_id(report.player_id)
        player_set.add(player.name)
    
    for p in sorted(player_set):
        body += f'\t{p}\n'

    embed.description = f'Reports processed within the last {days} days: {len(reports)} \n\n ```Players:\n{body}```'

    return embed