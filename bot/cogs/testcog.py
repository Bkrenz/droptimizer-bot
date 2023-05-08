import discord
from discord.ext import commands

class TestCog(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond("Hi, this is a test slash command.")


def setup(bot):
    bot.add_cog(TestCog(bot))
