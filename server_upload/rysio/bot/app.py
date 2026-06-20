from __future__ import annotations

import asyncio

from bot.core.bot import create_bot


async def run() -> None:
    bot = create_bot()
    async with bot:
        await bot.start(bot.settings.discord_token)


def main() -> None:
    asyncio.run(run())
