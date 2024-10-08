import os
import json

import discord
from discord.ext import commands

from constants import *
from util import *
from priority_sheet import PrioritySheet
from bot import BotImpl
from buttons import ActivityPostButtons


def assign_commands(bot: BotImpl):

    @bot.tree.command(name="post_activity")
    @discord.app_commands.describe(
        participants="Comma separated list of participants(name or dc mention, case insensitive), no spaces",
        activity="Activity name",
        img1="jpg or png"
    )
    @discord.app_commands.checks.cooldown(1, 10)
    async def post_activity(
            interaction: discord.Interaction,
            participants: str,
            activity: str,
            img1: discord.Attachment,
            img2: discord.Attachment = None,
            img3: discord.Attachment = None,
            img4: discord.Attachment = None
    ):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            await interaction.response.defer(ephemeral=False)
            if not bot.guilds_data[guild_id]["sheet"].get("activities"):
                return await interaction.followup.send("Activities not set.", ephemeral=True)
            names_set = set([name.lower() if not name.startswith("<@")
                             else interaction.guild.get_member(int(name.strip("<@!>"))).display_name.lower()
                             for name in participants.split(",")]
                            )

            allowed_activities = [activity.lower() for activity in await bot.load_activities(guild_id)]
            if activity.lower() not in allowed_activities:
                return await interaction.followup.send("Invalid activity.", ephemeral=True)
            members = await bot.load_members(guild_id)
            invalid_names = set()
            names_list = list()

            for member in members:
                if member.lower() in names_set:
                    names_list.append(member)
                    names_set.remove(member.lower())
            if names_set:
                return await interaction.followup.send(f"Invalid names: {','.join(invalid_names)}", ephemeral=True)

            valid_screenshots = [img for img in [img1, img2, img3, img4] if img]
            for screenshot in valid_screenshots:
                if screenshot.content_type not in ["image/jpeg", "image/png"]:
                    return await interaction.followup.send("Invalid file type.", ephemeral=True)
            guild_id = str(interaction.guild.id)

            embeds = []
            for screenshot in valid_screenshots:
                e = discord.Embed(url="https://example.com")
                for idx in range(0, len(names_list), 4):
                    participant_str = ", ".join(names_list[idx:idx + 4])
                    e.add_field(name="", value=participant_str, inline=False)
                e.set_image(url=screenshot.url)
                e.set_footer(text=activity)
                embeds.append(e)
            view = ActivityPostButtons()
            view.set_bot(bot)
            await interaction.followup.send(embeds=embeds, view=view, ephemeral=False)  # add embed

            message = await interaction.original_response()

            cache_activity(guild_id, str(message.id))
            bot.guilds_data[guild_id]["activities_awaiting_approval"].add(message.id)

    @bot.tree.command(name="points")
    @discord.app_commands.checks.cooldown(1, 5)
    async def fetch_points(interaction: discord.Interaction, member: str | None = None):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild.id)
        if not bot.guilds_data[guild_id]["sheet"].get("members"):
            return await interaction.followup.send("Sheet not configured.", ephemeral=True)
        with PrioritySheet(
                bot.guilds_data[guild_id]["sheet"]["members"]["id"],
                bot.guilds_data[guild_id]["sheet"]["members"]["range_name"]
        ) as p_sheet:
            if not member:
                nickname = interaction.user.display_name
            elif member.startswith('<@'):
                member_id = int(member.strip('<@!>'))
                nickname = interaction.guild.get_member(member_id).display_name
            else:
                nickname = member
            try:
                if nick_points := p_sheet.get_priority_from_nickname(nickname):
                    return await interaction.followup.send(f"{nick_points[0]} has {nick_points[1]} points.", ephemeral=True)
            except Exception:
                return await interaction.followup.send(f"Something went wrong.", ephemeral=True)
            await interaction.followup.send(f"{nickname} not found.", ephemeral=True)

    @bot.tree.command(name="add_scouts")
    @discord.app_commands.describe(
        scouts_foods="<Member1:Foods,Member2:Foods> etc."
    )
    @discord.app_commands.checks.cooldown(1, 5)
    async def add_scout(interaction: discord.Interaction, scouts_foods: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            if not bot.guilds_data[guild_id].get("sheet"):
                return await interaction.response.send_message("Sheet not configured.", ephemeral=True)
            with PrioritySheet(
                    bot.guilds_data[guild_id]["sheet"]["members"]["id"],
                    bot.guilds_data[guild_id]["sheet"]["members"]["range_name"]
            ) as p_sheet:
                if not (names_values := parse_names_values(scouts_foods)):
                    return await interaction.response.send_message("Something went wrong.", ephemeral=True)
                try:
                    result = p_sheet.activity_update("Scouting", names_values)
                    bot.log_change(guild_id, f"{interaction.user.display_name} added scout points: {names_values}")
                except Exception:
                    return await interaction.response.send_message("Something went wrong.", ephemeral=True)
                await interaction.response.send_message("Points updated.", ephemeral=True)

    @bot.tree.command(name="add_wb_done")
    @discord.app_commands.describe(
        members_foods="<Member1:Foods,Member2:Foods> etc."
    )
    @discord.app_commands.checks.cooldown(1, 5)
    async def use_common(interaction: discord.Interaction, members_foods: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            if not bot.guilds_data[guild_id].get("sheet"):
                return await interaction.response.send_message("Sheet not configured.", ephemeral=True)
            with PrioritySheet(
                    bot.guilds_data[guild_id]["sheet"]["members"]["id"],
                    bot.guilds_data[guild_id]["sheet"]["members"]["range_name"]
            ) as p_sheet:
                if not (names_values := parse_names_values(members_foods)):
                    return await interaction.response.send_message("Something went wrong.", ephemeral=True)
                try:
                    p_sheet.wb_update(names_values, float(bot.guilds_data[guild_id]["roles"]["common"]), USED_ID)
                    bot.log_change(guild_id, f"{interaction.user.display_name} used points common role: {names_values}")
                except Exception:
                    return await interaction.response.send_message("Something went wrong.", ephemeral=True)
                await interaction.response.send_message("Points updated.", ephemeral=True)

    @bot.tree.command(name="set_roles")
    @discord.app_commands.describe(
        roles_points="<Role1:Points,Role2:Points> etc."
    )
    async def set_roles(interaction: discord.Interaction, roles_points: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            if not bot.guilds_data[guild_id].get("sheet"):
                return await interaction.response.send_message("Sheet not configured.", ephemeral=True)
            if not (roles_values := parse_names_values(roles_points)):
                return await interaction.response.send_message("Something went wrong.", ephemeral=True)
            try:
                role_dict = {"roles": {role: points for role, points in roles_values}}
                bot.guilds_data[guild_id].update(role_dict)
                with open(os.path.join(GUILDS_DIR, guild_id, ROLES_FILE), "w") as roles_file:
                    json.dump(role_dict, roles_file)
                await interaction.response.send_message("Roles updated.", ephemeral=True)
            except Exception:
                await interaction.response.send_message("Something went wrong.", ephemeral=True)

    @bot.tree.command(name="set_activity_load")
    @discord.app_commands.describe(
        sheet_id="Sheet ID",
        range_name="Range name"
    )
    async def set_activity_load(interaction: discord.Interaction, sheet_id: str, range_name: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            await interaction.response.defer()
            if not is_valid_range_name(range_name):
                return await interaction.followup.send("Invalid range", ephemeral=True)
            if not is_valid_sheet_id(sheet_id):
                return await interaction.followup.send("Invalid sheet id", ephemeral=True)

            sheet_dict = {"activities": {"id": sheet_id, "range_name": range_name}}
            bot.write_sheet_file(interaction, guild_id, sheet_id, sheet_dict)
            return await interaction.followup.send("Activities load destination set.", ephemeral=True)

    @bot.tree.command(name="set_members_load")
    async def set_members_load(interaction: discord.Interaction, sheet_id: str, range_name: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            await interaction.response.defer()
            if not is_valid_sheet_id(sheet_id):
                return await interaction.followup.send("Invalid sheet ID", ephemeral=True)
            if not is_valid_range_name(range_name):
                return await interaction.followup.send("Invalid range", ephemeral=True)

            sheet_dict = {"members": {"id": sheet_id, "range_name": range_name}}
            bot.write_sheet_file(interaction, guild_id, sheet_id, sheet_dict)
            return await interaction.followup.send("Members load destination set.", ephemeral=True)

    @bot.tree.command(name="set_activity_write")
    async def set_activity_write(interaction: discord.Interaction, sheet_id: str, range_name: str):
        guild_id = str(interaction.guild.id)
        async with bot.locks[guild_id]:
            await interaction.response.defer()
            if not is_valid_sheet_id(sheet_id):
                return await interaction.followup.send("Invalid sheet ID", ephemeral=True)
            if not is_valid_range_name(range_name):
                return await interaction.followup.send("Invalid range", ephemeral=True)

            sheet_dict = {"activities_write": {"id": sheet_id, "range_name": range_name}}
            bot.write_sheet_file(interaction, guild_id, sheet_id, sheet_dict)
            return await interaction.followup.send("Activities write destination set.", ephemeral=True)

    @fetch_points.error
    @post_activity.error
    @add_scout.error
    @use_common.error
    async def on_cooldown_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)

    @post_activity.autocomplete("activity")
    async def activity_autocomplete(interaction: discord.Interaction, current: str):
        guild_id = str(interaction.guild_id)
        if not bot.guilds_data[guild_id]["sheet"].get("activities"):
            return []
        if activities := await bot.load_activities(guild_id):
            return [
                discord.app_commands.Choice(name=activity, value=activity)
                for activity in activities
                if current.lower() in activity.lower()
            ]
        else:
            return []

