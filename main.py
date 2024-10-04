import os

from events import assign_events
from commands import assign_commands
from bot import BotImpl

from util import set_intents


def main():
    intents = set_intents()

    bot = BotImpl(command_prefix='/', intents=intents)
    assign_commands(bot)
    assign_events(bot)

    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
