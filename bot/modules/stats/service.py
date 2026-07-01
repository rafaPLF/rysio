from __future__ import annotations

from collections.abc import Iterable
import time

import aiohttp
import discord

from bot.database.repositories.stat_channel_repo import StatChannelRepository

STAT_METRIC_TOTAL = "members_total"
STAT_METRIC_HUMANS = "members_humans"
STAT_METRIC_BOTS = "members_bots"
STAT_METRIC_ONLINE = "members_online"
STAT_METRIC_TWITCH_FOLLOWERS = "twitch_followers"

STAT_METRICS = {
    STAT_METRIC_TOTAL: "All Members: {value}",
    STAT_METRIC_HUMANS: "Members: {value}",
    STAT_METRIC_BOTS: "Bots: {value}",
    STAT_METRIC_ONLINE: "Online Members: {value}",
    STAT_METRIC_TWITCH_FOLLOWERS: "{target} Twitch Follower: {value}",
}


class StatsService:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._twitch_token: str | None = None
        self._twitch_token_expires_at: float = 0.0

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
        source_target: str | None = None,
    ):
        normalized_metric = self.normalize_metric(metric)
        normalized_target = self._normalize_target(normalized_metric, source_target)
        final_template = template or self.default_template(normalized_metric)
        channel_name = await self._build_channel_name(
            bot,
            guild,
            normalized_metric,
            final_template,
            source_target=normalized_target,
        )

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
                source_target=normalized_target,
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

            target_name = await self._build_channel_name(
                bot,
                guild,
                entry.metric_type,
                entry.template,
                source_target=entry.source_target,
            )
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
        if normalized_metric == STAT_METRIC_TWITCH_FOLLOWERS:
            raise ValueError("source_target_required")
        raise ValueError("unsupported_metric")

    async def _resolve_external_metric_value(
        self,
        bot: discord.Client,
        metric: str,
        source_target: str | None,
    ) -> int:
        normalized_metric = self.normalize_metric(metric)
        target = self._normalize_target(normalized_metric, source_target)
        if normalized_metric == STAT_METRIC_TWITCH_FOLLOWERS:
            return await self._fetch_twitch_follower_count(bot, target)
        raise ValueError("unsupported_metric")

    async def _build_channel_name(
        self,
        bot: discord.Client,
        guild: discord.Guild,
        metric: str,
        template: str,
        source_target: str | None = None,
    ) -> str:
        normalized_metric = self.normalize_metric(metric)
        if normalized_metric == STAT_METRIC_TWITCH_FOLLOWERS:
            value = await self._resolve_external_metric_value(bot, normalized_metric, source_target)
        else:
            value = await self._resolve_metric_value(bot, guild, normalized_metric)
        channel_name = template.replace("{value}", str(value))
        channel_name = channel_name.replace("{target}", source_target or "")
        return " ".join(channel_name.split())[:100]

    def _normalize_target(self, metric: str, source_target: str | None) -> str | None:
        normalized_metric = self.normalize_metric(metric)
        target = (source_target or "").strip()
        if normalized_metric == STAT_METRIC_TWITCH_FOLLOWERS:
            if not target:
                raise ValueError("missing_source_target")
            return target.lower()
        return target or None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_twitch_follower_count(self, bot: discord.Client, login_name: str) -> int:
        session = await self._ensure_session()
        token = await self._get_twitch_app_token(bot, session)
        client_id = bot.settings.twitch_client_id  # type: ignore[attr-defined]
        if token is None or not client_id:
            raise ValueError("twitch_not_configured")

        headers = {
            "Authorization": f"Bearer {token}",
            "Client-ID": client_id,
        }

        async with session.get(
            "https://api.twitch.tv/helix/users",
            params={"login": login_name},
            headers=headers,
        ) as response:
            if response.status >= 400:
                raise ValueError("twitch_lookup_failed")
            payload = await response.json()

        users = payload.get("data") or []
        if not users:
            raise ValueError("twitch_user_not_found")
        broadcaster_id = str(users[0].get("id") or "").strip()
        if not broadcaster_id:
            raise ValueError("twitch_user_not_found")

        async with session.get(
            "https://api.twitch.tv/helix/channels/followers",
            params={"broadcaster_id": broadcaster_id},
            headers=headers,
        ) as response:
            if response.status >= 400:
                raise ValueError("twitch_followers_unavailable")
            payload = await response.json()

        return int(payload.get("total") or 0)

    async def _get_twitch_app_token(self, bot: discord.Client, session: aiohttp.ClientSession) -> str | None:
        if time.time() < self._twitch_token_expires_at and self._twitch_token:
            return self._twitch_token

        client_id = bot.settings.twitch_client_id  # type: ignore[attr-defined]
        client_secret = bot.settings.twitch_client_secret  # type: ignore[attr-defined]
        if not client_id or not client_secret:
            return None

        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
        ) as response:
            if response.status >= 400:
                return None
            payload = await response.json()

        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in") or 0)
        if not access_token:
            return None

        self._twitch_token = str(access_token)
        self._twitch_token_expires_at = time.time() + max(60, expires_in - 120)
        return self._twitch_token

    @staticmethod
    def _iter_known_members(members: Iterable[discord.Member]) -> Iterable[discord.Member]:
        return members
