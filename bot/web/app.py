from __future__ import annotations

import json
from typing import Any

import discord
from aiohttp import web

from bot.database.repositories.audit_log_repo import AuditLogRepository
from bot.database.repositories.guild_repo import GuildRepository
from bot.database.repositories.ticket_repo import TicketRepository
from bot.database.session import DatabaseSessionManager
from bot.modules.tickets.views import TicketCreateView
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


def _serialize_text_channel(channel: discord.TextChannel) -> dict[str, Any]:
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


def _serialize_ticket_panel(panel, guild: discord.Guild) -> dict[str, Any]:
    channel = guild.get_channel(panel.channel_id)
    category = guild.get_channel(panel.category_id) if panel.category_id else None
    support_role = guild.get_role(panel.support_role_id) if panel.support_role_id else None
    return {
        "id": panel.id,
        "channel_id": str(panel.channel_id),
        "channel_name": channel.name if isinstance(channel, discord.TextChannel) else f"#{panel.channel_id}",
        "message_id": str(panel.message_id),
        "category_id": str(panel.category_id) if panel.category_id else None,
        "category_name": category.name if isinstance(category, discord.CategoryChannel) else None,
        "support_role_id": str(panel.support_role_id) if panel.support_role_id else None,
        "support_role_name": support_role.name if support_role else None,
        "welcome_message": panel.welcome_message or "",
    }


async def _get_authorized_guild(request: web.Request) -> discord.Guild | None:
    bot = request.app["bot"]
    if bot is None:
        return None

    guild_id = int(request.match_info["guild_id"])
    panel_session = request.get("panel_session")
    if panel_session is not None and guild_id not in get_manageable_guild_ids(panel_session):
        return None

    return bot.get_guild(guild_id)


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
        return web.json_response({"error": "guild_access_denied"}, status=403)

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        ticket_repo = TicketRepository(session)
        settings = await guild_repo.ensure_settings(guild.id)
        panels = await ticket_repo.get_panels_for_guild(guild.id)

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
        "categories": sorted(
            [_serialize_category(channel) for channel in guild.categories],
            key=lambda item: (item["position"], item["name"].lower()),
        ),
        "roles": sorted(
            [_serialize_role(role) for role in guild.roles if not role.is_default()],
            key=lambda item: (-item["position"], item["name"].lower()),
        ),
        "ticket_panels": [_serialize_ticket_panel(panel, guild) for panel in panels],
    }
    return web.json_response(payload)


async def create_ticket_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return web.json_response({"error": "guild_access_denied"}, status=403)

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

    language = await bot.guild_config.get_language(bot.database, guild.id)
    embed = discord.Embed(title=title, description=description_text, color=discord.Color.blurple())
    embed.add_field(
        name=bot.localization.translate("tickets.panel_field_name", language=language),
        value=bot.localization.translate("tickets.panel_field_value", language=language),
        inline=False,
    )

    message = await channel.send(embed=embed, view=TicketCreateView())

    database: DatabaseSessionManager = request.app["database"]
    async with database.session() as session:
        guild_repo = GuildRepository(session)
        ticket_repo = TicketRepository(session)
        await guild_repo.ensure_guild(guild.id, bot.guild_config.get_default_language())
        settings = await guild_repo.ensure_settings(guild.id)
        settings.ticket_enabled = True
        panel = await ticket_repo.create_panel(
            guild_id=guild.id,
            channel_id=channel.id,
            message_id=message.id,
            category_id=category.id if category else None,
            support_role_id=support_role.id if support_role else None,
            welcome_message=welcome_message or None,
        )

    bot.add_view(TicketCreateView(), message_id=message.id)
    return web.json_response(
        {
            "created": True,
            "panel": _serialize_ticket_panel(panel, guild),
        },
        status=201,
    )


async def delete_ticket_panel(request: web.Request) -> web.Response:
    guild = await _get_authorized_guild(request)
    if guild is None:
        return web.json_response({"error": "guild_access_denied"}, status=403)

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
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


def create_web_app(database: DatabaseSessionManager, api_token: str, allowed_origin: str = "", *, bot=None) -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app["database"] = database
    app["bot"] = bot
    app["api_token"] = api_token
    app["allowed_origin"] = allowed_origin
    app["oauth_states"] = {}
    app["panel_sessions"] = {}
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
    app.router.add_get("/api/guilds/{guild_id:\\d+}/logs", get_guild_logs)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/overview", get_guild_overview)
    app.router.add_post("/api/guilds/{guild_id:\\d+}/tickets/panels", create_ticket_panel)
    app.router.add_delete("/api/guilds/{guild_id:\\d+}/tickets/panels/{panel_id:\\d+}", delete_ticket_panel)
    return app
