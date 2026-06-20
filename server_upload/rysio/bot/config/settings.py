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
    bot_prefix: str = "!"
    default_language: str = "de"
    log_level: str = "INFO"
    enable_members_intent: bool = False
    enable_message_content_intent: bool = False


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

    return Settings(
        discord_token=discord_token,
        database_url=database_url,
        bot_prefix=os.getenv("BOT_PREFIX", "!").strip() or "!",
        default_language=os.getenv("DEFAULT_LANGUAGE", "de").strip() or "de",
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        enable_members_intent=_get_bool("ENABLE_MEMBERS_INTENT", False),
        enable_message_content_intent=_get_bool("ENABLE_MESSAGE_CONTENT_INTENT", False),
    )
