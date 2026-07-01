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

    async def delete_panel_by_id(self, panel_id: int) -> int:
        query = delete(TicketPanel).where(TicketPanel.id == panel_id)
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
        title: str,
        description_text: str,
        category_id: int | None,
        category_ids_json: str | None,
        topic_options_json: str | None,
        support_role_id: int | None,
        welcome_message: str | None,
    ) -> TicketPanel:
        panel = TicketPanel(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            title=title,
            description_text=description_text,
            category_id=category_id,
            category_ids_json=category_ids_json,
            topic_options_json=topic_options_json,
            support_role_id=support_role_id,
            welcome_message=welcome_message,
        )
        self.session.add(panel)
        await self.session.flush()
        return panel

    async def update_panel(
        self,
        panel: TicketPanel,
        *,
        channel_id: int,
        message_id: int,
        title: str,
        description_text: str,
        category_id: int | None,
        category_ids_json: str | None,
        topic_options_json: str | None,
        support_role_id: int | None,
        welcome_message: str | None,
    ) -> TicketPanel:
        panel.channel_id = channel_id
        panel.message_id = message_id
        panel.title = title
        panel.description_text = description_text
        panel.category_id = category_id
        panel.category_ids_json = category_ids_json
        panel.topic_options_json = topic_options_json
        panel.support_role_id = support_role_id
        panel.welcome_message = welcome_message
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

    async def get_active_tickets_for_guild(self, guild_id: int) -> list[Ticket]:
        query = select(Ticket).where(
            Ticket.guild_id == guild_id,
            Ticket.status.in_(["open", "claimed", "waiting_user"]),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_closed_tickets_for_guild(self, guild_id: int, limit: int = 25) -> list[Ticket]:
        query = (
            select(Ticket)
            .where(
                Ticket.guild_id == guild_id,
                Ticket.status == "closed",
                Ticket.transcript_path.is_not(None),
            )
            .order_by(Ticket.closed_at.desc(), Ticket.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_open_tickets_for_user(self, guild_id: int, user_id: int) -> list[Ticket]:
        query = select(Ticket).where(
            Ticket.guild_id == guild_id,
            Ticket.user_id == user_id,
            Ticket.status.in_(["open", "claimed", "waiting_user"]),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_open_tickets_for_user(self, guild_id: int, user_id: int) -> int:
        tickets = await self.get_open_tickets_for_user(guild_id, user_id)
        return len(tickets)

    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        panel_id: int | None = None,
        selected_topic: str | None = None,
    ) -> Ticket:
        ticket = Ticket(
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            panel_id=panel_id,
            selected_topic=selected_topic,
            status="open",
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def get_ticket_by_channel(self, channel_id: int) -> Ticket | None:
        query = select(Ticket).where(Ticket.channel_id == channel_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        return await self.session.get(Ticket, ticket_id)

    async def set_ticket_status(self, ticket: Ticket, status: str) -> Ticket:
        ticket.status = status
        await self.session.flush()
        return ticket

    async def claim_ticket(self, ticket: Ticket, moderator_user_id: int) -> Ticket:
        ticket.status = "claimed"
        ticket.claimed_by_user_id = moderator_user_id
        ticket.claimed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return ticket

    async def close_ticket(
        self,
        ticket: Ticket,
        *,
        closed_by_user_id: int | None = None,
        transcript_path: str | None = None,
    ) -> Ticket:
        ticket.status = "closed"
        ticket.closed_by_user_id = closed_by_user_id
        ticket.transcript_path = transcript_path
        ticket.closed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return ticket

    async def delete_ticket_transcript(self, ticket: Ticket) -> Ticket:
        ticket.transcript_path = None
        await self.session.flush()
        return ticket
