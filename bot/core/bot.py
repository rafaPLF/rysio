from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.config.settings import Settings, get_settings
from bot.core.extensions import load_extensions
from bot.core.logging import configure_logging
from bot.database.session import DatabaseSessionManager
from bot.services.guild_config_service import GuildConfigService
from bot.services.localization_service import LocalizationService
from bot.services.owner_service import OwnerService
from bot.services.patch_notes_service import PatchNotesService
from bot.services.premium_service import PremiumService
from bot.web.server import WebApiServer
from bot.modules.reaction_roles.service import ReactionRoleService
from bot.modules.tickets.service import TicketService
from bot.modules.verification.service import VerificationService

logger = logging.getLogger(__name__)


class DCBot(commands.Bot):
    def __init__(
        self,
        *,
        settings: Settings,
        database: DatabaseSessionManager,
        localization: LocalizationService,
        guild_config: GuildConfigService,
        premium: PremiumService,
        patch_notes: PatchNotesService,
        reaction_roles: ReactionRoleService,
        tickets: TicketService,
        verification: VerificationService,
        owner_control: OwnerService,
    ) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = settings.enable_members_intent
        intents.messages = True
        intents.message_content = settings.enable_message_content_intent
        intents.voice_states = True

        super().__init__(command_prefix=settings.bot_prefix, intents=intents)

        self.settings = settings
        self.database = database
        self.localization = localization
        self.guild_config = guild_config
        self.premium = premium
        self.patch_notes = patch_notes
        self.reaction_roles = reaction_roles
        self.tickets = tickets
        self.verification = verification
        self.owner_control = owner_control
        self.web_api = WebApiServer(settings, database, bot=self)
        self._patch_notes_checked = False

    async def setup_hook(self) -> None:
        await self.database.connect()
        await self.web_api.start()
        await self.owner_control.load()
        await load_extensions(self)
        await self.reaction_roles.restore_views(self)
        await self.tickets.restore_views(self)
        await self.verification.restore_views(self)
        await self.tree.sync()
        logger.info("Application commands synced")

    async def on_ready(self) -> None:
        logger.info(self.localization.translate("bot.ready", user=str(self.user)))
        if not self._patch_notes_checked:
            self._patch_notes_checked = True
            await self.patch_notes.publish_for_all_guilds(self)

    async def close(self) -> None:
        await self.web_api.close()
        await self.database.close()
        await super().close()


def create_bot() -> DCBot:
    settings = get_settings()
    configure_logging(settings.log_level)

    database = DatabaseSessionManager(settings.database_url)
    localization = LocalizationService(default_language=settings.default_language)
    guild_config = GuildConfigService(default_language=settings.default_language)
    premium = PremiumService()
    patch_notes = PatchNotesService()
    reaction_roles = ReactionRoleService()
    tickets = TicketService()
    verification = VerificationService()
    owner_control = OwnerService()

    return DCBot(
        settings=settings,
        database=database,
        localization=localization,
        guild_config=guild_config,
        premium=premium,
        patch_notes=patch_notes,
        reaction_roles=reaction_roles,
        tickets=tickets,
        verification=verification,
        owner_control=owner_control,
    )
