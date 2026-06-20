from __future__ import annotations

from bot.database.base import Base
from bot.database.models import Guild, GuildSettings, LFGPost, PremiumSubscription, Ticket, TicketPanel, VerificationSettings  # noqa: F401
from bot.database.session import DatabaseSessionManager


async def initialize_database(database: DatabaseSessionManager) -> None:
    async with database._engine.begin() as connection:  # noqa: SLF001
        await connection.run_sync(Base.metadata.create_all)
