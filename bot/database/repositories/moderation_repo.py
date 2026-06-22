from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.moderation_case import ModerationCase


class ModerationCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_next_case_number(self, guild_id: int) -> int:
        result = await self.session.execute(
            select(func.max(ModerationCase.case_number)).where(ModerationCase.guild_id == guild_id)
        )
        current_max = result.scalar_one()
        return int(current_max or 0) + 1

    async def create_case(
        self,
        *,
        guild_id: int,
        action_type: str,
        target_user_id: int,
        target_username: str,
        moderator_user_id: int,
        moderator_username: str,
        reason: str,
        duration_minutes: int | None = None,
        active: bool = True,
    ) -> ModerationCase:
        case_number = await self.get_next_case_number(guild_id)
        entry = ModerationCase(
            guild_id=guild_id,
            case_number=case_number,
            action_type=action_type,
            target_user_id=target_user_id,
            target_username=target_username,
            moderator_user_id=moderator_user_id,
            moderator_username=moderator_username,
            reason=reason,
            duration_minutes=duration_minutes,
            active=active,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_user(
        self,
        guild_id: int,
        target_user_id: int,
        *,
        limit: int = 10,
    ) -> list[ModerationCase]:
        result = await self.session.execute(
            select(ModerationCase)
            .where(
                ModerationCase.guild_id == guild_id,
                ModerationCase.target_user_id == target_user_id,
            )
            .order_by(desc(ModerationCase.created_at), desc(ModerationCase.id))
            .limit(limit)
        )
        return list(result.scalars().all())
