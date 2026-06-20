from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class PremiumSubscription(Base):
    __tablename__ = "premium_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    status: Mapped[str] = mapped_column(String(32), default="inactive")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
