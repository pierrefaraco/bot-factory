from typing import Optional, List, Dict, Any
from ai_server.dao.database import BotAssignment, Bot, User, db
from ai_server.dto.bot_assignment_dto import BotAssignmentDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from ai_server.config.constant import GUEST_ROLE
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.decorators.singleton import singleton

logger = BotFactoryLogger()


@singleton
class BotAssignmentService(BaseService[BotAssignmentDto]):
    """Service for managing bot user assignments"""

    def __init__(self):
        super().__init__()

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

    def create(self, data: Dict[str, Any]) -> BotAssignmentDto:
        """
        Create a new bot user assignment.

        Args:
            data: Assignment creation data containing bot_id, user_id, assigned_by

        Returns:
            Created BotAssignmentDto instance

        Raises:
            ServiceError: When assignment creation fails
        """
        result = self._perform_create(data)
        if result is None:
            raise ServiceError(
                "Assignment creation failed, no BotAssignmentDto returned."
            )
        return result

    def _perform_create(self, data: Dict[str, Any]) -> BotAssignmentDto:
        # Validate that bot exists and belongs to the assigner
        logger.debug(
            f"Creating bot assignment - bot_id: {data.get('bot_id')}, user_id: {data.get('user_id')}, assigned_by: {data.get('assigned_by')}"
        )
        bot = Bot.query.get(data["bot_id"])
        if not bot:
            raise NotFoundError("Bot", str(data["bot_id"]))

        if int(bot.user_account_id) != int(data["assigned_by"]):
            logger.info(
                f"bot.user_account_id {bot.user_account_id} data['assigned_by']: {data['assigned_by']:}"
            )
            raise ServiceError(
                f"Bot {data['bot_id']} does not belong to user {data['assigned_by']}"
            )

        # Validate that user exists and is a GUEST
        user: User = User.query.get(data["user_id"])
        if not user:
            raise NotFoundError("User", str(data["user_id"]))

        if user.roles != GUEST_ROLE:
            raise ServiceError(f"User {data['user_id']} is not a GUEST user")
        logger.info(f"user {user} ")
        logger.info(f"data {data} ")
        # Validate that user is child of assigner
        if int(user.parent_id) != int(data["assigned_by"]):
            raise ServiceError(
                f"Guest user {data['user_id']} is not a child of user {data['assigned_by']}"
            )

        # Check if assignment already exists
        existing_assignment = BotAssignment.query.filter_by(
            bot_id=data["bot_id"], user_id=data["user_id"]
        ).first()

        if existing_assignment:
            # Update existing assignment
            existing_assignment.is_active = data.get("is_active", True)
            existing_assignment.assigned_by = data["assigned_by"]
            db.session.commit()
            return self._assignment_to_dto(existing_assignment)

        # Create new assignment
        assignment = BotAssignment(
            bot_id=data["bot_id"],
            user_id=data["user_id"],
            assigned_by=data["assigned_by"],
            is_active=data.get("is_active", True),
        )

        db.session.add(assignment)
        db.session.commit()
        return self._assignment_to_dto(assignment)

    def get_dto_by_id(self, entity_id: int) -> Optional[BotAssignmentDto]:
        """
        Retrieve an assignment by its ID.

        Args:
            entity_id: ID of the assignment to retrieve

        Returns:
            BotAssignmentDto instance if found, None otherwise
        """
        return self._perform_get_by_id(entity_id)

    def _perform_get_by_id(self, entity_id: int) -> Optional[BotAssignmentDto]:
        assignment = BotAssignment.query.get(entity_id)
        if not assignment:
            return None
        return self._assignment_to_dto(assignment)

    def get_all(self) -> List[BotAssignmentDto]:
        """
        Retrieve all assignments.

        Returns:
            List of BotAssignmentDto instances

        Raises:
            ServiceError: When assignment retrieval fails
        """
        result = self._perform_get_all()
        if result is None:
            raise ServiceError("Assignment get_all failed, no list returned.")
        return result

    def _perform_get_all(self) -> List[BotAssignmentDto]:
        assignments: List[BotAssignment] = BotAssignment.query.filter_by(
            is_active=True
        ).all()
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    def get_assignments_by_parent(self, parent_user_id: int) -> List[BotAssignmentDto]:
        """
        Get all assignments created by a parent user.

        Args:
            parent_user_id: ID of the parent user

        Returns:
            List of BotAssignmentDto instances

        Raises:
            ServiceError: When assignment retrieval fails
        """
        result = self._perform_get_by_parent(parent_user_id)
        if result is None:
            raise ServiceError("Get assignments by parent failed.")
        return result

    def _perform_get_by_parent(self, parent_user_id: int) -> List[BotAssignmentDto]:
        assignments: List[BotAssignment] = BotAssignment.query.filter_by(
            assigned_by=parent_user_id, is_active=True
        ).all()
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    def get_assignments_by_user(
        self, user_id: int, all: bool = False
    ) -> List[BotAssignmentDto]:
        """
        Get all assignments for a user.

        Args:
            user_id: ID of the user

        Returns:
            List of BotAssignmentDto instances

        Raises:
            ServiceError: When assignment retrieval fails
        """
        if all:
            result = self._perform_get_all_by_user(user_id)
        else:
            result = self._perform_get_by_user(user_id)
        if result is None:
            raise ServiceError("Get assignments by user failed.")
        return result

    def _perform_get_all_by_user(self, user_id: int) -> List[BotAssignmentDto]:
        assignments: List[BotAssignment] = BotAssignment.query.filter_by(
            user_id=user_id,
        ).all()
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    def _perform_get_by_user(self, user_id: int) -> List[BotAssignmentDto]:
        assignments: List[BotAssignment] = BotAssignment.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        return [self._assignment_to_dto(assignment) for assignment in assignments]

    def get_assigned_bot_ids_for_user(self, user_id: int) -> List[int]:
        """
        Get list of bot IDs assigned to a user.

        Args:
            user_id: ID of the user

        Returns:
            List of bot IDs
        """
        result = self._perform_get_bot_ids(user_id)
        if result is None:
            return []
        return result

    def _perform_get_bot_ids(self, user_id: int) -> List[int]:
        assignments: List[BotAssignment] = BotAssignment.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        return [assignment.bot_id for assignment in assignments]

    def is_bot_assigned_to_user(self, bot_id: int, user_id: int) -> bool:
        """
        Check if a bot is assigned to a user.

        Args:
            bot_id: ID of the bot
            user_id: ID of the user

        Returns:
            True if the bot is assigned to the user, False otherwise
        """
        result = self._perform_check_assignment(
            bot_id,
            user_id,
        )
        return bool(result)

    def _perform_check_assignment(self, bot_id: int, user_id: int) -> bool:
        assignment = BotAssignment.query.filter_by(
            bot_id=bot_id, user_id=user_id, is_active=True
        ).first()
        return assignment is not None

    def update(self, entity_id: int, data: Dict[str, Any]) -> BotAssignmentDto:
        """
        Update assignment information.

        Args:
            entity_id: ID of the assignment to update
            data: Fields to update

        Returns:
            Updated BotAssignmentDto instance

        Raises:
            ServiceError: When assignment update fails
        """
        result = self._perform_update(
            entity_id,
            data,
        )
        if result is None:
            raise ServiceError(
                "Assignment update failed, no BotAssignmentDto returned."
            )
        return result

    def _perform_update(self, entity_id: int, data: Dict[str, Any]) -> BotAssignmentDto:
        assignment = BotAssignment.query.get(entity_id)
        if not assignment:
            raise NotFoundError("Assignment", str(entity_id))

        # Only allow updating is_active field
        if "is_active" in data:
            assignment.is_active = data["is_active"]

        db.session.commit()
        return self._assignment_to_dto(assignment)

    def delete_all_bot_assignments(self, bot_id) -> bool:

        assignments: list[BotAssignment] = BotAssignment.query.filter_by(
            bot_id=bot_id
        ).all()
        for assignment in assignments:
            self.delete(assignment.id)
        return True

    def delete(self, entity_id: int) -> bool:
        """
        Delete an assignment (soft delete by setting is_active to False).

        Args:
            entity_id: ID of the assignment to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When assignment deletion fails
        """
        result = self._perform_delete(entity_id)
        if result is None:
            raise ServiceError("Assignment delete failed, no assignment deleted.")
        return result

    def _perform_delete(self, entity_id: int) -> bool:
        assignment = BotAssignment.query.get(entity_id)
        if not assignment:
            raise NotFoundError("Assignment", str(entity_id))

        db.session.delete(assignment)
        db.session.commit()
        return True

    def remove_assignment(self, bot_id: int, user_id: int) -> bool:
        """
        Remove assignment between a bot and user.

        Args:
            bot_id: ID of the bot
            user_id: ID of the user

        Returns:
            True if removal was successful
        """
        result = self._perform_remove_assignment(
            bot_id,
            user_id,
        )
        return bool(result)

    def _perform_remove_assignment(self, bot_id: int, user_id: int) -> bool:
        assignment = BotAssignment.query.filter_by(
            bot_id=bot_id, user_id=user_id
        ).first()

        if not assignment:
            return False

        db.session.delete(assignment)
        db.session.commit()
        return True

    def _perform_remove_bot_for_user(self, user_id: int) -> bool:
        assignments = BotAssignment.query.filter_by(user_id=user_id).all()

        if not assignments:
            return False

        for assignment in assignments:
            db.session.delete(assignment)
        db.session.commit()
        return True
