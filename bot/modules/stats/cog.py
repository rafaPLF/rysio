from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.modules.stats.service import (
    STAT_METRIC_BOTS,
    STAT_METRIC_HUMANS,
    STAT_METRIC_ONLINE,
    STAT_METRIC_TOTAL,
    STAT_METRIC_TWITCH_FOLLOWERS,
    StatsService,
)
from bot.utils.access import can_manage_guild


def _metric_choices() -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name="Alle Mitglieder", value=STAT_METRIC_TOTAL),
        app_commands.Choice(name="Echte Mitglieder", value=STAT_METRIC_HUMANS),
        app_commands.Choice(name="Bots", value=STAT_METRIC_BOTS),
        app_commands.Choice(name="Online Mitglieder", value=STAT_METRIC_ONLINE),
        app_commands.Choice(name="Twitch Follower", value=STAT_METRIC_TWITCH_FOLLOWERS),
    ]


class StatsGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="stats", description="Server-Stats-Channels verwalten")

    @app_commands.command(name="add", description="Erstellt einen neuen Stats-Channel.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        metric="Welche Zahl angezeigt werden soll",
        category="Kategorie fuer den Stats-Channel",
        template="Optionales Format, z. B. Online Mitglieder: {value}",
        target="Optionaler Target-Name, z. B. Twitch Kanalname",
    )
    @app_commands.choices(metric=_metric_choices())
    async def add(
        self,
        interaction: discord.Interaction,
        metric: app_commands.Choice[str],
        category: discord.CategoryChannel | None = None,
        template: str | None = None,
        target: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None or not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message("Rysio braucht die Berechtigung `Kanaele verwalten`.", ephemeral=True)
            return

        service = StatsService()
        try:
            entry, channel = await service.create_stat_channel(
                interaction.client,
                guild=interaction.guild,
                metric=metric.value,
                category=category,
                template=template.strip() if template else None,
                source_target=target.strip() if target else None,
            )
        except ValueError:
            await interaction.response.send_message("Diese Statistik wird aktuell noch nicht unterstuetzt.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Stats-Channel erstellt: {channel.mention}\nTyp: `{entry.metric_type}`",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="Zeigt alle eingerichteten Stats-Channels.")
    async def list(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        entries = await StatsService().list_for_guild(interaction.client, interaction.guild.id)
        if not entries:
            await interaction.response.send_message("Auf diesem Server sind noch keine Stats-Channels eingerichtet.", ephemeral=True)
            return

        lines: list[str] = []
        for entry in entries:
            channel = interaction.guild.get_channel(entry.channel_id)
            channel_text = channel.mention if isinstance(channel, discord.VoiceChannel) else f"`{entry.channel_id}`"
            target_text = f" | Target: `{entry.source_target}`" if entry.source_target else ""
            lines.append(f"{channel_text} -> `{entry.metric_type}` mit `{entry.template}`{target_text}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="remove", description="Entfernt einen Stats-Channel und loescht ihn direkt.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(channel="Der Stats-Channel, der entfernt werden soll")
    async def remove(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        removed = await StatsService().remove_stat_channel(interaction.client, channel_id=channel.id, delete_channel=True)
        if removed == 0:
            await interaction.response.send_message("Dieser Channel ist nicht als Stats-Channel gespeichert.", ephemeral=True)
            return

        await interaction.response.send_message("Stats-Channel wurde entfernt.", ephemeral=True)

    @app_commands.command(name="refresh", description="Aktualisiert alle Stats-Channels dieses Servers sofort.")
    async def refresh(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        updated = await StatsService().refresh_guild(interaction.client, interaction.guild)
        await interaction.response.send_message(f"Stats aktualisiert. Bearbeitete Channels: `{updated}`.", ephemeral=True)


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = StatsService()
        self.bot.tree.add_command(StatsGroup())
        self._refresh_loop.start()

    def cog_unload(self) -> None:
        self._refresh_loop.cancel()

    @tasks.loop(minutes=5)
    async def _refresh_loop(self) -> None:
        await self.service.refresh_all(self.bot)

    @_refresh_loop.before_loop
    async def _before_refresh_loop(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self.service.refresh_guild(self.bot, member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self.service.refresh_guild(self.bot, member.guild)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.status == after.status:
            return
        await self.service.refresh_guild(self.bot, after.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await self.service.remove_stat_channel(self.bot, channel_id=channel.id, delete_channel=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCog(bot))
