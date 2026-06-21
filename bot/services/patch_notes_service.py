from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import discord


@dataclass(slots=True)
class ReleaseNotes:
    version: str
    title: str
    summary: str
    highlights: list[str]


class PatchNotesService:
    def __init__(self) -> None:
        self._release_path = Path(__file__).resolve().parent.parent / "release_notes.json"

    def get_release_notes(self) -> ReleaseNotes | None:
        if not self._release_path.exists():
            return None

        try:
            raw = json.loads(self._release_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        version = str(raw.get("version", "")).strip()
        title = str(raw.get("title", "")).strip()
        summary = str(raw.get("summary", "")).strip()
        highlights = [str(item).strip() for item in raw.get("highlights", []) if str(item).strip()]
        if not version or not title or not summary:
            return None

        return ReleaseNotes(
            version=version,
            title=title,
            summary=summary,
            highlights=highlights,
        )

    async def publish_for_all_guilds(self, bot: discord.Client) -> None:
        release = self.get_release_notes()
        if release is None:
            return

        for guild in bot.guilds:
            await self.publish_for_guild(bot, guild, release)

    async def publish_for_guild(self, bot: discord.Client, guild: discord.Guild, release: ReleaseNotes) -> None:
        settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
        if settings is None:
            return

        if settings.info_channel_id is None:
            return

        if settings.last_patch_notes_version == release.version:
            return

        channel = guild.get_channel(settings.info_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        bot_member = guild.me or guild.get_member(bot.user.id)  # type: ignore[attr-defined]
        if bot_member is None:
            return

        permissions = channel.permissions_for(bot_member)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
            return

        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
        embed = discord.Embed(
            title=bot.localization.translate("patch_notes.title", language=language, version=release.version),  # type: ignore[attr-defined]
            description=release.summary,
            color=discord.Color.teal(),
        )
        embed.add_field(
            name=release.title,
            value="\n".join(f"- {item}" for item in release.highlights) if release.highlights else release.summary,
            inline=False,
        )
        embed.set_footer(
            text=bot.localization.translate("patch_notes.footer", language=language)  # type: ignore[attr-defined]
        )

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            return

        await bot.guild_config.set_last_patch_notes_version(  # type: ignore[attr-defined]
            bot.database,
            guild.id,
            release.version,
        )
