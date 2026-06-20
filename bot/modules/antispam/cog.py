from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.antispam.service import AntiSpamService
from bot.utils.access import can_manage_guild


class AntiSpamGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="antispam", description="Anti-Spam verwalten")

    @app_commands.command(name="status", description="Zeigt den Status des Anti-Spam-Moduls.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        settings = await interaction.client.guild_config.get_settings(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        if settings is None or not settings.spam_protection_enabled:
            message = interaction.client.localization.translate("antispam.status_disabled", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "antispam.status_enabled",
            language=language,
            threshold=settings.spam_threshold,
            interval=settings.spam_interval_seconds,
            action=settings.spam_action,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Aktiviert den Flood-Schutz fuer diesen Server.")
    @app_commands.describe(
        threshold="Wie viele Nachrichten erlaubt sind",
        interval_seconds="In welchem Zeitfenster geprueft wird",
        action="Wie der Bot reagieren soll",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Nachricht loeschen + warnen", value="delete_warn"),
            app_commands.Choice(name="Nur warnen", value="warn"),
            app_commands.Choice(name="Nur loeschen", value="delete"),
        ]
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        threshold: app_commands.Range[int, 3, 15],
        interval_seconds: app_commands.Range[int, 3, 30],
        action: app_commands.Choice[str],
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.client.guild_config.set_antispam(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            True,
            threshold,
            interval_seconds,
            action.value,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "antispam.setup_success",
            language=language,
            threshold=threshold,
            interval=interval_seconds,
            action=action.value,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="disable", description="Deaktiviert Anti-Spam fuer diesen Server.")
    async def disable(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        settings = await interaction.client.guild_config.get_settings(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        threshold = settings.spam_threshold if settings else 5
        interval = settings.spam_interval_seconds if settings else 8
        action = settings.spam_action if settings else "delete_warn"

        await interaction.client.guild_config.set_antispam(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            False,
            threshold,
            interval,
            action,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("antispam.disabled", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)


class AntiSpamCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = AntiSpamService()
        self.bot.tree.add_command(AntiSpamGroup())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.service.process_message(self.bot, message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiSpamCog(bot))
