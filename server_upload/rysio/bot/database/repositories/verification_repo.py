from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.verification import VerificationSettings


class VerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_settings(self, guild_id: int) -> VerificationSettings | None:
        return await self.session.get(VerificationSettings, guild_id)

    async def upsert_settings(
        self,
        guild_id: int,
        verification_channel_id: int | None,
        verified_role_id: int | None,
        panel_message_id: int | None,
        captcha_type: str = "button",
    ) -> VerificationSettings:
        settings = await self.get_settings(guild_id)
        if settings is None:
            settings = VerificationSettings(
                guild_id=guild_id,
                verification_channel_id=verification_channel_id,
                verified_role_id=verified_role_id,
                panel_message_id=panel_message_id,
                captcha_type=captcha_type,
            )
            self.session.add(settings)
        else:
            settings.verification_channel_id = verification_channel_id
            settings.verified_role_id = verified_role_id
            settings.panel_message_id = panel_message_id
            settings.captcha_type = captcha_type

        await self.session.flush()
        return settings
