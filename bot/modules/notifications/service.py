from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import aiohttp
import discord

from bot.database.repositories.notification_repo import NotificationSubscriptionRepository

YOUTUBE_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


@dataclass(slots=True)
class NotificationContent:
    content_id: str
    title: str
    url: str
    creator_name: str
    description: str | None = None
    thumbnail_url: str | None = None
    platform_label: str = ""


class NotificationService:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._twitch_token: str | None = None
        self._twitch_token_expires_at: float = 0.0

    async def startup(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def add_subscription(
        self,
        bot: discord.Client,
        *,
        guild_id: int,
        platform: str,
        target: str,
        announce_channel_id: int,
    ) -> str | None:
        normalized_platform = self.normalize_platform(platform)
        normalized_target = self.normalize_target(normalized_platform, target)
        await bot.guild_config.ensure_guild(bot.database, guild_id)  # type: ignore[attr-defined]
        initial_content = await self.fetch_latest_content(bot, normalized_platform, normalized_target)

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = NotificationSubscriptionRepository(session)
            subscription = await repo.upsert_subscription(
                guild_id=guild_id,
                platform=normalized_platform,
                target=normalized_target,
                announce_channel_id=announce_channel_id,
                last_seen_content_id=initial_content.content_id if initial_content else None,
            )
        return subscription.last_seen_content_id

    async def remove_subscription(self, bot: discord.Client, *, guild_id: int, platform: str, target: str) -> int:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = NotificationSubscriptionRepository(session)
            return await repo.delete_by_target(
                guild_id=guild_id,
                platform=self.normalize_platform(platform),
                target=self.normalize_target(self.normalize_platform(platform), target),
            )

    async def list_for_guild(self, bot: discord.Client, guild_id: int):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = NotificationSubscriptionRepository(session)
            return await repo.list_for_guild(guild_id)

    async def poll_all(self, bot: discord.Client) -> None:
        await self.startup()
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = NotificationSubscriptionRepository(session)
            subscriptions = await repo.list_enabled()

        for subscription in subscriptions:
            try:
                content = await self.fetch_latest_content(bot, subscription.platform, subscription.target)
            except Exception:
                continue

            if content is None or content.content_id == subscription.last_seen_content_id:
                continue

            guild = bot.get_guild(subscription.guild_id)
            if guild is None:
                continue

            channel = guild.get_channel(subscription.announce_channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            bot_member = guild.me or guild.get_member(bot.user.id)  # type: ignore[attr-defined]
            if bot_member is None:
                continue
            permissions = channel.permissions_for(bot_member)
            if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
                continue

            embed = self._build_announcement_embed(content)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                continue

            async with bot.database.session() as session:  # type: ignore[attr-defined]
                repo = NotificationSubscriptionRepository(session)
                await repo.update_last_seen_content_id(subscription.id, content.content_id)

    def normalize_platform(self, platform: str) -> str:
        normalized = platform.strip().lower()
        if normalized not in {"youtube", "twitch", "kick"}:
            raise ValueError("unsupported_platform")
        return normalized

    def normalize_target(self, platform: str, target: str) -> str:
        raw = target.strip()
        if platform == "youtube":
            if "/channel/" in raw:
                raw = raw.split("/channel/", 1)[1].split("/", 1)[0]
            return raw
        if raw.startswith("https://"):
            raw = raw.rstrip("/").rsplit("/", 1)[-1]
        return raw.lower()

    async def fetch_latest_content(
        self,
        bot: discord.Client,
        platform: str,
        target: str,
    ) -> NotificationContent | None:
        await self.startup()
        if self._session is None:
            return None
        if platform == "youtube":
            return await self._fetch_youtube_latest(target)
        if platform == "twitch":
            return await self._fetch_twitch_latest(bot, target)
        if platform == "kick":
            return await self._fetch_kick_latest(target)
        return None

    async def _fetch_youtube_latest(self, channel_id: str) -> NotificationContent | None:
        assert self._session is not None
        async with self._session.get(
            "https://www.youtube.com/feeds/videos.xml",
            params={"channel_id": channel_id},
        ) as response:
            if response.status >= 400:
                return None
            xml_text = await response.text()

        root = ET.fromstring(xml_text)
        entry = root.find("atom:entry", YOUTUBE_ATOM_NS)
        if entry is None:
            return None

        video_id = entry.findtext("yt:videoId", default="", namespaces=YOUTUBE_ATOM_NS).strip()
        title = entry.findtext("atom:title", default="Neues Video", namespaces=YOUTUBE_ATOM_NS).strip()
        link = entry.find("atom:link", YOUTUBE_ATOM_NS)
        author = entry.find("atom:author/atom:name", YOUTUBE_ATOM_NS)
        if not video_id:
            return None

        return NotificationContent(
            content_id=video_id,
            title=title or "Neues Video",
            url=link.attrib.get("href", f"https://www.youtube.com/watch?v={video_id}") if link is not None else f"https://www.youtube.com/watch?v={video_id}",
            creator_name=author.text.strip() if author is not None and author.text else channel_id,
            description="Neues YouTube-Video hochgeladen.",
            thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            platform_label="YouTube",
        )

    async def _fetch_twitch_latest(self, bot: discord.Client, login_name: str) -> NotificationContent | None:
        assert self._session is not None
        token = await self._get_twitch_app_token(bot)
        if token is None or not bot.settings.twitch_client_id:  # type: ignore[attr-defined]
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Client-ID": bot.settings.twitch_client_id,  # type: ignore[attr-defined]
        }
        async with self._session.get(
            "https://api.twitch.tv/helix/streams",
            params={"user_login": login_name},
            headers=headers,
        ) as response:
            if response.status >= 400:
                return None
            payload = await response.json()

        data = payload.get("data") or []
        if not data:
            return None
        stream = data[0]
        thumbnail = str(stream.get("thumbnail_url", "")).replace("{width}", "1280").replace("{height}", "720")
        return NotificationContent(
            content_id=str(stream.get("id")),
            title=str(stream.get("title") or f"{login_name} ist live"),
            url=f"https://www.twitch.tv/{login_name}",
            creator_name=str(stream.get("user_name") or login_name),
            description=str(stream.get("game_name") or "Twitch Livestream"),
            thumbnail_url=thumbnail or None,
            platform_label="Twitch",
        )

    async def _fetch_kick_latest(self, slug: str) -> NotificationContent | None:
        assert self._session is not None
        async with self._session.get(f"https://kick.com/api/v2/channels/{slug}") as response:
            if response.status >= 400:
                return None
            payload = await response.json()

        livestream = payload.get("livestream")
        if not isinstance(livestream, dict):
            return None

        content_id = str(
            livestream.get("id")
            or livestream.get("session_title")
            or livestream.get("created_at")
            or slug
        )
        title = str(livestream.get("session_title") or f"{slug} ist live auf Kick")
        thumbnail = livestream.get("thumbnail") or payload.get("banner_image", {}).get("url")
        return NotificationContent(
            content_id=content_id,
            title=title,
            url=f"https://kick.com/{slug}",
            creator_name=str(payload.get("user", {}).get("username") or payload.get("slug") or slug),
            description="Kick Livestream gestartet.",
            thumbnail_url=str(thumbnail) if thumbnail else None,
            platform_label="Kick",
        )

    async def _get_twitch_app_token(self, bot: discord.Client) -> str | None:
        if time.time() < self._twitch_token_expires_at and self._twitch_token:
            return self._twitch_token

        client_id = bot.settings.twitch_client_id  # type: ignore[attr-defined]
        client_secret = bot.settings.twitch_client_secret  # type: ignore[attr-defined]
        if not client_id or not client_secret or self._session is None:
            return None

        async with self._session.post(
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

    def _build_announcement_embed(self, content: NotificationContent) -> discord.Embed:
        embed = discord.Embed(
            title=content.title,
            url=content.url,
            description=content.description,
            color=discord.Color.purple() if content.platform_label == "Twitch" else discord.Color.red(),
        )
        embed.add_field(name="Plattform", value=content.platform_label, inline=True)
        embed.add_field(name="Creator", value=content.creator_name, inline=True)
        embed.add_field(name="Link", value=f"[Jetzt ansehen]({content.url})", inline=False)
        if content.thumbnail_url:
            embed.set_image(url=content.thumbnail_url)
        return embed
