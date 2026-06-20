from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class Guild(Base):
    __tablename__ = "guilds"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="de")
    premium_plan: Mapped[str] = mapped_column(String(32), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
