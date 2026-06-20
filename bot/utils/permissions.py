from __future__ import annotations

import discord


def get_missing_core_permissions(guild: discord.Guild, member: discord.Member | None) -> list[str]:
    if member is None:
        return [
            "view_channel",
            "send_messages",
            "embed_links",
            "manage_channels",
            "manage_roles",
            "manage_messages",
        ]

    permissions = guild.text_channels[0].permissions_for(member) if guild.text_channels else member.guild_permissions
    required = {
        "view_channel": permissions.view_channel,
        "send_messages": permissions.send_messages,
        "embed_links": permissions.embed_links,
        "manage_channels": member.guild_permissions.manage_channels,
        "manage_roles": member.guild_permissions.manage_roles,
        "manage_messages": member.guild_permissions.manage_messages,
    }
    return [name for name, allowed in required.items() if not allowed]
