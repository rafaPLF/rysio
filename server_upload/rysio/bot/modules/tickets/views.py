from __future__ import annotations

import discord


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
            await repo.create_ticket(interaction.guild.id, ticket_channel.id, interaction.user.id)

        content = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.created_channel_message",
            language=language,
            user=interaction.user.mention,
        )
        await ticket_channel.send(content, view=TicketCloseView())

        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "tickets.created_success",
            language=language,
            channel=ticket_channel.mention,
        )
        await interaction.response.send_message(response, ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket schliessen", style=discord.ButtonStyle.red, custom_id="tickets:close")
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from bot.database.repositories.ticket_repo import TicketRepository

        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = TicketRepository(session)
            ticket = await repo.get_ticket_by_channel(interaction.channel.id)
            if ticket is None or ticket.status != "open":
                message = interaction.client.localization.translate("tickets.not_found", language=language)  # type: ignore[attr-defined]
                await interaction.response.send_message(message, ephemeral=True)
                return

            await repo.close_ticket(ticket)

        await interaction.response.send_message(
            interaction.client.localization.translate("tickets.closing", language=language),  # type: ignore[attr-defined]
            ephemeral=True,
        )
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
