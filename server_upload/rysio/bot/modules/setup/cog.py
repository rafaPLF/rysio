from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.setup.service import SetupMessageService
from bot.utils.access import can_manage_guild
from bot.utils.permissions import get_missing_core_permissions


class SetupGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="setup", description="Grundkonfiguration des Bots")

    @app_commands.command(name="status", description="Zeigt die aktuelle Grundkonfiguration an.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        text = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "setup.status",
            language=language,
            language_code=language,
        )
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="check", description="Prueft, ob Rysio die wichtigsten Berechtigungen hat.")
    async def check(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        missing = get_missing_core_permissions(interaction.guild, bot_member)
        if not missing:
            message = interaction.client.localization.translate("setup.check_ok", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "setup.check_missing",
            language=language,
            permissions=", ".join(missing),
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="language", description="Setzt die Sprache fuer diesen Server.")
    @app_commands.describe(language="Aktuell unterstuetzt: de, en")
    async def language(self, interaction: discord.Interaction, language: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        normalized = language.lower().strip()
        if normalized not in {"de", "en"}:
            await interaction.response.send_message("Aktuell sind nur `de` und `en` verfuegbar.", ephemeral=True)
            return

        await interaction.client.guild_config.set_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            normalized,
        )
        text = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "setup.language_updated",
            language=normalized,
            language_code=normalized,
        )
        await interaction.response.send_message(text, ephemeral=True)


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.message_service = SetupMessageService()
        self.bot.tree.add_command(SetupGroup())

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.bot.guild_config.ensure_guild(self.bot.database, guild.id)  # type: ignore[attr-defined]
        target_channel = guild.system_channel
        if target_channel is None:
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages and permissions.embed_links:
                    target_channel = channel
                    break

        if target_channel is not None:
            try:
                await self.message_service.send_join_prompt(self.bot, guild, target_channel)
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupCog(bot))
