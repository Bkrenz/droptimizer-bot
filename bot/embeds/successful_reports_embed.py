from discord import Embed

def create_successful_reports_embed(successful_reports: list, failed_reports: list):
    # Setup the Basics
    embed = Embed(title='Processed Reports')
    embed.set_thumbnail(url= 'https://raw.githubusercontent.com/Bkrenz/mist-bot/main/resources/images/mist_logo_192.png')
    embed.description = f'Finished processing {len(successful_reports) + len(failed_reports)} reports. \n'

    # Build the list of Successful Reports
    if len(successful_reports) > 0:
        embed.description += '\nSuccessful Reports:```'
        for success in successful_reports:
            embed.description += success + '\n'
        embed.description += '```'

    # Build the list of Successful Reports
    if len(failed_reports) > 0:
        embed.description += '\nFailed Reports:```'
        for failed in failed_reports:
            embed.description += failed + '\n'
        embed.description += '```'

    return embed
