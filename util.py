import os
import re
import csv

import discord

from constants import *


def is_valid_sheet_id(sheet_id: str) -> bool:
    return re.match(r"^[a-zA-Z0-9-_]+$", sheet_id) is not None


def is_valid_range_name(range_name: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_]+![A-Z]+[0-9]+:[A-Z]+[0-9]+$", range_name) is not None


def cache_activity(guild_id: str, message_id: str):
    with open(os.path.join(GUILDS_DIR, guild_id, "activities.csv"), "a") as cached_activities:
        csvwriter = csv.writer(cached_activities, delimiter=",")
        csvwriter.writerow([message_id])


def set_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.members = True
    return intents
