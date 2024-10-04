import os

import discord
from discord.ext import commands

from constants import *
from util import *
from priority_sheet import PrioritySheet
from bot import BotImpl


def assign_commands(bot: BotImpl):
    @bot.tree.command(name="set_sheet")
    async def set_sheet(interaction: discord.Interaction, sheet_id: str, range_name: str):
        guild_id = str(interaction.guild.id)

        if not is_valid_sheet_id(sheet_id):
            await interaction.response.send_message("Invalid sheet ID", ephemeral=True)
            return
        if not is_valid_range_name(range_name):
            await interaction.response.send_message("Invalid range", ephemeral=True)
            return

        try:
            with open(os.path.join(GUILDS_DIR, guild_id, SHEET_CACHE_FILE), "w", newline='') as sheet_cache:
                csvwriter = csv.writer(sheet_cache, delimiter=",")
                csvwriter.writerow([sheet_id, range_name])
                bot.guilds_data[guild_id]["sheet"] = {
                    "id": sheet_id,
                    "range_name": range_name
                }
            await interaction.response.send_message("Google Sheets configuration saved successfully.", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"An error occurred.", ephemeral=True)

    @bot.tree.command(name="post_activity")
    @discord.app_commands.describe(
        participants="Comma separated list of participants, no spaces",
        activity="Activity name",
        img1="jpg or png"
    )
    @discord.app_commands.choices(activity=[
        discord.app_commands.Choice(name=name, value=name) for name, value in ACTIVITIES.items()
        ]
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
        async with bot.lock:
            valid_screenshots = [img for img in [img1, img2, img3, img4] if img]
            if not bot.guilds_data[str(interaction.guild.id)]["sheet"]:
                return await interaction.response.send_message("Sheet not configured.")
            for screenshot in valid_screenshots:
                if screenshot.content_type not in ["image/jpeg", "image/png"]:
                    return await interaction.response.send_message("Invalid file type.")
            guild_id = str(interaction.guild.id)

            embeds = []
            for screenshot in valid_screenshots:
                e = discord.Embed(url="https://example.com")
                e.set_author(name=participants)
                e.set_image(url=screenshot.url)
                e.set_footer(text=activity)
                embeds.append(e)
            await interaction.response.send_message(embeds=embeds)  # add embed

            message = await interaction.original_response()
            await message.add_reaction(CHECK_MARK_EMOJI)
            await message.add_reaction(CROSS_MARK_EMOJI)

            cache_activity(guild_id, str(message.id))
            bot.guilds_data[guild_id]["activities_awaiting_approval"].add(message.id)

    @bot.tree.command(name="points")
    @discord.app_commands.checks.cooldown(1, 5)
    async def fetch_points(interaction: discord.Interaction, member: str):
        if not bot.guilds_data[str(interaction.guild.id)]["sheet"]:
            return await interaction.response.send_message("Sheet not configured.")
        with PrioritySheet(
                bot.guilds_data[str(interaction.guild.id)]["sheet"]["id"],
                bot.guilds_data[str(interaction.guild.id)]["sheet"]["range_name"]
        ) as p_sheet:
            if str(member).startswith('<@'):
                member_id = int(member.strip('<@!>'))
                nickname = interaction.guild.get_member(member_id).display_name
            else:
                nickname = member
            if points := p_sheet.get_priority_from_nickname(nickname):
                await interaction.response.send_message(f"{nickname} has {points} points.")
                return
            await interaction.response.send_message(f"{nickname} not found.")

    @fetch_points.error
    @post_activity.error
    async def on_cooldown_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)