from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.premium import PremiumSubscription


class PremiumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_plan(self, guild_id: int) -> str:
        query = (
            select(PremiumSubscription)
            .where(PremiumSubscription.guild_id == guild_id)
            .order_by(desc(PremiumSubscription.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        subscription = result.scalar_one_or_none()
        if subscription is None or subscription.status != "active":
            return "free"
        return subscription.plan

    async def set_plan(self, guild_id: int, plan: str, *, active: bool) -> PremiumSubscription:
        subscription = PremiumSubscription(
            guild_id=guild_id,
            plan=plan,
            status="active" if active else "inactive",
            source="owner_override",
            expires_at=datetime.now(timezone.utc) if not active else None,
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription
