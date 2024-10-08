import discord


class ActivityPostButtons(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = None

    def set_bot(self, bot):
        self.bot = bot

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept_button")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        if self.bot is None:
            return
        async with self.bot.locks[guild_id]:
            if interaction.message.id in self.bot.guilds_data[guild_id]["activities_awaiting_approval"]:
                await interaction.response.defer()
                return await self.bot.accept_posted_activity(interaction.message)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_button")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        if self.bot is None:
            return
        async with self.bot.locks[guild_id]:
            if interaction.message.id in self.bot.guilds_data[guild_id]["activities_awaiting_approval"]:
                await interaction.response.defer()
                return await self.bot.deny_posted_activity(interaction.message)
