from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class GuildSettings(Base):
    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), primary_key=True)
    autorole_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    autorole_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    autorole_mode: Mapped[str] = mapped_column(String(16), default="join")
    spam_protection_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    spam_threshold: Mapped[int] = mapped_column(default=5)
    spam_interval_seconds: Mapped[int] = mapped_column(default=8)
    spam_action: Mapped[str] = mapped_column(String(16), default="delete_warn")
    info_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verification_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ticket_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
