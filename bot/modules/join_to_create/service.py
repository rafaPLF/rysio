from __future__ import annotations

import discord

from bot.database.repositories.temp_voice_repo import TempVoiceRepository


class JoinToCreateService:
    async def handle_voice_state_update(
        self,
        bot: discord.Client,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        settings = await bot.guild_config.get_settings(bot.database, member.guild.id)  # type: ignore[attr-defined]
        if settings is None:
            return

        if before.channel is not None:
            await self._cleanup_temp_channel(bot, before.channel)

        if (
            settings.join_to_create_enabled
            and after.channel is not None
            and settings.join_to_create_channel_id == after.channel.id
        ):
            await self._create_temp_channel(bot, member, settings.join_to_create_category_id)

    async def _create_temp_channel(
        self,
        bot: discord.Client,
        member: discord.Member,
        category_id: int | None,
    ) -> None:
        category = member.guild.get_channel(category_id) if category_id else None
        bot_member = member.guild.me or member.guild.get_member(bot.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            return

        channel = await member.guild.create_voice_channel(
            name=f"{member.display_name}s Raum",
            category=category if isinstance(category, discord.CategoryChannel) else None,
            reason=f"Join to create for {member}",
        )

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TempVoiceRepository(session)
            await repo.create_channel(member.guild.id, channel.id, member.id)

        try:
            await member.move_to(channel, reason="Join to create temp voice")
        except discord.HTTPException:
            pass

    async def _cleanup_temp_channel(self, bot: discord.Client, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        if len(channel.members) > 0:
            return

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TempVoiceRepository(session)
            temp = await repo.get_by_channel_id(channel.id)
            if temp is None:
                return
            await repo.delete_by_channel_id(channel.id)

        try:
            await channel.delete(reason="Temporary voice channel empty")
        except discord.HTTPException:
            pass
