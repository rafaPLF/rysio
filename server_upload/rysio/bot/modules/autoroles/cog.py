from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.autoroles.service import AutoroleService
from bot.utils.access import can_manage_guild


class AutoroleGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="autorole", description="Autoroles verwalten")

    @app_commands.command(name="status", description="Zeigt den Status des Autorole-Moduls.")
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

        if settings is None or not settings.autorole_enabled or settings.autorole_role_id is None:
            message = interaction.client.localization.translate("autoroles.status_disabled", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        role = interaction.guild.get_role(settings.autorole_role_id)
        role_name = role.mention if role else f"`{settings.autorole_role_id}`"
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "autoroles.status_enabled",
            language=language,
            role=role_name,
            mode=settings.autorole_mode,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Konfiguriert die Autorole fuer diesen Server.")
    @app_commands.describe(role="Die Rolle, die automatisch vergeben werden soll", mode="Wann die Rolle vergeben wird")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Beim Beitritt", value="join"),
            app_commands.Choice(name="Nach Verifikation", value="verified"),
        ]
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        mode: app_commands.Choice[str],
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message("Der Bot braucht die Berechtigung `Rollen verwalten`.", ephemeral=True)
            return

        if role >= bot_member.top_role:
            await interaction.response.send_message("Diese Rolle ist hoeher oder gleich hoch wie die Bot-Rolle.", ephemeral=True)
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.client.guild_config.set_autorole(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            role.id,
            mode.value,
            True,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "autoroles.setup_success",
            language=language,
            role=role.mention,
            mode=mode.value,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="disable", description="Deaktiviert die Autorole fuer diesen Server.")
    async def disable(self, interaction: discord.Interaction) -> None:
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
        await interaction.client.guild_config.set_autorole(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            None,
            "join",
            False,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("autoroles.disabled", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)


class AutorolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = AutoroleService()
        self.bot.tree.add_command(AutoroleGroup())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self.service.assign_join_role(self.bot, member)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutorolesCog(bot))
