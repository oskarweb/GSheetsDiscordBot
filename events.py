import discord

from util import *
from bot import BotImpl


def assign_events(bot: BotImpl):
    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')
        for guild in bot.guilds:
            guild_id = str(guild.id)
            bot.read_cache(guild_id)

    @bot.event
    async def on_guild_join(guild):
        async with bot.lock:
            os.makedirs(os.path.join(GUILDS_DIR, str(guild.id)), exist_ok=True)
