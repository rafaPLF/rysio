from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class VerificationSettings(Base):
    __tablename__ = "verification_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.guild_id"), primary_key=True)
    verification_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verified_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    panel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    captcha_type: Mapped[str] = mapped_column(String(32), default="button")
    panel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    panel_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reaction_emoji: Mapped[str | None] = mapped_column(String(128), nullable=True)
