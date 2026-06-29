from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.modules.welcome.service import WELCOME_STYLE_NEON, WELCOME_STYLE_RYSIO, send_welcome_message
from bot.utils.access import can_manage_guild


def _welcome_status_text(settings, channel: discord.TextChannel | None) -> str:
    if settings is None or not settings.welcome_enabled or settings.welcome_channel_id is None:
        return "Welcome-Nachrichten sind aktuell nicht eingerichtet."
    channel_text = channel.mention if channel is not None else f"`{settings.welcome_channel_id}`"
    return (
        "Welcome-Nachrichten sind aktiv.\n"
        f"Channel: {channel_text}\n"
        f"Style: `{settings.welcome_style or WELCOME_STYLE_NEON}`"
    )


class WelcomeGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="welcome", description="Begruessungen fuer neue Mitglieder verwalten")

    @app_commands.command(name="status", description="Zeigt den aktuellen Welcome-Status an.")
    @app_commands.default_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        settings = await interaction.client.guild_config.get_settings(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        channel = interaction.guild.get_channel(settings.welcome_channel_id) if settings and settings.welcome_channel_id else None
        text = _welcome_status_text(settings, channel if isinstance(channel, discord.TextChannel) else None)
        if not interaction.client.settings.enable_members_intent:  # type: ignore[attr-defined]
            text += "\n\nHinweis: `ENABLE_MEMBERS_INTENT` ist aktuell aus. Ohne Members-Intent werden Join-Welcomes nicht automatisch gesendet."
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="setup", description="Legt den Welcome-Channel fuer neue Mitglieder fest.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel fuer die Begruessung", style="Waehle die Welcome-Grafik aus")
    @app_commands.choices(
        style=[
            app_commands.Choice(name="Neon Card", value=WELCOME_STYLE_NEON),
            app_commands.Choice(name="Rysio Card", value=WELCOME_STYLE_RYSIO),
        ]
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        style: app_commands.Choice[str] | None = None,
    ) -> None:
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

        permissions = channel.permissions_for(bot_member)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links and permissions.attach_files):
            await interaction.response.send_message(
                "Rysio braucht in diesem Channel `Kanal ansehen`, `Nachrichten senden`, `Links einbetten` und `Dateien anhaengen`.",
                ephemeral=True,
            )
            return

        selected_style = style.value if style else WELCOME_STYLE_NEON
        await interaction.client.guild_config.ensure_guild(interaction.client.database, interaction.guild.id)  # type: ignore[attr-defined]
        await interaction.client.guild_config.set_welcome(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            True,
            channel.id,
            selected_style,
        )
        await interaction.response.send_message(
            f"Welcome-Nachrichten wurden fuer {channel.mention} gespeichert. Style: `{selected_style}`",
            ephemeral=True,
        )

    @app_commands.command(name="preview", description="Sendet eine Test-Welcome-Nachricht mit dir selbst.")
    @app_commands.default_permissions(manage_guild=True)
    async def preview(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Member konnte nicht geladen werden.", ephemeral=True)
            return

        settings = await interaction.client.guild_config.get_settings(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
        )
        if settings is None or not settings.welcome_channel_id:
            await interaction.response.send_message("Es ist noch kein Welcome-Channel gespeichert.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(settings.welcome_channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Der gespeicherte Welcome-Channel wurde nicht gefunden.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await send_welcome_message(interaction.client, interaction.user, channel=channel, style=settings.welcome_style or WELCOME_STYLE_NEON)
        await interaction.followup.send(f"Preview wurde in {channel.mention} gesendet.", ephemeral=True)

    @app_commands.command(name="disable", description="Deaktiviert Welcome-Nachrichten fuer diesen Server.")
    @app_commands.default_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Das geht nur in einem Server.", ephemeral=True)
            return
        if not can_manage_guild(interaction.client, interaction.user):
            await interaction.response.send_message("Dafuer brauchst du Server-verwalten-Rechte.", ephemeral=True)
            return

        await interaction.client.guild_config.set_welcome(  # type: ignore[attr-defined]
            interaction.client.database,
            interaction.guild.id,
            False,
            None,
            WELCOME_STYLE_NEON,
        )
        await interaction.response.send_message("Welcome-Nachrichten wurden deaktiviert.", ephemeral=True)


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(WelcomeGroup())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        settings = await self.bot.guild_config.get_settings(self.bot.database, member.guild.id)  # type: ignore[attr-defined]
        if settings is None or not settings.welcome_enabled or not settings.welcome_channel_id:
            return

        channel = member.guild.get_channel(settings.welcome_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            await send_welcome_message(self.bot, member, channel=channel, style=settings.welcome_style or WELCOME_STYLE_NEON)
        except discord.HTTPException:
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
