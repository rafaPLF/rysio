from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.notification_subscription import NotificationSubscription


class NotificationSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_subscription(
        self,
        *,
        guild_id: int,
        platform: str,
        target: str,
        announce_channel_id: int,
        mention_role_id: int | None,
        last_seen_content_id: str | None,
    ) -> NotificationSubscription:
        existing = await self.get_by_target(guild_id=guild_id, platform=platform, target=target)
        if existing is None:
            existing = NotificationSubscription(
                guild_id=guild_id,
                platform=platform,
                target=target,
                announce_channel_id=announce_channel_id,
                mention_role_id=mention_role_id,
                last_seen_content_id=last_seen_content_id,
                enabled=True,
            )
            self.session.add(existing)
        else:
            existing.announce_channel_id = announce_channel_id
            existing.mention_role_id = mention_role_id
            existing.enabled = True
            if last_seen_content_id is not None:
                existing.last_seen_content_id = last_seen_content_id
        await self.session.flush()
        return existing

    async def list_for_guild(self, guild_id: int) -> list[NotificationSubscription]:
        result = await self.session.execute(
            select(NotificationSubscription)
            .where(NotificationSubscription.guild_id == guild_id)
            .order_by(NotificationSubscription.platform, NotificationSubscription.target)
        )
        return list(result.scalars().all())

    async def list_enabled(self) -> list[NotificationSubscription]:
        result = await self.session.execute(
            select(NotificationSubscription)
            .where(NotificationSubscription.enabled.is_(True))
            .order_by(NotificationSubscription.guild_id, NotificationSubscription.platform, NotificationSubscription.target)
        )
        return list(result.scalars().all())

    async def get_by_target(
        self,
        *,
        guild_id: int,
        platform: str,
        target: str,
    ) -> NotificationSubscription | None:
        result = await self.session.execute(
            select(NotificationSubscription).where(
                NotificationSubscription.guild_id == guild_id,
                NotificationSubscription.platform == platform,
                NotificationSubscription.target == target,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, subscription_id: int) -> NotificationSubscription | None:
        return await self.session.get(NotificationSubscription, subscription_id)

    async def update_subscription(
        self,
        subscription: NotificationSubscription,
        *,
        platform: str,
        target: str,
        announce_channel_id: int,
        mention_role_id: int | None,
        enabled: bool = True,
    ) -> NotificationSubscription:
        subscription.platform = platform
        subscription.target = target
        subscription.announce_channel_id = announce_channel_id
        subscription.mention_role_id = mention_role_id
        subscription.enabled = enabled
        await self.session.flush()
        return subscription

    async def delete_by_target(self, *, guild_id: int, platform: str, target: str) -> int:
        result = await self.session.execute(
            delete(NotificationSubscription).where(
                NotificationSubscription.guild_id == guild_id,
                NotificationSubscription.platform == platform,
                NotificationSubscription.target == target,
            )
        )
        return int(result.rowcount or 0)

    async def delete_by_id(self, subscription_id: int) -> int:
        result = await self.session.execute(
            delete(NotificationSubscription).where(NotificationSubscription.id == subscription_id)
        )
        return int(result.rowcount or 0)

    async def update_last_seen_content_id(self, subscription_id: int, content_id: str | None) -> None:
        subscription = await self.session.get(NotificationSubscription, subscription_id)
        if subscription is None:
            return
        subscription.last_seen_content_id = content_id
        await self.session.flush()
