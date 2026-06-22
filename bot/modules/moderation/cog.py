from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.moderation.service import ModerationService
from bot.utils.access import can_manage_guild, can_use_moderation, has_owner_bypass


class ModerationGroup(app_commands.Group):
    def __init__(self, service: ModerationService) -> None:
        super().__init__(name="mod", description="Moderations-Befehle fuer Warns, Timeouts und Serverstrafen")
        self._service = service

    def _can_target(self, interaction: discord.Interaction, target: discord.Member) -> tuple[bool, str | None]:
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        if target.id == interaction.user.id:
            return False, "Du kannst dich nicht selbst moderieren."
        if target.id == interaction.client.user.id:  # type: ignore[attr-defined]
            return False, "Rysio kann nicht gegen sich selbst eingesetzt werden."
        if target == interaction.guild.owner:
            return False, "Den Server-Owner kannst du nicht moderieren."
        if has_owner_bypass(interaction.client, target.id):
            return False, "Owner-Bypass-Ziele koennen nicht moderiert werden."
        if target.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return False, "Diese Person steht in der Rollen-Hierarchie ueber dir oder gleich hoch."

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            return False, "Ich konnte meine eigenen Bot-Rechte nicht pruefen."
        if target.top_role >= bot_member.top_role:
            return False, "Ich bin in der Rollen-Hierarchie nicht hoch genug fuer diese Aktion."
        return True, None

    def _has_permission(self, interaction: discord.Interaction, permission_name: str) -> bool:
        if has_owner_bypass(interaction.client, interaction.user.id):
            return True
        return isinstance(interaction.user, discord.Member) and getattr(interaction.user.guild_permissions, permission_name)

    async def _ensure_mod_access(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return False
        if await can_use_moderation(interaction.client, interaction.user, interaction.guild.id):
            return True
        await interaction.response.send_message(
            "Dafuer brauchst du Admin-/Server-Rechte oder eine freigeschaltete Moderations-Rolle.",
            ephemeral=True,
        )
        return False

    @app_commands.command(name="setrole", description="Fuegt eine Moderations-Rolle hinzu oder entfernt sie wieder.")
    @app_commands.describe(action="Aktion fuer die Rolle", role="Rolle mit Zugriff auf /mod")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Hinzufuegen", value="add"),
            app_commands.Choice(name="Entfernen", value="remove"),
        ]
    )
    async def setrole(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: discord.Role,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        current_roles = await interaction.client.guild_config.get_mod_role_ids(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        if action.value == "add":
            updated_roles = sorted(set([*current_roles, role.id]))
            await interaction.client.guild_config.set_mod_role_ids(  # type: ignore[attr-defined]
                interaction.client.database,
                interaction.guild.id,
                updated_roles,
            )
            await interaction.response.send_message(
                f"Moderations-Rolle hinzugefuegt: {role.mention}",
                ephemeral=True,
            )
            return

        updated_roles = [role_id for role_id in current_roles if role_id != role.id]
        await interaction.client.guild_config.set_mod_role_ids(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            updated_roles,
        )
        await interaction.response.send_message(
            f"Moderations-Rolle entfernt: {role.mention}",
            ephemeral=True,
        )

    @app_commands.command(name="roles", description="Zeigt alle Rollen mit Zugriff auf /mod.")
    async def roles(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        role_ids = await interaction.client.guild_config.get_mod_role_ids(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        if not role_ids:
            await interaction.response.send_message(
                "Es sind aktuell keine extra Moderations-Rollen gesetzt. Admins koennen sie mit `/mod setrole` hinzufuegen.",
                ephemeral=True,
            )
            return

        mentions = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            mentions.append(role.mention if role else f"`{role_id}`")
        await interaction.response.send_message(
            "Aktive Moderations-Rollen:\n" + "\n".join(f"- {mention}" for mention in mentions),
            ephemeral=True,
        )

    @app_commands.command(name="warn", description="Vermerkt eine Warnung fuer einen User.")
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await self._ensure_mod_access(interaction):
            return

        allowed, error = self._can_target(interaction, user)
        if not allowed:
            await interaction.response.send_message(error or "Diese Aktion ist nicht moeglich.", ephemeral=True)
            return

        case_entry = await self._service.create_case(
            interaction.client,
            guild=interaction.guild,
            action_type="warn",
            target_user_id=user.id,
            target_username=str(user),
            moderator_user=interaction.user,
            reason=reason,
            active=False,
        )
        await interaction.response.send_message(
            f"Warnung gespeichert. Case `#{case_entry.case_number}` fuer {user.mention}. Grund: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="timeout", description="Gibt einem User einen Timeout.")
    @app_commands.describe(minutes="Dauer des Timeouts in Minuten")
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await self._ensure_mod_access(interaction):
            return

        allowed, error = self._can_target(interaction, user)
        if not allowed:
            await interaction.response.send_message(error or "Diese Aktion ist nicht moeglich.", ephemeral=True)
            return

        try:
            await user.timeout(timedelta(minutes=minutes), reason=f"{interaction.user}: {reason}")
        except discord.HTTPException:
            await interaction.response.send_message("Der Timeout konnte nicht gesetzt werden.", ephemeral=True)
            return

        case_entry = await self._service.create_case(
            interaction.client,
            guild=interaction.guild,
            action_type="timeout",
            target_user_id=user.id,
            target_username=str(user),
            moderator_user=interaction.user,
            reason=reason,
            duration_minutes=minutes,
            active=True,
        )
        await interaction.response.send_message(
            f"Timeout gesetzt. Case `#{case_entry.case_number}` fuer {user.mention} fuer `{minutes}` Minuten. Grund: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="kick", description="Kickt einen User vom Server.")
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await self._ensure_mod_access(interaction):
            return

        allowed, error = self._can_target(interaction, user)
        if not allowed:
            await interaction.response.send_message(error or "Diese Aktion ist nicht moeglich.", ephemeral=True)
            return

        target_name = str(user)
        target_id = user.id
        try:
            await user.kick(reason=f"{interaction.user}: {reason}")
        except discord.HTTPException:
            await interaction.response.send_message("Der Kick konnte nicht ausgefuehrt werden.", ephemeral=True)
            return

        case_entry = await self._service.create_case(
            interaction.client,
            guild=interaction.guild,
            action_type="kick",
            target_user_id=target_id,
            target_username=target_name,
            moderator_user=interaction.user,
            reason=reason,
            active=False,
        )
        await interaction.response.send_message(
            f"Kick ausgefuehrt. Case `#{case_entry.case_number}` fuer `{target_name}`. Grund: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="ban", description="Bannt einen User vom Server.")
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await self._ensure_mod_access(interaction):
            return

        allowed, error = self._can_target(interaction, user)
        if not allowed:
            await interaction.response.send_message(error or "Diese Aktion ist nicht moeglich.", ephemeral=True)
            return

        target_name = str(user)
        target_id = user.id
        try:
            await interaction.guild.ban(user, reason=f"{interaction.user}: {reason}", delete_message_seconds=0)
        except discord.HTTPException:
            await interaction.response.send_message("Der Ban konnte nicht ausgefuehrt werden.", ephemeral=True)
            return

        case_entry = await self._service.create_case(
            interaction.client,
            guild=interaction.guild,
            action_type="ban",
            target_user_id=target_id,
            target_username=target_name,
            moderator_user=interaction.user,
            reason=reason,
            active=False,
        )
        await interaction.response.send_message(
            f"Ban ausgefuehrt. Case `#{case_entry.case_number}` fuer `{target_name}`. Grund: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="history", description="Zeigt die letzten Moderations-Cases eines Users.")
    async def history(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not await self._ensure_mod_access(interaction):
            return

        entries = await self._service.list_cases_for_user(
            interaction.client,
            guild_id=interaction.guild.id,
            target_user_id=user.id,
            limit=10,
        )
        if not entries:
            await interaction.response.send_message("Fuer diesen User wurden noch keine Cases gefunden.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Moderations-Historie fuer {user}",
            color=discord.Color.orange(),
        )
        for entry in entries:
            duration_text = f" | Dauer: {entry.duration_minutes} Min." if entry.duration_minutes else ""
            embed.add_field(
                name=f"Case #{entry.case_number} | {entry.action_type.upper()}",
                value=f"Moderator: `{entry.moderator_username}`\nGrund: {entry.reason}{duration_text}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._service = ModerationService()
        self.bot.tree.add_command(ModerationGroup(self._service))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
