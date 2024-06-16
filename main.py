import discord
from discord.ext import commands
import os, asyncio
from help_cog import help_cog
from music_cog import music_cog
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())
load_dotenv()
TOKEN: str = os.getenv('TOKEN')
# remove the default help command so that we can write out own
bot.remove_command('help')

async def main():
    async with bot:
        await bot.add_cog(help_cog(bot))
        await bot.add_cog(music_cog(bot))
        await bot.start(token=TOKEN)

asyncio.run(main())