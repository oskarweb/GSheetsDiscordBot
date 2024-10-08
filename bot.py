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
from buttons import ActivityPostButtons


class BotImpl(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guilds_data: Dict[str, Dict] = {}
        self.locks: Dict[str, Lock] = {}
        self.global_lock = Lock()
        self.loggers: Dict[str, logging.Logger] = {}
        self.locked_sheets: set = set()

    async def setup_hook(self):
        await self.tree.sync()

    async def load_activities(self, guild_id: str) -> list[str]:
        with PrioritySheet(
                self.guilds_data[guild_id]["sheet"]["activities"]["id"],
                self.guilds_data[guild_id]["sheet"]["activities"]["range_name"]
        ) as p_sheet:
            return [row[0] for row in p_sheet.get_sheet_values()]

    async def load_members(self, guild_id: str) -> list[str]:
        with PrioritySheet(
                self.guilds_data[guild_id]["sheet"]["members"]["id"],
                self.guilds_data[guild_id]["sheet"]["members"]["range_name"]
        ) as p_sheet:
            return [row[0] for row in p_sheet.get_sheet_values()]

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild_id = str(payload.guild_id)
        async with self.locks[guild_id]:
            if payload.user_id == self.user.id:
                return

    async def accept_posted_activity(self, message: discord.Message):
        guild_id = str(message.guild.id)
        guild_dir = os.path.join(GUILDS_DIR, guild_id)
        participants = list()
        for field in message.embeds[0].fields:
            participants.extend(field.value.split(", "))
        participants_str = ", ".join(participants)
        activity = message.embeds[0].footer.text
        names_values = [(name, 1) for name in participants]
        try:
            with PrioritySheet(
                self.guilds_data[guild_id]["sheet"]["activities_write"]["id"],
                self.guilds_data[guild_id]["sheet"]["activities_write"]["range_name"]
            ) as p_sheet:
                await p_sheet.activity_update(
                    activity,
                    names_values,
                    self.guilds_data[guild_id]["sheet"]["members"],
                    self.guilds_data[guild_id]["sheet"]["activities"]
                )
                self.log_change(guild_id, f"activity post accepted: {activity} for: {participants}")
        except ValueError as err:
            return await self.get_channel(message.channel.id).send(f"{err}")
        except Exception:
            return await self.get_channel(message.channel.id).send("Something went wrong.")
        await self.get_channel(message.channel.id).send(
            f"Accepted {message.embeds[0].footer.text} for {participants_str}"
        )
        guild_dir = os.path.join(GUILDS_DIR, guild_id)
        with open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE), "r", newline='') as cached_activities, \
                open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE + ".temp"), "w", newline='') as temp_activities:
            posted_activities = csv.reader(cached_activities, delimiter=",")
            csvwriter = csv.writer(temp_activities, delimiter=",")
            for activity in posted_activities:
                if len(activity) > 0 and int(activity[0]) != message.id:
                    csvwriter.writerow(activity)
        os.replace(os.path.join(guild_dir, ACTIVITY_CACHE_FILE + ".temp"), os.path.join(guild_dir, ACTIVITY_CACHE_FILE))
        self.guilds_data[guild_id]["activities_awaiting_approval"].remove(message.id)
        await message.delete()

    async def deny_posted_activity(self, message: discord.Message):
        guild_id = str(message.guild.id)
        guild_dir = os.path.join(GUILDS_DIR, guild_id)
        participants = list()
        for field in message.embeds[0].fields:
            participants.extend(field.value.split(", "))
        participants_str = ", ".join(participants)

        await self.get_channel(message.channel.id).send(
            f"Refused {message.embeds[0].footer.text} for {participants_str}"
        )

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
            "activities_awaiting_approval": set(),
            "sheet": {}
        }
        try:
            os.makedirs(guild_dir, exist_ok=False)
        except Exception:
            if os.path.exists(os.path.join(guild_dir, SHEET_FILE)):
                with open(os.path.join(guild_dir, SHEET_FILE), "r", newline='', encoding="utf-8") as sheet_file:
                    self.guilds_data[guild_id]["sheet"] = json.load(sheet_file)
            if os.path.exists(os.path.join(guild_dir, ACTIVITY_CACHE_FILE)):
                with open(os.path.join(guild_dir, ACTIVITY_CACHE_FILE), "r", newline='', encoding="utf-8") as cached_activities:
                    posted_activities = csv.reader(cached_activities, delimiter=",")
                    for activity in posted_activities:
                        if len(activity) > 0:
                            message_id = int(activity[0])
                            self.guilds_data[guild_id]["activities_awaiting_approval"].add(message_id)
                            view = ActivityPostButtons()
                            view.set_bot(self)
                            self.add_view(view, message_id=message_id)
            if os.path.exists(os.path.join(guild_dir, ROLES_FILE)):
                with open(os.path.join(guild_dir, ROLES_FILE), "r", encoding="utf-8") as roles_file:
                    self.guilds_data[guild_id].update(json.load(roles_file))
            if os.path.exists(LOCKED_SHEETS):
                with open(LOCKED_SHEETS, "r") as locked_sheets:
                    locked_sheets = csv.reader(locked_sheets, delimiter=",")
                    for sheet_id in locked_sheets:
                        if len(sheet_id) > 0:
                            self.locked_sheets.add(sheet_id[0])

    def setup_logger_for_guild(self, guild_id: str):
        if guild_id not in self.loggers:
            logger = logging.getLogger(f'guild_{guild_id}')
            logger.setLevel(logging.INFO)
            guild_log_dir = os.path.join(GUILDS_DIR, guild_id)
            os.makedirs(guild_log_dir, exist_ok=True)

            file_handler = logging.FileHandler(os.path.join(guild_log_dir, "point_changes.log"))
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            self.loggers[guild_id] = logger

    def get_logger_for_guild(self, guild_id: str) -> logging.Logger:
        self.setup_logger_for_guild(guild_id)
        return self.loggers[guild_id]

    def log_change(self, guild_id: str, msg: str):
        self.get_logger_for_guild(guild_id).info(msg)

    def lock_sheet(self, sheet_id):
        if sheet_id not in self.locked_sheets:
            with open(LOCKED_SHEETS, "a") as locked_sheets:
                csvwriter = csv.writer(locked_sheets, delimiter=",")
                csvwriter.writerow([sheet_id])
            return True
        return False

# Class BotImpl

