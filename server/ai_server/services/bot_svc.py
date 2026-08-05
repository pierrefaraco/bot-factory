from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ai_server.dao.database import Bot, User, db
from ai_server.dto.bot_assignment_dto import BotAssignmentDto
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.dto.bot_dto import BotDto
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.exceptions.service_exceptions import ServiceError
from ai_server.services.base_service import BaseService
from ai_server.services.avatar_svc import AvatarService
from ai_server.decorators.singleton import singleton
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.template_svc import TemplateSvc

# Lazy import to avoid circular dependency
from ai_server.log.app_logger import AppLogger

if TYPE_CHECKING:
    from ai_server.services.knowledge_svc import KnowledgeSvc


@singleton
class BotService(BaseService[BotDto]):
    """Service for managing bot entities"""

    def __init__(self):
        super().__init__()
        self.avatar_svc = AvatarService()
        self.bot_assignment_svc = BotAssignmentService()
        self.bot_parameters_svc = BotParametersService()
        self.template_svc = TemplateSvc()
        self._context_svc = None
        self.logger = AppLogger()

    @property
    def context_svc(self):
        """Lazy load ContextSvc to avoid circular import."""
        if self._context_svc is None:
            from ai_server.services.knowledge_svc import KnowledgeSvc
            from ai_server.services.rag_svc import RagService

            rag_svc = RagService()
            self._context_svc = KnowledgeSvc(rag_svc)
        return self._context_svc

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

    def is_bot_belong_to_user(self, bot_id: int, user_account_id: int) -> bool:
        """
        Check if a bot belongs to a specific user.

        Args:
            bot_id: ID of the bot
            user_account_id: ID of the user account

        Returns:
            True if the bot belongs to the user, False otherwise
        """
        return bool(
            self._safe_execute(
                "check_bot_ownership",
                self._check_bot_ownership,
                bot_id,
                user_account_id,
            )
        )

    def _check_bot_ownership(self, bot_id: int, user_account_id: int) -> bool:
        bot: Bot = Bot.query.get(bot_id)
        return bot is not None and bot.user_account_id == user_account_id

    def create_random_bot(self, user_account_id) -> BotDto:
        bot = Bot(user_account_id=user_account_id, prompt="")
        db.session.add(bot)

        user: User = User.query.filter_by(id=user_account_id).first()
        if not user:
            raise Exception("User not found")
        db.session.commit()
        avatar_dto = self.avatar_svc.create_random_avatar(bot.id)
        parameters_dto = self.bot_parameters_svc.create_random_parameters(
            user.name, bot.id
        )
        self.template_svc.importTemplateInDB(bot.id, "start")
        return self._big_bot_to_dto(bot, avatar_dto, parameters_dto)

    def create(self, data: Dict[str, Any]) -> BotDto:
        """
        Create a new bot.

        Args:
            data: Bot creation data containing user_account_id and optional prompt

        Returns:
            Created BotDto instance

        Raises:
            ServiceError: When bot creation fails
        """
        result = self._safe_execute("_perform_create", self._perform_create, data)
        if result is None:
            raise ServiceError("Bot creation failed, no BotDto returned.")
        return result

    def _perform_create(self, data: Dict[str, Any]) -> BotDto:
        bot = Bot(
            user_account_id=data["user_account_id"], prompt=data.get("prompt", "")
        )
        db.session.add(bot)
        db.session.commit()
        return self._bot_to_dto(bot, None)

    def get_prompt(self, entity_id: int):
        bot: Bot = Bot.query.filter_by(id=entity_id).first()
        return bot.prompt

    def get_dto_by_id(self, entity_id: int, view="minimal") -> BotDto:
        """
        Retrieve a bot by its ID.

        Args:
            entity_id: ID of the bot to retrieve

        Returns:
            Bot instance if found, None otherwise
        """
        self.logger.info(f"get_dto_by_id {view}")
        result = self._safe_execute(
            "_perform_get_by_id", self._perform_get_by_id, entity_id, view
        )
        if result is None:
            raise ServiceError("Get bot by id failed, no BotDto returned.")
        return result

    def _perform_get_by_id(self, entity_id: int, view: str) -> BotDto:
        bot = Bot.query.filter_by(id=entity_id).first()
        avatar = self.avatar_svc.get_avatar_by_bot_id(entity_id)
        avatar = avatar if avatar is not None else AvatarDto()
        if view == "full":
            try:
                self.logger.info(
                    f"Get full view for bot bot_id={entity_id} view={view}"
                )
                bot_parameters = self.bot_parameters_svc.get_by_bot_id(entity_id)
                return self._big_bot_to_dto(bot, avatar, bot_parameters)
            except Exception as e:
                self.logger.error(
                    f"Error getting full bot view for bot_id={entity_id}: {str(e)}"
                )
                return self._bot_to_dto(bot, avatar)
        else:
            self.logger.info(f"Get minimal view for bot bot_id={entity_id} view={view}")
            return self._bot_to_dto(bot, avatar)

    def get_all(self) -> List[BotDto]:
        """
        Retrieve all bots .

        Returns:
            List of Bot instances
        """
        result = self._safe_execute("_perform_get_all", self._perform_get_all)
        if result is None:
            raise ServiceError("Bot get_all failed, no list returned.")
        return result

    def _perform_get_all(self) -> List[BotDto]:
        bots: List[Bot] = Bot.query.filter_by().all()
        return [self._bot_to_dto(bot, None) for bot in bots]

    def update(self, entity_id: int, data: Dict[str, Any]) -> BotDto:
        """
        Update a bot's information.

        Args:
            entity_id: ID of the bot to update
            data: Fields to update (e.g., prompt)

        Returns:
            Updated BotDto instance or None if update fails
        """
        result = self._safe_execute(
            "_perform_update", self._perform_update, entity_id, data
        )
        if result is None:
            raise ServiceError("Update Bot failed, no list returned.")
        return result

    def _perform_update(self, entity_id, data) -> BotDto:
        bot = Bot.query.get(entity_id)
        for key, value in data.items():
            if hasattr(bot, key):
                setattr(bot, key, value)

        db.session.commit()
        return self._bot_to_dto(bot, None)

    def delete(self, entity_id: int) -> bool:
        """
        Delete a bot.

        Args:
            entity_id: ID of the bot to delete

        Returns:
            True if deletion was successful, False otherwise

        Note:
            Thanks to CASCADE delete on foreign keys, the following will be automatically deleted:
            - BotParameters
            - BotAvatar
            - Chapter
            - Session
            - BotAssignment
            - IFrame
        """

        # Delete context manually (not managed by database CASCADE)
        self.context_svc.delete_all(entity_id)

        result = self._safe_execute("_perform_delete", self._perform_delete, entity_id)
        if result is None:
            raise ServiceError("Bot delete failed, no bot deleted.")
        return result

    def _perform_delete(self, entity_id) -> bool:
        bot = Bot.query.get(entity_id)
        if not bot:
            return False

        db.session.delete(bot)
        db.session.commit()
        return True

    def get_bot_owner(self, bot_id: int) -> Optional[User]:
        """
        Retrieve the owner of a specific bot.

        Args:
            bot_id: ID of the bot

        Returns:
            User instance if found, None otherwise
        """
        return self._safe_execute("get_bot_owner", self._perform_get_bot_owner, bot_id)

    def _perform_get_bot_owner(self, bot_id: int) -> Optional[User]:
        bot = Bot.query.get(bot_id)
        if not bot:
            return None
        return User.query.get(bot.user_account_id)

    def get_bots_by_user(self, user_account_id: int) -> List[BotDto]:
        """
        Retrieve all bots belonging to a specific user.

        Args:
            user_account_id: ID of the user account

        Returns:
            List of Bot instances belonging to the user
        """
        result = self._safe_execute(
            "_perform_get_by_user", self._perform_get_by_user, user_account_id
        )
        if result is None:
            raise ServiceError("Bot delete failed, no bot deleted.")
        return result

    def _perform_get_by_user(self, user_account_id: int) -> list[BotDto]:
        bots: list[Bot] = Bot.query.filter_by(user_account_id=user_account_id).all()
        return [
            self._bot_to_dto(bot, self.avatar_svc.get_avatar_by_bot_id(bot.id))
            for bot in bots
        ]

    def get_assigned_bots(self, user_id) -> List[BotDto]:
        """
        Retrieve all assigned bots .

        Returns:
            List of Bot instances
        """
        bots_assigments: List[BotAssignmentDto] = (
            self.bot_assignment_svc.get_assignments_by_user(user_id)
        )
        bots_dto: List[BotDto] = self._safe_execute(
            "_perform_get_all", self._perform_get_assigned_bots, bots_assigments
        )
        if bots_dto is None:
            raise ServiceError("Bot get_all failed, no list returned.")
        return bots_dto

    def _perform_get_assigned_bots(
        self, bots_assigments: List[BotAssignmentDto]
    ) -> list[BotDto]:
        bots_dto = []
        for bot_assigment in bots_assigments:
            bot: Bot = Bot.query.filter_by(id=bot_assigment.bot_id).first()
            bots_dto.append(
                self._bot_to_dto(bot, self.avatar_svc.get_avatar_by_bot_id(bot.id))
            )
        return bots_dto

    def get_bot_count_by_user(self, user_account_id: int) -> int:
        """
        Retrieve the count of bots belonging to a specific user.

        Args:
            user_account_id: ID of the user account

        Returns:
            Count of bots belonging to the user
        """
        return self._safe_execute(
            "count_bots_by_user", self._count_bots_by_user, user_account_id
        )

    def _count_bots_by_user(self, user_account_id: int) -> int:
        return Bot.query.filter_by(user_account_id=user_account_id).count()

    def get_bot_parameters_description(self) -> dict:
        return self.bot_parameters_svc.get_bot_parameters_description()

    def is_bot_assigned_to_user(self, bot_id, user_id):
        return self.bot_assignment_svc.is_bot_assigned_to_user(bot_id, user_id)

    def delete_all_bot_assignments(self, bot_id):
        return self.bot_assignment_svc.delete_all_bot_assignments(bot_id)
