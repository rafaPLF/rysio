from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.repositories.reaction_role_repo import ReactionRoleRepository
from bot.modules.reaction_roles.views import ReactionRoleManageView
from bot.utils.access import can_manage_guild


class ReactionRolesGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="reactionroles", description="Reaction Roles verwalten")

    @app_commands.command(name="status", description="Zeigt eine Uebersicht aller Reaction-Role-Panels.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panels = await repo.get_panels_for_guild(interaction.guild.id)

        if not panels:
            message = interaction.client.localization.translate("reaction_roles.status_empty", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        lines: list[str] = []
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            for panel in panels:
                entries = await repo.get_entries_for_panel(panel.id)
                lines.append(
                    interaction.client.localization.translate(  # type: ignore[attr-defined]
                        "reaction_roles.status_line",
                        language=language,
                        panel_id=panel.id,
                        count=len(entries),
                        channel=f"<#{panel.channel_id}>",
                    )
                )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="create", description="Erstellt ein neues Reaction-Role-Panel im aktuellen Kanal.")
    @app_commands.describe(title="Titel des Panels", description_text="Beschreibung fuer Nutzer")
    async def create(self, interaction: discord.Interaction, title: str, description_text: str) -> None:
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

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        embed = discord.Embed(title=title, description=description_text, color=discord.Color.gold())
        embed.add_field(
            name=interaction.client.localization.translate("reaction_roles.panel_field_name", language=language),  # type: ignore[attr-defined]
            value=interaction.client.localization.translate("reaction_roles.panel_field_value_empty", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        message = await interaction.channel.send(embed=embed)

        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panel = await repo.create_panel(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                message_id=message.id,
                title=title,
                description=description_text,
            )

        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "reaction_roles.panel_created",
            language=language,
            panel_id=panel.id,
        )
        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(name="manage", description="Oeffnet die UI-Verwaltung fuer ein Reaction-Role-Panel.")
    @app_commands.describe(panel_id="Die ID des Panels")
    async def manage(self, interaction: discord.Interaction, panel_id: int) -> None:
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
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panel = await repo.get_panel_by_id(panel_id)
            if panel is None or panel.guild_id != interaction.guild.id:
                message = interaction.client.localization.translate("reaction_roles.panel_missing", language=language)  # type: ignore[attr-defined]
                await interaction.response.send_message(message, ephemeral=True)
                return

            entries = await repo.get_entries_for_panel(panel_id)

        embed = discord.Embed(title=panel.title, description=panel.description, color=discord.Color.orange())
        lines = []
        for entry in entries:
            role = interaction.guild.get_role(entry.role_id)
            lines.append(f"- {entry.label}: {role.mention if role else entry.role_id}")
        embed.add_field(
            name=interaction.client.localization.translate("reaction_roles.manage_status_title", language=language),  # type: ignore[attr-defined]
            value="\n".join(lines) if lines else interaction.client.localization.translate("reaction_roles.panel_field_value_empty", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        embed.set_footer(
            text=interaction.client.localization.translate("reaction_roles.manage_footer", language=language)  # type: ignore[attr-defined]
        )
        await interaction.response.send_message(
            embed=embed,
            view=ReactionRoleManageView(panel_id),
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="Loescht ein komplettes Reaction-Role-Panel.")
    @app_commands.describe(panel_id="Die ID des Panels")
    async def delete(self, interaction: discord.Interaction, panel_id: int) -> None:
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
        panel = None
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panel = await repo.get_panel_by_id(panel_id)
            if panel is None or panel.guild_id != interaction.guild.id:
                message = interaction.client.localization.translate("reaction_roles.panel_missing", language=language)  # type: ignore[attr-defined]
                await interaction.response.send_message(message, ephemeral=True)
                return
            await repo.delete_panel(panel_id)

        channel = interaction.guild.get_channel(panel.channel_id) if panel else None
        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(panel.message_id)
                await message.delete()
            except discord.HTTPException:
                pass

        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "reaction_roles.panel_deleted",
            language=language,
            panel_id=panel_id,
        )
        await interaction.response.send_message(message, ephemeral=True)


class ReactionRolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(ReactionRolesGroup())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReactionRolesCog(bot))
