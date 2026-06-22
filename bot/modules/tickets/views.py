from __future__ import annotations

import discord

from bot.utils.access import can_manage_guild, can_use_moderation


class TicketCreateView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket erstellen", style=discord.ButtonStyle.green, custom_id="tickets:create")
    async def create_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from bot.database.repositories.ticket_repo import TicketRepository

        if interaction.guild is None or interaction.channel is None or interaction.message is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            panel = await repo.get_panel_by_message(interaction.message.id)
            existing_ticket = await repo.get_open_ticket_for_user(interaction.guild.id, interaction.user.id)

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        if panel is None:
            message = interaction.client.localization.translate("tickets.panel_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if existing_ticket is not None:
            message = interaction.client.localization.translate("tickets.already_open", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        category = interaction.guild.get_channel(panel.category_id) if panel.category_id else None
        support_role = interaction.guild.get_role(panel.support_role_id) if panel.support_role_id else None
        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }
        if support_role is not None:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

        channel_name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:90]
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason=f"Ticket for {interaction.user}",
        )

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            ticket = await repo.create_ticket(interaction.guild.id, ticket_channel.id, interaction.user.id, panel.id if panel else None)

        content = panel.welcome_message if panel and panel.welcome_message else interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.created_channel_message",
            language=language,
            user=interaction.user.mention,
        )
        auto_status = f"\n\nStatus: `open`\nTicket-ID: `{ticket.id}`"
        await ticket_channel.send(content + auto_status, view=TicketManageView())

        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.created_success",
            language=language,
            channel=ticket_channel.mention,
        )
        await interaction.response.send_message(response, ephemeral=True)


class TicketManageView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple, custom_id="tickets:claim")
    async def claim_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            await interaction.response.send_message("Dafuer brauchst du Moderations-Zugriff.", ephemeral=True)
            return

        ticket_service = interaction.client.tickets  # type: ignore[attr-defined]
        ticket, error = await ticket_service.claim_ticket(interaction.client, interaction.channel, interaction.user)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.send_message(
            f"Ticket uebernommen von {interaction.user.mention}. Status: `claimed`",
            ephemeral=False,
        )

    @discord.ui.button(label="Wartet auf User", style=discord.ButtonStyle.gray, custom_id="tickets:waiting_user")
    async def waiting_user(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            await interaction.response.send_message("Dafuer brauchst du Moderations-Zugriff.", ephemeral=True)
            return

        ticket_service = interaction.client.tickets  # type: ignore[attr-defined]
        ticket = await ticket_service.set_waiting_user(interaction.client, interaction.channel)
        if ticket is None:
            await interaction.response.send_message("Ticket nicht gefunden.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Ticket-Status auf `waiting_user` gesetzt.",
            ephemeral=False,
        )

    @discord.ui.button(label="Ticket schliessen", style=discord.ButtonStyle.red, custom_id="tickets:close")
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user) and not await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            await interaction.response.send_message("Dafuer brauchst du Moderations-Zugriff.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        ticket_service = interaction.client.tickets  # type: ignore[attr-defined]
        ticket, transcript_path = await ticket_service.close_ticket(interaction.client, interaction.channel, interaction.user)
        if ticket is None:
            message = interaction.client.localization.translate("tickets.not_found", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        await interaction.response.send_message(
            f"{interaction.client.localization.translate('tickets.closing', language=language)}\nTranscript: `{transcript_path}`",  # type: ignore[attr-defined]
            ephemeral=False,
        )
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
