from __future__ import annotations

import discord


class VerificationView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.green, custom_id="verification:confirm")
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from bot.database.repositories.verification_repo import VerificationRepository

        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = VerificationRepository(session)
            settings = await repo.get_settings(interaction.guild.id)

        if settings is None or settings.verified_role_id is None:
            message = interaction.client.localization.translate("verification.not_configured", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            message = interaction.client.localization.translate("verification.member_required", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        role = interaction.guild.get_role(settings.verified_role_id)
        if role is None:
            message = interaction.client.localization.translate("verification.role_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if role in interaction.user.roles:
            message = interaction.client.localization.translate("verification.already_verified", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        await interaction.user.add_roles(role, reason="User completed verification")
        autoroles_cog = interaction.client.get_cog("AutorolesCog")
        if autoroles_cog is not None:
            await autoroles_cog.service.assign_verified_role(  # type: ignore[attr-defined]
                interaction.client,
                interaction.user,
            )
        message = interaction.client.localization.translate("verification.success", language=language, role=role.mention)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)
