from __future__ import annotations

from collections.abc import Iterable

import discord

from bot.database.repositories.stat_channel_repo import StatChannelRepository

STAT_METRIC_TOTAL = "members_total"
STAT_METRIC_HUMANS = "members_humans"
STAT_METRIC_BOTS = "members_bots"
STAT_METRIC_ONLINE = "members_online"

STAT_METRICS = {
    STAT_METRIC_TOTAL: "All Members: {value}",
    STAT_METRIC_HUMANS: "Members: {value}",
    STAT_METRIC_BOTS: "Bots: {value}",
    STAT_METRIC_ONLINE: "Online Members: {value}",
}


class StatsService:
    def normalize_metric(self, metric: str) -> str:
        value = metric.strip().lower()
        if value not in STAT_METRICS:
            raise ValueError("unsupported_metric")
        return value

    def default_template(self, metric: str) -> str:
        return STAT_METRICS[self.normalize_metric(metric)]

    async def create_stat_channel(
        self,
        bot: discord.Client,
        *,
        guild: discord.Guild,
        metric: str,
        category: discord.CategoryChannel | None,
        template: str | None = None,
    ):
        normalized_metric = self.normalize_metric(metric)
        final_template = template or self.default_template(normalized_metric)
        channel_name = await self._build_channel_name(bot, guild, normalized_metric, final_template)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, speak=False),
        }
        channel = await guild.create_voice_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Stats channel created for metric {normalized_metric}",
        )

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = StatChannelRepository(session)
            entry = await repo.create(
                guild_id=guild.id,
                channel_id=channel.id,
                category_id=category.id if category else None,
                metric_type=normalized_metric,
                template=final_template,
            )
        return entry, channel

    async def list_for_guild(self, bot: discord.Client, guild_id: int):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = StatChannelRepository(session)
            return await repo.list_for_guild(guild_id)

    async def remove_stat_channel(
        self,
        bot: discord.Client,
        *,
        channel_id: int,
        delete_channel: bool = True,
    ) -> int:
        guild_channel: discord.abc.GuildChannel | None = None
        if delete_channel:
            for guild in bot.guilds:
                found = guild.get_channel(channel_id)
                if isinstance(found, discord.abc.GuildChannel):
                    guild_channel = found
                    break

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = StatChannelRepository(session)
            removed = await repo.delete_by_channel_id(channel_id)

        if guild_channel is not None:
            try:
                await guild_channel.delete(reason="Stats channel removed")
            except discord.HTTPException:
                pass
        return removed

    async def refresh_guild(self, bot: discord.Client, guild: discord.Guild) -> int:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = StatChannelRepository(session)
            entries = await repo.list_for_guild(guild.id)

        updated = 0
        stale_channel_ids: list[int] = []
        for entry in entries:
            channel = guild.get_channel(entry.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                stale_channel_ids.append(entry.channel_id)
                continue

            target_name = await self._build_channel_name(bot, guild, entry.metric_type, entry.template)
            if channel.name == target_name:
                updated += 1
                continue

            try:
                await channel.edit(name=target_name, reason="Refreshing stats channel")
                updated += 1
            except discord.HTTPException:
                continue

        if stale_channel_ids:
            async with bot.database.session() as session:  # type: ignore[attr-defined]
                repo = StatChannelRepository(session)
                for channel_id in stale_channel_ids:
                    await repo.delete_by_channel_id(channel_id)

        return updated

    async def refresh_all(self, bot: discord.Client) -> int:
        total_updated = 0
        for guild in bot.guilds:
            total_updated += await self.refresh_guild(bot, guild)
        return total_updated

    async def _build_channel_name(
        self,
        bot: discord.Client,
        guild: discord.Guild,
        metric: str,
        template: str,
    ) -> str:
        value = await self._resolve_metric_value(bot, guild, metric)
        return template.replace("{value}", str(value))[:100]

    async def _resolve_metric_value(self, bot: discord.Client, guild: discord.Guild, metric: str) -> int:
        normalized_metric = self.normalize_metric(metric)
        if normalized_metric == STAT_METRIC_TOTAL:
            return int(guild.member_count or len(guild.members))
        if normalized_metric == STAT_METRIC_HUMANS:
            return sum(1 for member in self._iter_known_members(guild.members) if not member.bot)
        if normalized_metric == STAT_METRIC_BOTS:
            return sum(1 for member in self._iter_known_members(guild.members) if member.bot)
        if normalized_metric == STAT_METRIC_ONLINE:
            try:
                fetched = await bot.fetch_guild(guild.id, with_counts=True)
                if fetched.approximate_presence_count is not None:
                    return int(fetched.approximate_presence_count)
            except discord.HTTPException:
                pass
            return sum(
                1 for member in self._iter_known_members(guild.members) if member.status != discord.Status.offline
            )
        raise ValueError("unsupported_metric")

    @staticmethod
    def _iter_known_members(members: Iterable[discord.Member]) -> Iterable[discord.Member]:
        return members
