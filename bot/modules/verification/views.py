from __future__ import annotations

import discord

from bot.database.models.verification import VerificationSettings


async def complete_verification(
    client: discord.Client,
    guild: discord.Guild,
    member: discord.Member,
    *,
    settings: VerificationSettings | None = None,
) -> tuple[bool, str]:
    from bot.database.repositories.verification_repo import VerificationRepository

    language = await client.guild_config.get_language(  # type: ignore[attr-defined]
        client.database,
        guild.id,
    )

    if settings is None:
        async with client.database.session() as session:  # type: ignore[attr-defined]
            repo = VerificationRepository(session)
            settings = await repo.get_settings(guild.id)

    if settings is None or settings.verified_role_id is None:
        message = client.localization.translate("verification.not_configured", language=language)  # type: ignore[attr-defined]
        return False, message

    role = guild.get_role(settings.verified_role_id)
    if role is None:
        message = client.localization.translate("verification.role_missing", language=language)  # type: ignore[attr-defined]
        return False, message

    if role in member.roles:
        message = client.localization.translate("verification.already_verified", language=language)  # type: ignore[attr-defined]
        return False, message

    await member.add_roles(role, reason="User completed verification")
    autoroles_cog = client.get_cog("AutorolesCog")
    if autoroles_cog is not None:
        await autoroles_cog.service.assign_verified_role(  # type: ignore[attr-defined]
            client,
            member,
        )
    message = client.localization.translate("verification.success", language=language, role=role.mention)  # type: ignore[attr-defined]
    return True, message


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

        _, message = await complete_verification(
            interaction.client,
            interaction.guild,
            interaction.user,
            settings=settings,
        )
        await interaction.response.send_message(message, ephemeral=True)
