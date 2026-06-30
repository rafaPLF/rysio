from __future__ import annotations

from datetime import timezone
from html import escape
from pathlib import Path

import discord

from bot.database.repositories.ticket_repo import TicketRepository
from bot.database.repositories.ticket_note_repo import TicketNoteRepository
from bot.database.session import DatabaseSessionManager


class TicketService:
    def _transcript_dir(self) -> Path:
        return Path(__file__).resolve().parents[3] / "transcripts"

    def _ticket_status_label(self, status: str) -> str:
        labels = {
            "open": "Open",
            "claimed": "Claimed",
            "waiting_user": "Wartet auf User",
            "closed": "Closed",
        }
        return labels.get(status, status)

    def _ticket_status_color(self, status: str) -> discord.Color:
        colors = {
            "open": discord.Color.blurple(),
            "claimed": discord.Color.gold(),
            "waiting_user": discord.Color.orange(),
            "closed": discord.Color.red(),
        }
        return colors.get(status, discord.Color.blurple())

    def build_ticket_status_embed(self, ticket) -> discord.Embed:
        embed = discord.Embed(
            title="Rysio Ticket Info",
            description="Aktueller Ticket-Status und Bearbeitungsstand.",
            color=self._ticket_status_color(ticket.status),
        )
        embed.add_field(name="Status", value=f"`{self._ticket_status_label(ticket.status)}`", inline=True)
        embed.add_field(
            name="Claim",
            value=f"<@{ticket.claimed_by_user_id}>" if ticket.claimed_by_user_id else "`Nicht geclaimt`",
            inline=True,
        )
        embed.add_field(name="Ticket-ID", value=f"`{ticket.id}`", inline=True)
        embed.add_field(name="Erstellt von", value=f"<@{ticket.user_id}>", inline=True)
        return embed

    async def refresh_ticket_status_message(
        self,
        bot: discord.Client,
        ticket_channel: discord.TextChannel,
        ticket,
        *,
        fallback_content: str | None = None,
    ) -> bool:
        from bot.modules.tickets.views import TicketManageView

        status_message = None
        async for message in ticket_channel.history(limit=25, oldest_first=True):
            if bot.user is None or message.author.id != bot.user.id:
                continue
            if message.components:
                status_message = message
                break

        if status_message is None:
            return False

        try:
            await status_message.edit(
                content=status_message.content or fallback_content,
                embed=self.build_ticket_status_embed(ticket),
                view=TicketManageView(),
            )
            return True
        except discord.HTTPException:
            return False

    async def notify_waiting_user(
        self,
        bot: discord.Client,
        ticket,
        ticket_channel: discord.TextChannel,
    ) -> bool:
        user = bot.get_user(ticket.user_id)
        if user is None:
            try:
                user = await bot.fetch_user(ticket.user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return False

        try:
            await user.send(
                f"Hallo! In deinem Ticket auf **{ticket_channel.guild.name}** gibt es eine neue Antwort vom Team.\n"
                f"Bitte schau in **#{ticket_channel.name}** vorbei."
            )
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def restore_views(self, bot: discord.Client) -> None:
        from bot.modules.tickets.views import TicketCreateView, TicketManageView

        bot.add_view(TicketManageView())

        database: DatabaseSessionManager = bot.database  # type: ignore[attr-defined]
        async with database.session() as session:
            repo = TicketRepository(session)
            panels = await repo.get_all_panels()

        for panel in panels:
            bot.add_view(TicketCreateView(), message_id=panel.message_id)

    async def get_ticket(self, bot: discord.Client, channel_id: int):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            return await repo.get_ticket_by_channel(channel_id)

    async def claim_ticket(self, bot: discord.Client, ticket_channel: discord.TextChannel, moderator: discord.Member):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            ticket = await repo.get_ticket_by_channel(ticket_channel.id)
            if ticket is None:
                return None, "Dieses Ticket wurde nicht in der Datenbank gefunden."
            if ticket.status == "closed":
                return None, "Dieses Ticket ist bereits geschlossen."
            if ticket.claimed_by_user_id and ticket.claimed_by_user_id != moderator.id:
                return None, f"Dieses Ticket wurde bereits von <@{ticket.claimed_by_user_id}> uebernommen."
            await repo.claim_ticket(ticket, moderator.id)
            return ticket, None

    async def set_waiting_user(self, bot: discord.Client, ticket_channel: discord.TextChannel):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            ticket = await repo.get_ticket_by_channel(ticket_channel.id)
            if ticket is None:
                return None
            ticket = await repo.set_ticket_status(ticket, "waiting_user")

        await self.refresh_ticket_status_message(bot, ticket_channel, ticket)
        await self.notify_waiting_user(bot, ticket, ticket_channel)
        return ticket

    async def add_note(self, bot: discord.Client, ticket_channel: discord.TextChannel, author: discord.abc.User, note_text: str):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            ticket_repo = TicketRepository(session)
            note_repo = TicketNoteRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel(ticket_channel.id)
            if ticket is None:
                return None
            await note_repo.create_note(
                ticket_id=ticket.id,
                author_user_id=author.id,
                author_username=str(author),
                note_text=note_text,
            )
            return ticket

    async def list_notes(self, bot: discord.Client, ticket_channel: discord.TextChannel, limit: int = 10):
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            ticket_repo = TicketRepository(session)
            note_repo = TicketNoteRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel(ticket_channel.id)
            if ticket is None:
                return None, []
            notes = await note_repo.list_for_ticket(ticket.id, limit=limit)
            return ticket, notes

    async def render_transcript(self, channel: discord.TextChannel) -> str:
        transcript_dir = self._transcript_dir()
        transcript_dir.mkdir(parents=True, exist_ok=True)
        messages = []
        async for message in channel.history(limit=200, oldest_first=True):
            created_at = message.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            content = escape(message.content or "")
            attachments = "".join(
                f'<li><a href="{escape(attachment.url)}">{escape(attachment.filename)}</a></li>'
                for attachment in message.attachments
            )
            messages.append(
                "<article>"
                f"<h3>{escape(str(message.author))}</h3>"
                f"<p><small>{created_at}</small></p>"
                f"<p>{content or '(keine Textnachricht)'}</p>"
                f"{f'<ul>{attachments}</ul>' if attachments else ''}"
                "</article>"
            )

        filename = f"ticket-{channel.guild.id}-{channel.id}.html"
        transcript_path = transcript_dir / filename
        transcript_html = (
            "<html><head><meta charset='utf-8'><title>Rysio Ticket Transcript</title></head><body>"
            f"<h1>Transcript fuer #{escape(channel.name)}</h1>"
            + "".join(messages)
            + "</body></html>"
        )
        transcript_path.write_text(transcript_html, encoding="utf-8")
        return str(transcript_path)

    async def close_ticket(self, bot: discord.Client, ticket_channel: discord.TextChannel, closer: discord.abc.User):
        transcript_path = await self.render_transcript(ticket_channel)
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            ticket = await repo.get_ticket_by_channel(ticket_channel.id)
            if ticket is None:
                return None, None
            await repo.close_ticket(ticket, closed_by_user_id=closer.id, transcript_path=transcript_path)
            return ticket, transcript_path

    async def cleanup_stale_panels(self, bot: discord.Client, guild: discord.Guild) -> int:
        removed = 0
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            panels = await repo.get_panels_for_guild(guild.id)
            for panel in panels:
                channel = guild.get_channel(panel.channel_id)
                if not isinstance(channel, discord.TextChannel):
                    removed += await repo.delete_panel_by_message_id(panel.message_id)
                    continue

                try:
                    await channel.fetch_message(panel.message_id)
                except discord.NotFound:
                    removed += await repo.delete_panel_by_message_id(panel.message_id)
                except discord.HTTPException:
                    continue
        return removed
