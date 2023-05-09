from discord import Embed
from ..models.player import Player

def create_report_list_embed(reports: list):
    # Setup the Basic Info for the Embed
    embed = Embed(title='Droptimizer Reports')
    embed.set_thumbnail(url='resources/images/mist_logo_192.png')

    # Build the main body
    body = ''
    for report in reports:
        player = Player.get_player_by_id(report.player_id)
        body += f'({str(report.report_date)}) {player.name}\n'
    
    embed.description = f'```{body}```'
    

    return embed