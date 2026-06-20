from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class PremiumCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="premium-status", description="Zeigt den Status des Premium-Systems.")
    async def premium_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Premium-System ist vorbereitet.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumCog(bot))
