from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.reaction_roles import ReactionRoleEntry, ReactionRolePanel


class ReactionRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_panel(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        title: str,
        description: str,
    ) -> ReactionRolePanel:
        panel = ReactionRolePanel(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            title=title,
            description=description,
        )
        self.session.add(panel)
        await self.session.flush()
        return panel

    async def get_panels_for_guild(self, guild_id: int) -> list[ReactionRolePanel]:
        result = await self.session.execute(
            select(ReactionRolePanel).where(ReactionRolePanel.guild_id == guild_id)
        )
        return list(result.scalars().all())

    async def get_all_panels(self) -> list[ReactionRolePanel]:
        result = await self.session.execute(select(ReactionRolePanel))
        return list(result.scalars().all())

    async def get_panel_by_message_id(self, message_id: int) -> ReactionRolePanel | None:
        result = await self.session.execute(
            select(ReactionRolePanel).where(ReactionRolePanel.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_panel_by_id(self, panel_id: int) -> ReactionRolePanel | None:
        return await self.session.get(ReactionRolePanel, panel_id)

    async def delete_panel(self, panel_id: int) -> int:
        await self.session.execute(delete(ReactionRoleEntry).where(ReactionRoleEntry.panel_id == panel_id))
        result = await self.session.execute(delete(ReactionRolePanel).where(ReactionRolePanel.id == panel_id))
        return result.rowcount or 0

    async def create_entry(self, panel_id: int, role_id: int, label: str) -> ReactionRoleEntry:
        entry = ReactionRoleEntry(panel_id=panel_id, role_id=role_id, label=label)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_entries_for_panel(self, panel_id: int) -> list[ReactionRoleEntry]:
        result = await self.session.execute(
            select(ReactionRoleEntry).where(ReactionRoleEntry.panel_id == panel_id).order_by(ReactionRoleEntry.id)
        )
        return list(result.scalars().all())

    async def get_entry_by_id(self, entry_id: int) -> ReactionRoleEntry | None:
        return await self.session.get(ReactionRoleEntry, entry_id)

    async def get_entry_by_panel_and_role(self, panel_id: int, role_id: int) -> ReactionRoleEntry | None:
        result = await self.session.execute(
            select(ReactionRoleEntry).where(
                ReactionRoleEntry.panel_id == panel_id,
                ReactionRoleEntry.role_id == role_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_entry(self, entry_id: int) -> int:
        result = await self.session.execute(delete(ReactionRoleEntry).where(ReactionRoleEntry.id == entry_id))
        return result.rowcount or 0
