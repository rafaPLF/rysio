from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.database.base import Base
from bot.database.models import AuditLog, Guild, GuildSettings, LFGPost, ModerationCase, NotificationSubscription, PremiumSubscription, ReactionRoleEntry, ReactionRolePanel, TempVoiceChannel, Ticket, TicketNote, TicketPanel, VerificationSettings  # noqa: F401


class DatabaseSessionManager:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(database_url, future=True)
        self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)

    async def connect(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(self._run_bootstrap_migrations)

    async def close(self) -> None:
        await self._engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        session = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @staticmethod
    def _run_bootstrap_migrations(connection) -> None:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if "verification_settings" not in tables:
            return

        columns = {column["name"] for column in inspector.get_columns("verification_settings")}
        if "panel_message_id" not in columns:
            connection.execute(text("ALTER TABLE verification_settings ADD COLUMN panel_message_id BIGINT"))
        if "panel_title" not in columns:
            connection.execute(text("ALTER TABLE verification_settings ADD COLUMN panel_title VARCHAR(255)"))
        if "panel_description" not in columns:
            connection.execute(text("ALTER TABLE verification_settings ADD COLUMN panel_description TEXT"))
        if "reaction_emoji" not in columns:
            connection.execute(text("ALTER TABLE verification_settings ADD COLUMN reaction_emoji VARCHAR(128)"))

        if "guild_settings" not in tables:
            return

        guild_settings_columns = {column["name"] for column in inspector.get_columns("guild_settings")}
        if "autorole_mode" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN autorole_mode VARCHAR(16) DEFAULT 'join'"))
        if "spam_threshold" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN spam_threshold INTEGER DEFAULT 5"))
        if "spam_interval_seconds" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN spam_interval_seconds INTEGER DEFAULT 8"))
        if "spam_action" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN spam_action VARCHAR(16) DEFAULT 'delete_warn'"))
        if "info_channel_id" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN info_channel_id BIGINT"))
        if "logs_enabled" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN logs_enabled BOOLEAN DEFAULT FALSE"))
        if "logs_channel_id" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN logs_channel_id BIGINT"))
        if "last_patch_notes_version" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN last_patch_notes_version VARCHAR(32)"))
        if "join_to_create_enabled" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN join_to_create_enabled BOOLEAN DEFAULT FALSE"))
        if "join_to_create_channel_id" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN join_to_create_channel_id BIGINT"))
        if "join_to_create_category_id" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN join_to_create_category_id BIGINT"))
        if "mod_role_ids_json" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN mod_role_ids_json TEXT"))
        if "welcome_enabled" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN welcome_enabled BOOLEAN DEFAULT FALSE"))
        if "welcome_channel_id" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN welcome_channel_id BIGINT"))
        if "welcome_style" not in guild_settings_columns:
            connection.execute(text("ALTER TABLE guild_settings ADD COLUMN welcome_style VARCHAR(32) DEFAULT 'rysio_card'"))

        if "notification_subscriptions" not in tables:
            return

        notification_columns = {column["name"] for column in inspector.get_columns("notification_subscriptions")}
        if "mention_role_id" not in notification_columns:
            connection.execute(text("ALTER TABLE notification_subscriptions ADD COLUMN mention_role_id BIGINT"))

        if "tickets" in tables:
            ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
            if "panel_id" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN panel_id INTEGER"))
            if "claimed_by_user_id" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN claimed_by_user_id BIGINT"))
            if "claimed_at" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN claimed_at TIMESTAMP"))
            if "closed_by_user_id" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN closed_by_user_id BIGINT"))
            if "transcript_path" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN transcript_path VARCHAR(500)"))
            if "selected_topic" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN selected_topic VARCHAR(255)"))

        if "ticket_panels" in tables:
            ticket_panel_columns = {column["name"] for column in inspector.get_columns("ticket_panels")}
            if "title" not in ticket_panel_columns:
                connection.execute(text("ALTER TABLE ticket_panels ADD COLUMN title VARCHAR(255) DEFAULT 'Support Ticket'"))
            if "description_text" not in ticket_panel_columns:
                connection.execute(text("ALTER TABLE ticket_panels ADD COLUMN description_text TEXT DEFAULT 'Klicke unten auf den Button, um ein Ticket zu erstellen.'"))
            if "category_ids_json" not in ticket_panel_columns:
                connection.execute(text("ALTER TABLE ticket_panels ADD COLUMN category_ids_json TEXT"))
            if "topic_options_json" not in ticket_panel_columns:
                connection.execute(text("ALTER TABLE ticket_panels ADD COLUMN topic_options_json TEXT"))
            if "welcome_message" not in ticket_panel_columns:
                connection.execute(text("ALTER TABLE ticket_panels ADD COLUMN welcome_message TEXT"))
