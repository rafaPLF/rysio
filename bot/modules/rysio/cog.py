from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.setup.service import SetupMessageService
from bot.database.repositories.ticket_repo import TicketRepository
from bot.database.repositories.premium_repo import PremiumRepository
from bot.database.repositories.verification_repo import VerificationRepository
from bot.utils.access import can_manage_guild, has_owner_access, has_owner_bypass
from bot.utils.permissions import get_missing_core_permissions


class RysioGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="rysio", description="Zentrale Rysio-Kommandos")

    @app_commands.command(name="help", description="Zeigt alle wichtigen Commands und Features.")
    async def help(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        embed = build_help_embed(interaction.client, language)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Zeigt die aktuelle Rysio-Setup-Uebersicht fuer diesen Server.")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        embed = await build_status_embed(interaction.client, interaction.guild, language)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Legt den Info-Channel fuer Rysio fest und postet die Uebersicht.")
    @app_commands.describe(channel="Channel, in dem Rysio seine Infos und Hilfe posten soll")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        channel_permissions = channel.permissions_for(bot_member)
        if not (channel_permissions.view_channel and channel_permissions.send_messages and channel_permissions.embed_links):
            await interaction.response.send_message(
                "Rysio braucht in diesem Channel `Kanal ansehen`, `Nachrichten senden` und `Links einbetten`.",
                ephemeral=True,
            )
            return

        await interaction.client.guild_config.ensure_guild(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.client.guild_config.set_info_channel(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            channel.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        message_service = SetupMessageService()
        await message_service.send_welcome_message(interaction.client, interaction.guild, channel)

        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "rysio.setup_success",
            language=language,
            channel=channel.mention,
        )
        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(name="commands", description="Postet die aktuelle Command-Uebersicht erneut.")
    async def commands(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        settings = await interaction.client.guild_config.get_settings(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )

        if settings is None or settings.info_channel_id is None:
            message = interaction.client.localization.translate("rysio.no_info_channel", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        channel = interaction.guild.get_channel(settings.info_channel_id)
        if not isinstance(channel, discord.TextChannel):
            message = interaction.client.localization.translate("rysio.info_channel_missing", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        channel_permissions = channel.permissions_for(bot_member)
        if not (channel_permissions.view_channel and channel_permissions.send_messages and channel_permissions.embed_links):
            message = interaction.client.localization.translate("rysio.info_channel_not_writable", language=language)  # type: ignore[attr-defined]
            await interaction.response.send_message(message, ephemeral=True)
            return

        await SetupMessageService().send_welcome_message(interaction.client, interaction.guild, channel)
        response = interaction.client.localization.translate(  # type: ignore[attr-defined]
            "rysio.commands_posted",
            language=language,
            channel=channel.mention,
        )
        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(name="owner", description="Postet ein Owner-Control-Panel in einen ausgewaehlten Channel.")
    @app_commands.describe(channel="Channel fuer das Owner-Control-Panel")
    async def owner(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        if not has_owner_access(interaction.user.id):
            await interaction.response.send_message("Dieser Bereich ist nur fuer den Bot-Owner.", ephemeral=True)
            return

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            await interaction.response.send_message("Bot-Mitglied konnte nicht gefunden werden.", ephemeral=True)
            return

        channel_permissions = channel.permissions_for(bot_member)
        if not (channel_permissions.view_channel and channel_permissions.send_messages and channel_permissions.embed_links):
            await interaction.response.send_message(
                "Rysio braucht in diesem Channel `Kanal ansehen`, `Nachrichten senden` und `Links einbetten`.",
                ephemeral=True,
            )
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        embed = await build_owner_embed(interaction.client, interaction.guild, interaction.user.id, language)  # type: ignore[arg-type]
        await channel.send(embed=embed, view=RysioOwnerView())
        await interaction.response.send_message(
            interaction.client.localization.translate(  # type: ignore[attr-defined]
                "owner.panel_posted",
                language=language,
                channel=channel.mention,
            ),
            ephemeral=True,
        )


def build_help_embed(bot: commands.Bot, language: str) -> discord.Embed:
    embed = discord.Embed(
        title=bot.localization.translate("rysio.help_title", language=language),  # type: ignore[attr-defined]
        description=bot.localization.translate("rysio.help_description", language=language),  # type: ignore[attr-defined]
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Rysio",
        value=(
            "`/rysio help`\n"
            "`/rysio setup`\n"
            "`/rysio commands`\n"
            "`/rysio status`\n"
            "`/rysio owner`\n"
            "`/help`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Setup",
        value="`/setup status`\n`/setup language`\n`/setup check`",
        inline=False,
    )
    embed.add_field(
        name="Tickets",
        value="`/tickets status`\n`/tickets panel`\n`/tickets note`\n`/tickets info`\n`/tickets panels-reset`",
        inline=False,
    )
    embed.add_field(
        name="Verification",
        value="`/verification status`\n`/verification setup`",
        inline=False,
    )
    embed.add_field(
        name="Reaction Roles",
        value="`/reactionroles status`\n`/reactionroles create`\n`/reactionroles manage`\n`/reactionroles delete`",
        inline=False,
    )
    embed.add_field(
        name="Autoroles",
        value="`/autorole status`\n`/autorole setup`\n`/autorole disable`",
        inline=False,
    )
    embed.add_field(
        name="Join To Create",
        value="`/jtc status`\n`/jtc setup`\n`/jtc disable`",
        inline=False,
    )
    embed.add_field(
        name="Logs",
        value="`/logs status`\n`/logs setup`\n`/logs disable`",
        inline=False,
    )
    embed.add_field(
        name="Notifications",
        value="`/notifications add`\n`/notifications remove`\n`/notifications list`\n`/notifications check`",
        inline=False,
    )
    embed.add_field(
        name="Moderation",
        value="`/mod setrole`\n`/mod roles`\n`/mod warn`\n`/mod timeout`\n`/mod kick`\n`/mod ban`\n`/mod history`",
        inline=False,
    )
    embed.add_field(
        name="Anti-Spam",
        value="`/antispam status`\n`/antispam setup`\n`/antispam disable`",
        inline=False,
    )
    embed.set_footer(
        text=bot.localization.translate("rysio.help_footer", language=language)  # type: ignore[attr-defined]
    )
    return embed


async def build_status_embed(bot: commands.Bot, guild: discord.Guild, language: str) -> discord.Embed:
    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    async with bot.database.session() as session:  # type: ignore[attr-defined]
        ticket_repo = TicketRepository(session)
        verification_repo = VerificationRepository(session)
        panels = await ticket_repo.get_panels_for_guild(guild.id)
        verification = await verification_repo.get_settings(guild.id)

    info_channel = guild.get_channel(settings.info_channel_id) if settings and settings.info_channel_id else None
    autorole_role = guild.get_role(settings.autorole_role_id) if settings and settings.autorole_role_id else None
    verification_role = guild.get_role(verification.verified_role_id) if verification and verification.verified_role_id else None
    bot_member = guild.me or guild.get_member(bot.user.id)  # type: ignore[attr-defined]
    missing_permissions = get_missing_core_permissions(guild, bot_member)

    embed = discord.Embed(
        title=bot.localization.translate("rysio.status_title", language=language),  # type: ignore[attr-defined]
        description=bot.localization.translate("rysio.status_description", language=language),  # type: ignore[attr-defined]
        color=discord.Color.green(),
    )
    embed.add_field(
        name=bot.localization.translate("rysio.status_overview_title", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate(
            "rysio.status_overview_value",
            language=language,
            language_code=await bot.guild_config.get_language(bot.database, guild.id),  # type: ignore[attr-defined]
            info_channel=info_channel.mention if info_channel else "-",
        ),
        inline=False,
    )
    embed.add_field(
        name=bot.localization.translate("rysio.status_checklist_title", language=language),  # type: ignore[attr-defined]
        value=_build_checklist_text(
            bot,
            language,
            info_channel is not None,
            len(panels) > 0,
            verification is not None and verification_role is not None,
            settings is not None and settings.autorole_enabled and autorole_role is not None,
            settings is not None and settings.spam_protection_enabled,
        ),
        inline=False,
    )
    embed.add_field(
        name=bot.localization.translate("rysio.status_details_title", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate(
            "rysio.status_details_value",
            language=language,
            tickets=len(panels),
            verification_role=verification_role.mention if verification_role else "-",
            autorole=autorole_role.mention if autorole_role else "-",
            autorole_mode=settings.autorole_mode if settings and settings.autorole_enabled else "-",
            antispam=(
                f"{settings.spam_threshold}/{settings.spam_interval_seconds}s ({settings.spam_action})"
                if settings and settings.spam_protection_enabled
                else "-"
            ),
        ),
        inline=False,
    )
    embed.add_field(
        name=bot.localization.translate("rysio.status_permissions_title", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate(
            "rysio.status_permissions_value",
            language=language,
            permissions=", ".join(missing_permissions) if missing_permissions else "none",
        ),
        inline=False,
    )
    embed.set_footer(text=bot.localization.translate("rysio.status_footer", language=language))  # type: ignore[attr-defined]
    return embed


def _build_checklist_text(
    bot: commands.Bot,
    language: str,
    has_info_channel: bool,
    has_ticket_panel: bool,
    has_verification: bool,
    has_autorole: bool,
    has_antispam: bool,
) -> str:
    def state(value: bool) -> str:
        return "Done" if value else "Open"

    return "\n".join(
        [
            bot.localization.translate("rysio.check_info_channel", language=language, state=state(has_info_channel)),  # type: ignore[attr-defined]
            bot.localization.translate("rysio.check_tickets", language=language, state=state(has_ticket_panel)),  # type: ignore[attr-defined]
            bot.localization.translate("rysio.check_verification", language=language, state=state(has_verification)),  # type: ignore[attr-defined]
            bot.localization.translate("rysio.check_autorole", language=language, state=state(has_autorole)),  # type: ignore[attr-defined]
            bot.localization.translate("rysio.check_antispam", language=language, state=state(has_antispam)),  # type: ignore[attr-defined]
        ]
    )


class RysioInfoView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Commands", style=discord.ButtonStyle.blurple, custom_id="rysio:commands")
    async def commands_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        await interaction.response.send_message(
            embed=build_help_embed(interaction.client, language),  # type: ignore[arg-type]
            ephemeral=True,
        )

    @discord.ui.button(label="Setup Status", style=discord.ButtonStyle.green, custom_id="rysio:status")
    async def status_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        embed = await build_status_embed(interaction.client, interaction.guild, language)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def build_owner_embed(bot: commands.Bot, guild: discord.Guild, user_id: int, language: str) -> discord.Embed:
    async with bot.database.session() as session:  # type: ignore[attr-defined]
        premium_repo = PremiumRepository(session)
        plan = await premium_repo.get_active_plan(guild.id)

    bypass_enabled = has_owner_bypass(bot, user_id)  # type: ignore[arg-type]
    embed = discord.Embed(
        title=bot.localization.translate("owner.panel_title", language=language),  # type: ignore[attr-defined]
        description=bot.localization.translate("owner.panel_description", language=language),  # type: ignore[attr-defined]
        color=discord.Color.orange(),
    )
    embed.add_field(
        name=bot.localization.translate("owner.panel_status_title", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate(
            "owner.status",
            language=language,
            bypass="on" if bypass_enabled else "off",
            premium=plan,
        ),
        inline=False,
    )
    embed.add_field(
        name=bot.localization.translate("owner.panel_actions_title", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate("owner.panel_actions_value", language=language),  # type: ignore[attr-defined]
        inline=False,
    )
    return embed


async def _set_premium_plan(bot: commands.Bot, guild_id: int, plan: str) -> None:
    async with bot.database.session() as session:  # type: ignore[attr-defined]
        repo = PremiumRepository(session)
        if plan == "free":
            await repo.set_plan(guild_id, "free", active=False)
        else:
            await repo.set_plan(guild_id, plan, active=True)


class RysioOwnerView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def _ensure_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return False

        if not has_owner_access(interaction.user.id):
            await interaction.response.send_message("Dieser Bereich ist nur fuer den Bot-Owner.", ephemeral=True)
            return False

        return True

    async def _refresh_panel(self, interaction: discord.Interaction, confirmation_key: str | None = None, **kwargs: str) -> None:
        language = await interaction.client.guild_config.get_language(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        embed = await build_owner_embed(interaction.client, interaction.guild, interaction.user.id, language)  # type: ignore[arg-type]
        await interaction.response.edit_message(embed=embed, view=self)
        if confirmation_key is not None:
            await interaction.followup.send(
                interaction.client.localization.translate(confirmation_key, language=language, **kwargs),  # type: ignore[attr-defined]
                ephemeral=True,
            )

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple, custom_id="rysio-owner:refresh", row=0)
    async def refresh_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_owner(interaction):
            return
        await self._refresh_panel(interaction)

    @discord.ui.button(label="Toggle Bypass", style=discord.ButtonStyle.gray, custom_id="rysio-owner:bypass", row=0)
    async def bypass_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_owner(interaction):
            return

        enabled = not has_owner_bypass(interaction.client, interaction.user.id)
        interaction.client.owner_control.set_bypass_enabled(interaction.user.id, enabled)  # type: ignore[attr-defined]
        await self._refresh_panel(
            interaction,
            "owner.bypass_updated",
            state="on" if enabled else "off",
        )

    @discord.ui.button(label="Premium Free", style=discord.ButtonStyle.secondary, custom_id="rysio-owner:premium-free", row=1)
    async def premium_free_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_owner(interaction):
            return
        await _set_premium_plan(interaction.client, interaction.guild.id, "free")  # type: ignore[arg-type]
        await self._refresh_panel(interaction, "owner.premium_updated", plan="free")

    @discord.ui.button(label="Premium Plus", style=discord.ButtonStyle.success, custom_id="rysio-owner:premium-plus", row=1)
    async def premium_plus_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_owner(interaction):
            return
        await _set_premium_plan(interaction.client, interaction.guild.id, "plus")  # type: ignore[arg-type]
        await self._refresh_panel(interaction, "owner.premium_updated", plan="plus")

    @discord.ui.button(label="Premium Pro", style=discord.ButtonStyle.danger, custom_id="rysio-owner:premium-pro", row=1)
    async def premium_pro_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_owner(interaction):
            return
        await _set_premium_plan(interaction.client, interaction.guild.id, "pro")  # type: ignore[arg-type]
        await self._refresh_panel(interaction, "owner.premium_updated", plan="pro")


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(RysioGroup())
        self.bot.add_view(RysioInfoView())
        self.bot.add_view(RysioOwnerView())

    @app_commands.command(name="help", description="Zeigt eine Uebersicht aller wichtigen Rysio-Commands.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return

        language = await self.bot.guild_config.get_language(self.bot.database, interaction.guild.id)  # type: ignore[attr-defined]
        embed = build_help_embed(self.bot, language)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
