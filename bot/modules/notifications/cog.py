from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.modules.notifications.service import NotificationService
from bot.utils.access import can_manage_guild


PLATFORM_CHOICES = [
    app_commands.Choice(name="YouTube", value="youtube"),
    app_commands.Choice(name="Twitch", value="twitch"),
    app_commands.Choice(name="Kick", value="kick"),
]


class NotificationsGroup(app_commands.Group):
    def __init__(self, service: NotificationService) -> None:
        super().__init__(name="notifications", description="Benachrichtigungen fuer Twitch, Kick und YouTube")
        self._service = service

    @app_commands.command(name="add", description="Fuegt eine Benachrichtigung fuer Twitch, Kick oder YouTube hinzu.")
    @app_commands.describe(
        platform="Plattform",
        target="Bei YouTube: Channel-ID. Bei Twitch/Kick: Username.",
        channel="Discord-Channel fuer die Benachrichtigung",
    )
    @app_commands.choices(platform=PLATFORM_CHOICES)
    async def add(
        self,
        interaction: discord.Interaction,
        platform: app_commands.Choice[str],
        target: str,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        try:
            last_seen_id = await self._service.add_subscription(
                interaction.client,
                guild_id=interaction.guild.id,
                platform=platform.value,
                target=target,
                announce_channel_id=channel.id,
            )
        except ValueError:
            await interaction.response.send_message("Diese Plattform wird aktuell nicht unterstuetzt.", ephemeral=True)
            return

        target_label = self._service.normalize_target(platform.value, target)
        suffix = "Es wird erst ab dem naechsten neuen Upload/Live-Start gepostet."
        if last_seen_id is None:
            suffix = "Aktuell wurde noch kein letzter Inhalt gefunden. Der erste Fund wird direkt gepostet."
        await interaction.response.send_message(
            f"Benachrichtigung gespeichert: `{platform.value}` fuer `{target_label}` in {channel.mention}. {suffix}",
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Entfernt eine Benachrichtigung.")
    @app_commands.choices(platform=PLATFORM_CHOICES)
    async def remove(
        self,
        interaction: discord.Interaction,
        platform: app_commands.Choice[str],
        target: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        deleted = await self._service.remove_subscription(
            interaction.client,
            guild_id=interaction.guild.id,
            platform=platform.value,
            target=target,
        )
        if deleted == 0:
            await interaction.response.send_message("Fuer diese Kombination wurde nichts gefunden.", ephemeral=True)
            return
        await interaction.response.send_message("Benachrichtigung entfernt.", ephemeral=True)

    @app_commands.command(name="list", description="Zeigt alle gespeicherten Benachrichtigungen auf diesem Server.")
    async def list(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        subscriptions = await self._service.list_for_guild(interaction.client, interaction.guild.id)
        if not subscriptions:
            await interaction.response.send_message("Es sind noch keine Benachrichtigungen eingerichtet.", ephemeral=True)
            return

        lines = []
        for subscription in subscriptions:
            lines.append(
                f"- `{subscription.platform}` | `{subscription.target}` -> <#{subscription.announce_channel_id}>"
            )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="check", description="Prueft die Benachrichtigungen sofort einmal manuell.")
    async def check(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        await interaction.response.send_message("Pruefe Benachrichtigungen jetzt manuell...", ephemeral=True)
        await self._service.poll_all(interaction.client)
        await interaction.followup.send("Manueller Check abgeschlossen.", ephemeral=True)


class NotificationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._service = NotificationService()
        self.bot.tree.add_command(NotificationsGroup(self._service))
        self._poll_loop.change_interval(seconds=max(60, bot.settings.notifications_poll_interval_seconds))  # type: ignore[attr-defined]
        self._poll_loop.start()

    def cog_unload(self) -> None:
        self._poll_loop.cancel()

    @tasks.loop(seconds=180)
    async def _poll_loop(self) -> None:
        await self._service.poll_all(self.bot)

    @_poll_loop.before_loop
    async def _before_poll_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self._service.startup()

    @_poll_loop.after_loop
    async def _after_poll_loop(self) -> None:
        await self._service.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NotificationsCog(bot))
