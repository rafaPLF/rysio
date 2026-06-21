from __future__ import annotations

import discord

from bot.database.models.reaction_roles import ReactionRoleEntry


class ReactionRoleButton(discord.ui.Button["ReactionRolePanelView"]):
    def __init__(self, entry: ReactionRoleEntry) -> None:
        super().__init__(
            label=entry.label[:80],
            style=discord.ButtonStyle.secondary,
            custom_id=f"reaction-role:{entry.id}",
        )
        self.entry_id = entry.id

    async def callback(self, interaction: discord.Interaction) -> None:
        from bot.database.repositories.reaction_role_repo import ReactionRoleRepository

        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Das geht nur als Servermitglied.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        async with interaction.client.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            entry = await repo.get_entry_by_id(self.entry_id)

        if entry is None:
            message = interaction.client.localization.translate("reaction_roles.entry_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        role = interaction.guild.get_role(entry.role_id)
        if role is None:
            message = interaction.client.localization.translate("reaction_roles.role_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            message = interaction.client.localization.translate("reaction_roles.bot_missing_permissions", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if role >= bot_member.top_role:
            message = interaction.client.localization.translate("reaction_roles.role_too_high", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Reaction role toggle remove")
            message = interaction.client.localization.translate(  # type: ignore[attr-defined]
                "reaction_roles.role_removed",
                language=language,
                role=role.mention,
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        await interaction.user.add_roles(role, reason="Reaction role toggle add")
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "reaction_roles.role_added",
            language=language,
            role=role.mention,
        )
        await interaction.response.send_message(message, ephemeral=True)


class ReactionRolePanelView(discord.ui.View):
    def __init__(self, entries: list[ReactionRoleEntry]) -> None:
        super().__init__(timeout=None)
        for entry in entries[:25]:
            self.add_item(ReactionRoleButton(entry))


class ReactionRoleManageView(discord.ui.View):
    def __init__(self, panel_id: int) -> None:
        super().__init__(timeout=600)
        self.panel_id = panel_id

    async def _ensure_admin(self, interaction: discord.Interaction) -> bool:
        from bot.utils.access import can_manage_guild

        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return False

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Rolle hinzufuegen", style=discord.ButtonStyle.green, custom_id="reactionroles:manage:add")
    async def add_role(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_admin(interaction):
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        view = ReactionRoleAddView(self.panel_id)
        message = interaction.client.localization.translate("reaction_roles.manage_add_prompt", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, view=view, ephemeral=True)

    @discord.ui.button(label="Rolle entfernen", style=discord.ButtonStyle.red, custom_id="reactionroles:manage:remove")
    async def remove_role(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_admin(interaction):
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        entries = await interaction.client.reaction_roles.get_panel_entries(interaction.client, self.panel_id)  # type: ignore[attr-defined]
        if not entries:
            message = interaction.client.localization.translate("reaction_roles.manage_remove_empty", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        view = ReactionRoleRemoveView(self.panel_id, entries)
        message = interaction.client.localization.translate("reaction_roles.manage_remove_prompt", language=language)  # type: ignore[attr-defined]
        await interaction.response.send_message(message, view=view, ephemeral=True)

    @discord.ui.button(label="Neu laden", style=discord.ButtonStyle.blurple, custom_id="reactionroles:manage:refresh")
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_admin(interaction):
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        panel = await interaction.client.reaction_roles.get_panel(interaction.client, self.panel_id)  # type: ignore[attr-defined]
        entries = await interaction.client.reaction_roles.get_panel_entries(interaction.client, self.panel_id)  # type: ignore[attr-defined]
        if panel is None:
            message = interaction.client.localization.translate("reaction_roles.panel_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.edit_message(content=message, embed=None, view=None)
            return

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
        await interaction.response.edit_message(embed=embed, view=self)


class ReactionRoleAddSelect(discord.ui.RoleSelect):
    def __init__(self, panel_id: int) -> None:
        super().__init__(placeholder="Rolle auswaehlen...", min_values=1, max_values=1)
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        selected_role = self.values[0]
        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            message = interaction.client.localization.translate("reaction_roles.bot_missing_permissions", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        if selected_role >= bot_member.top_role:
            message = interaction.client.localization.translate("reaction_roles.role_too_high", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        entry = await interaction.client.reaction_roles.add_entry(  # type: ignore[attr-defined]
            interaction.client,
            self.panel_id,
            selected_role.id,
            selected_role.name,
        )
        if entry is None:
            message = interaction.client.localization.translate("reaction_roles.entry_exists", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        await interaction.client.reaction_roles.refresh_panel_message(interaction.client, interaction.guild, self.panel_id)  # type: ignore[attr-defined]
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "reaction_roles.entry_added",
            language=language,
            role=selected_role.mention,
            panel_id=self.panel_id,
        )
        await interaction.response.send_message(message, ephemeral=True)


class ReactionRoleAddView(discord.ui.View):
    def __init__(self, panel_id: int) -> None:
        super().__init__(timeout=300)
        self.add_item(ReactionRoleAddSelect(panel_id))


class ReactionRoleRemoveSelect(discord.ui.Select["ReactionRoleRemoveView"]):
    def __init__(self, panel_id: int, entries: list[ReactionRoleEntry]) -> None:
        options = [
            discord.SelectOption(label=entry.label[:100], value=str(entry.id))
            for entry in entries[:25]
        ]
        super().__init__(placeholder="Rolle entfernen...", min_values=1, max_values=1, options=options)
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        entry_id = int(self.values[0])
        entries = await interaction.client.reaction_roles.get_panel_entries(interaction.client, self.panel_id)  # type: ignore[attr-defined]
        entry = next((item for item in entries if item.id == entry_id), None)
        if entry is None:
            message = interaction.client.localization.translate("reaction_roles.entry_not_found", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        role = interaction.guild.get_role(entry.role_id)
        await interaction.client.reaction_roles.remove_entry(interaction.client, entry_id)  # type: ignore[attr-defined]
        await interaction.client.reaction_roles.refresh_panel_message(interaction.client, interaction.guild, self.panel_id)  # type: ignore[attr-defined]
        message = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "reaction_roles.entry_removed",
            language=language,
            role=role.mention if role else f"`{entry.role_id}`",
            panel_id=self.panel_id,
        )
        await interaction.response.send_message(message, ephemeral=True)


class ReactionRoleRemoveView(discord.ui.View):
    def __init__(self, panel_id: int, entries: list[ReactionRoleEntry]) -> None:
        super().__init__(timeout=300)
        self.add_item(ReactionRoleRemoveSelect(panel_id, entries))
