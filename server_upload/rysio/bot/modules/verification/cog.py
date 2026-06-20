from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.repositories.verification_repo import VerificationRepository
from bot.modules.verification.views import VerificationView
from bot.utils.access import can_manage_guild


class VerificationGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="verification", description="Verifikation verwalten")

    @app_commands.command(name="status", description="Zeigt den Status des Verifizierungs-Moduls.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("verification.status", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Erstellt oder aktualisiert das Verifikations-Panel.")
    @app_commands.describe(
        channel="Kanal fuer das Verifikations-Panel",
        verified_role="Rolle, die nach erfolgreicher Verifikation vergeben wird",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        verified_role: discord.Role,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message("Der Bot braucht die Berechtigung `Rollen verwalten`.", ephemeral=True)
            return

        if verified_role >= bot_member.top_role:
            await interaction.response.send_message("Diese Rolle ist hoeher oder gleich hoch wie die Bot-Rolle.", ephemeral=True)
            return

        channel_permissions = channel.permissions_for(bot_member)
        if not (channel_permissions.send_messages and channel_permissions.embed_links):
            await interaction.response.send_message(
                "Rysio braucht im ausgewaehlten Channel `Nachrichten senden` und `Links einbetten`.",
                ephemeral=True,
            )
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=interaction.client.localization.translate("verification.panel_title", language=language),  # type: ignore[attr-defined]
            description=interaction.client.localization.translate("verification.panel_description", language=language),  # type: ignore[attr-defined]
            color=discord.Color.green(),
        )
        embed.add_field(
            name=interaction.client.localization.translate("verification.panel_field_name", language=language),  # type: ignore[attr-defined]
            value=interaction.client.localization.translate("verification.panel_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        panel_message = await channel.send(embed=embed, view=VerificationView())

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = VerificationRepository(session)
            await repo.upsert_settings(
                guild_id=interaction.guild.id,
                verification_channel_id=channel.id,
                verified_role_id=verified_role.id,
                panel_message_id=panel_message.id,
                captcha_type="button",
            )

        interaction.client.add_view(VerificationView(), message_id=panel_message.id)  # type: ignore[attr-defined]
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "verification.setup_success",
            language=language,
            channel=channel.mention,
            role=verified_role.mention,
        )
        await interaction.followup.send(message, ephemeral=True)


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(VerificationGroup())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
