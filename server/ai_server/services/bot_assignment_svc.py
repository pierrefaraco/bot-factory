from typing import Optional, List, Dict, Any
from ai_server.models import BotAssignment, Bot, User
from ai_server.database.session import db
from ai_server.dto.bot_assignment_dto import BotAssignmentDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.repositories import (
    BotAssignmentRepository,
    BotRepository,
    UserRepository,
)
from ai_server.services.base_service import BaseService
from ai_server.config.constant import GUEST_ROLE, USER_ROLE
from ai_server.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()


class BotAssignmentService(BaseService[BotAssignmentDto]):
    """Service for managing bot user assignments"""

    def __init__(
        self,
        bot_assignment_repo: BotAssignmentRepository,
        bot_repo: BotRepository,
        user_repo: UserRepository,
    ):
        super().__init__()
        self.bot_assignment_repo = bot_assignment_repo
        self.bot_repo = bot_repo
        self.user_repo = user_repo

    def _assignment_to_dto(self, assignment: BotAssignment) -> BotAssignmentDto:
        """
        Convert BotAssignment entity to BotAssignmentDto.

        Args:
            assignment: BotAssignment entity to convert

        Returns:
            BotAssignmentDto representation of the assignment
        """
        return BotAssignmentDto(
            id=assignment.id,
            bot_id=assignment.bot_id,
            user_id=assignment.user_id,
            assigned_by=assignment.assigned_by,
            assigned_at=assignment.assigned_at,
            is_active=assignment.is_active,
        )

    @staticmethod
    def _check_assignable(
        bot: Optional[Bot],
        user: Optional[User],
        bot_id: int,
        user_id: int,
        assigned_by: int,
    ) -> None:
        """Business rules for assigning bot_id to user_id on behalf of
        assigned_by, given the already-loaded rows (None if not found).
        Shared by the async path and the sync one below."""
        if not bot:
            logger.warning(f"assignment rejected: bot_id={bot_id} not found")
            raise NotFoundError("Bot", str(bot_id))

        if int(bot.user_account_id) != int(assigned_by):
            logger.warning(
                f"assignment rejected: bot_id={bot_id} owner={bot.user_account_id} "
                f"does not match assigned_by={assigned_by}"
            )
            raise ServiceError(f"Bot {bot_id} does not belong to user {assigned_by}")

        # Validate that user exists and can be assigned bots (GUEST or USER
        # -- "My Bots" now shows assigned bots for Users too, and
        # admin.component.ts's "Assign Bot" action is already offered for
        # User rows in the Users tab, so this used to 500 for them).
        if not user:
            logger.warning(f"assignment rejected: user_id={user_id} not found")
            raise NotFoundError("User", str(user_id))

        if user.roles not in (GUEST_ROLE, USER_ROLE):
            logger.warning(
                f"assignment rejected: user_id={user_id} role={user.roles} "
                "is not GUEST or USER"
            )
            raise ServiceError(f"User {user_id} is not a GUEST or USER account")
        # Guests are only assignable by their own parent -- Users have no
        # equivalent parent relationship to check here, and the calling
        # route (PATCH /users/<id>) already ran authorize_user_scope, which
        # is what actually gates who may reach this point for a User target
        # (Admin, since a User has no guests of their own to assign bots
        # through this same endpoint anyway).
        if user.roles == GUEST_ROLE and int(user.parent_id) != int(assigned_by):
            logger.warning(
                f"assignment rejected: guest user_id={user_id} is not a child "
                f"of assigned_by={assigned_by}"
            )
            raise ServiceError(
                f"Guest user {user_id} is not a child of user {assigned_by}"
            )

    async def _validate(self, bot_id: int, user_id: int, assigned_by: int) -> None:
        self._check_assignable(
            await self.bot_repo.get(bot_id),
            await self.user_repo.get(user_id),
            bot_id,
            user_id,
            assigned_by,
        )

    async def create(self, data: Dict[str, Any]) -> BotAssignmentDto:
        """
        Create a new bot user assignment, or reactivate/update the existing
        one for the same bot and user.

        Args:
            data: Assignment creation data containing bot_id, user_id, assigned_by

        Returns:
            Created BotAssignmentDto instance

        Raises:
            NotFoundError/ServiceError: When the assignment is not allowed
        """
        logger.debug(
            f"Creating bot assignment - bot_id: {data.get('bot_id')}, user_id: {data.get('user_id')}, assigned_by: {data.get('assigned_by')}"
        )
        await self._validate(data["bot_id"], data["user_id"], data["assigned_by"])

        existing_assignment = await self.bot_assignment_repo.find(
            data["bot_id"], data["user_id"]
        )
        if existing_assignment:
            existing_assignment.is_active = data.get("is_active", True)
            existing_assignment.assigned_by = data["assigned_by"]
            await self.bot_assignment_repo.commit()
            logger.info(
                f"Bot assignment reactivated/updated: assignment_id={existing_assignment.id} "
                f"bot_id={data['bot_id']} user_id={data['user_id']} is_active={existing_assignment.is_active}"
            )
            return self._assignment_to_dto(existing_assignment)

        assignment = BotAssignment(
            bot_id=data["bot_id"],
            user_id=data["user_id"],
            assigned_by=data["assigned_by"],
            is_active=data.get("is_active", True),
        )
        self.bot_assignment_repo.add(assignment)
        await self.bot_assignment_repo.commit()
        logger.info(
            f"Bot assignment created: assignment_id={assignment.id} "
            f"bot_id={data['bot_id']} user_id={data['user_id']}"
        )
        return self._assignment_to_dto(assignment)

    async def get_dto_by_id(self, entity_id: int) -> Optional[BotAssignmentDto]:
        """
        Retrieve an assignment by its ID.

        Args:
            entity_id: ID of the assignment to retrieve

        Returns:
            BotAssignmentDto instance if found, None otherwise
        """
        assignment = await self.bot_assignment_repo.get(entity_id)
        if not assignment:
            return None
        return self._assignment_to_dto(assignment)

    async def get_assignments_by_parent(
        self, parent_user_id: int
    ) -> List[BotAssignmentDto]:
        """
        Get all active assignments created by a parent user.

        Args:
            parent_user_id: ID of the parent user

        Returns:
            List of BotAssignmentDto instances
        """
        assignments = await self.bot_assignment_repo.list_active_by_assigner(
            parent_user_id
        )
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    async def get_assignments_by_user(
        self, user_id: int, include_inactive: bool = False
    ) -> List[BotAssignmentDto]:
        """
        Get the assignments of a user -- active ones only, unless
        include_inactive.

        Args:
            user_id: ID of the user

        Returns:
            List of BotAssignmentDto instances
        """
        assignments = await self.bot_assignment_repo.list_for_user(
            user_id, active_only=not include_inactive
        )
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    async def get_assigned_bot_ids_for_user(self, user_id: int) -> List[int]:
        """
        Get list of bot IDs actively assigned to a user.

        Args:
            user_id: ID of the user

        Returns:
            List of bot IDs
        """
        assignments = await self.bot_assignment_repo.list_for_user(user_id)
        return [assignment.bot_id for assignment in assignments]

    async def is_bot_assigned_to_user(self, bot_id: int, user_id: int) -> bool:
        """
        Check if a bot is actively assigned to a user.

        Args:
            bot_id: ID of the bot
            user_id: ID of the user

        Returns:
            True if the bot is assigned to the user, False otherwise
        """
        assignment = await self.bot_assignment_repo.find(
            bot_id, user_id, active_only=True
        )
        return assignment is not None

    async def update(self, entity_id: int, data: Dict[str, Any]) -> BotAssignmentDto:
        """
        Update assignment information (only is_active can change).

        Args:
            entity_id: ID of the assignment to update
            data: Fields to update

        Returns:
            Updated BotAssignmentDto instance

        Raises:
            NotFoundError: When the assignment does not exist
        """
        assignment = await self.bot_assignment_repo.get(entity_id)
        if not assignment:
            logger.warning(f"update rejected: assignment_id={entity_id} not found")
            raise NotFoundError("Assignment", str(entity_id))

        if "is_active" in data:
            assignment.is_active = data["is_active"]

        await self.bot_assignment_repo.commit()
        logger.info(
            f"Bot assignment updated: assignment_id={entity_id} is_active={assignment.is_active}"
        )
        return self._assignment_to_dto(assignment)

    async def delete(self, entity_id: int) -> bool:
        """
        Delete an assignment.

        Args:
            entity_id: ID of the assignment to delete

        Returns:
            True if deletion was successful

        Raises:
            NotFoundError: When the assignment does not exist
        """
        assignment = await self.bot_assignment_repo.get(entity_id)
        if not assignment:
            logger.warning(f"delete rejected: assignment_id={entity_id} not found")
            raise NotFoundError("Assignment", str(entity_id))

        bot_id, user_id = assignment.bot_id, assignment.user_id
        await self.bot_assignment_repo.delete(assignment)
        await self.bot_assignment_repo.commit()
        logger.info(
            f"Bot assignment deleted: assignment_id={entity_id} bot_id={bot_id} user_id={user_id}"
        )
        return True

    async def remove_assignment(self, bot_id: int, user_id: int) -> bool:
        """
        Remove the assignment between a bot and user, active or not.

        Returns:
            True if an assignment was removed, False if there was none
        """
        assignment = await self.bot_assignment_repo.find(bot_id, user_id)
        if not assignment:
            return False

        assignment_id = assignment.id
        await self.bot_assignment_repo.delete(assignment)
        await self.bot_assignment_repo.commit()
        logger.info(
            f"Bot assignment removed: assignment_id={assignment_id} bot_id={bot_id} user_id={user_id}"
        )
        return True

    async def replace_user_assignments(
        self, user_id: int, assigned_by: int, bot_ids: List[int]
    ) -> List[BotAssignmentDto]:
        """Make bot_ids the exact set of (active) assignments of user_id.

        Does not commit: the caller owns the transaction, so a rejected bot
        leaves the user's previous assignments untouched instead of already
        having deleted them."""
        logger.debug(
            f"Replacing bot assignments for user {user_id} with {len(bot_ids)} bots"
        )
        for bot_id in bot_ids:
            await self._validate(int(bot_id), user_id, assigned_by)

        await self.bot_assignment_repo.delete_for_user(user_id)
        assignments = [
            BotAssignment(
                bot_id=int(bot_id), user_id=user_id, assigned_by=int(assigned_by)
            )
            for bot_id in bot_ids
        ]
        for assignment in assignments:
            self.bot_assignment_repo.add(assignment)
        await self.bot_assignment_repo.flush()
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    # Transitional sync twin of replace_user_assignments(), for
    # UserAdminService.create()'s still-sync register_* chain (run in a
    # threadpool for its CPU-heavy password hashing, see user_admin_svc.py).
    # Goes away once that chain -- the User aggregate -- is migrated to
    # repositories. Commits itself: that chain has no async unit of work.
    def replace_user_assignments_sync(
        self, user_id: int, assigned_by: int, bot_ids: List[int]
    ) -> List[BotAssignmentDto]:
        logger.debug(
            f"Replacing bot assignments for user {user_id} with {len(bot_ids)} bots"
        )
        for bot_id in bot_ids:
            self._check_assignable(
                Bot.query.get(int(bot_id)),
                User.query.get(user_id),
                int(bot_id),
                user_id,
                assigned_by,
            )

        BotAssignment.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        assignments = [
            BotAssignment(
                bot_id=int(bot_id), user_id=user_id, assigned_by=int(assigned_by)
            )
            for bot_id in bot_ids
        ]
        db.session.add_all(assignments)
        db.session.commit()
        return [self._assignment_to_dto(assignment) for assignment in assignments]
