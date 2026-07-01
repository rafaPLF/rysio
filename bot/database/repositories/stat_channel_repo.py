from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.stat_channel import StatChannel


class StatChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        guild_id: int,
        channel_id: int,
        category_id: int | None,
        metric_type: str,
        template: str,
        source_target: str | None = None,
    ) -> StatChannel:
        entry = StatChannel(
            guild_id=guild_id,
            channel_id=channel_id,
            category_id=category_id,
            metric_type=metric_type,
            template=template,
            source_target=source_target,
            enabled=True,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_guild(self, guild_id: int) -> list[StatChannel]:
        result = await self.session.execute(
            select(StatChannel)
            .where(StatChannel.guild_id == guild_id)
            .order_by(StatChannel.category_id, StatChannel.id)
        )
        return list(result.scalars().all())

    async def list_enabled(self) -> list[StatChannel]:
        result = await self.session.execute(
            select(StatChannel)
            .where(StatChannel.enabled.is_(True))
            .order_by(StatChannel.guild_id, StatChannel.category_id, StatChannel.id)
        )
        return list(result.scalars().all())

    async def get_by_channel_id(self, channel_id: int) -> StatChannel | None:
        result = await self.session.execute(select(StatChannel).where(StatChannel.channel_id == channel_id))
        return result.scalar_one_or_none()

    async def delete_by_channel_id(self, channel_id: int) -> int:
        result = await self.session.execute(delete(StatChannel).where(StatChannel.channel_id == channel_id))
        return int(result.rowcount or 0)
