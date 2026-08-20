from http import HTTPStatus
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from ai_server.dto.bot_assignment_dto import BotAssignmentDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.dao.database import Bot, BotAssignment, Message, Session, TokenUsage, User, db
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.exceptions.api_error import ApiError
from typing import List, Optional, Dict, Any
from ai_server.dto.user_dto import UserDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from flask import jsonify
from ai_server.decorators.singleton import singleton
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.bot_svc import BotService


logger = BotFactoryLogger()


@singleton
class UserAdminService(BaseService[UserDto]):
    """Service for managing user entities"""

    def __init__(self):
        super().__init__()
        self.bot_assignment_svc = BotAssignmentService()
        self.bot_svc = BotService()

    def user_to_dto(self, user: User) -> UserDto:
        """
        Convert User entity to UserDto.

        Args:
            user: User entity to convert

        Returns:
            UserDto representation of the user
        """
        return UserDto(
            user.id,
            user.mail,
            user.name,
            user.roles,
            user.parent_id,
            user.is_active,
            user.selected_bot_id,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )

    def register_new_user(self, mail: str, user_name: str, password: str) -> UserDto:
        """
        Register a new user with USER_ROLE.

        Args:
            mail: User email
            user_name: User name
            password: User password

        Returns:
            Created UserDto instance

        Raises:
            ServiceError: When user registration fails
        """
        data = {
            "email": mail,
            "name": user_name,
            "password": password,
            "roles": USER_ROLE,
            "is_active": True,
        }
        return self.create(data)

    def register_new_guest(self, parent_id, data) -> UserDto:
        """
        Register a new guest user.

        Args:
            parent_id: ID of the parent user
            mail: User email
            user_name: User name
            password: User password

        Returns:
            Created UserDto instance

        Raises:
            ServiceError: When guest registration fails
        """

        data["roles"] = GUEST_ROLE
        data["is_active"] = False
        data["parent_id"] = parent_id

        return self.create(data)

    def register_user(
        self,
        mail: str,
        user_name: str,
        password: str,
        roles: str,
        parent_id: int = -1,
        is_active: bool = False,
    ) -> UserDto:
        """
        Register a user with specific parameters.

        Args:
            mail: User email
            user_name: User name
            password: User password
            roles: User roles
            parent_id: ID of parent user (default -1)
            is_active: Whether user is active (default False)

        Returns:
            Created UserDto instance

        Raises:
            ServiceError: When user registration fails
        """
        user_data = {
            "email": mail,
            "name": user_name,
            "password": password,
            "roles": roles,
            "parent_id": parent_id,
            "is_active": is_active,
        }
        return self.create(user_data)

    def create(self, user_data: Dict[str, Any]) -> UserDto:
        """
        Create a new user.

        Args:
            data: User creation data

        Returns:
            Created UserDto instance

        Raises:
            ServiceError: When user creation fails
        """

        user_dto: UserDto = self._perform_create(user_data)
        # user_dto : UserDto = self._safe_execute("_perform_create", self._perform_create, user_data)
        if user_dto is None:
            raise ServiceError("User creation failed, no UserDto returned.")
        user_data["id"] = user_dto.id
        bots_ass_dto: BotAssignmentDto = self._perform_assign_bot(user_data)
        if bots_ass_dto:
            user_dto.assigned_bots = bots_ass_dto

        return user_dto

    def _perform_create(self, data: Dict[str, Any]) -> UserDto:
        password_hash = generate_password_hash(data["password"])
        new_user = User(
            name=data["name"],
            password_hash=password_hash,
            mail=data["email"],
            roles=data["roles"],
            parent_id=data.get("parent_id", -1),
            is_active=data.get("is_active", False),
        )
        db.session.add(new_user)

        db.session.commit()

        self.logger.info(
            f"User created id={new_user.id} email={data['email']} roles={data['roles']}"
        )
        return self.get_user_by_email(data["email"])

    def _perform_assign_bot(self, user_data) -> list[BotAssignmentDto]:
        user_id = int(user_data.get("id"))
        actual_assigment_datalist: list[BotAssignmentDto] = (
            self.bot_assignment_svc.get_assignments_by_user(user_id, all=True)
        )
        for assigment in actual_assigment_datalist:
            self.bot_assignment_svc.remove_assignment(
                assigment.bot_id, assigment.user_id
            )

        bot_ids: list[int] = user_data.get("assigned_bot_ids") or []
        bots_ass_dto: list[BotAssignmentDto] = []
        self.logger.debug(
            f"Updating bot assignments for user {user_id} with {len(bot_ids)} bots"
        )
        self.bot_assignment_svc._perform_remove_bot_for_user(user_id)
        for bot_id in bot_ids:
            assigment_data = {}
            assigment_data["bot_id"] = int(bot_id)
            assigment_data["assigned_by"] = int(user_data.get("parent_id"))
            assigment_data["user_id"] = user_id
            assigment_data["is_active"] = True
            bot_ass_dto = self.bot_assignment_svc._perform_create(assigment_data)
            bots_ass_dto.append(bot_ass_dto)
        return bots_ass_dto

    def get_dto_by_id(self, entity_id: int) -> UserDto:
        """
        Retrieve a user by their ID.

        Args:
            entity_id: ID of the user to retrieve

        Returns:
            UserDto instance if found

        Raises:
            ServiceError: When user retrieval fails
        """
        result = self._perform_get_by_id(entity_id)
        if result is None:
            raise ServiceError("Get user by id failed, no UserDto returned.")
        return result

    def _perform_get_by_id(self, entity_id: int) -> UserDto:
        user = User.query.filter_by(id=entity_id).first()
        if not user:
            raise NotFoundError("User", str(entity_id))

        user_dto = self.user_to_dto(user)
        self.logger.debug(f"Fetched user id={entity_id}")
        return user_dto

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get User entity by ID (for backward compatibility).

        Args:
            user_id: ID of the user to retrieve

        Returns:
            User entity if found, None otherwise

        Raises:
            ServiceError: When user retrieval fails
        """
        return self._perform_get_user_by_id(user_id)

    def _perform_get_user_by_id(self, user_id: int) -> Optional[User]:
        self.logger.debug(f"Fetching user with id: {user_id}")
        return User.query.filter_by(id=user_id).first()

    def get_user_dto_by_id(self, user_id: int) -> Optional[UserDto]:
        """
        Get UserDto by ID.

        Args:
            user_id: ID of the user to retrieve

        Returns:
            UserDto instance if found, None otherwise
        """
        try:
            return self.get_dto_by_id(user_id)
        except (ServiceError, NotFoundError):
            self.logger.debug(f"get_user_dto_by_id: user {user_id} not found")
            return None

    def get_all(self, caller_id: int) -> List[UserDto]:
        """
        Retrieve all non-Admin users -- authorize_user_scope() 403s on
        Admin targets for every action this list feeds into (role change,
        delete, bot assignment...), so Admin rows (including the caller's
        own) are left out entirely rather than shown and then rejected on
        click.

        Returns:
            List of UserDto instances

        Raises:
            ServiceError: When user retrieval fails
        """
        result = self._perform_get_all(caller_id)
        if result is None:
            raise ServiceError("User get_all failed, no list returned.")
        return result

    def _perform_get_all(self, caller_id: int) -> List[UserDto]:
        users: List[User] = User.query.filter(User.roles != ADMIN_ROLE).all()
        # user_to_dto() alone leaves assigned_bots at its dataclass default
        # ([]) -- the admin "All users" list needs it populated the same way
        # _perform_get_children() already does, so its bot-assignment column
        # isn't blank for every row regardless of actual assignments.
        dtos = [self._get_assignated_bots(user) for user in users]
        for dto, user in zip(dtos, users):
            # parent_email, not just parent_id: this feeds the "All users"
            # table's Parent column directly, and the parent itself may be
            # an Admin (excluded from `users` above), so the frontend can't
            # always resolve it by matching parent_id against this same list.
            if user.parent_id and user.parent_id != -1:
                parent = User.query.filter_by(id=user.parent_id).first()
                dto.parent_email = parent.mail if parent else None
            # owned_bots_count: distinct from assigned_bots (dto.assigned_bots
            # is bots *assigned to* this account, e.g. to a Guest by its
            # parent). A User creates/owns bots directly (Bot.user_account_id),
            # which is a completely different relationship -- the "Bots"
            # column shows one or the other depending on role.
            if user.roles == USER_ROLE:
                dto.owned_bots_count = Bot.query.filter_by(
                    user_account_id=user.id
                ).count()
        self.logger.debug(f"get_all users: caller_id={caller_id} count={len(dtos)}")
        return dtos

    def get_all_users(self, caller_id: int) -> List[UserDto]:
        """
        Get all users (for backward compatibility).

        Returns:
            List of UserDto instances

        Raises:
            ServiceError: When user retrieval fails
        """
        return self.get_all(caller_id)

    def update(self, user_id: int, user_data: Dict[str, Any]) -> UserDto:
        """
        Update user information.

        Args:
            user_id: ID of the user to update
            data: Fields to update

        Returns:
            Updated UserDto instance

        Raises:
            ServiceError: When user update fails
        """
        user_dto: UserDto = self._perform_update(
            user_id,
            user_data,
        )
        if user_dto is None:
            raise ServiceError("User update failed, no UserDto returned.")

        user_data["id"] = user_dto.id
        user_data["parent_id"] = user_dto.parent_id

        # bots_ass_dto: BotAssignmentDto = self._safe_execute("_perform_assign_bot", self._perform_assign_bot, user_data)
        # if bots_ass_dto:
        #     user_dto.assigned_bots = bots_ass_dto
        return user_dto

    def _perform_update(self, user_id: int, data: Dict[str, Any]) -> UserDto:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            raise NotFoundError("User", str(user_id))

        # UserUpdateRequest's "email" field maps to the User model's "mail"
        # column (user_to_dto already does the reverse, user.mail -> "email",
        # on the read side) -- without this, hasattr(user, "email") is always
        # False (there's no such attribute), so the loop below silently
        # skipped every email update instead of applying it.
        update_fields = dict(data)
        if "email" in update_fields:
            update_fields["mail"] = update_fields.pop("email")

        for key, value in update_fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
            elif not hasattr(user, key):
                self.logger.debug(
                    f"User {user_id} update: ignoring unknown field '{key}'"
                )

        db.session.commit()
        self.logger.info(f"User {user_id} updated fields={list(update_fields.keys())}")
        return self.user_to_dto(user)

    def patch_user(self, parent_id: int, guest_id: int, data: dict) -> UserDto:
        user_dto = self._perform_patch_user(
            parent_id,
            guest_id,
            data,
        )
        if user_dto is None:
            raise ServiceError("Patch user failed.")
        return user_dto

    def _perform_patch_user(self, parent_id, guest_id: int, data: dict) -> UserDto:
        parent_user: User = User.query.filter_by(id=parent_id).first()
        if not parent_user:
            raise NotFoundError("parent-user", str(parent_id))

        # Update fields with specific logic (keeping original print statements for debugging)
        if selected_bot_id := data.get("selected_bot_id"):
            bot = self.bot_svc.get_dto_by_id(selected_bot_id)
            if not bot:
                raise NotFoundError("Selected Bot", str(selected_bot_id))
            parent_user.selected_bot_id = selected_bot_id
            self.logger.info(
                f"User {parent_id} selected_bot_id set to {selected_bot_id}"
            )

        user_dto: UserDto = self.user_to_dto(parent_user)

        if "assigned_bot_ids" in data:
            assigned_bot_ids = data.get("assigned_bot_ids")
            user_data = {
                "id": guest_id,
                "parent_id": parent_id,
                "assigned_bot_ids": assigned_bot_ids,
            }
            bots_ass_dto = self._perform_assign_bot(user_data)
            if bots_ass_dto:
                user_dto.assigned_bots = bots_ass_dto
        db.session.commit()
        return user_dto

    def delete(self, entity_id: int) -> bool:
        """
        Delete a user.

        Args:
            entity_id: ID of the user to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When user deletion fails
        """
        result = self._perform_delete(entity_id)
        if result is None:
            raise ServiceError("User delete failed, no user deleted.")
        return result

    def _perform_delete(self, entity_id: int) -> bool:
        user = User.query.filter_by(id=entity_id).first()
        if not user:
            raise NotFoundError("User", str(entity_id))

        # Check for children users
        children = User.query.filter_by(parent_id=entity_id).all()
        if children:
            self.logger.warning(
                f"delete user {entity_id} rejected: {len(children)} child user(s) still attached"
            )
            raise ServiceError(
                "Cannot delete user with children. Please delete or reassign children first."
            )

        # Session.user_id, TokenUsage.user_id, BotAssignment.user_id/
        # assigned_by and Bot.user_account_id are all real FKs to
        # user_account.id with no ondelete=CASCADE -- deleting a user who
        # has ever chatted, been assigned a bot, or owns a bot used to 500
        # with a raw IntegrityError instead of actually deleting anything.
        # Deleted in dependency order (children before parents), same as
        # server/test/factories.py's registry for the same reason: Message
        # references session_id, so sessions must go after their messages.
        session_ids = [
            row.id for row in Session.query.filter_by(user_id=entity_id).all()
        ]
        self.logger.info(
            f"Deleting user {entity_id}: cascading {len(session_ids)} session(s), "
            "their messages, token usage, bot assignments and owned bots"
        )
        if session_ids:
            Message.query.filter(Message.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
        Session.query.filter_by(user_id=entity_id).delete(synchronize_session=False)
        TokenUsage.query.filter_by(user_id=entity_id).delete(synchronize_session=False)
        BotAssignment.query.filter(
            (BotAssignment.user_id == entity_id)
            | (BotAssignment.assigned_by == entity_id)
        ).delete(synchronize_session=False)
        # Bot's own children (BotParameters/BotAvatar/Knowledge) do have
        # ondelete=CASCADE, so removing the Bot rows here is enough for them.
        Bot.query.filter_by(user_account_id=entity_id).delete(synchronize_session=False)

        db.session.delete(user)
        db.session.commit()
        self.logger.info(f"User {entity_id} deleted successfully")
        return True

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user (for backward compatibility).

        Args:
            user_id: ID of the user to delete

        Returns:
            True if deletion was successful

        Raises:
            ApiError: When user deletion fails
        """
        try:
            return self.delete(user_id)
        except ServiceError as e:
            if "children" in str(e):
                self.logger.warning(f"delete_user({user_id}) blocked: has children")
                raise ApiError(
                    "Cannot delete user with children. Please delete or reassign children first.",
                    400,
                )
            self.logger.warning(f"delete_user({user_id}) failed: {e}")
            raise ApiError("User not found", 404)
        except NotFoundError:
            self.logger.warning(f"delete_user({user_id}) failed: user not found")
            raise ApiError("User not found", 404)

    def get_user_by_email(self, email: str) -> Optional[UserDto]:
        """
        Get user by email.

        Args:
            email: Email to search for

        Returns:
            UserDto instance if found, None otherwise

        Raises:
            ServiceError: When user retrieval fails
        """
        return self._perform_get_by_email(email)

    def _perform_get_by_email(self, email: str) -> Optional[UserDto]:
        self.logger.debug(f"Fetching user by email: {email}")
        user = User.query.filter_by(mail=email).first()
        if user:
            return self.user_to_dto(user)
        return None

    def get_users_by_role(self, role: str, caller_id: int) -> List[UserDto]:
        """
        Get all users with a specific role, excluding every Admin account
        other than the caller's own (same rule as get_all() -- this route
        accepts role=Admin same as any other, and would otherwise be a
        second, unfiltered way to list every Admin in the system).

        Args:
            role: Role to filter by

        Returns:
            List of UserDto instances with the specified role

        Raises:
            ServiceError: When user retrieval fails
        """
        result = self._perform_get_by_role(role, caller_id)
        if result is None:
            raise ServiceError("Get users by role failed.")
        return result

    def _perform_get_by_role(self, role: str, caller_id: int) -> List[UserDto]:
        users = User.query.filter(
            User.roles.contains(role),
            or_(User.roles != ADMIN_ROLE, User.id == int(caller_id)),
        ).all()
        dtos = [self.user_to_dto(user) for user in users]
        self.logger.debug(f"get_users_by_role role={role} caller_id={caller_id} count={len(dtos)}")
        return dtos

    def get_children_users_count(self, parent_id: int) -> List[UserDto]:
        """
        Get count of all child users of a parent.

        Args:
            parent_id: ID of the parent user

        Returns:
            Count of child users

        Raises:
            ServiceError: When user retrieval fails
        """
        result = self._perform_get_children_count(parent_id)
        if result is None:
            raise ServiceError("Get children users count failed.")
        return result

    def get_children_users(self, parent_id: int) -> List[UserDto]:
        """
        Get all child users of a parent.

        Args:
            parent_id: ID of the parent user

        Returns:
            List of UserDto instances that are children of the parent

        Raises:
            ServiceError: When user retrieval fails
        """
        result = self._perform_get_children(parent_id)
        if result is None:
            raise ServiceError("Get children users failed.")
        return result

    def _perform_get_children(self, parent_id: int) -> List[UserDto]:
        users = User.query.filter_by(parent_id=parent_id).all()

        dtos = [self._get_assignated_bots(user) for user in users]
        self.logger.debug(f"get_children_users parent_id={parent_id} count={len(dtos)}")
        return dtos

    def _get_assignated_bots(self, user) -> List[UserDto]:
        user_dto = self.user_to_dto(user)
        user_dto.assigned_bots = self.bot_assignment_svc.get_assignments_by_user(
            user.id, all=True
        )
        return user_dto

    def change_user_role(self, user_id: int, new_role: str) -> UserDto:
        """
        Change user role.

        Args:
            user_id: ID of the user
            new_role: New role to assign

        Returns:
            Updated UserDto instance

        Raises:
            ServiceError: When role change fails
        """
        result = self._perform_change_role(
            user_id,
            new_role,
        )
        if result is None:
            raise ServiceError("Change user role failed.")
        return result

    def _perform_change_role(self, user_id: int, new_role: str) -> UserDto:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            self.logger.warning(f"change_role({user_id}) failed: user not found")
            raise ApiError("User not found", 404)

        old_role = user.roles
        user.roles = new_role
        db.session.commit()
        self.logger.info(f"User {user_id} role changed: {old_role} -> {new_role}")
        return self.user_to_dto(user)

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: ID of the user
            old_password: Current password
            new_password: New password

        Returns:
            True if password was changed successfully

        Raises:
            ServiceError: When password change fails
        """
        result = self._perform_change_password(
            user_id,
            old_password,
            new_password,
        )
        if result is None:
            raise ServiceError("Change password failed.")
        return result

    def _perform_change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            self.logger.warning(f"change_password({user_id}) failed: user not found")
            raise ApiError("User not found", 404)

        if not check_password_hash(user.password_hash, old_password):
            # Never log password/hash values, only the outcome.
            self.logger.warning(f"change_password({user_id}) failed: invalid old password")
            raise ApiError("Invalid old password", 401)

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        self.logger.info(f"Password changed for user {user_id}")
        return True

    def deactivate_user(self, user_id: int) -> UserDto:
        """
        Deactivate a user account.

        Args:
            user_id: ID of the user to deactivate

        Returns:
            Updated UserDto instance

        Raises:
            ServiceError: When user deactivation fails
        """
        result = self._perform_deactivate(user_id)
        if result is None:
            raise ServiceError("Deactivate user failed.")
        return result

    def _perform_deactivate(self, user_id: int) -> UserDto:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            self.logger.warning(f"deactivate_user({user_id}) failed: user not found")
            raise ApiError("User not found", 404)

        was_active = user.is_active
        user.is_active = False
        db.session.commit()
        self.logger.info(f"User {user_id} deactivated (was_active={was_active})")
        return self.user_to_dto(user)

    def activate_user(self, user_id: int) -> UserDto:
        """
        Activate a user account.

        Args:
            user_id: ID of the user to activate

        Returns:
            Updated UserDto instance

        Raises:
            ServiceError: When user activation fails
        """
        result = self._perform_activate(user_id)
        if result is None:
            raise ServiceError("Activate user failed.")
        return result

    def _perform_activate(self, user_id: int) -> UserDto:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            self.logger.warning(f"activate_user({user_id}) failed: user not found")
            raise ApiError("User not found", 404)

        was_active = user.is_active
        user.is_active = True
        db.session.commit()
        self.logger.info(f"User {user_id} activated (was_active={was_active})")
        return self.user_to_dto(user)

    def reassign_children(self, old_parent_id: int, new_parent_id: int) -> bool:
        """
        Reassign all children from one parent to another.

        Args:
            old_parent_id: ID of the current parent
            new_parent_id: ID of the new parent

        Returns:
            True if reassignment was successful

        Raises:
            ServiceError: When reassignment fails
        """
        result = self._perform_reassign_children(
            old_parent_id,
            new_parent_id,
        )
        if result is None:
            raise ServiceError("Reassign children failed.")
        return result

    def _perform_reassign_children(
        self, old_parent_id: int, new_parent_id: int
    ) -> bool:
        children_dtos = self.get_children_users(old_parent_id)
        new_parent = User.query.filter_by(id=new_parent_id).first()

        if not new_parent:
            self.logger.warning(
                f"reassign_children({old_parent_id} -> {new_parent_id}) failed: new parent not found"
            )
            raise ApiError("New parent user not found", 404)

        # Update children's parent_id
        reassigned_count = 0
        skipped_count = 0
        for child_dto in children_dtos:
            child = User.query.filter_by(id=child_dto.id).first()
            if child:
                child.parent_id = new_parent_id
                reassigned_count += 1
            else:
                skipped_count += 1

        db.session.commit()
        self.logger.info(
            f"Reassigned {reassigned_count} child(ren) from parent {old_parent_id} "
            f"to {new_parent_id}"
            + (f", {skipped_count} skipped (not found)" if skipped_count else "")
        )
        return True

    @staticmethod
    def get_selected_bot(user_id: int):
        """
        Get selected bot for a user (static method for backward compatibility).

        Args:
            user_id: ID of the user

        Returns:
            JSON response with selected bot information
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"get_selected_bot({user_id}) failed: user not found")
                return jsonify({"error": "User not found"}), 404

            if not user.selected_bot_id:
                return jsonify({"selected_bot_id": None, "bot": None}), 200

            bot = Bot.query.get(user.selected_bot_id)
            if not bot:
                return jsonify(
                    {"selected_bot_id": user.selected_bot_id, "bot": None}
                ), 200

            return jsonify(
                {
                    "selected_bot_id": user.selected_bot_id,
                    "bot": {
                        "id": bot.id,
                        "bot_name": bot.bot_name,
                        "prompt": bot.prompt,
                    },
                }
            ), 200
        except Exception as exc:
            logger.exception(f"Error retrieving selected bot for user {user_id}: {exc}")
            return jsonify({"error": "Internal server error"}), 500
