import datetime
import os
import discord
from discord import Embed
from discord.commands import SlashCommandGroup
from discord.ext import commands

from ..models.absence import Absence

from ..embeds import ItemColors, MIST_LOGO_URL, ISSUES_NOTE, FOOTER_DESC

class AbsenceCog(commands.Cog, name='Absences'):

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(AbsenceView())

    absence_group = SlashCommandGroup('absences', 'Raid Absence Commands')
    absence_admin = absence_group.create_subgroup('admin', 'Absence Admin commands.')

    @commands.slash_command(description='Setup this channel to support Raid Absences.')
    async def setup_absences(self, ctx: commands.Context):
        await ctx.respond("## Use this button to register a new Absence", view=AbsenceView())

    @commands.slash_command(description='Get all registered absences.')
    async def get_absences(self, ctx: commands.Context):
        absences = sorted(Absence.get_absences(), key=lambda x: x.date_begin)
        embed = Embed(title='Upcoming Absences', color=ItemColors.Common)
        for absence in absences:
            embed.add_field(name='ID', value=absence.id)
            embed.add_field(name='Player', value=absence.player)
            b = absence.date_begin.date()
            e = absence.date_end.date()
            d = f'{b.month}/{b.day} - {e.month}/{e.day}'
            embed.add_field(name='Dates', value=d)

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.description = f'\n{ISSUES_NOTE}'
            
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        await ctx.respond(embed=embed)

    @commands.slash_command(description='Delete this absence.')
    async def delete_absence(self, ctx:commands.context, id: int):
        Absence.delete(id)
        embed = Embed(title='Deleted Absence', color=ItemColors.Common)

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        embed.description = f'\n{ISSUES_NOTE}'

        embed.description += f'\nDeleted absence {id}.'

        await ctx.respond(embed=embed)

        



class AbsenceView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Add Absence', style=discord.ButtonStyle.primary, custom_id='button-add-absence')
    async def button_callback(self, button, interaction: discord.Interaction):
        user = interaction.user
        await interaction.response.send_modal(AbsenceModal(title='Add Absence'))

class AbsenceModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        days = []
        self.add_item(discord.ui.InputText(label='Name'))
        self.add_item(discord.ui.InputText(label='Begin Date (mm/dd/yy)',))
        self.add_item(discord.ui.InputText(label='End Date (mm/dd/yy)'))
        self.add_item(discord.ui.InputText(label='Note', max_length=50))

    async def callback(self, interaction: discord.Interaction):
        date_fmt = '%m/%d/%y'
        try:
            embed = discord.Embed(title='Added Absence', color=ItemColors.Common)
            embed.description = ''
            begin_date = datetime.datetime.strptime(self.children[1].value, date_fmt)
            end_date = datetime.datetime.strptime(self.children[2].value, date_fmt)
            absence = Absence(player=self.children[0].value, 
                            date_begin=begin_date, 
                            date_end=end_date, 
                            note=self.children[3].value)
            absence.save()

            embed.add_field(name='ID', value=absence.id)
            embed.add_field(name='Player', value=self.children[0].value)
            embed.add_field(name='Begin', value=begin_date.date())
            embed.add_field(name='End', value=end_date.date())
            embed.add_field(name='Note', value=self.children[3].value)
        except:
            embed = discord.Embed(title='Error', color=ItemColors.Common)
            embed.description = ''
            embed.description += 'Error in data entry, please try again.'

        embed.set_thumbnail(url= MIST_LOGO_URL)
        embed.set_author(name='Mist Guild Tools', url='https://github.com/Bkrenz/droptimizer-bot')
        
        embed.description += f'\n\n{ISSUES_NOTE}'
            
        embed.set_footer(text=FOOTER_DESC, icon_url=MIST_LOGO_URL)

        await interaction.response.send_message(embeds=[embed], view=AbsenceView())
        # await interaction.user.send(embed=embed)


def setup(bot):
    bot.add_cog(AbsenceCog(bot))