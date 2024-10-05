import os
import csv
import typing
from typing import Dict
from asyncio import Lock
import json
import logging

import discord
from discord.ext import commands

from constants import *
from priority_sheet import PrioritySheet
from util import log_point_change

logger = logging.getLogger(__name__)


class BotImpl(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guilds_data: Dict[str, Dict] = {}
        self.locks: Dict[str, Lock] = {}

    async def setup_hook(self):
        await self.tree.sync()

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild_id = str(payload.guild_id)
        async with self.locks[guild_id]:
            if payload.user_id == self.user.id:
                return

            if payload.message_id in self.guilds_data[guild_id]["activities_awaiting_approval"]:
                try:
                    with PrioritySheet(
                        self.guilds_data[guild_id]["sheet"]["id"],
                        self.guilds_data[guild_id]["sheet"]["range_name"]
                    ) as p_sheet:
                        await self.handle_posted_activity(
                            await self.get_message(payload.channel_id, payload.message_id),
                            payload.emoji,
                            p_sheet
                        )
                except Exception as e:
                    await self.get_channel(payload.channel_id).send(f"Error handling activity{e}")

    async def handle_posted_activity(self, message: discord.Message, emoji: discord.PartialEmoji, p_sheet: PrioritySheet):
        guild_id = str(message.guild.id)
        members = message.embeds[0].author.name
        activity = message.embeds[0].footer.text
        if str(emoji) == CHECK_MARK_EMOJI:
            try:
                p_sheet.update_priority_from_activity(members, activity)
                log_point_change(logger, guild_id, f"Added {activity} points: {members}")
            except ValueError as err:
                return await self.get_channel(message.channel.id).send(f"{err}")
            except Exception:
                return await self.get_channel(message.channel.id).send("Something went wrong.")
            await self.get_channel(message.channel.id).send(
                f"Accepted {message.embeds[0].footer.text} for {message.embeds[0].author.name}"
            )
        elif str(emoji) == CROSS_MARK_EMOJI:
            await self.get_channel(message.channel.id).send(
                f"Refused {message.embeds[0].footer.text} for {message.embeds[0].author.name}"
            )

        guild_id = str(message.guild.id)
        guild_dir = os.path.join(GUILDS_DIR, guild_id)
        with open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE), "r", newline='') as cached_activities,\
                open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE+".temp"), "w", newline='') as temp_activities:
            posted_activities = csv.reader(cached_activities, delimiter=",")
            csvwriter = csv.writer(temp_activities, delimiter=",")
            for activity in posted_activities:
                if len(activity) > 0 and int(activity[0]) != message.id:
                    csvwriter.writerow(activity)
        os.replace(os.path.join(guild_dir, ACTIVITY_CACHE_FILE+".temp"), os.path.join(guild_dir, ACTIVITY_CACHE_FILE))
        self.guilds_data[guild_id]["activities_awaiting_approval"].remove(message.id)
        await message.delete()

    async def get_message(self, channel_id: int, message_id: int):
        channel = await self.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        return message

    def read_cache(self, guild_id: str):
        guild_dir = os.path.join(GUILDS_DIR, guild_id)
        self.guilds_data[guild_id] = {
            "sheet": {},
            "activities_awaiting_approval": set(),
            "roles": {}
        }
        try:
            os.makedirs(guild_dir, exist_ok=False)
        except Exception:
            if os.path.exists(os.path.join(guild_dir, SHEET_CACHE_FILE)):
                with open(os.path.join(guild_dir, SHEET_CACHE_FILE), "r", newline='', encoding="utf-8") as sheet_cache:
                    csvreader = csv.reader(sheet_cache, delimiter=",")
                    for sheet in csvreader:
                        self.guilds_data[guild_id]["sheet"] = {
                            "id": sheet[0],
                            "range_name": sheet[1]
                        }
            if os.path.exists(os.path.join(guild_dir, ACTIVITY_CACHE_FILE)):
                with open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE), "r", newline='', encoding="utf-8") as cached_activities:
                    posted_activities = csv.reader(cached_activities, delimiter=",")
                    for activity in posted_activities:
                        if len(activity) > 0:
                            self.guilds_data[guild_id]["activities_awaiting_approval"].add(int(activity[0]))
            if os.path.exists(os.path.join(guild_dir, ROLES_FILE)):
                with open(os.path.join(guild_dir, ROLES_FILE), "r", encoding="utf-8") as roles_file:
                    self.guilds_data[guild_id].update(json.load(roles_file))

# Class BotImpl

