from typing import Optional, List, Dict, Any

from starlette.concurrency import run_in_threadpool

from ai_server.models import Bot
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.dto.bot_dto import BotDto
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.repositories import BotRepository, UserRepository
from ai_server.services.base_service import BaseService
from ai_server.services.avatar_svc import AvatarService
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.template_svc import TemplateSvc
from ai_server.services.knowledge_svc import KnowledgeSvc


class BotService(BaseService[BotDto]):
    """Service for managing bot entities.

    Async throughout. The only sync work left is KnowledgeSvc/TemplateSvc
    (knowledge chapters + their ChromaDB vectors -- ChromaDB has no async
    client), which create_random_bot()/delete() run through
    run_in_threadpool, off the event loop."""

    def __init__(
        self,
        avatar_svc: AvatarService,
        bot_assignment_svc: BotAssignmentService,
        bot_parameters_svc: BotParametersService,
        knowledge_svc: KnowledgeSvc,
        template_svc: TemplateSvc,
        bot_repo: BotRepository,
        user_repo: UserRepository,
    ):
        super().__init__()
        self.avatar_svc = avatar_svc
        self.bot_assignment_svc = bot_assignment_svc
        self.bot_parameters_svc = bot_parameters_svc
        self.knowledge_svc = knowledge_svc
        self.template_svc = template_svc
        self.bot_repo = bot_repo
        self.user_repo = user_repo
        self.logger = BotFactoryLogger()

    def _big_bot_to_dto(
        self, bot: Bot, avatar_dto: AvatarDto, bot_parameters_dto: BotParametersDto
    ) -> BotDto:
        """
        Convert Bot entity to BotDto.

        Args:
            bot: Bot entity to convert
            avatar_dto: Optional avatar DTO

        Returns:
            BotDto representation of the bot
        """
        return BotDto(
            bot.id,
            bot.user_account_id,
            avatar=avatar_dto,
            bot_parameters=bot_parameters_dto,
        )

    def _bot_to_dto(self, bot: Bot, avatar_dto: Optional[AvatarDto]) -> BotDto:
        """
        Convert Bot entity to BotDto.

        Args:
            bot: Bot entity to convert
            avatar_dto: Optional avatar DTO

        Returns:
            BotDto representation of the bot
        """
        return BotDto(bot.id, bot.user_account_id, avatar_dto)

    async def is_bot_belong_to_user(self, bot_id: int, user_account_id: int) -> bool:
        """
        Check if a bot belongs to a specific user.
        """
        bot = await self.bot_repo.get(bot_id)
        return bot is not None and int(bot.user_account_id) == int(user_account_id)

    async def create_random_bot(self, user_account_id) -> BotDto:
        """Create a bot for user_account_id with a random avatar, a random
        persona (bot parameters + generated prompt) and the "start"
        template's knowledge chapters, indexed in ChromaDB."""
        self.logger.info(
            f"create_random_bot starting for user_account_id={user_account_id}"
        )
        # JWT "sub" is a string: the sync session used to hand back the int
        # column value on reload after commit, the async one (with
        # expire_on_commit=False) would keep the string as given.
        user_account_id = int(user_account_id)
        user = await self.user_repo.get(user_account_id)
        if not user:
            self.logger.warning(
                f"create_random_bot rejected: user_account_id={user_account_id} not found"
            )
            raise Exception("User not found")
        bot = Bot(user_account_id=user_account_id, prompt="")
        self.bot_repo.add(bot)
        await self.bot_repo.commit()

        avatar_dto = await self.avatar_svc.create_random_avatar(bot.id)
        parameters_dto = await self.bot_parameters_svc.create_random_parameters(
            user.name, bot.id
        )
        # Sync (Knowledge rows on the sync session + ChromaDB writes):
        # off the event loop. The bot row is already committed above, so
        # the sync session's own connection sees it.
        await run_in_threadpool(self.template_svc.importTemplateInDB, bot.id, "start")
        await run_in_threadpool(self.knowledge_svc.recordChaptersToVectorDB, bot.id)
        self.logger.info(
            f"create_random_bot succeeded bot_id={bot.id} user_account_id={user_account_id}"
        )
        return self._big_bot_to_dto(bot, avatar_dto, parameters_dto)

    async def get_dto_by_id(self, entity_id: int, view="minimal") -> Optional[BotDto]:
        """
        Retrieve a bot by its ID, with its avatar -- and its parameters too
        when view == "full". None if not found.
        """
        bot = await self.bot_repo.get(entity_id)
        if bot is None:
            self.logger.debug(
                f"get_dto_by_id bot_id={entity_id} view={view} found=False"
            )
            return None
        avatar = await self.avatar_svc.get_avatar_by_bot_id(entity_id)
        avatar = avatar if avatar is not None else AvatarDto()
        self.logger.debug(f"get_dto_by_id bot_id={entity_id} view={view} found=True")
        if view != "full":
            return self._bot_to_dto(bot, avatar)
        try:
            bot_parameters = await self.bot_parameters_svc.get_by_bot_id(entity_id)
            return self._big_bot_to_dto(bot, avatar, bot_parameters)
        except Exception as e:
            # Handled fallback: full view degrades to minimal rather than
            # failing the request, so this is a warning, not an error.
            self.logger.warning(
                f"get_dto_by_id({entity_id}) full view failed, falling back "
                f"to minimal: {str(e)}"
            )
            return self._bot_to_dto(bot, avatar)

    async def get_all(self) -> List[BotDto]:
        """
        Retrieve all bots (without avatars).
        """
        bots = await self.bot_repo.list_all()
        self.logger.debug(f"get_all fetched {len(bots)} bots")
        return [self._bot_to_dto(bot, None) for bot in bots]

    async def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[BotDto]:
        """
        Update a bot's fields present in data. None if the bot does not exist.
        """
        bot = await self.bot_repo.get(entity_id)
        if not bot:
            return None
        for key, value in data.items():
            if hasattr(bot, key):
                setattr(bot, key, value)

        await self.bot_repo.commit()
        self.logger.info(f"Bot updated bot_id={entity_id} fields={list(data.keys())}")
        return self._bot_to_dto(bot, None)

    async def delete(self, entity_id: int) -> bool:
        """
        Delete a bot and everything attached to it.

        Returns:
            True if deletion was successful, False if the bot does not exist

        Note:
            Thanks to CASCADE delete on foreign keys, the following will be automatically deleted:
            - BotParameters
            - BotAvatar
            - Chapter
            - Session
            - BotAssignment
        """
        self.logger.info(f"delete bot_id={entity_id} starting")
        # Knowledge's ChromaDB vectors aren't covered by any DB CASCADE --
        # sync (ChromaDB), so off the event loop.
        await run_in_threadpool(self.knowledge_svc.delete_all, entity_id)

        bot = await self.bot_repo.get(entity_id)
        if not bot:
            self.logger.warning(f"delete bot_id={entity_id} not found")
            return False

        await self.user_repo.clear_selected_bot(entity_id)
        await self.bot_repo.delete(bot)
        await self.bot_repo.commit()
        self.logger.info(f"Bot deleted bot_id={entity_id}")
        return True

    async def get_bots_by_user(self, user_account_id: int) -> List[BotDto]:
        """
        Retrieve all bots belonging to a specific user, with their avatars.
        """
        bots = await self.bot_repo.list_by_owner(user_account_id)
        self.logger.debug(
            f"get_bots_by_user user_account_id={user_account_id} count={len(bots)}"
        )
        return [
            self._bot_to_dto(bot, await self.avatar_svc.get_avatar_by_bot_id(bot.id))
            for bot in bots
        ]

    async def get_assigned_bots(self, user_id) -> List[BotDto]:
        """
        Retrieve the bots actively assigned to user_id, with their avatars.
        """
        assignments = await self.bot_assignment_svc.get_assignments_by_user(user_id)
        bots_dto = []
        for assignment in assignments:
            bot = await self.bot_repo.get(assignment.bot_id)
            bots_dto.append(
                self._bot_to_dto(
                    bot, await self.avatar_svc.get_avatar_by_bot_id(bot.id)
                )
            )
        self.logger.debug(
            f"get_assigned_bots processed {len(assignments)} assignments "
            f"-> {len(bots_dto)} bots"
        )
        return bots_dto

    async def get_owned_and_assigned_bots(self, user_id: int) -> List[BotDto]:
        """
        Retrieve every bot a User/Admin should see in "My Bots": the ones
        they created themselves (Bot.user_account_id) plus any a parent
        assigned to them the same way a Guest gets assigned bots
        (BotAssignment) -- previously only the owned half was returned here,
        so an assigned bot never showed up in the workspace bot-list for
        anyone but a Guest.

        Returns:
            List of BotDto instances, deduplicated by id (defensive: a bot
            assigned to its own owner would otherwise appear twice).
        """
        owned = await self.get_bots_by_user(user_id)
        assigned = await self.get_assigned_bots(user_id)
        seen_ids = {bot.id for bot in owned}
        merged = owned + [bot for bot in assigned if bot.id not in seen_ids]
        self.logger.debug(
            f"get_owned_and_assigned_bots user_id={user_id} owned={len(owned)} "
            f"assigned={len(assigned)} merged={len(merged)}"
        )
        return merged

    def get_bot_parameters_description(self) -> dict:
        return self.bot_parameters_svc.get_bot_parameters_description()

    async def is_bot_assigned_to_user(self, bot_id, user_id):
        return await self.bot_assignment_svc.is_bot_assigned_to_user(bot_id, user_id)
