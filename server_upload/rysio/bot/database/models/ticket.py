from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketPanel(Base):
    __tablename__ = "ticket_panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    support_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
