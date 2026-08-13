from discord import Embed
from ..apis.raidbots import RaidBots
from . import ItemColors, MIST_LOGO_URL, ISSUES_NOTE, FOOTER_DESC

class RaidbotsEmbed:

    @staticmethod
    def create(report_code, success, issue):
        # Setup the Basics
        t = 'Processed Successfully' if success else 'Report Error'
        embed = Embed(title=t, color=ItemColors.Common)

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.description = f'[Report Link]({RaidBots.create_report_link(report_code)}) \n'
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')

        embed.description += 'Finished uploading report to WowAudit.\n'
        embed.description += 'To view the WowAudit Wishlists, follow [this link](https://wowaudit.com/us/illidan/mist/mist/wishlists/overview).\n'

        if not success:
            embed.description += '\nYour report could not be processed due to the following error(s): '
            # Format the error message - handle both list and string inputs
            if isinstance(issue, list):
                error_msg = '\n'.join(str(e) for e in issue) if issue else 'Unknown error'
            else:
                error_msg = str(issue)
            embed.description += f'```{error_msg}```'

        embed.description += f'\n{ISSUES_NOTE}'
            
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        return embed
    