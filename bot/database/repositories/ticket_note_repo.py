from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.ticket import TicketNote


class TicketNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_note(
        self,
        *,
        ticket_id: int,
        author_user_id: int,
        author_username: str,
        note_text: str,
    ) -> TicketNote:
        entry = TicketNote(
            ticket_id=ticket_id,
            author_user_id=author_user_id,
            author_username=author_username,
            note_text=note_text,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_ticket(self, ticket_id: int, *, limit: int = 10) -> list[TicketNote]:
        result = await self.session.execute(
            select(TicketNote)
            .where(TicketNote.ticket_id == ticket_id)
            .order_by(desc(TicketNote.created_at), desc(TicketNote.id))
            .limit(limit)
        )
        return list(result.scalars().all())
