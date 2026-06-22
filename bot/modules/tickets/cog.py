from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.repositories.premium_repo import PremiumRepository
from bot.database.repositories.ticket_repo import TicketRepository
from bot.modules.tickets.service import TicketService
from bot.modules.tickets.views import TicketCreateView
from bot.utils.access import can_manage_guild, can_use_moderation, has_owner_bypass


class TicketsGroup(app_commands.Group):
    def __init__(self, ticket_service: TicketService) -> None:
        super().__init__(name="tickets", description="Ticket-System verwalten")
        self.ticket_service = ticket_service

    @app_commands.command(name="status", description="Zeigt den Status des Ticket-Moduls.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message = interaction.client.localization.translate("tickets.status", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="panel", description="Erstellt ein Ticket-Panel im aktuellen Kanal.")
    @app_commands.describe(
        title="Titel des Panels",
        description_text="Kurze Beschreibung fuer Nutzer",
        category="Kategorie fuer neue Ticket-Channels",
        support_role="Support-Rolle mit Zugriff auf Tickets",
        welcome_message="Optionale erste Auto-Nachricht im Ticket",
    )
    async def panel(
        self,
        interaction: discord.Interaction,
        title: str,
        description_text: str,
        category: discord.CategoryChannel | None = None,
        support_role: discord.Role | None = None,
        welcome_message: str | None = None,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        channel_permissions = interaction.channel.permissions_for(bot_member)
        if not (channel_permissions.send_messages and channel_permissions.embed_links):
            await interaction.response.send_message(
                "Rysio braucht in diesem Channel `Nachrichten senden` und `Links einbetten`.",
                ephemeral=True,
            )
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.response.defer(ephemeral=True)
        await self.ticket_service.cleanup_stale_panels(interaction.client, interaction.guild)

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            premium_repo = PremiumRepository(session)
            ticket_repo = TicketRepository(session)
            plan = await premium_repo.get_active_plan(interaction.guild.id)
            current_panels = await ticket_repo.count_panels_for_guild(interaction.guild.id)
            limit = interaction.client.premium.get_panel_limit(  # type: ignore[attr-defined]
                plan,
                unlimited=has_owner_bypass(interaction.client, interaction.user.id),
            )

            if current_panels >= limit:
                feature_message = interaction.client.localization.translate(  # type: ignore[attr-defined]
                    "tickets.panel_limit_reached",
                    language=language,
                    limit=limit,
                )
                await interaction.followup.send(feature_message, ephemeral=True)
                return

        embed = discord.Embed(title=title, description=description_text, color=discord.Color.blurple())
        embed.add_field(
            name=interaction.client.localization.translate("tickets.panel_field_name", language=language),  # type: ignore[attr-defined]
            value=interaction.client.localization.translate("tickets.panel_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        message = await interaction.channel.send(embed=embed, view=TicketCreateView())

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            ticket_repo = TicketRepository(session)
            await ticket_repo.create_panel(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                message_id=message.id,
                category_id=category.id if category else None,
                support_role_id=support_role.id if support_role else None,
                welcome_message=welcome_message.strip() if welcome_message else None,
            )

        interaction.client.add_view(TicketCreateView(), message_id=message.id)  # type: ignore[attr-defined]
        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.panel_created",
            language=language,
            channel=interaction.channel.mention,
        )
        await interaction.followup.send(response, ephemeral=True)

    @app_commands.command(name="note", description="Speichert eine interne Team-Notiz im aktuellen Ticket.")
    async def note(self, interaction: discord.Interaction, note_text: str) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Das geht nur in einem Ticket-Channel.", ephemeral=True)
            return
        if not await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            await interaction.response.send_message("Dafuer brauchst du Moderations-Zugriff.", ephemeral=True)
            return

        ticket = await self.ticket_service.add_note(interaction.client, interaction.channel, interaction.user, note_text)
        if ticket is None:
            await interaction.response.send_message("In diesem Channel wurde kein Ticket gefunden.", ephemeral=True)
            return
        await interaction.response.send_message("Team-Notiz gespeichert.", ephemeral=True)

    @app_commands.command(name="info", description="Zeigt Status, Claim und Notizen des aktuellen Tickets.")
    async def info(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Das geht nur in einem Ticket-Channel.", ephemeral=True)
            return
        if not await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            await interaction.response.send_message("Dafuer brauchst du Moderations-Zugriff.", ephemeral=True)
            return

        ticket, notes = await self.ticket_service.list_notes(interaction.client, interaction.channel, limit=5)
        if ticket is None:
            await interaction.response.send_message("In diesem Channel wurde kein Ticket gefunden.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Ticket #{ticket.id}", color=discord.Color.blurple())
        embed.add_field(name="Status", value=f"`{ticket.status}`", inline=True)
        embed.add_field(
            name="Claimed By",
            value=f"<@{ticket.claimed_by_user_id}>" if ticket.claimed_by_user_id else "-",
            inline=True,
        )
        embed.add_field(
            name="Transcript",
            value=ticket.transcript_path or "-",
            inline=False,
        )
        if notes:
            embed.add_field(
                name="Letzte Team-Notizen",
                value="\n".join(
                    f"- `{note.author_username}`: {note.note_text[:120]}"
                    for note in notes
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="panels-reset", description="Loescht alle gespeicherten Ticket-Panels fuer diesen Server.")
    async def panels_reset(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.response.defer(ephemeral=True)

        deleted_messages = 0
        stale_entries = 0
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            panels = await repo.get_panels_for_guild(interaction.guild.id)
            for panel in panels:
                channel = interaction.guild.get_channel(panel.channel_id)
                if isinstance(channel, discord.TextChannel):
                    try:
                        message = await channel.fetch_message(panel.message_id)
                        await message.delete()
                        deleted_messages += 1
                    except discord.NotFound:
                        stale_entries += 1
                    except discord.HTTPException:
                        stale_entries += 1
                else:
                    stale_entries += 1

            removed_records = await repo.delete_panels_for_guild(interaction.guild.id)

        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.panels_reset_done",
            language=language,
            removed=removed_records,
            deleted=deleted_messages,
            stale=stale_entries,
        )
        await interaction.followup.send(message, ephemeral=True)


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(TicketsGroup(bot.tickets))  # type: ignore[attr-defined]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketsCog(bot))
