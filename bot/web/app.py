from __future__ import annotations

import json
from typing import Any

import discord
from aiohttp import web

from bot.database.repositories.audit_log_repo import AuditLogRepository
from bot.database.repositories.guild_repo import GuildRepository
from bot.database.repositories.notification_repo import NotificationSubscriptionRepository
from bot.database.repositories.premium_repo import PremiumRepository
from bot.database.repositories.ticket_note_repo import TicketNoteRepository
from bot.database.repositories.ticket_repo import TicketRepository
from bot.database.repositories.verification_repo import VerificationRepository
from bot.database.session import DatabaseSessionManager
from bot.modules.notifications.service import NotificationService
from bot.modules.tickets.views import TicketCreateView
from bot.modules.verification.views import VerificationView
from bot.modules.welcome.service import send_welcome_message
from bot.utils.access import has_owner_access
from bot.web.oauth import (
    build_callback_redirect,
    build_login_url,
    create_oauth_settings,
    create_session,
    create_state,
    exchange_code_for_session_payload,
    get_manageable_guild_ids,
    get_session,
    pop_state,
)
from bot.web.viewer_page import render_logs_viewer_page


def _parse_positive_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def _decode_details(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return data if isinstance(data, dict) else {"value": data}


def _normalize_origin(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().rstrip("/").lower()


def _session_user_id(request: web.Request) -> int | None:
    session = request.get("panel_session")
    if not session:
        return None
    try:
        return int(session["user"]["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _serialize_text_channel(channel: discord.TextChannel) -> dict[str, Any]:
    return {
        "id": str(channel.id),
        "name": channel.name,
        "position": channel.position,
        "category_id": str(channel.category_id) if channel.category_id else None,
    }


def _serialize_voice_channel(channel: discord.VoiceChannel) -> dict[str, Any]:
    return {
        "id": str(channel.id),
        "name": channel.name,
        "position": channel.position,
        "category_id": str(channel.category_id) if channel.category_id else None,
    }


def _serialize_category(channel: discord.CategoryChannel) -> dict[str, Any]:
    return {
        "id": str(channel.id),
        "name": channel.name,
        "position": channel.position,
    }


def _serialize_role(role: discord.Role) -> dict[str, Any]:
    return {
        "id": str(role.id),
        "name": role.name,
        "position": role.position,
        "managed": role.managed,
    }


def _display_name_for_member(member: discord.Member | None, fallback_id: int | None) -> str:
    if member is not None:
        return member.display_name
    if fallback_id:
        return f"User {fallback_id}"
    return "Unbekannt"


def _serialize_ticket_panel(panel, guild: discord.Guild) -> dict[str, Any]:
    channel = guild.get_channel(panel.channel_id)
    category = guild.get_channel(panel.category_id) if panel.category_id else None
    support_role = guild.get_role(panel.support_role_id) if panel.support_role_id else None
    return {
        "id": panel.id,
        "channel_id": str(panel.channel_id),
        "channel_name": channel.name if isinstance(channel, discord.TextChannel) else f"#{panel.channel_id}",
        "message_id": str(panel.message_id),
        "title": panel.title,
        "description_text": panel.description_text,
        "category_id": str(panel.category_id) if panel.category_id else None,
        "category_name": category.name if isinstance(category, discord.CategoryChannel) else None,
        "support_role_id": str(panel.support_role_id) if panel.support_role_id else None,
        "support_role_name": support_role.name if support_role else None,
        "welcome_message": panel.welcome_message or "",
    }


def _serialize_ticket(ticket, guild: discord.Guild, notes: list[Any]) -> dict[str, Any]:
    channel = guild.get_channel(ticket.channel_id)
    opener = guild.get_member(ticket.user_id)
    claimer = guild.get_member(ticket.claimed_by_user_id) if ticket.claimed_by_user_id else None
    return {
        "id": ticket.id,
        "channel_id": str(ticket.channel_id),
        "channel_name": channel.name if isinstance(channel, discord.TextChannel) else f"ticket-{ticket.channel_id}",
        "user_id": str(ticket.user_id),
        "opener_name": _display_name_for_member(opener, ticket.user_id),
        "status": ticket.status,
        "panel_id": ticket.panel_id,
        "claimed_by_user_id": str(ticket.claimed_by_user_id) if ticket.claimed_by_user_id else None,
        "claimed_by_name": _display_name_for_member(claimer, ticket.claimed_by_user_id) if ticket.claimed_by_user_id else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "transcript_path": ticket.transcript_path,
        "notes": [
            {
                "id": note.id,
                "author_user_id": str(note.author_user_id),
                "author_username": note.author_username,
                "note_text": note.note_text,
                "created_at": note.created_at.isoformat() if note.created_at else None,
            }
            for note in notes
        ],
    }


def _serialize_notification_subscription(subscription, guild: discord.Guild) -> dict[str, Any]:
    channel = guild.get_channel(subscription.announce_channel_id)
    mention_role = guild.get_role(subscription.mention_role_id) if subscription.mention_role_id else None
    return {
        "id": subscription.id,
        "platform": subscription.platform,
        "target": subscription.target,
        "announce_channel_id": str(subscription.announce_channel_id),
        "announce_channel_name": channel.name if isinstance(channel, discord.TextChannel) else f"#{subscription.announce_channel_id}",
        "mention_role_id": str(subscription.mention_role_id) if subscription.mention_role_id else None,
        "mention_role_name": mention_role.name if mention_role else None,
        "enabled": bool(subscription.enabled),
        "last_seen_content_id": subscription.last_seen_content_id,
        "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
    }


def _serialize_verification_settings(settings, guild: discord.Guild, *, enabled: bool) -> dict[str, Any]:
    channel = guild.get_channel(settings.verification_channel_id) if settings and settings.verification_channel_id else None
    role = guild.get_role(settings.verified_role_id) if settings and settings.verified_role_id else None
    return {
        "enabled": enabled,
        "verification_channel_id": str(settings.verification_channel_id) if settings and settings.verification_channel_id else None,
        "verification_channel_name": channel.name if isinstance(channel, discord.TextChannel) else None,
        "verified_role_id": str(settings.verified_role_id) if settings and settings.verified_role_id else None,
        "verified_role_name": role.name if role else None,
        "panel_message_id": str(settings.panel_message_id) if settings and settings.panel_message_id else None,
        "captcha_type": settings.captcha_type if settings else "button",
        "panel_title": settings.panel_title if settings else None,
        "panel_description": settings.panel_description if settings else None,
        "reaction_emoji": settings.reaction_emoji if settings else None,
    }


def _serialize_welcome_settings(settings, guild: discord.Guild) -> dict[str, Any]:
    channel = guild.get_channel(settings.welcome_channel_id) if settings and settings.welcome_channel_id else None
    return {
        "enabled": bool(settings.welcome_enabled) if settings else False,
        "welcome_channel_id": str(settings.welcome_channel_id) if settings and settings.welcome_channel_id else None,
        "welcome_channel_name": channel.name if isinstance(channel, discord.TextChannel) else None,
        "welcome_style": settings.welcome_style if settings and settings.welcome_style else "rysio_card",
    }


def _serialize_join_to_create_settings(settings, guild: discord.Guild) -> dict[str, Any]:
    lobby = guild.get_channel(settings.join_to_create_channel_id) if settings and settings.join_to_create_channel_id else None
    category = guild.get_channel(settings.join_to_create_category_id) if settings and settings.join_to_create_category_id else None
    return {
        "enabled": bool(settings.join_to_create_enabled) if settings else False,
        "lobby_channel_id": str(settings.join_to_create_channel_id) if settings and settings.join_to_create_channel_id else None,
        "lobby_channel_name": lobby.name if isinstance(lobby, discord.VoiceChannel) else None,
        "category_id": str(settings.join_to_create_category_id) if settings and settings.join_to_create_category_id else None,
        "category_name": category.name if isinstance(category, discord.CategoryChannel) else None,
    }


def _serialize_admin_guild(guild: discord.Guild, *, owner_name: str, plan: str) -> dict[str, Any]:
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
        "member_count": guild.member_count,
        "owner_id": str(guild.owner_id),
        "owner_name": owner_name,
        "plan": plan,
        "premium_active": plan != "free",
    }


def _build_ticket_panel_embed(bot: discord.Client, *, language: str, title: str, description_text: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=description_text, color=discord.Color.blurple())
    embed.add_field(
        name=bot.localization.translate("tickets.panel_field_name", language=language),  # type: ignore[attr-defined]
        value=bot.localization.translate("tickets.panel_field_value", language=language),  # type: ignore[attr-defined]
        inline=False,
    )
    return embed


def _build_verification_reaction_hint(language: str, reaction_emoji: str) -> str:
    if language.lower().startswith("de"):
        return f"Reagiere mit {reaction_emoji}, um dich zu verifizieren."
    return f"React with {reaction_emoji} to verify yourself."


def _build_verification_panel_embed(
    bot: discord.Client,
    *,
    language: str,
    panel_title: str | None = None,
    panel_description: str | None = None,
    captcha_type: str = "button",
    reaction_emoji: str | None = None,
) -> discord.Embed:
    title = (panel_title or "").strip() or bot.localization.translate("verification.panel_title", language=language)  # type: ignore[attr-defined]
    description = (panel_description or "").strip() or bot.localization.translate("verification.panel_description", language=language)  # type: ignore[attr-defined]
    field_value = bot.localization.translate("verification.panel_field_value", language=language)  # type: ignore[attr-defined]
    if captcha_type == "reaction":
        field_value = _build_verification_reaction_hint(language, reaction_emoji or "✅")

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green(),
    )
    embed.add_field(
        name=bot.localization.translate("verification.panel_field_name", language=language),  # type: ignore[attr-defined]
        value=field_value,
        inline=False,
    )
    return embed


async def _delete_verification_panel_message(guild: discord.Guild, verification_settings) -> None:
    if verification_settings is None or verification_settings.panel_message_id is None:
        return

    channel = guild.get_channel(verification_settings.verification_channel_id) if verification_settings.verification_channel_id else None
    if not isinstance(channel, discord.TextChannel):
        return

    try:
        message = await channel.fetch_message(verification_settings.panel_message_id)
        await message.delete()
    except (discord.NotFound, discord.HTTPException):
        return


async def _send_verification_panel_message(
    channel: discord.TextChannel,
    *,
    embed: discord.Embed,
    captcha_type: str,
    reaction_emoji: str | None,
) -> discord.Message:
    if captcha_type == "reaction":
        message = await channel.send(embed=embed)
        await message.add_reaction(reaction_emoji or "✅")
        return message

    return await channel.send(embed=embed, view=VerificationView())


async def _get_authorized_guild(request: web.Request) -> discord.Guild | None:
    bot = request.app["bot"]
    if bot is None:
        return None

    guild_id = int(request.match_info["guild_id"])
    panel_session = request.get("panel_session")
    if panel_session is not None and guild_id not in get_manageable_guild_ids(panel_session):
        return None

    return bot.get_guild(guild_id)


async def _get_authorized_member(request: web.Request, guild: discord.Guild) -> discord.Member | None:
    user_id = _session_user_id(request)
    if user_id is None:
        return None

    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except discord.HTTPException:
        return None


async def _session_can_manage_guild(request: web.Request, guild: discord.Guild) -> bool:
    if request.get("panel_session") is None:
        return True
    user_id = _session_user_id(request)
    if user_id is None:
        return False
    if has_owner_access(user_id):
        return True
    member = await _get_authorized_member(request, guild)
    if member is None:
        return False
    return member.guild_permissions.administrator or member.guild_permissions.manage_guild


async def _session_can_use_ticket_staff(request: web.Request, guild: discord.Guild) -> bool:
    if request.get("panel_session") is None:
        return True
    user_id = _session_user_id(request)
    if user_id is None:
        return False
    if has_owner_access(user_id):
        return True

    member = await _get_authorized_member(request, guild)
    if member is None:
        return False
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True

    bot = request.app["bot"]
    role_ids = await bot.guild_config.get_mod_role_ids(bot.database, guild.id)  # type: ignore[attr-defined]
    return any(role.id in role_ids for role in member.roles)


def _forbidden(message: str, *, status: int = 403) -> web.Response:
    return web.json_response({"error": message}, status=status)


def _session_is_owner(request: web.Request) -> bool:
    user_id = _session_user_id(request)
    if user_id is None:
        return False
    return has_owner_access(user_id)


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return web.Response(status=204)

    if request.path in {
        "/",
        "/logs",
        "/api/health",
        "/api/oauth/discord/login",
        "/api/oauth/discord/callback",
        "/api/panel/session",
    }:
        return await handler(request)

    expected_token = request.app["api_token"]
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        provided_token = auth_header.removeprefix("Bearer ").strip()
        if provided_token == expected_token:
            request["panel_session"] = None
            return await handler(request)
        return web.json_response({"error": "invalid_token"}, status=403)

    panel_token = request.headers.get("X-Rysio-Panel-Token", "").strip()
    session = get_session(request.app, panel_token)
    if session is None:
        return web.json_response({"error": "missing_authentication"}, status=401)

    request["panel_session"] = session
    return await handler(request)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def logs_viewer(_: web.Request) -> web.Response:
    return web.Response(text=render_logs_viewer_page(), content_type="text/html")


async def get_guild_logs(request: web.Request) -> web.Response:
    panel_session = request.get("panel_session")
    database: DatabaseSessionManager = request.app["database"]
    guild_id = int(request.match_info["guild_id"])
    if panel_session is not None and guild_id not in get_manageable_guild_ids(panel_session):
        return web.json_response({"error": "guild_access_denied"}, status=403)
    limit = _parse_positive_int(request.query.get("limit"), 50, minimum=1, maximum=200)
    offset = _parse_positive_int(request.query.get("offset"), 0, minimum=0, maximum=10000)
    event_type = request.query.get("event_type")

    async with database.session() as session:
        repo = AuditLogRepository(session)
        total = await repo.count_for_guild(guild_id, event_type=event_type)
        entries = await repo.list_for_guild(
            guild_id,
            limit=limit,
            offset=offset,
            event_type=event_type,
        )

    payload = {
        "guild_id": guild_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "summary": entry.summary,
                "user_id": entry.user_id,
                "channel_id": entry.channel_id,
                "details": _decode_details(entry.details_json),
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
            for entry in entries
        ],
    }
    return web.json_response(payload)


async def get_guild_overview(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")

    database: DatabaseSessionManager = request.app["database"]
    bot = request.app["bot"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        notification_repo = NotificationSubscriptionRepository(session)
        ticket_repo = TicketRepository(session)
        note_repo = TicketNoteRepository(session)
        verification_repo = VerificationRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)
        verification = await verification_repo.get_settings(guild.id)
        notifications = await notification_repo.list_for_guild(guild.id)
        panels = await ticket_repo.get_panels_for_guild(guild.id)
        active_tickets = await ticket_repo.get_active_tickets_for_guild(guild.id)

        serialized_tickets = []
        for ticket in active_tickets:
            notes = await note_repo.list_for_ticket(ticket.id, limit=3)
            serialized_tickets.append(_serialize_ticket(ticket, guild, notes))

    payload = {
        "guild": {
            "id": str(guild.id),
            "name": guild.name,
            "icon": str(guild.icon.url) if guild.icon else None,
            "member_count": guild.member_count,
        },
        "settings": {
            "info_channel_id": str(settings.info_channel_id) if settings.info_channel_id else None,
            "logs_enabled": bool(settings.logs_enabled),
            "logs_channel_id": str(settings.logs_channel_id) if settings.logs_channel_id else None,
            "ticket_enabled": bool(settings.ticket_enabled),
        },
        "channels": sorted(
            [_serialize_text_channel(channel) for channel in guild.text_channels],
            key=lambda item: (item["position"], item["name"].lower()),
        ),
        "voice_channels": sorted(
            [_serialize_voice_channel(channel) for channel in guild.voice_channels],
            key=lambda item: (item["position"], item["name"].lower()),
        ),
        "categories": sorted(
            [_serialize_category(channel) for channel in guild.categories],
            key=lambda item: (item["position"], item["name"].lower()),
        ),
        "roles": sorted(
            [_serialize_role(role) for role in guild.roles if not role.is_default()],
            key=lambda item: (-item["position"], item["name"].lower()),
        ),
        "notifications": [_serialize_notification_subscription(subscription, guild) for subscription in notifications],
        "verification": _serialize_verification_settings(verification, guild, enabled=bool(settings.verification_enabled)),
        "welcome": _serialize_welcome_settings(settings, guild),
        "join_to_create": _serialize_join_to_create_settings(settings, guild),
        "members_intent_enabled": bool(getattr(bot.settings, "enable_members_intent", False)),
        "ticket_panels": [_serialize_ticket_panel(panel, guild) for panel in panels],
        "active_tickets": serialized_tickets,
    }
    return web.json_response(payload)


async def get_guild_welcome(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")

    database: DatabaseSessionManager = request.app["database"]
    bot = request.app["bot"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)

    return web.json_response(
        {
            "welcome": _serialize_welcome_settings(settings, guild),
            "members_intent_enabled": bool(getattr(bot.settings, "enable_members_intent", False)),
        }
    )


async def get_guild_join_to_create(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)

    return web.json_response(
        {
            "join_to_create": _serialize_join_to_create_settings(settings, guild),
        }
    )


async def save_welcome_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    channel_id_raw = str(payload.get("welcome_channel_id", "")).strip()
    style = str(payload.get("welcome_style", "rysio_card")).strip() or "rysio_card"
    if style not in {"neon_card", "rysio_card"}:
        return web.json_response({"error": "unsupported_welcome_style"}, status=400)
    if not channel_id_raw:
        return web.json_response({"error": "missing_welcome_channel_id"}, status=400)

    try:
        channel_id = int(channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_welcome_channel_id"}, status=400)

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "welcome_channel_not_found"}, status=404)

    bot = request.app["bot"]
    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return web.json_response({"error": "bot_member_missing"}, status=500)

    permissions = channel.permissions_for(bot_member)
    if not (permissions.view_channel and permissions.send_messages and permissions.embed_links and permissions.attach_files):
        return web.json_response({"error": "missing_welcome_channel_permissions"}, status=400)

    await bot.guild_config.set_welcome(bot.database, guild.id, True, channel.id, style)  # type: ignore[attr-defined]
    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    return web.json_response({"updated": True, "welcome": _serialize_welcome_settings(settings, guild)})


async def delete_welcome_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    await bot.guild_config.set_welcome(bot.database, guild.id, False, None, "rysio_card")  # type: ignore[attr-defined]
    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    return web.json_response({"deleted": True, "welcome": _serialize_welcome_settings(settings, guild)})


async def preview_welcome_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    user_id = _session_user_id(request)
    if user_id is None:
        return web.json_response({"error": "missing_panel_user"}, status=401)

    member = await _get_authorized_member(request, guild)
    if member is None:
        return web.json_response({"error": "member_not_found"}, status=404)

    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    if settings is None or not settings.welcome_channel_id:
        return web.json_response({"error": "welcome_not_configured"}, status=400)

    channel = guild.get_channel(settings.welcome_channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "welcome_channel_not_found"}, status=404)

    await send_welcome_message(bot, member, channel=channel, style=settings.welcome_style or "rysio_card")
    return web.json_response({"preview_sent": True, "channel_id": str(channel.id)})


async def save_join_to_create_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    lobby_channel_id_raw = str(payload.get("lobby_channel_id", "")).strip()
    category_id_raw = str(payload.get("category_id", "")).strip()
    if not lobby_channel_id_raw:
        return web.json_response({"error": "missing_lobby_channel_id"}, status=400)

    try:
        lobby_channel_id = int(lobby_channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_lobby_channel_id"}, status=400)

    lobby_channel = guild.get_channel(lobby_channel_id)
    if not isinstance(lobby_channel, discord.VoiceChannel):
        return web.json_response({"error": "lobby_channel_not_found"}, status=404)

    category_id: int | None = None
    if category_id_raw:
        try:
            category_id = int(category_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_category_id"}, status=400)
        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return web.json_response({"error": "category_not_found"}, status=404)

    bot = request.app["bot"]
    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return web.json_response({"error": "bot_member_missing"}, status=500)
    if not bot_member.guild_permissions.manage_channels:
        return web.json_response({"error": "missing_manage_channels_permission"}, status=400)
    if not bot_member.guild_permissions.move_members:
        return web.json_response({"error": "missing_move_members_permission"}, status=400)

    await bot.guild_config.set_join_to_create(bot.database, guild.id, True, lobby_channel.id, category_id)  # type: ignore[attr-defined]
    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    return web.json_response({"updated": True, "join_to_create": _serialize_join_to_create_settings(settings, guild)})


async def delete_join_to_create_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    await bot.guild_config.set_join_to_create(bot.database, guild.id, False, None, None)  # type: ignore[attr-defined]
    settings = await bot.guild_config.get_settings(bot.database, guild.id)  # type: ignore[attr-defined]
    return web.json_response({"deleted": True, "join_to_create": _serialize_join_to_create_settings(settings, guild)})


async def get_guild_verification(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        verification_repo = VerificationRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)
        verification = await verification_repo.get_settings(guild.id)

    return web.json_response(
        {
            "guild_id": str(guild.id),
            "verification": _serialize_verification_settings(verification, guild, enabled=bool(settings.verification_enabled)),
        }
    )


async def create_notification_subscription(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    service: NotificationService = request.app["notification_service"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    platform = str(payload.get("platform", "")).strip()
    target = str(payload.get("target", "")).strip()
    channel_id_raw = str(payload.get("announce_channel_id", "")).strip()
    mention_role_id_raw = str(payload.get("mention_role_id", "")).strip()
    if not platform or not target or not channel_id_raw:
        return web.json_response({"error": "missing_required_fields"}, status=400)

    try:
        channel_id = int(channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_channel_id"}, status=400)

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "channel_not_found"}, status=404)

    mention_role = None
    mention_role_id = None
    if mention_role_id_raw:
        try:
            mention_role_id = int(mention_role_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_mention_role_id"}, status=400)
        mention_role = guild.get_role(mention_role_id)
        if mention_role is None:
            return web.json_response({"error": "mention_role_not_found"}, status=404)

    try:
        subscription, initial_content_found = await service.add_subscription(
            bot,
            guild_id=guild.id,
            platform=platform,
            target=target,
            announce_channel_id=channel.id,
            mention_role_id=mention_role.id if mention_role else None,
        )
    except ValueError:
        return web.json_response({"error": "unsupported_platform"}, status=400)

    return web.json_response(
        {
            "created": True,
            "subscription": _serialize_notification_subscription(subscription, guild),
            "initial_content_found": initial_content_found,
        },
        status=201,
    )


async def update_notification_subscription(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    service: NotificationService = request.app["notification_service"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    subscription_id = int(request.match_info["subscription_id"])
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    platform = str(payload.get("platform", "")).strip()
    target = str(payload.get("target", "")).strip()
    channel_id_raw = str(payload.get("announce_channel_id", "")).strip()
    mention_role_id_raw = str(payload.get("mention_role_id", "")).strip()
    if not platform or not target or not channel_id_raw:
        return web.json_response({"error": "missing_required_fields"}, status=400)

    try:
        channel_id = int(channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_channel_id"}, status=400)
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "channel_not_found"}, status=404)

    mention_role = None
    mention_role_id = None
    if mention_role_id_raw:
        try:
            mention_role_id = int(mention_role_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_mention_role_id"}, status=400)
        mention_role = guild.get_role(mention_role_id)
        if mention_role is None:
            return web.json_response({"error": "mention_role_not_found"}, status=404)

    try:
        subscription, initial_content_found = await service.update_subscription(
            bot,
            guild_id=guild.id,
            subscription_id=subscription_id,
            platform=platform,
            target=target,
            announce_channel_id=channel.id,
            mention_role_id=mention_role.id if mention_role else None,
        )
    except ValueError:
        return web.json_response({"error": "unsupported_platform"}, status=400)

    if subscription is None:
        return web.json_response({"error": "subscription_not_found"}, status=404)

    return web.json_response(
        {
            "updated": True,
            "subscription": _serialize_notification_subscription(subscription, guild),
            "initial_content_found": initial_content_found,
        }
    )


async def delete_notification_subscription(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    service: NotificationService = request.app["notification_service"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    subscription_id = int(request.match_info["subscription_id"])
    deleted = await service.delete_subscription_by_id(bot, guild_id=guild.id, subscription_id=subscription_id)
    if deleted == 0:
        return web.json_response({"error": "subscription_not_found"}, status=404)
    return web.json_response({"deleted": True, "subscription_id": subscription_id})


async def check_guild_notifications(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    service: NotificationService = request.app["notification_service"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    processed = await service.poll_guild(bot, guild.id)
    return web.json_response({"checked": True, "processed": processed})


async def create_ticket_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    channel_id_raw = str(payload.get("channel_id", "")).strip()
    title = str(payload.get("title", "")).strip()
    description_text = str(payload.get("description_text", "")).strip()
    category_id_raw = str(payload.get("category_id", "")).strip()
    support_role_id_raw = str(payload.get("support_role_id", "")).strip()
    welcome_message = str(payload.get("welcome_message", "")).strip()

    if not channel_id_raw or not title or not description_text:
        return web.json_response({"error": "missing_required_fields"}, status=400)

    try:
        channel_id = int(channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_channel_id"}, status=400)

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "channel_not_found"}, status=404)

    category = None
    if category_id_raw:
        try:
            category_id = int(category_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_category_id"}, status=400)
        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return web.json_response({"error": "category_not_found"}, status=404)

    support_role = None
    if support_role_id_raw:
        try:
            support_role_id = int(support_role_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_support_role_id"}, status=400)
        support_role = guild.get_role(support_role_id)
        if support_role is None:
            return web.json_response({"error": "support_role_not_found"}, status=404)

    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return web.json_response({"error": "bot_member_missing"}, status=500)

    permissions = channel.permissions_for(bot_member)
    if not (permissions.send_messages and permissions.embed_links):
        return web.json_response({"error": "missing_channel_permissions"}, status=400)

    language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
    embed = _build_ticket_panel_embed(bot, language=language, title=title, description_text=description_text)
    message = await channel.send(embed=embed, view=TicketCreateView())

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        ticket_repo = TicketRepository(session)
        await guild_repo.ensure_guild(guild.id, bot.guild_config.get_default_language())  # type: ignore[attr-defined]
        settings = await guild_repo.ensure_settings(guild.id)
        settings.ticket_enabled = True
        panel = await ticket_repo.create_panel(
            guild_id=guild.id,
            channel_id=channel.id,
            message_id=message.id,
            title=title,
            description_text=description_text,
            category_id=category.id if category else None,
            support_role_id=support_role.id if support_role else None,
            welcome_message=welcome_message or None,
        )

    bot.add_view(TicketCreateView(), message_id=message.id)
    return web.json_response({"created": True, "panel": _serialize_ticket_panel(panel, guild)}, status=201)


async def save_verification_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    verification_channel_id_raw = str(payload.get("verification_channel_id", "")).strip()
    verified_role_id_raw = str(payload.get("verified_role_id", "")).strip()
    captcha_type = str(payload.get("captcha_type", "button")).strip().lower() or "button"
    panel_title = str(payload.get("panel_title", "")).strip() or None
    panel_description = str(payload.get("panel_description", "")).strip() or None
    reaction_emoji = str(payload.get("reaction_emoji", "")).strip() or None

    if not verification_channel_id_raw or not verified_role_id_raw:
        return web.json_response({"error": "missing_required_fields"}, status=400)
    if captcha_type not in {"button", "reaction"}:
        return web.json_response({"error": "unsupported_captcha_type"}, status=400)
    if captcha_type == "reaction" and not reaction_emoji:
        return web.json_response({"error": "missing_reaction_emoji"}, status=400)
    if captcha_type == "button":
        reaction_emoji = None

    try:
        verification_channel_id = int(verification_channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_verification_channel_id"}, status=400)

    try:
        verified_role_id = int(verified_role_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_verified_role_id"}, status=400)

    channel = guild.get_channel(verification_channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "verification_channel_not_found"}, status=404)

    verified_role = guild.get_role(verified_role_id)
    if verified_role is None:
        return web.json_response({"error": "verified_role_not_found"}, status=404)

    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return web.json_response({"error": "bot_member_missing"}, status=500)
    if not bot_member.guild_permissions.manage_roles:
        return web.json_response({"error": "missing_manage_roles_permission"}, status=400)
    if verified_role >= bot_member.top_role:
        return web.json_response({"error": "verified_role_above_bot"}, status=400)

    permissions = channel.permissions_for(bot_member)
    if not (permissions.send_messages and permissions.embed_links):
        return web.json_response({"error": "missing_channel_permissions"}, status=400)
    if captcha_type == "reaction" and not permissions.add_reactions:
        return web.json_response({"error": "missing_reaction_permissions"}, status=400)

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        verification_repo = VerificationRepository(session)
        await guild_repo.ensure_guild(guild.id, bot.guild_config.get_default_language())  # type: ignore[attr-defined]
        settings = await guild_repo.ensure_settings(guild.id)
        verification_settings = await verification_repo.get_settings(guild.id)
        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
        embed = _build_verification_panel_embed(
            bot,
            language=language,
            panel_title=panel_title,
            panel_description=panel_description,
            captcha_type=captcha_type,
            reaction_emoji=reaction_emoji,
        )

        final_message_id = verification_settings.panel_message_id if verification_settings else None
        recreate_message = (
            verification_settings is None
            or verification_settings.panel_message_id is None
            or verification_settings.verification_channel_id != channel.id
            or verification_settings.captcha_type != captcha_type
            or (captcha_type == "reaction" and verification_settings.reaction_emoji != reaction_emoji)
        )

        if recreate_message:
            message = await _send_verification_panel_message(
                channel,
                embed=embed,
                captcha_type=captcha_type,
                reaction_emoji=reaction_emoji,
            )
            if captcha_type == "button":
                bot.add_view(VerificationView(), message_id=message.id)
            final_message_id = message.id
            await _delete_verification_panel_message(guild, verification_settings)
        else:
            try:
                existing_message = await channel.fetch_message(verification_settings.panel_message_id)
                if captcha_type == "button":
                    await existing_message.edit(embed=embed, view=VerificationView())
                    bot.add_view(VerificationView(), message_id=existing_message.id)
                else:
                    await existing_message.edit(embed=embed, view=None)
                    await existing_message.add_reaction(reaction_emoji or "✅")
                final_message_id = existing_message.id
            except discord.NotFound:
                message = await _send_verification_panel_message(
                    channel,
                    embed=embed,
                    captcha_type=captcha_type,
                    reaction_emoji=reaction_emoji,
                )
                if captcha_type == "button":
                    bot.add_view(VerificationView(), message_id=message.id)
                final_message_id = message.id
            except discord.HTTPException:
                return web.json_response({"error": "verification_panel_update_failed"}, status=500)

        verification_settings = await verification_repo.upsert_settings(
            guild_id=guild.id,
            verification_channel_id=channel.id,
            verified_role_id=verified_role.id,
            panel_message_id=final_message_id,
            captcha_type=captcha_type,
            panel_title=panel_title,
            panel_description=panel_description,
            reaction_emoji=reaction_emoji,
        )
        settings.verification_enabled = True

    return web.json_response(
        {
            "saved": True,
            "verification": _serialize_verification_settings(verification_settings, guild, enabled=True),
        }
    )


async def delete_verification_settings(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        verification_repo = VerificationRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)
        verification_settings = await verification_repo.get_settings(guild.id)
        await _delete_verification_panel_message(guild, verification_settings)
        await verification_repo.delete_settings(guild.id)
        settings.verification_enabled = False

    return web.json_response(
        {
            "deleted": True,
            "guild_id": str(guild.id),
            "verification": _serialize_verification_settings(None, guild, enabled=False),
        }
    )


async def update_ticket_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    bot = request.app["bot"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    panel_id = int(request.match_info["panel_id"])
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    channel_id_raw = str(payload.get("channel_id", "")).strip()
    title = str(payload.get("title", "")).strip()
    description_text = str(payload.get("description_text", "")).strip()
    category_id_raw = str(payload.get("category_id", "")).strip()
    support_role_id_raw = str(payload.get("support_role_id", "")).strip()
    welcome_message = str(payload.get("welcome_message", "")).strip()

    if not channel_id_raw or not title or not description_text:
        return web.json_response({"error": "missing_required_fields"}, status=400)

    try:
        channel_id = int(channel_id_raw)
    except ValueError:
        return web.json_response({"error": "invalid_channel_id"}, status=400)

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "channel_not_found"}, status=404)

    category = None
    if category_id_raw:
        try:
            category_id = int(category_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_category_id"}, status=400)
        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return web.json_response({"error": "category_not_found"}, status=404)

    support_role = None
    if support_role_id_raw:
        try:
            support_role_id = int(support_role_id_raw)
        except ValueError:
            return web.json_response({"error": "invalid_support_role_id"}, status=400)
        support_role = guild.get_role(support_role_id)
        if support_role is None:
            return web.json_response({"error": "support_role_not_found"}, status=404)

    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return web.json_response({"error": "bot_member_missing"}, status=500)
    permissions = channel.permissions_for(bot_member)
    if not (permissions.send_messages and permissions.embed_links):
        return web.json_response({"error": "missing_channel_permissions"}, status=400)

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        panel = await ticket_repo.get_panel_by_id(panel_id)
        if panel is None or panel.guild_id != guild.id:
            return web.json_response({"error": "panel_not_found"}, status=404)

        language = await bot.guild_config.get_language(bot.database, guild.id)  # type: ignore[attr-defined]
        embed = _build_ticket_panel_embed(bot, language=language, title=title, description_text=description_text)

        final_message_id = panel.message_id
        if panel.channel_id != channel.id:
            new_message = await channel.send(embed=embed, view=TicketCreateView())
            bot.add_view(TicketCreateView(), message_id=new_message.id)
            final_message_id = new_message.id

            old_channel = guild.get_channel(panel.channel_id)
            if isinstance(old_channel, discord.TextChannel):
                try:
                    old_message = await old_channel.fetch_message(panel.message_id)
                    await old_message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass
        else:
            try:
                existing_message = await channel.fetch_message(panel.message_id)
                await existing_message.edit(embed=embed, view=TicketCreateView())
                bot.add_view(TicketCreateView(), message_id=existing_message.id)
            except discord.NotFound:
                recreated_message = await channel.send(embed=embed, view=TicketCreateView())
                bot.add_view(TicketCreateView(), message_id=recreated_message.id)
                final_message_id = recreated_message.id
            except discord.HTTPException:
                return web.json_response({"error": "panel_message_update_failed"}, status=500)

        panel = await ticket_repo.update_panel(
            panel,
            channel_id=channel.id,
            message_id=final_message_id,
            title=title,
            description_text=description_text,
            category_id=category.id if category else None,
            support_role_id=support_role.id if support_role else None,
            welcome_message=welcome_message or None,
        )

    return web.json_response({"updated": True, "panel": _serialize_ticket_panel(panel, guild)})


async def delete_ticket_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_manage_guild(request, guild):
        return _forbidden("guild_manage_required")

    panel_id = int(request.match_info["panel_id"])
    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        repo = TicketRepository(session)
        panel = await repo.get_panel_by_id(panel_id)
        if panel is None or panel.guild_id != guild.id:
            return web.json_response({"error": "panel_not_found"}, status=404)

        channel = guild.get_channel(panel.channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(panel.message_id)
                await message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass

        await repo.delete_panel_by_id(panel_id)

    return web.json_response({"deleted": True, "panel_id": panel_id})


async def add_ticket_note(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_use_ticket_staff(request, guild):
        return _forbidden("ticket_staff_required")

    ticket_id = int(request.match_info["ticket_id"])
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    note_text = str(payload.get("note_text", "")).strip()
    if not note_text:
        return web.json_response({"error": "missing_note_text"}, status=400)

    user_id = _session_user_id(request) or 0
    member = await _get_authorized_member(request, guild)
    author_name = member.display_name if member is not None else f"PanelUser {user_id}"

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        note_repo = TicketNoteRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        if ticket is None or ticket.guild_id != guild.id:
            return web.json_response({"error": "ticket_not_found"}, status=404)
        note = await note_repo.create_note(
            ticket_id=ticket.id,
            author_user_id=user_id,
            author_username=author_name,
            note_text=note_text,
        )

    return web.json_response(
        {
            "created": True,
            "note": {
                "id": note.id,
                "author_user_id": str(note.author_user_id),
                "author_username": note.author_username,
                "note_text": note.note_text,
                "created_at": note.created_at.isoformat() if note.created_at else None,
            },
        },
        status=201,
    )


async def claim_ticket_from_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_use_ticket_staff(request, guild):
        return _forbidden("ticket_staff_required")

    ticket_id = int(request.match_info["ticket_id"])
    user_id = _session_user_id(request)
    if user_id is None:
        return web.json_response({"error": "missing_panel_user"}, status=401)

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        if ticket is None or ticket.guild_id != guild.id:
            return web.json_response({"error": "ticket_not_found"}, status=404)
        if ticket.status == "closed":
            return web.json_response({"error": "ticket_closed"}, status=400)
        if ticket.claimed_by_user_id and ticket.claimed_by_user_id != user_id:
            return web.json_response({"error": "ticket_already_claimed"}, status=409)
        ticket = await ticket_repo.claim_ticket(ticket, user_id)

    channel = guild.get_channel(ticket.channel_id)
    member = await _get_authorized_member(request, guild)
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(f"Ticket uebernommen von {member.mention if member else f'<@{user_id}>'}. Status: `claimed`")
        except discord.HTTPException:
            pass

    return web.json_response({"updated": True, "status": ticket.status})


async def set_ticket_waiting_user_from_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_use_ticket_staff(request, guild):
        return _forbidden("ticket_staff_required")

    bot = request.app["bot"]
    ticket_id = int(request.match_info["ticket_id"])
    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        if ticket is None or ticket.guild_id != guild.id:
            return web.json_response({"error": "ticket_not_found"}, status=404)
        ticket = await ticket_repo.set_ticket_status(ticket, "waiting_user")

    channel = guild.get_channel(ticket.channel_id)
    if isinstance(channel, discord.TextChannel):
        await bot.tickets.notify_waiting_user(bot, ticket, channel)  # type: ignore[attr-defined]
        try:
            await channel.send("Ticket-Status auf `waiting_user` gesetzt.")
        except discord.HTTPException:
            pass

    return web.json_response({"updated": True, "status": ticket.status})


async def close_ticket_from_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return _forbidden("guild_access_denied")
    if not await _session_can_use_ticket_staff(request, guild):
        return _forbidden("ticket_staff_required")

    bot = request.app["bot"]
    ticket_id = int(request.match_info["ticket_id"])
    database: DatabaseSessionManager = request.app["database"]
    user_id = _session_user_id(request)

    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        if ticket is None or ticket.guild_id != guild.id:
            return web.json_response({"error": "ticket_not_found"}, status=404)

    channel = guild.get_channel(ticket.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return web.json_response({"error": "ticket_channel_not_found"}, status=404)

    transcript_path = await bot.tickets.render_transcript(channel)  # type: ignore[attr-defined]
    async with database.session() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        if ticket is None:
            return web.json_response({"error": "ticket_not_found"}, status=404)
        ticket = await ticket_repo.close_ticket(ticket, closed_by_user_id=user_id, transcript_path=transcript_path)

    try:
        await channel.send(f"Ticket wird geschlossen.\nTranscript: `{transcript_path}`")
    except discord.HTTPException:
        pass

    try:
        await channel.delete(reason=f"Ticket closed from panel by {user_id}")
    except discord.HTTPException:
        pass

    return web.json_response({"updated": True, "status": ticket.status, "transcript_path": transcript_path})


async def discord_login(request: web.Request) -> web.Response:
    oauth_settings = request.app["oauth_settings"]
    if not oauth_settings.enabled:
        return web.Response(text="Discord OAuth ist noch nicht konfiguriert.", status=503)

    state = create_state(request.app)
    raise web.HTTPFound(build_login_url(oauth_settings, state))


async def discord_callback(request: web.Request) -> web.Response:
    oauth_settings = request.app["oauth_settings"]
    if not oauth_settings.enabled:
        raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token="", error="oauth_not_configured"))

    error = request.query.get("error")
    if error:
        raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token="", error=error))

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    if not state or not pop_state(request.app, state):
        raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token="", error="invalid_state"))
    if not code:
        raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token="", error="missing_code"))

    try:
        payload = await exchange_code_for_session_payload(
            settings=oauth_settings,
            bot=request.app["bot"],
            code=code,
        )
    except RuntimeError as exc:
        raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token="", error=str(exc))) from exc

    session_token = create_session(request.app, payload)
    raise web.HTTPFound(build_callback_redirect(oauth_settings, session_token=session_token))


async def get_panel_session(request: web.Request) -> web.Response:
    session_token = request.headers.get("X-Rysio-Panel-Token", "").strip()
    session = get_session(request.app, session_token)
    if session is None:
        return web.json_response({"error": "invalid_or_expired_session"}, status=401)
    return web.json_response(
        {
            "user": session["user"],
            "guilds": session["guilds"],
            "expires_at": session["expires_at"],
            "is_owner": has_owner_access(int(session["user"]["id"])),
        }
    )


async def get_admin_guilds(request: web.Request) -> web.Response:
    if not _session_is_owner(request):
        return _forbidden("owner_required")

    bot = request.app["bot"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    database: DatabaseSessionManager = request.app["database"]
    guild_payload: list[dict[str, Any]] = []
    async with database.session() as session:
        premium_repo = PremiumRepository(session)
        for guild in sorted(bot.guilds, key=lambda entry: entry.name.lower()):
            owner_member = guild.get_member(guild.owner_id)
            owner_name = owner_member.display_name if owner_member is not None else f"User {guild.owner_id}"
            plan = await premium_repo.get_active_plan(guild.id)
            guild_payload.append(_serialize_admin_guild(guild, owner_name=owner_name, plan=plan))

    return web.json_response({"guilds": guild_payload})


async def update_admin_guild_premium(request: web.Request) -> web.Response:
    if not _session_is_owner(request):
        return _forbidden("owner_required")

    bot = request.app["bot"]
    if bot is None:
        return web.json_response({"error": "bot_unavailable"}, status=503)

    guild = bot.get_guild(int(request.match_info["guild_id"]))
    if guild is None:
        return web.json_response({"error": "guild_not_found"}, status=404)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid_json"}, status=400)

    plan = str(payload.get("plan", "")).strip().lower()
    if plan not in {"free", "premium"}:
        return web.json_response({"error": "invalid_plan"}, status=400)

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        premium_repo = PremiumRepository(session)
        await premium_repo.set_plan(guild.id, plan, active=(plan != "free"))
        current_plan = await premium_repo.get_active_plan(guild.id)

    owner_member = guild.get_member(guild.owner_id)
    owner_name = owner_member.display_name if owner_member is not None else f"User {guild.owner_id}"
    return web.json_response(
        {
            "updated": True,
            "guild": _serialize_admin_guild(guild, owner_name=owner_name, plan=current_plan),
        }
    )


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    allowed_origin = _normalize_origin(request.app["allowed_origin"])
    origin = _normalize_origin(request.headers.get("Origin"))
    if allowed_origin and origin == allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", allowed_origin).rstrip("/")
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Rysio-Panel-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response


def create_web_app(database: DatabaseSessionManager, api_token: str, allowed_origin: str = "", *, bot=None) -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app["database"] = database
    app["bot"] = bot
    app["api_token"] = api_token
    app["allowed_origin"] = allowed_origin
    app["oauth_states"] = {}
    app["panel_sessions"] = {}
    app["notification_service"] = NotificationService()
    app["oauth_settings"] = create_oauth_settings(
        client_id=getattr(bot.settings, "discord_client_id", "") if bot is not None else "",
        client_secret=getattr(bot.settings, "discord_client_secret", "") if bot is not None else "",
        redirect_uri=getattr(bot.settings, "discord_redirect_uri", "") if bot is not None else "",
        panel_public_url=getattr(bot.settings, "panel_public_url", "") if bot is not None else "",
    )
    app.router.add_get("/", logs_viewer)
    app.router.add_get("/logs", logs_viewer)
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/oauth/discord/login", discord_login)
    app.router.add_get("/api/oauth/discord/callback", discord_callback)
    app.router.add_get("/api/panel/session", get_panel_session)
    app.router.add_get("/api/admin/guilds", get_admin_guilds)
    app.router.add_put("/api/admin/guilds/{guild_id:\\d+}/premium", update_admin_guild_premium)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/logs", get_guild_logs)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/overview", get_guild_overview)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/welcome", get_guild_welcome)
    app.router.add_put("/api/guilds/{guild_id:\\d+}/welcome", save_welcome_settings)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/welcome", delete_welcome_settings)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/welcome/preview", preview_welcome_settings)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/join-to-create", get_guild_join_to_create)
    app.router.add_put("/api/guilds/{guild_id:\\d+}/join-to-create", save_join_to_create_settings)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/join-to-create", delete_join_to_create_settings)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/verification", get_guild_verification)
    app.router.add_put("/api/guilds/{guild_id:\\d+}/verification", save_verification_settings)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/verification", delete_verification_settings)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/notifications", create_notification_subscription)
    app.router.add_patch("/api/guilds/{guild_id:\\d+}/notifications/{subscription_id:\\d+}", update_notification_subscription)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/notifications/{subscription_id:\\d+}", delete_notification_subscription)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/notifications/check", check_guild_notifications)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/panels", create_ticket_panel)
    app.router.add_patch("/api/guilds/{guild_id:\\d+}/tickets/panels/{panel_id:\\d+}", update_ticket_panel)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/tickets/panels/{panel_id:\\d+}", delete_ticket_panel)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/{ticket_id:\\d+}/note", add_ticket_note)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/{ticket_id:\\d+}/claim", claim_ticket_from_panel)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/{ticket_id:\\d+}/waiting-user", set_ticket_waiting_user_from_panel)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/{ticket_id:\\d+}/close", close_ticket_from_panel)
    async def _close_notification_service(application: web.Application) -> None:
        await application["notification_service"].close()

    app.on_cleanup.append(_close_notification_service)
    return app
