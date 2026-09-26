from typing import List, Optional, Dict, Any

from starlette.concurrency import run_in_threadpool
from werkzeug.security import generate_password_hash, check_password_hash

from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.models import User
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.exceptions.api_error import ApiError
from ai_server.dto.user_dto import UserDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.repositories import (
    BotAssignmentRepository,
    BotRepository,
    ConversationRepository,
    TokenUsageRepository,
    UserRepository,
)
from ai_server.services.base_service import BaseService
from ai_server.services.bot_assignment_svc import BotAssignmentService


logger = BotFactoryLogger()


class UserAdminService(BaseService[UserDto]):
    """Service for managing user entities.

    Password hashing/checking (werkzeug's generate_password_hash/
    check_password_hash) is deliberately CPU-heavy: it always runs through
    run_in_threadpool, so it never blocks the event loop while the rest of
    each use case stays plain async."""

    def __init__(
        self,
        bot_assignment_svc: BotAssignmentService,
        user_repo: UserRepository,
        bot_repo: BotRepository,
        conversation_repo: ConversationRepository,
        token_usage_repo: TokenUsageRepository,
        bot_assignment_repo: BotAssignmentRepository,
    ):
        super().__init__()
        self.bot_assignment_svc = bot_assignment_svc
        self.user_repo = user_repo
        self.bot_repo = bot_repo
        self.conversation_repo = conversation_repo
        self.token_usage_repo = token_usage_repo
        self.bot_assignment_repo = bot_assignment_repo

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

    async def _get_user_or_404(self, user_id: int, action: str) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            self.logger.warning(f"{action}({user_id}) failed: user not found")
            raise ApiError("User not found", 404)
        return user

    async def register_new_user(
        self, mail: str, user_name: str, password: str
    ) -> UserDto:
        """
        Register a new, active user with USER_ROLE.

        Returns:
            Created UserDto instance
        """
        data = {
            "email": mail,
            "name": user_name,
            "password": password,
            "roles": USER_ROLE,
            "is_active": True,
        }
        return await self.create(data)

    async def register_new_guest(self, parent_id, data) -> UserDto:
        """
        Register a new (inactive) guest user of parent_id; data may carry
        assigned_bot_ids.

        Returns:
            Created UserDto instance
        """
        data["roles"] = GUEST_ROLE
        data["is_active"] = False
        data["parent_id"] = parent_id

        return await self.create(data)

    async def register_user(
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

        Returns:
            Created UserDto instance
        """
        user_data = {
            "email": mail,
            "name": user_name,
            "password": password,
            "roles": roles,
            "parent_id": parent_id,
            "is_active": is_active,
        }
        return await self.create(user_data)

    async def create(self, user_data: Dict[str, Any]) -> UserDto:
        """
        Create a new user, and assign it user_data["assigned_bot_ids"] if
        any -- in one transaction: a rejected bot creates no user at all.

        Returns:
            Created UserDto instance
        """
        password_hash = await run_in_threadpool(
            generate_password_hash, user_data["password"]
        )
        user = User(
            name=user_data["name"],
            password_hash=password_hash,
            mail=user_data["email"],
            roles=user_data["roles"],
            parent_id=int(user_data.get("parent_id", -1)),
            is_active=user_data.get("is_active", False),
        )
        self.user_repo.add(user)
        await self.user_repo.flush()
        user_dto = self.user_to_dto(user)

        bot_ids = user_data.get("assigned_bot_ids") or []
        if bot_ids:
            user_dto.assigned_bots = (
                await self.bot_assignment_svc.replace_user_assignments(
                    user.id, int(user_data["parent_id"]), bot_ids
                )
            )

        await self.user_repo.commit()
        self.logger.info(
            f"User created id={user.id} email={user_data['email']} roles={user_data['roles']}"
        )
        return user_dto

    async def get_dto_by_id(self, entity_id: int) -> UserDto:
        """
        Retrieve a user by their ID.

        Raises:
            NotFoundError: When the user does not exist
        """
        user = await self.user_repo.get(entity_id)
        if not user:
            raise NotFoundError("User", str(entity_id))
        self.logger.debug(f"Fetched user id={entity_id}")
        return self.user_to_dto(user)

    async def get_user_dto_by_id(self, user_id: int) -> Optional[UserDto]:
        """
        Get UserDto by ID, None if not found.
        """
        try:
            return await self.get_dto_by_id(user_id)
        except NotFoundError:
            self.logger.debug(f"get_user_dto_by_id: user {user_id} not found")
            return None

    async def get_user_by_email(self, email: str) -> Optional[UserDto]:
        """
        Get user by email, None if not found.
        """
        self.logger.debug(f"Fetching user by email: {email}")
        user = await self.user_repo.get_by_email(email)
        return self.user_to_dto(user) if user else None

    async def get_all(self, caller_id: int) -> List[UserDto]:
        """
        Retrieve all non-Admin users -- authorize_user_scope() 403s on
        Admin targets for every action this list feeds into (role change,
        delete, bot assignment...), so Admin rows (including the caller's
        own) are left out entirely rather than shown and then rejected on
        click.

        Returns:
            List of UserDto instances
        """
        users = await self.user_repo.list_non_admins()
        # user_to_dto() alone leaves assigned_bots at its dataclass default
        # ([]) -- the admin "All users" list needs it populated the same way
        # get_children_users() already does, so its bot-assignment column
        # isn't blank for every row regardless of actual assignments.
        dtos = [await self._get_assignated_bots(user) for user in users]
        for dto, user in zip(dtos, users):
            # parent_email, not just parent_id: this feeds the "All users"
            # table's Parent column directly, and the parent itself may be
            # an Admin (excluded from `users` above), so the frontend can't
            # always resolve it by matching parent_id against this same list.
            if user.parent_id and user.parent_id != -1:
                parent = await self.user_repo.get(user.parent_id)
                dto.parent_email = parent.mail if parent else None
            # owned_bots_count: distinct from assigned_bots (dto.assigned_bots
            # is bots *assigned to* this account, e.g. to a Guest by its
            # parent). A User creates/owns bots directly (Bot.user_account_id),
            # which is a completely different relationship -- the "Bots"
            # column shows one or the other depending on role.
            if user.roles == USER_ROLE:
                dto.owned_bots_count = await self.bot_repo.count_by_owner(user.id)
        self.logger.debug(f"get_all users: caller_id={caller_id} count={len(dtos)}")
        return dtos

    async def get_all_users(self, caller_id: int) -> List[UserDto]:
        """
        Get all users (for backward compatibility).
        """
        return await self.get_all(caller_id)

    async def update(self, user_id: int, user_data: Dict[str, Any]) -> UserDto:
        """
        Update user information.

        Raises:
            NotFoundError: When the user does not exist
        """
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))

        # UserUpdateRequest's "email" field maps to the User model's "mail"
        # column (user_to_dto already does the reverse, user.mail -> "email",
        # on the read side) -- without this, hasattr(user, "email") is always
        # False (there's no such attribute), so the loop below silently
        # skipped every email update instead of applying it.
        update_fields = dict(user_data)
        if "email" in update_fields:
            update_fields["mail"] = update_fields.pop("email")

        for key, value in update_fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
            elif not hasattr(user, key):
                self.logger.debug(
                    f"User {user_id} update: ignoring unknown field '{key}'"
                )

        await self.user_repo.commit()
        self.logger.info(f"User {user_id} updated fields={list(update_fields.keys())}")
        return self.user_to_dto(user)

    async def patch_user(self, parent_id: int, guest_id: int, data: dict) -> UserDto:
        """
        Set parent_id's selected bot and/or replace guest_id's assigned
        bots, in one transaction.

        Raises:
            NotFoundError: When the parent user or the selected bot does not exist
        """
        parent_user = await self.user_repo.get(parent_id)
        if not parent_user:
            raise NotFoundError("parent-user", str(parent_id))

        if selected_bot_id := data.get("selected_bot_id"):
            if not await self.bot_repo.get(selected_bot_id):
                raise NotFoundError("Selected Bot", str(selected_bot_id))
            parent_user.selected_bot_id = selected_bot_id
            self.logger.info(
                f"User {parent_id} selected_bot_id set to {selected_bot_id}"
            )

        user_dto: UserDto = self.user_to_dto(parent_user)

        if "assigned_bot_ids" in data:
            bots_ass_dto = await self.bot_assignment_svc.replace_user_assignments(
                guest_id, parent_id, data.get("assigned_bot_ids") or []
            )
            if bots_ass_dto:
                user_dto.assigned_bots = bots_ass_dto
        await self.user_repo.commit()
        return user_dto

    async def select_bot(self, user_id: int, bot_id: int) -> bool:
        """Set user_id's selected bot (bot_id is not checked). False if the
        user does not exist."""
        user = await self.user_repo.get(user_id)
        if not user:
            return False
        user.selected_bot_id = bot_id
        await self.user_repo.commit()
        return True

    async def get_selected_bot(self, user_id: int) -> dict:
        """The asymmetric response shapes (some branches include a "bot"
        key, the final one doesn't) are the original route's own behavior,
        kept verbatim."""
        user = await self.user_repo.get(user_id)
        if not user.selected_bot_id:
            self.logger.info(f"get_selected_bot({user_id}) succeeded: no bot selected")
            return {"selected_bot_id": None, "bot": None}

        if not await self.bot_repo.get(user.selected_bot_id):
            self.logger.warning(
                f"get_selected_bot({user_id}) selected_bot_id={user.selected_bot_id} not found"
            )
            return {"selected_bot_id": user.selected_bot_id, "bot": None}

        self.logger.info(
            f"get_selected_bot({user_id}) succeeded selected_bot_id={user.selected_bot_id}"
        )
        return {"selected_bot_id": user.selected_bot_id}

    async def delete(self, entity_id: int) -> bool:
        """
        Delete a user and everything that references it.

        Raises:
            NotFoundError: When the user does not exist
            ServiceError: When the user still has children
        """
        user = await self.user_repo.get(entity_id)
        if not user:
            raise NotFoundError("User", str(entity_id))

        children = await self.user_repo.list_children(entity_id)
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
        # server/test/factories.py's registry for the same reason.
        session_count = await self.conversation_repo.delete_for_user(entity_id)
        self.logger.info(
            f"Deleting user {entity_id}: cascaded {session_count} session(s), "
            "their messages, token usage, bot assignments and owned bots"
        )
        await self.token_usage_repo.delete_by_user_id(entity_id)
        await self.bot_assignment_repo.delete_involving_user(entity_id)
        await self.bot_repo.delete_by_owner(entity_id)

        await self.user_repo.delete(user)
        await self.user_repo.commit()
        self.logger.info(f"User {entity_id} deleted successfully")
        return True

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user, mapping service errors to API errors.

        Raises:
            ApiError: When user deletion fails
        """
        try:
            return await self.delete(user_id)
        except NotFoundError:
            self.logger.warning(f"delete_user({user_id}) failed: user not found")
            raise ApiError("User not found", 404)
        except ServiceError as e:
            if "children" in str(e):
                self.logger.warning(f"delete_user({user_id}) blocked: has children")
                raise ApiError(
                    "Cannot delete user with children. Please delete or reassign children first.",
                    400,
                )
            self.logger.warning(f"delete_user({user_id}) failed: {e}")
            raise ApiError("User not found", 404)

    async def get_users_by_role(self, role: str, caller_id: int) -> List[UserDto]:
        """
        Get all users with a specific role, excluding every Admin account
        other than the caller's own (same rule as get_all() -- this route
        accepts role=Admin same as any other, and would otherwise be a
        second, unfiltered way to list every Admin in the system).
        """
        users = await self.user_repo.list_by_role(role, int(caller_id))
        dtos = [self.user_to_dto(user) for user in users]
        self.logger.debug(
            f"get_users_by_role role={role} caller_id={caller_id} count={len(dtos)}"
        )
        return dtos

    async def get_children_users(self, parent_id: int) -> List[UserDto]:
        """
        Get all child users of a parent, with their assigned bots.
        """
        users = await self.user_repo.list_children(parent_id)
        dtos = [await self._get_assignated_bots(user) for user in users]
        self.logger.debug(f"get_children_users parent_id={parent_id} count={len(dtos)}")
        return dtos

    async def _get_assignated_bots(self, user) -> UserDto:
        user_dto = self.user_to_dto(user)
        user_dto.assigned_bots = await self.bot_assignment_svc.get_assignments_by_user(
            user.id, include_inactive=True
        )
        return user_dto

    async def change_user_role(self, user_id: int, new_role: str) -> UserDto:
        """
        Change user role.

        Raises:
            ApiError: 404 when the user does not exist
        """
        user = await self._get_user_or_404(user_id, "change_role")
        old_role = user.roles
        user.roles = new_role
        await self.user_repo.commit()
        self.logger.info(f"User {user_id} role changed: {old_role} -> {new_role}")
        return self.user_to_dto(user)

    async def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Raises:
            ApiError: 404 when the user does not exist, 401 on a wrong old password
        """
        user = await self._get_user_or_404(user_id, "change_password")

        if not await run_in_threadpool(
            check_password_hash, user.password_hash, old_password
        ):
            # Never log password/hash values, only the outcome.
            self.logger.warning(
                f"change_password({user_id}) failed: invalid old password"
            )
            raise ApiError("Invalid old password", 401)

        user.password_hash = await run_in_threadpool(
            generate_password_hash, new_password
        )
        await self.user_repo.commit()
        self.logger.info(f"Password changed for user {user_id}")
        return True

    async def deactivate_user(self, user_id: int) -> UserDto:
        """
        Deactivate a user account.

        Raises:
            ApiError: 404 when the user does not exist
        """
        user = await self._get_user_or_404(user_id, "deactivate_user")
        was_active = user.is_active
        user.is_active = False
        await self.user_repo.commit()
        self.logger.info(f"User {user_id} deactivated (was_active={was_active})")
        return self.user_to_dto(user)

    async def activate_user(self, user_id: int) -> UserDto:
        """
        Activate a user account.

        Raises:
            ApiError: 404 when the user does not exist
        """
        user = await self._get_user_or_404(user_id, "activate_user")
        was_active = user.is_active
        user.is_active = True
        await self.user_repo.commit()
        self.logger.info(f"User {user_id} activated (was_active={was_active})")
        return self.user_to_dto(user)

    async def reassign_children(self, old_parent_id: int, new_parent_id: int) -> bool:
        """
        Reassign all children from one parent to another.

        Raises:
            ApiError: 404 when the new parent does not exist
        """
        children = await self.user_repo.list_children(old_parent_id)
        if not await self.user_repo.get(new_parent_id):
            self.logger.warning(
                f"reassign_children({old_parent_id} -> {new_parent_id}) failed: new parent not found"
            )
            raise ApiError("New parent user not found", 404)

        for child in children:
            child.parent_id = new_parent_id
        await self.user_repo.commit()
        self.logger.info(
            f"Reassigned {len(children)} child(ren) from parent {old_parent_id} "
            f"to {new_parent_id}"
        )
        return True

    async def authorize_user_scope(
        self, caller_id, target_id: int, allow_self: bool = True
    ) -> None:
        """Raises ApiError unless the caller may act on target_id -- the
        shared "own it or be admin" check of every guest/<id> + admin/<id>
        route.

        - allow_self and target_id is the caller's own id: allowed (including
          an Admin acting on themselves).
        - target_id belongs to another Admin: always 403, even for an Admin
          caller -- peer admin accounts are out of scope for this whole route
          family (role change, delete, activate/deactivate, bot assignment...).
        - ADMIN (any other target): unrestricted.
        - USER: allowed only if target_id is one of their guests
          (target.parent_id == caller_id).
        - Anything else: 403.
        """
        caller = await self.user_repo.get(int(caller_id))
        if not caller:
            raise ApiError("User not found", status_code=401)

        if allow_self and int(caller_id) == target_id:
            return

        target = await self.user_repo.get(target_id)
        if not target:
            raise ApiError("Guest user not found", status_code=404)

        # int(target_id) != int(caller_id) here specifically, not just "any
        # Admin target": allow_self=False routes (deactivate/activate) reach
        # this point even when target_id IS the caller's own id, and an Admin
        # has always been allowed to self-service those (that's what
        # allow_self=False was gating for non-admins in the first place, via
        # the parent_id check below -- it was never meant to touch this case).
        if target.roles == ADMIN_ROLE and int(target_id) != int(caller_id):
            raise ApiError(
                f"Unable to act on user {target_id} - target is an Admin",
                status_code=403,
            )

        if caller.roles == ADMIN_ROLE:
            return

        if target.parent_id == int(caller_id):
            return

        raise ApiError(
            f"Unable to access user {target_id} - not your guest", status_code=403
        )
