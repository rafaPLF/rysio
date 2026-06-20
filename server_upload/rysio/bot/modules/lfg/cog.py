from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class LFGCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="lfg-status", description="Zeigt den Status des LFG-Moduls.")
    async def lfg_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("LFG-Modul ist bereit.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LFGCog(bot))
