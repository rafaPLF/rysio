from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import discord


class AntiSpamService:
    def __init__(self) -> None:
        self._history: dict[tuple[int, int], deque[datetime]] = defaultdict(deque)

    async def process_message(self, bot: discord.Client, message: discord.Message) -> bool:
        if message.guild is None or message.author.bot:
            return False

        settings = await bot.guild_config.get_settings(bot.database, message.guild.id)  # type: ignore[attr-defined]
        if settings is None or not settings.spam_protection_enabled:
            return False

        key = (message.guild.id, message.author.id)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=settings.spam_interval_seconds)
        history = self._history[key]

        while history and history[0] < cutoff:
            history.popleft()

        history.append(now)
        if len(history) < settings.spam_threshold:
            return False

        history.clear()
        await self._apply_action(bot, message, settings.spam_action)
        return True

    async def _apply_action(self, bot: discord.Client, message: discord.Message, action: str) -> None:
        language = await bot.guild_config.get_language(bot.database, message.guild.id)  # type: ignore[attr-defined]
        warning = bot.localization.translate("antispam.triggered", language=language, user=message.author.mention)  # type: ignore[attr-defined]
        bot_member = message.guild.me or message.guild.get_member(bot.user.id)  # type: ignore[attr-defined]

        if action in {"delete_warn", "delete"}:
            if bot_member is not None and message.channel.permissions_for(bot_member).manage_messages:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass

        warning_message = None
        if action in {"delete_warn", "warn"}:
            try:
                warning_message = await message.channel.send(warning)
            except discord.HTTPException:
                warning_message = None

        if warning_message is not None:
            try:
                await warning_message.delete(delay=6)
            except discord.HTTPException:
                pass
