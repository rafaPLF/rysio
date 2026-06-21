from __future__ import annotations

import json
from typing import Any

from aiohttp import web

from bot.database.repositories.audit_log_repo import AuditLogRepository
from bot.database.session import DatabaseSessionManager
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

    if request.path in {"/", "/logs", "/api/health"}:
        return await handler(request)

    expected_token = request.app["api_token"]
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return web.json_response({"error": "missing_bearer_token"}, status=401)

    provided_token = auth_header.removeprefix("Bearer ").strip()
    if provided_token != expected_token:
        return web.json_response({"error": "invalid_token"}, status=403)

    return await handler(request)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def logs_viewer(_: web.Request) -> web.Response:
    return web.Response(text=render_logs_viewer_page(), content_type="text/html")


async def get_guild_logs(request: web.Request) -> web.Response:
    database: DatabaseSessionManager = request.app["database"]
    guild_id = int(request.match_info["guild_id"])
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
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


def create_web_app(database: DatabaseSessionManager, api_token: str, allowed_origin: str = "") -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app["database"] = database
    app["api_token"] = api_token
    app["allowed_origin"] = allowed_origin
    app.router.add_get("/", logs_viewer)
    app.router.add_get("/logs", logs_viewer)
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/guilds/{guild_id:\\d+}/logs", get_guild_logs)
    return app
