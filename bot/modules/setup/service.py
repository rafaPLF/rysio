from __future__ import annotations

import discord


class SetupMessageService:
    CREATOR_USER_ID = 727980706575286323

    async def send_welcome_message(self, bot: discord.Client, guild: discord.Guild, channel: discord.abc.Messageable) -> None:
        from bot.modules.rysio.cog import RysioInfoView

        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]

        embed = discord.Embed(
            title=bot.localization.translate("rysio.welcome_title", language=language),  # type: ignore[attr-defined]
            description=bot.localization.translate("rysio.welcome_description", language=language),  # type: ignore[attr-defined]
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name=bot.localization.translate("rysio.help_field_title", language=language),  # type: ignore[attr-defined]
            value=bot.localization.translate("rysio.help_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        embed.add_field(
            name=bot.localization.translate("rysio.features_field_title", language=language),  # type: ignore[attr-defined]
            value=bot.localization.translate("rysio.features_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        embed.add_field(
            name=bot.localization.translate("rysio.contact_field_title", language=language),  # type: ignore[attr-defined]
            value=bot.localization.translate(
                "rysio.contact_field_value",
                language=language,
                creator=f"<@{self.CREATOR_USER_ID}>",
            ),  # type: ignore[attr-defined]
            inline=False,
        )
        embed.add_field(
            name=bot.localization.translate("rysio.next_steps_field_title", language=language),  # type: ignore[attr-defined]
            value=bot.localization.translate("rysio.next_steps_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        await channel.send(embed=embed, view=RysioInfoView())

    async def send_join_prompt(self, bot: discord.Client, guild: discord.Guild, channel: discord.abc.Messageable) -> None:
        from bot.modules.rysio.cog import RysioInfoView

        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
        embed = discord.Embed(
            title=bot.localization.translate("rysio.join_title", language=language),  # type: ignore[attr-defined]
            description=bot.localization.translate("rysio.join_description", language=language),  # type: ignore[attr-defined]
            color=discord.Color.green(),
        )
        embed.add_field(
            name=bot.localization.translate("rysio.join_field_title", language=language),  # type: ignore[attr-defined]
            value=bot.localization.translate("rysio.join_field_value", language=language),  # type: ignore[attr-defined]
            inline=False,
        )
        await channel.send(embed=embed, view=RysioInfoView())
