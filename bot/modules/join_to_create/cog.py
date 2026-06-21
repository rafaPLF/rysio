from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.join_to_create.service import JoinToCreateService
from bot.utils.access import can_manage_guild


class JoinToCreateGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="jtc", description="Join to Create Voice verwalten")

    @app_commands.command(name="status", description="Zeigt den Status von Join to Create.")
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
        if settings is None or not settings.join_to_create_enabled or settings.join_to_create_channel_id is None:
            message = interaction.client.localization.translate("jtc.status_disabled", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        lobby = interaction.guild.get_channel(settings.join_to_create_channel_id)
        category = interaction.guild.get_channel(settings.join_to_create_category_id) if settings.join_to_create_category_id else None
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "jtc.status_enabled",
            language=language,
            lobby=lobby.mention if isinstance(lobby, discord.abc.GuildChannel) else f"`{settings.join_to_create_channel_id}`",
            category=category.mention if isinstance(category, discord.CategoryChannel) else "-",
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Richtet einen Join-to-Create-Voicechannel ein.")
    @app_commands.describe(
        lobby_channel="Voicechannel, den Nutzer joinen sollen",
        category="Kategorie, in der die temporaeren Voicechannels erstellt werden",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        lobby_channel: discord.VoiceChannel,
        category: discord.CategoryChannel | None = None,
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

        if not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message("Rysio braucht die Berechtigung `Kanaele verwalten`.", ephemeral=True)
            return

        if not bot_member.guild_permissions.move_members:
            await interaction.response.send_message("Rysio braucht die Berechtigung `Mitglieder verschieben`.", ephemeral=True)
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.client.guild_config.set_join_to_create(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            True,
            lobby_channel.id,
            category.id if category else None,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "jtc.setup_success",
            language=language,
            lobby=lobby_channel.mention,
            category=category.mention if category else "-",
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="disable", description="Deaktiviert Join to Create.")
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
        await interaction.client.guild_config.set_join_to_create(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            False,
            None,
            None,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("jtc.disabled", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)


class JoinToCreateCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = JoinToCreateService()
        self.bot.tree.add_command(JoinToCreateGroup())

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return
        await self.service.handle_voice_state_update(self.bot, member, before, after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(JoinToCreateCog(bot))
