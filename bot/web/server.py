from __future__ import annotations

import logging

from aiohttp import web

from bot.config.settings import Settings
from bot.database.session import DatabaseSessionManager
from bot.web.app import create_web_app

logger = logging.getLogger(__name__)


class WebApiServer:
    def __init__(self, settings: Settings, database: DatabaseSessionManager) -> None:
        self._settings = settings
        self._database = database
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def start(self) -> None:
        if not self._settings.web_api_enabled or self._runner is not None:
            return

        app = create_web_app(
            self._database,
            self._settings.web_api_token,
            allowed_origin=self._settings.web_api_allowed_origin,
        )
        self._runner = web.AppRunner(app)
        await self._runner.setup()

        self._site = web.TCPSite(
            self._runner,
            host=self._settings.web_api_host,
            port=self._settings.web_api_port,
        )
        await self._site.start()
        logger.info(
            "Web API started on http://%s:%s",
            self._settings.web_api_host,
            self._settings.web_api_port,
        )

    async def close(self) -> None:
        if self._runner is None:
            return

        await self._runner.cleanup()
        self._runner = None
        self._site = None
