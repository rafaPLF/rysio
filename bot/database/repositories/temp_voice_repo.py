from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.temp_voice import TempVoiceChannel


class TempVoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_channel(self, guild_id: int, channel_id: int, owner_id: int) -> TempVoiceChannel:
        temp = TempVoiceChannel(guild_id=guild_id, channel_id=channel_id, owner_id=owner_id)
        self.session.add(temp)
        await self.session.flush()
        return temp

    async def get_by_channel_id(self, channel_id: int) -> TempVoiceChannel | None:
        result = await self.session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_channel_id(self, channel_id: int) -> int:
        result = await self.session.execute(
            delete(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        return result.rowcount or 0
