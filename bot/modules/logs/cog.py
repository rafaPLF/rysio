from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.logs.service import LogService
from bot.utils.access import can_manage_guild


class LogsGroup(app_commands.Group):
    def __init__(self, service: LogService) -> None:
        super().__init__(name="logs", description="Server-Logs verwalten")
        self._service = service

    @app_commands.command(name="status", description="Zeigt den Status des Logging-Systems.")
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
        if settings is None or not settings.logs_enabled:
            message = interaction.client.localization.translate("logs.status_disabled", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        count = await self._service.get_log_count(interaction.client, interaction.guild.id)
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "logs.status_enabled",
            language=language,
            count=count,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Aktiviert das Audit-Logging fuer diesen Server.")
    async def setup(self, interaction: discord.Interaction) -> None:
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
        await interaction.client.guild_config.set_logs(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            True,
            None,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("logs.setup_success", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="disable", description="Deaktiviert das Logging-System.")
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
        await interaction.client.guild_config.set_logs(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            False,
            None,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("logs.disabled", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)


class LogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._service = LogService()
        self.bot.tree.add_command(LogsGroup(self._service))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self._service.write_event(
            self.bot,
            member.guild,
            "member.join",
            f"{member} joined the server.",
            user_id=member.id,
            details={"display_name": member.display_name},
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._service.write_event(
            self.bot,
            member.guild,
            "member.leave",
            f"{member} left the server.",
            user_id=member.id,
            details={"display_name": member.display_name},
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        await self._service.write_event(
            self.bot,
            message.guild,
            "message.delete",
            f"Message deleted in #{message.channel}.",
            user_id=message.author.id,
            channel_id=message.channel.id,
            details={
                "author": str(message.author),
                "content": message.content[:900] if message.content else None,
                "message_id": message.id,
            },
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot:
            return

        if before.content == after.content:
            return

        await self._service.write_event(
            self.bot,
            before.guild,
            "message.edit",
            f"Message edited in #{before.channel}.",
            user_id=before.author.id,
            channel_id=before.channel.id,
            details={
                "author": str(before.author),
                "before": before.content[:700] if before.content else None,
                "after": after.content[:700] if after.content else None,
                "message_id": before.id,
            },
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        if before.channel == after.channel:
            return

        if before.channel is None and after.channel is not None:
            await self._service.write_event(
                self.bot,
                member.guild,
                "voice.join",
                f"{member} joined voice channel {after.channel.name}.",
                user_id=member.id,
                channel_id=after.channel.id,
                details={"channel_name": after.channel.name},
            )
            return

        if before.channel is not None and after.channel is None:
            await self._service.write_event(
                self.bot,
                member.guild,
                "voice.leave",
                f"{member} left voice channel {before.channel.name}.",
                user_id=member.id,
                channel_id=before.channel.id,
                details={"channel_name": before.channel.name},
            )
            return

        await self._service.write_event(
            self.bot,
            member.guild,
            "voice.move",
            f"{member} moved from {before.channel.name if before.channel else '-'} to {after.channel.name if after.channel else '-'}.",
            user_id=member.id,
            channel_id=after.channel.id if after.channel else None,
            details={
                "before_channel_name": before.channel.name if before.channel else None,
                "after_channel_name": after.channel.name if after.channel else None,
            },
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LogsCog(bot))
