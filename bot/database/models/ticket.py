from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    panel_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ticket_panels.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="open")
    claimed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    transcript_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketPanel(Base):
    __tablename__ = "ticket_panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255), default="Support Ticket")
    description_text: Mapped[str] = mapped_column(Text, default="Klicke unten auf den Button, um ein Ticket zu erstellen.")
    category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    support_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class TicketNote(Base):
    __tablename__ = "ticket_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), index=True)
    author_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    author_username: Mapped[str] = mapped_column(String(255))
    note_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
