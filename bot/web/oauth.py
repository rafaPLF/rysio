from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
import discord

DISCORD_API_BASE = "https://discord.com/api/v10"
MANAGE_GUILD = 0x20
ADMINISTRATOR = 0x8
STATE_TTL_SECONDS = 600
SESSION_TTL_SECONDS = 60 * 60 * 12


@dataclass(slots=True)
class DiscordOAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    panel_public_url: str

    @property
    def enabled(self) -> bool:
        return all(
            [
                self.client_id,
                self.client_secret,
                self.redirect_uri,
                self.panel_public_url,
            ]
        )


def create_oauth_settings(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    panel_public_url: str,
) -> DiscordOAuthSettings:
    return DiscordOAuthSettings(
        client_id=client_id.strip(),
        client_secret=client_secret.strip(),
        redirect_uri=redirect_uri.strip(),
        panel_public_url=panel_public_url.strip().rstrip("/"),
    )


def create_state(app) -> str:
    token = secrets.token_urlsafe(24)
    app["oauth_states"][token] = time.time() + STATE_TTL_SECONDS
    _cleanup_expiring_mapping(app["oauth_states"])
    return token


def pop_state(app, state: str) -> bool:
    expires_at = app["oauth_states"].pop(state, None)
    if expires_at is None:
        return False
    return expires_at >= time.time()


def create_session(app, payload: dict[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    app["panel_sessions"][token] = {
        **payload,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    _cleanup_expiring_mapping(app["panel_sessions"], nested_expiry=True)
    return token


def get_session(app, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    session = app["panel_sessions"].get(token)
    if not session:
        return None
    if session.get("expires_at", 0) < time.time():
        app["panel_sessions"].pop(token, None)
        return None
    return session


def get_manageable_guild_ids(session: dict[str, Any]) -> set[int]:
    manageable_ids: set[int] = set()
    for guild in session.get("guilds", []):
        try:
            guild_id = int(guild["id"])
        except (KeyError, TypeError, ValueError):
            continue
        manageable_ids.add(guild_id)
    return manageable_ids


def build_login_url(settings: DiscordOAuthSettings, state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": settings.redirect_uri,
            "response_type": "code",
            "scope": "identify guilds",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


async def exchange_code_for_session_payload(
    *,
    settings: DiscordOAuthSettings,
    bot: discord.Client,
    code: str,
) -> dict[str, Any]:
    async with aiohttp.ClientSession() as client:
        token_response = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": settings.client_id,
                "client_secret": settings.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_payload = await token_response.json()
        if token_response.status >= 400:
            raise RuntimeError(token_payload.get("error_description") or token_payload.get("error") or "oauth_token_exchange_failed")

        access_token = token_payload.get("access_token")
        if not access_token:
            raise RuntimeError("oauth_missing_access_token")

        auth_headers = {"Authorization": f"Bearer {access_token}"}

        user_response = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=auth_headers)
        user_payload = await user_response.json()
        if user_response.status >= 400:
            raise RuntimeError(user_payload.get("message") or "oauth_user_fetch_failed")

        guilds_response = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=auth_headers)
        guilds_payload = await guilds_response.json()
        if guilds_response.status >= 400:
            raise RuntimeError("oauth_guild_fetch_failed")

    bot_guild_ids = {guild.id for guild in bot.guilds}
    manageable_guilds = []
    for guild in guilds_payload:
        permissions = _parse_permissions(guild.get("permissions"))
        if not _can_manage_guild(permissions):
            continue
        guild_id = guild.get("id")
        manageable_guilds.append(
            {
                "id": guild_id,
                "name": guild.get("name", "Unknown"),
                "icon": guild.get("icon"),
                "owner": bool(guild.get("owner")),
                "permissions": str(guild.get("permissions", "0")),
                "bot_in_guild": int(guild_id) in bot_guild_ids if guild_id else False,
            }
        )

    return {
        "user": {
            "id": user_payload.get("id"),
            "username": user_payload.get("username"),
            "global_name": user_payload.get("global_name"),
            "discriminator": user_payload.get("discriminator"),
            "avatar": user_payload.get("avatar"),
        },
        "guilds": manageable_guilds,
    }


def build_callback_redirect(settings: DiscordOAuthSettings, *, session_token: str, error: str | None = None) -> str:
    parts = []
    if session_token:
        parts.append(f"rysio_panel_token={session_token}")
    if error:
        parts.append(f"rysio_oauth_error={error}")
    fragment = "&".join(parts)
    return f"{settings.panel_public_url}/#{fragment}" if fragment else settings.panel_public_url


def _parse_permissions(raw_value: str | int | None) -> int:
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError):
        return 0


def _can_manage_guild(permissions: int) -> bool:
    return bool(permissions & ADMINISTRATOR or permissions & MANAGE_GUILD)


def _cleanup_expiring_mapping(mapping: dict[str, Any], *, nested_expiry: bool = False) -> None:
    now = time.time()
    expired_keys = []
    for key, value in mapping.items():
        expires_at = value.get("expires_at", 0) if nested_expiry else value
        if expires_at < now:
            expired_keys.append(key)
    for key in expired_keys:
        mapping.pop(key, None)
