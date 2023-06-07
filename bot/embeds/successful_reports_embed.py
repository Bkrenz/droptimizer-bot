from discord import Embed
from . import ItemColors, MIST_LOGO_URL

def create_successful_reports_embed(successful_reports: list, failed_reports: list):
    # Setup the Basics
    embed = Embed(title='Processed Reports', color=ItemColors.Common)
    embed.set_thumbnail(url= MIST_LOGO_URL)
    embed.description = f'Finished processing {len(successful_reports) + len(failed_reports)} reports. \n'

    # Build the list of Successful Reports
    if len(successful_reports) > 0:
        embed.description += '\n**Successful Reports**:\n'
        for success in successful_reports:
            report_code = success['code']
            name = success['player']
            spec = success['spec']
            difficulty = success['difficulty']
            embed.description += f'\t{name} - {spec} \u2022 {difficulty} \u2022 '
            embed.description += f'[Report Link](https://raidbots.com/simbot/report/{report_code})\n'

    # Build the list of Successful Reports
    if len(failed_reports) > 0:
        embed.description += '\n**Failed Reports**:```'
        for failed in failed_reports:
            embed.description += failed + '\n'
        embed.description += '```'
        
    embed.set_footer(text='Mist Analytics | Issues? Contact BKrenz#4028', icon_url=MIST_LOGO_URL)

    return embed
 