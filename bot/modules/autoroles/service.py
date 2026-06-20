from __future__ import annotations

import discord


class AutoroleService:
    async def assign_join_role(self, bot: discord.Client, member: discord.Member) -> bool:
        settings = await bot.guild_config.get_settings(bot.database, member.guild.id)  # type: ignore[attr-defined]
        if settings is None or not settings.autorole_enabled or settings.autorole_mode != "join":
            return False

        role = member.guild.get_role(settings.autorole_role_id) if settings.autorole_role_id else None
        if role is None or role in member.roles:
            return False

        await member.add_roles(role, reason="Autorole on join")
        return True

    async def assign_verified_role(self, bot: discord.Client, member: discord.Member) -> bool:
        settings = await bot.guild_config.get_settings(bot.database, member.guild.id)  # type: ignore[attr-defined]
        if settings is None or not settings.autorole_enabled or settings.autorole_mode != "verified":
            return False

        role = member.guild.get_role(settings.autorole_role_id) if settings.autorole_role_id else None
        if role is None or role in member.roles:
            return False

        await member.add_roles(role, reason="Autorole after verification")
        return True
