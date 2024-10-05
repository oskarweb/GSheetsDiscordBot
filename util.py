import os
import re
import csv
import logging

import discord

from constants import *


def is_valid_sheet_id(sheet_id: str) -> bool:
    return re.match(r"^[a-zA-Z0-9-_]+$", sheet_id) is not None


def is_valid_range_name(range_name: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_]+![A-Z]+[0-9]+:[A-Z]+[0-9]+$", range_name) is not None


def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def cache_activity(guild_id: str, message_id: str):
    with open(os.path.join(GUILDS_DIR, guild_id, "activities.csv"), "a") as cached_activities:
        csvwriter = csv.writer(cached_activities, delimiter=",")
        csvwriter.writerow([message_id])


def parse_names_values(names_values: str) -> list[tuple[str, float]] | None:
    names_values_split = names_values.split(",")
    names_values_list = []
    for name_value in names_values_split:
        name_value_split = name_value.split(":")
        if len(name_value_split) != 2 or not is_number(name_value_split[1]):
            return None
        names_values_list.append((name_value_split[0], float(name_value_split[1])))
    return names_values_list


def set_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.members = True
    return intents


def log_point_change(logger: logging.Logger, guild_id: str, msg: str):
    file_handler = logging.FileHandler(os.path.join(GUILDS_DIR, guild_id, "point_changes.log"))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(msg)
    logger.removeHandler(file_handler)

