from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class ModerationCase(Base):
    __tablename__ = "moderation_cases"
    __table_args__ = (
        UniqueConstraint("guild_id", "case_number", name="uq_moderation_case_number_per_guild"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    case_number: Mapped[int] = mapped_column(Integer, index=True)
    action_type: Mapped[str] = mapped_column(String(32), index=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_username: Mapped[str] = mapped_column(String(255))
    moderator_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    moderator_username: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
