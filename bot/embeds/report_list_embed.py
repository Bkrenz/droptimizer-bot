from discord import Embed
from ..models.player import Player
from . import ItemColors, MIST_LOGO_URL

def create_report_list_embed(reports: list, days):
    # Setup the Basic Info for the Embed
    embed = Embed(title='Droptimizer Reports', color=ItemColors.Common)
    embed.set_thumbnail(url=MIST_LOGO_URL)

    # Build the main body
    body = ''
    latest_reports = {}
    for report in reports:
        player = Player.get_player_by_id(report.player_id)
        date = report.report_date.date().strftime('%b %d')
        code = report.report_link.split('/')[5]
        if player in latest_reports:
            if date < latest_reports[player]['date']:
                continue
        latest_reports[player.name] = {'date': date, 'code': code }

    for player in latest_reports:
        date = latest_reports[player]['date']
        code = latest_reports[player]['code']
        body += f' {date} \u2022 {player:12} \u2022 {code}\n'

    embed.description = f'Reports processed within the last {days} days: {len(reports)} \n\n Latest report per player:```{body}```'

    return embed