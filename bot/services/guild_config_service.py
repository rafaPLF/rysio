from __future__ import annotations

import json

from bot.database.repositories.guild_repo import GuildRepository
from bot.database.session import DatabaseSessionManager

class GuildConfigService:
    def __init__(self, default_language: str = "de") -> None:
        self.default_language = default_language

    def get_default_language(self) -> str:
        return self.default_language

    async def ensure_guild(self, database: DatabaseSessionManager, guild_id: int) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.ensure_guild(guild_id, self.default_language)
            await repo.ensure_settings(guild_id)

    async def get_language(self, database: DatabaseSessionManager, guild_id: int) -> str:
        async with database.session() as session:
            repo = GuildRepository(session)
            language = await repo.get_language(guild_id)
            return language or self.default_language

    async def set_language(self, database: DatabaseSessionManager, guild_id: int, language: str) -> str:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_language(guild_id, language, self.default_language)
            await repo.ensure_settings(guild_id)
            return language

    async def get_settings(self, database: DatabaseSessionManager, guild_id: int):
        async with database.session() as session:
            repo = GuildRepository(session)
            return await repo.get_settings(guild_id)

    async def set_autorole(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        role_id: int | None,
        mode: str,
        enabled: bool,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_autorole(guild_id, role_id, mode, enabled, self.default_language)

    async def set_antispam(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        enabled: bool,
        threshold: int,
        interval_seconds: int,
        action: str,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_antispam(
                guild_id,
                enabled,
                threshold,
                interval_seconds,
                action,
                self.default_language,
            )

    async def set_info_channel(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        channel_id: int | None,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_info_channel(guild_id, channel_id, self.default_language)

    async def set_join_to_create(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        enabled: bool,
        channel_id: int | None,
        category_id: int | None,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_join_to_create(
                guild_id,
                enabled,
                channel_id,
                category_id,
                self.default_language,
            )

    async def set_last_patch_notes_version(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        version: str | None,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_last_patch_notes_version(guild_id, version, self.default_language)

    async def set_logs(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        enabled: bool,
        channel_id: int | None,
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            await repo.set_logs(guild_id, enabled, channel_id, self.default_language)

    async def get_mod_role_ids(self, database: DatabaseSessionManager, guild_id: int) -> list[int]:
        settings = await self.get_settings(database, guild_id)
        if settings is None or not settings.mod_role_ids_json:
            return []
        try:
            raw_ids = json.loads(settings.mod_role_ids_json)
        except json.JSONDecodeError:
            return []
        if not isinstance(raw_ids, list):
            return []
        result: list[int] = []
        for value in raw_ids:
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return result

    async def set_mod_role_ids(
        self,
        database: DatabaseSessionManager,
        guild_id: int,
        role_ids: list[int],
    ) -> None:
        async with database.session() as session:
            repo = GuildRepository(session)
            serialized = json.dumps(sorted(set(role_ids)), ensure_ascii=True) if role_ids else None
            await repo.set_mod_roles(guild_id, serialized, self.default_language)
