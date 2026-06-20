from __future__ import annotations

import discord

from bot.database.repositories.ticket_repo import TicketRepository
from bot.database.session import DatabaseSessionManager


class TicketService:
    async def restore_views(self, bot: discord.Client) -> None:
        from bot.modules.tickets.views import TicketCloseView, TicketCreateView

        bot.add_view(TicketCloseView())

        database: DatabaseSessionManager = bot.database  # type: ignore[attr-defined]
        async with database.session() as session:
            repo = TicketRepository(session)
            panels = await repo.get_all_panels()

        for panel in panels:
            bot.add_view(TicketCreateView(), message_id=panel.message_id)

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
