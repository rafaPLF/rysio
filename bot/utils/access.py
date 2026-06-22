from __future__ import annotations

import discord


OWNER_USER_IDS = {727980706575286323}


def has_owner_access(user_id: int) -> bool:
    return user_id in OWNER_USER_IDS


def has_owner_bypass(bot: discord.Client, user_id: int) -> bool:
    if not has_owner_access(user_id):
        return False

    owner_control = getattr(bot, "owner_control", None)
    if owner_control is None:
        return True

    return owner_control.is_bypass_enabled(user_id)


def is_bot_owner(bot: discord.Client, user: discord.abc.User) -> bool:
    return has_owner_bypass(bot, user.id)


def can_manage_guild(bot: discord.Client, user: discord.abc.User) -> bool:
    if has_owner_bypass(bot, user.id):
        return True
    return isinstance(user, discord.Member) and user.guild_permissions.manage_guild


async def can_use_moderation(bot: discord.Client, user: discord.abc.User, guild_id: int) -> bool:
    if has_owner_bypass(bot, user.id):
        return True
    if not isinstance(user, discord.Member):
        return False
    if user.guild_permissions.administrator or user.guild_permissions.manage_guild:
        return True

    role_ids = await bot.guild_config.get_mod_role_ids(bot.database, guild_id)  # type: ignore[attr-defined]
    if not role_ids:
        return False
    return any(role.id in role_ids for role in user.roles)
