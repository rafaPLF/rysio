from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_entry(
        self,
        guild_id: int,
        event_type: str,
        summary: str,
        user_id: int | None = None,
        channel_id: int | None = None,
        details_json: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            guild_id=guild_id,
            event_type=event_type,
            summary=summary,
            user_id=user_id,
            channel_id=channel_id,
            details_json=details_json,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def count_for_guild(self, guild_id: int, event_type: str | None = None) -> int:
        query = select(func.count(AuditLog.id)).where(AuditLog.guild_id == guild_id)
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def list_for_guild(
        self,
        guild_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
    ) -> list[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.guild_id == guild_id)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .limit(limit)
            .offset(offset)
        )
        if event_type:
            query = query.where(AuditLog.event_type == event_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())
