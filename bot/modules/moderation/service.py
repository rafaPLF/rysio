from __future__ import annotations

import discord

from bot.database.repositories.moderation_repo import ModerationCaseRepository
from bot.modules.logs.service import LogService


class ModerationService:
    def __init__(self) -> None:
        self._logs = LogService()

    async def create_case(
        self,
        bot: discord.Client,
        *,
        guild: discord.Guild,
        action_type: str,
        target_user_id: int,
        target_username: str,
        moderator_user: discord.abc.User,
        reason: str,
        duration_minutes: int | None = None,
        active: bool = True,
    ):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ModerationCaseRepository(session)
            entry = await repo.create_case(
                guild_id=guild.id,
                action_type=action_type,
                target_user_id=target_user_id,
                target_username=target_username,
                moderator_user_id=moderator_user.id,
                moderator_username=str(moderator_user),
                reason=reason,
                duration_minutes=duration_minutes,
                active=active,
            )

        await self._logs.write_event(
            bot,
            guild,
            event_type=f"moderation_{action_type}",
            summary=f"{action_type.upper()} gegen {target_username} durch {moderator_user}",
            user_id=target_user_id,
            details={
                "case_number": entry.case_number,
                "moderator_id": moderator_user.id,
                "reason": reason,
                "duration_minutes": duration_minutes,
            },
        )
        return entry

    async def list_cases_for_user(
        self,
        bot: discord.Client,
        *,
        guild_id: int,
        target_user_id: int,
        limit: int = 10,
    ):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ModerationCaseRepository(session)
            return await repo.list_for_user(guild_id, target_user_id, limit=limit)
