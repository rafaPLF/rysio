from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.ticket import Ticket, TicketPanel


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_panels_for_guild(self, guild_id: int) -> int:
        query = select(TicketPanel).where(TicketPanel.guild_id == guild_id)
        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def delete_panel_by_message_id(self, message_id: int) -> int:
        query = delete(TicketPanel).where(TicketPanel.message_id == message_id)
        result = await self.session.execute(query)
        return result.rowcount or 0

    async def delete_panels_for_guild(self, guild_id: int) -> int:
        query = delete(TicketPanel).where(TicketPanel.guild_id == guild_id)
        result = await self.session.execute(query)
        return result.rowcount or 0

    async def create_panel(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        category_id: int | None,
        support_role_id: int | None,
    ) -> TicketPanel:
        panel = TicketPanel(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            category_id=category_id,
            support_role_id=support_role_id,
        )
        self.session.add(panel)
        await self.session.flush()
        return panel

    async def get_panel_by_message(self, message_id: int) -> TicketPanel | None:
        query = select(TicketPanel).where(TicketPanel.message_id == message_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_panel_by_id(self, panel_id: int) -> TicketPanel | None:
        return await self.session.get(TicketPanel, panel_id)

    async def get_panels_for_guild(self, guild_id: int) -> list[TicketPanel]:
        query = select(TicketPanel).where(TicketPanel.guild_id == guild_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_panels(self) -> list[TicketPanel]:
        query = select(TicketPanel)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_open_ticket_for_user(self, guild_id: int, user_id: int) -> Ticket | None:
        query = select(Ticket).where(
            Ticket.guild_id == guild_id,
            Ticket.user_id == user_id,
            Ticket.status == "open",
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_ticket(self, guild_id: int, channel_id: int, user_id: int) -> Ticket:
        ticket = Ticket(guild_id=guild_id, channel_id=channel_id, user_id=user_id, status="open")
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def get_ticket_by_channel(self, channel_id: int) -> Ticket | None:
        query = select(Ticket).where(Ticket.channel_id == channel_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def close_ticket(self, ticket: Ticket) -> Ticket:
        ticket.status = "closed"
        ticket.closed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return ticket
