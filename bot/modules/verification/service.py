from __future__ import annotations

import discord

from bot.database.repositories.verification_repo import VerificationRepository


class VerificationService:
    async def restore_views(self, bot: discord.Client) -> None:
        from bot.modules.verification.views import VerificationView

        bot.add_view(VerificationView())

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = VerificationRepository(session)
            from sqlalchemy import select
            from bot.database.models.verification import VerificationSettings

            result = await session.execute(select(VerificationSettings).where(VerificationSettings.panel_message_id.is_not(None)))
            settings_list = result.scalars().all()

        for settings in settings_list:
            if settings.panel_message_id and settings.captcha_type == "button":
                bot.add_view(VerificationView(), message_id=settings.panel_message_id)
