from __future__ import annotations

import json
from typing import Any

from aiohttp import web

from bot.database.repositories.audit_log_repo import AuditLogRepository
from bot.database.session import DatabaseSessionManager
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
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
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
    return app
