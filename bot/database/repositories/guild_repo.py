from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.guild import Guild
from bot.database.models.guild_settings import GuildSettings


class GuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_guild(self, guild_id: int, default_language: str) -> Guild:
        guild = await self.session.get(Guild, guild_id)
        if guild is None:
            guild = Guild(guild_id=guild_id, language=default_language)
            self.session.add(guild)
            await self.session.flush()
        return guild

    async def ensure_settings(self, guild_id: int) -> GuildSettings:
        settings = await self.session.get(GuildSettings, guild_id)
        if settings is None:
            settings = GuildSettings(guild_id=guild_id)
            self.session.add(settings)
            await self.session.flush()
        return settings

    async def get_guild(self, guild_id: int) -> Guild | None:
        return await self.session.get(Guild, guild_id)

    async def get_settings(self, guild_id: int) -> GuildSettings | None:
        return await self.session.get(GuildSettings, guild_id)

    async def set_language(self, guild_id: int, language: str, default_language: str) -> Guild:
        guild = await self.ensure_guild(guild_id, default_language)
        guild.language = language
        await self.session.flush()
        return guild

    async def get_language(self, guild_id: int) -> str | None:
        guild = await self.get_guild(guild_id)
        return guild.language if guild else None

    async def set_autorole(
        self,
        guild_id: int,
        role_id: int | None,
        mode: str,
        enabled: bool,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.autorole_role_id = role_id
        settings.autorole_mode = mode
        settings.autorole_enabled = enabled
        await self.session.flush()
        return settings

    async def set_antispam(
        self,
        guild_id: int,
        enabled: bool,
        threshold: int,
        interval_seconds: int,
        action: str,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.spam_protection_enabled = enabled
        settings.spam_threshold = threshold
        settings.spam_interval_seconds = interval_seconds
        settings.spam_action = action
        await self.session.flush()
        return settings

    async def set_info_channel(
        self,
        guild_id: int,
        channel_id: int | None,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.info_channel_id = channel_id
        await self.session.flush()
        return settings

    async def set_join_to_create(
        self,
        guild_id: int,
        enabled: bool,
        channel_id: int | None,
        category_id: int | None,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.join_to_create_enabled = enabled
        settings.join_to_create_channel_id = channel_id
        settings.join_to_create_category_id = category_id
        await self.session.flush()
        return settings

    async def set_logs(
        self,
        guild_id: int,
        enabled: bool,
        channel_id: int | None,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.logs_enabled = enabled
        settings.logs_channel_id = channel_id
        await self.session.flush()
        return settings

    async def set_last_patch_notes_version(
        self,
        guild_id: int,
        version: str | None,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.last_patch_notes_version = version
        await self.session.flush()
        return settings

    async def set_mod_roles(
        self,
        guild_id: int,
        mod_role_ids_json: str | None,
        default_language: str,
    ) -> GuildSettings:
        await self.ensure_guild(guild_id, default_language)
        settings = await self.ensure_settings(guild_id)
        settings.mod_role_ids_json = mod_role_ids_json
        await self.session.flush()
        return settings
