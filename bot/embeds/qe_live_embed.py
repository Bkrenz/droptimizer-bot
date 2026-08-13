from discord import Embed
import json
from ..apis.raidbots import RaidBots
from . import ItemColors, MIST_LOGO_URL, ISSUES_NOTE, FOOTER_DESC

class QELiveEmbed:

    @staticmethod
    def create(report_code, success, issue):
        # Setup the Basics
        t = 'Processed Successfully' if success else 'Report Error'
        embed = Embed(title=t, color=ItemColors.Common)

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.description = f'[QELive Link](https://questionablyepic.com/live/) \n'

        embed.description += f'Finished uploading report `{report_code}` to WowAudit.\n'
        embed.description += 'To view the WowAudit Wishlists, follow [this link](https://wowaudit.com/us/illidan/mist/mist/wishlists/overview).\n'

        if not success:
            embed.description += '\nYour report could not be processed due to the following error(s): '
            
            # Normalize issue to always be a list
            if isinstance(issue, str):
                # Handle case where issue is a string that might be JSON
                try:
                    parsed = json.loads(issue)
                    issue = parsed if isinstance(parsed, list) else [issue]
                except (json.JSONDecodeError, ValueError):
                    issue = [issue]
            elif not isinstance(issue, list):
                issue = [str(issue)] if issue else ['Unknown error']
            
            # Format error messages
            error_lines = [str(e).strip() for e in issue if e]
            error_msg = '\n'.join(error_lines) if error_lines else 'Unknown error'
            embed.description += f'```{error_msg}```'

        embed.description += f'\n{ISSUES_NOTE}'
            
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        return embed
    