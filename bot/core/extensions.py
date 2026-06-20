from __future__ import annotations

import logging

from discord.ext import commands

from bot.core.constants import INITIAL_EXTENSIONS

logger = logging.getLogger(__name__)


async def load_extensions(bot: commands.Bot) -> None:
    for extension in INITIAL_EXTENSIONS:
        await bot.load_extension(extension)
        logger.info("Loaded extension: %s", extension)
