from __future__ import annotations

import json

import discord

from bot.database.repositories.audit_log_repo import AuditLogRepository


class LogService:
    async def is_enabled(self, bot: discord.Client, guild_id: int) -> bool:
        settings = await bot.guild_config.get_settings(bot.database, guild_id)  # type: ignore[attr-defined]
        return settings is not None and settings.logs_enabled

    async def get_log_count(self, bot: discord.Client, guild_id: int) -> int:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = AuditLogRepository(session)
            return await repo.count_for_guild(guild_id)

    async def write_event(
        self,
        bot: discord.Client,
        guild: discord.Guild,
        event_type: str,
        summary: str,
        user_id: int | None = None,
        channel_id: int | None = None,
        details: dict[str, str | int | None] | None = None,
    ) -> None:
        if not await self.is_enabled(bot, guild.id):
            return

        details_json = json.dumps(details, ensure_ascii=True) if details else None

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = AuditLogRepository(session)
            await repo.create_entry(
                guild_id=guild.id,
                event_type=event_type,
                summary=summary,
                user_id=user_id,
                channel_id=channel_id,
                details_json=details_json,
            )
