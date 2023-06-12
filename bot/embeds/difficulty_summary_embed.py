from discord import Embed
import datetime
from . import ItemColors, MIST_LOGO_URL, FOOTER_DESC

class DifficultySummaryEmbed:

    @staticmethod
    def get_difficulty_summary_embed(difficulty: str, data: dict):
        # Setup the Base Embed
        embed = Embed(title=f'Summary for {difficulty}', color=ItemColors.get_by_difficulty(difficulty))
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)
        embed.set_thumbnail(url=MIST_LOGO_URL)

        # Add the Data
        embed.description = ''
        for item in data:
            vals = dict(sorted(data[item].items(), key=lambda item: item[1], reverse=True))
            embed.description += f'\n**{item}**:```\n'
            
            for player in vals:
                embed.description += f'\t{vals[player]} - {player}\n'
            embed.description += '```'
        return embed