from __future__ import annotations

import discord

from bot.database.models.reaction_roles import ReactionRoleEntry, ReactionRolePanel
from bot.database.repositories.reaction_role_repo import ReactionRoleRepository


class ReactionRoleService:
    async def restore_views(self, bot: discord.Client) -> None:
        from bot.modules.reaction_roles.views import ReactionRolePanelView

        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panels = await repo.get_all_panels()
            panel_entries = {
                panel.id: await repo.get_entries_for_panel(panel.id)
                for panel in panels
            }

        for panel in panels:
            entries = panel_entries.get(panel.id, [])
            if entries:
                bot.add_view(ReactionRolePanelView(entries), message_id=panel.message_id)

    async def get_panel(self, bot: discord.Client, panel_id: int) -> ReactionRolePanel | None:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            return await repo.get_panel_by_id(panel_id)

    async def get_panel_entries(self, bot: discord.Client, panel_id: int) -> list[ReactionRoleEntry]:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            return await repo.get_entries_for_panel(panel_id)

    async def add_entry(self, bot: discord.Client, panel_id: int, role_id: int, label: str) -> ReactionRoleEntry | None:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            existing = await repo.get_entry_by_panel_and_role(panel_id, role_id)
            if existing is not None:
                return None
            return await repo.create_entry(panel_id, role_id, label)

    async def remove_entry(self, bot: discord.Client, entry_id: int) -> int:
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            return await repo.delete_entry(entry_id)

    async def refresh_panel_message(self, bot: discord.Client, guild: discord.Guild, panel_id: int) -> None:
        from bot.modules.reaction_roles.views import ReactionRolePanelView

        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
        async with bot.database.session() as session:  # type: ignore[attr-defined]
            repo = ReactionRoleRepository(session)
            panel = await repo.get_panel_by_id(panel_id)
            if panel is None:
                return
            entries = await repo.get_entries_for_panel(panel_id)

        channel = guild.get_channel(panel.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(panel.message_id)
        except discord.HTTPException:
            return

        lines = []
        for entry in entries:
            role = guild.get_role(entry.role_id)
            lines.append(f"- {entry.label}: {role.mention if role else entry.role_id}")

        embed = discord.Embed(
            title=panel.title,
            description=panel.description,
            color=discord.Color.gold(),
        )
        embed.add_field(
            name=bot.localization.translate("reaction_roles.panel_field_name", language=language),  # type: ignore[attr-defined]
            value="\n".join(lines) if lines else bot.localization.translate("reaction_roles.panel_field_value_empty", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        view = ReactionRolePanelView(entries) if entries else None
        await message.edit(embed=embed, view=view)
        if entries:
            bot.add_view(ReactionRolePanelView(entries), message_id=panel.message_id)
