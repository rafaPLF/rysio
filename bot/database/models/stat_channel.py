from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class StatChannel(Base):
    __tablename__ = "stat_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metric_type: Mapped[str] = mapped_column(String(32))
    template: Mapped[str] = mapped_column(String(255))
    source_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
