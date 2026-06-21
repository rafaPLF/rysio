from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from bot.core.errors import BotConfigurationError

load_dotenv()


@dataclass(slots=True)
class Settings:
    discord_token: str
    database_url: str
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = ""
    panel_public_url: str = ""
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    bot_prefix: str = "!"
    default_language: str = "de"
    log_level: str = "INFO"
    notifications_poll_interval_seconds: int = 180
    enable_members_intent: bool = False
    enable_message_content_intent: bool = False
    web_api_enabled: bool = False
    web_api_host: str = "127.0.0.1"
    web_api_port: int = 8080
    web_api_token: str = ""
    web_api_allowed_origin: str = ""


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    discord_token = os.getenv("DISCORD_TOKEN", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not discord_token:
        raise BotConfigurationError("DISCORD_TOKEN is missing in the environment.")

    if not database_url:
        raise BotConfigurationError("DATABASE_URL is missing in the environment.")

    web_api_enabled = _get_bool("WEB_API_ENABLED", False)
    web_api_token = os.getenv("WEB_API_TOKEN", "").strip()
    if web_api_enabled and not web_api_token:
        raise BotConfigurationError("WEB_API_TOKEN is required when WEB_API_ENABLED is true.")

    return Settings(
        discord_token=discord_token,
        database_url=database_url,
        discord_client_id=os.getenv("DISCORD_CLIENT_ID", "").strip(),
        discord_client_secret=os.getenv("DISCORD_CLIENT_SECRET", "").strip(),
        discord_redirect_uri=os.getenv("DISCORD_REDIRECT_URI", "").strip(),
        panel_public_url=os.getenv("PANEL_PUBLIC_URL", "").strip(),
        twitch_client_id=os.getenv("TWITCH_CLIENT_ID", "").strip(),
        twitch_client_secret=os.getenv("TWITCH_CLIENT_SECRET", "").strip(),
        bot_prefix=os.getenv("BOT_PREFIX", "!").strip() or "!",
        default_language=os.getenv("DEFAULT_LANGUAGE", "de").strip() or "de",
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        notifications_poll_interval_seconds=int(
            os.getenv("NOTIFICATIONS_POLL_INTERVAL_SECONDS", "180").strip() or "180"
        ),
        enable_members_intent=_get_bool("ENABLE_MEMBERS_INTENT", False),
        enable_message_content_intent=_get_bool("ENABLE_MESSAGE_CONTENT_INTENT", False),
        web_api_enabled=web_api_enabled,
        web_api_host=os.getenv("WEB_API_HOST", "127.0.0.1").strip() or "127.0.0.1",
        web_api_port=int(os.getenv("WEB_API_PORT", "8080").strip() or "8080"),
        web_api_token=web_api_token,
        web_api_allowed_origin=os.getenv("WEB_API_ALLOWED_ORIGIN", "").strip(),
    )
