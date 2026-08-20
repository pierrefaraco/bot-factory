import random
from typing import Optional, List, Dict, Any
from ai_server.dao.database import Bot, BotAvatar, db
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from ai_server.decorators.singleton import singleton


@singleton
class AvatarService(BaseService[AvatarDto]):
    """Service for managing avatar entities"""

    def __init__(self):
        super().__init__()

    def _avatar_to_dto(self, avatar: BotAvatar) -> AvatarDto:
        """
        Convert an Avatar instance to a DTO.

        Args:
            avatar: Avatar instance to convert
        """
        avatar_dto = AvatarDto()
        avatar_dto.id = avatar.id
        avatar_dto.bot_id = avatar.bot_id
        avatar_dto.body = avatar.body
        avatar_dto.body_color = avatar.body_color
        avatar_dto.hat = avatar.hat
        avatar_dto.hat_color = avatar.hat_color
        avatar_dto.eyes = avatar.eyes
        avatar_dto.eyes_color = avatar.eyes_color
        avatar_dto.mouth = avatar.mouth
        avatar_dto.mouth_color = avatar.mouth_color
        return avatar_dto

    def create_random_avatar(self, bot_id: int) -> AvatarDto:
        """
        Create a random avatar for a bot.

        Args:
            bot_id: ID of the bot owning the avatar

        Returns:
            Created AvatarDto instance

        Raises:
            ServiceError: When avatar creation fails
        """
        data = {}
        data["bot_id"] = bot_id
        data["body"] = random.randrange(15)
        data["body_color"] = random.randrange(5)
        data["hat"] = random.randrange(15)
        data["hat_color"] = random.randrange(5)
        data["eyes"] = random.randrange(7)
        data["eyes_color"] = random.randrange(5)
        data["mouth"] = random.randrange(7)
        data["mouth_color"] = random.randrange(5)
        self.logger.debug(f"Generated random avatar attributes for bot_id={bot_id}: {data}")
        return self.create(data)

    def create(self, data: Dict[str, Any]) -> AvatarDto:
        """
        Create a new avatar.

        Args:
            data: Avatar creation data containing bot_id and avatar components

        Returns:
            Created AvatarDto instance

        Raises:
            ServiceError: When avatar creation fails
        """
        self.logger.info(f"Creating avatar for bot_id={data.get('bot_id')}")
        result = self._perform_create(data)
        if result is None:
            self.logger.warning(f"Avatar creation returned no result for bot_id={data.get('bot_id')}")
            raise ServiceError("Avatar creation failed, no AvatarDto returned.")
        return result

    def _perform_create(self, data: Dict[str, Any]) -> AvatarDto:
        avatar = BotAvatar(
            bot_id=data["bot_id"],
            body=data.get("body", 0),
            body_color=data.get("body_color", 0),
            hat=data.get("hat", 0),
            hat_color=data.get("hat_color", 0),
            eyes=data.get("eyes", 0),
            eyes_color=data.get("eyes_color", 0),
            mouth=data.get("mouth", 0),
            mouth_color=data.get("mouth_color", 0),
        )
        db.session.add(avatar)
        db.session.commit()
        self.logger.info(f"Avatar created id={avatar.id} bot_id={avatar.bot_id}")
        return self._avatar_to_dto(avatar)

    def get_dto_by_id(self, entity_id: int) -> AvatarDto:
        """
        Retrieve an avatar by its ID.

        Args:
            entity_id: ID of the avatar to retrieve

        Returns:
            AvatarDto instance if found

        Raises:
            ServiceError: When avatar retrieval fails
        """
        self.logger.debug(f"Fetching avatar id={entity_id}")
        result = self._perform_get_by_id(entity_id)
        if result is None:
            raise ServiceError("Get avatar by id failed, no AvatarDto returned.")
        return result

    def _perform_get_by_id(self, entity_id: int) -> AvatarDto:
        avatar = BotAvatar.query.get(entity_id)
        if not avatar:
            self.logger.warning(f"Avatar not found id={entity_id}")
            raise NotFoundError("Avatar", str(entity_id))
        return self._avatar_to_dto(avatar)

    def get_all(self) -> List[AvatarDto]:
        """
        Retrieve all avatars.

        Returns:
            List of AvatarDto instances

        Raises:
            ServiceError: When avatar retrieval fails
        """
        result = self._perform_get_all()
        if result is None:
            raise ServiceError("Avatar get_all failed, no list returned.")
        self.logger.info(f"Retrieved {len(result)} avatars")
        return result

    def _perform_get_all(self) -> List[AvatarDto]:
        avatars: List[BotAvatar] = BotAvatar.query.filter_by().all()
        return [self._avatar_to_dto(avatar) for avatar in avatars]

    def patch_avatar(self, data: Dict[str, Any]) -> AvatarDto:
        """
        Update an avatar's information.

        Args:
            data: Fields to update

        Returns:
            Updated AvatarDto instance

        Raises:
            ServiceError: When avatar update fails
        """
        entity_id = data.get("id")
        avatar = BotAvatar.query.get(entity_id)
        if not avatar:
            self.logger.warning(f"patch_avatar: avatar not found id={entity_id}")
            raise NotFoundError("Avatar", str(entity_id))

        if body := data.get("body"):
            avatar.body = body
        if body_color := data.get("body_color"):
            avatar.body_color = body_color

        if hat := data.get("hat"):
            avatar.hat = hat
        if hat_color := data.get("hat_color"):
            avatar.hat_color = hat_color

        if eyes := data.get("eyes"):
            avatar.eyes = eyes

        if eyes_color := data.get("eyes_color"):
            avatar.eyes_color = eyes_color

        if mouth := data.get("mouth"):
            avatar.mouth = mouth
        if mouth_color := data.get("mouth_color"):
            avatar.mouth_color = mouth_color

        db.session.commit()
        self.logger.info(
            f"Avatar patched id={entity_id} fields={[k for k in data if k != 'id']}"
        )

    def update_and_return_datat(self, data: Dict[str, Any]) -> AvatarDto:
        """
        Update an avatar's information.

        Args:
            entity_id: ID of the avatar to update
            data: Fields to update

        Returns:
            Updated AvatarDto instance

        Raises:
            ServiceError: When avatar update fails
        """
        self.logger.info(f"Updating avatar id={data.get('id')}")
        result = self._perform_update(
            data.get("id"),
            data,
        )
        if result is None:
            raise ServiceError("Avatar update failed, no AvatarDto returned.")
        return result

    def _perform_update(self, entity_id: int, data: Dict[str, Any]) -> AvatarDto:
        avatar = BotAvatar.query.get(entity_id)
        if not avatar:
            self.logger.warning(f"Avatar update failed: id={entity_id} not found")
            raise NotFoundError("Avatar", str(entity_id))

        for key, value in data.items():
            if hasattr(avatar, key):
                setattr(avatar, key, value)

        db.session.commit()
        self.logger.info(f"Avatar updated id={entity_id}")
        return self._avatar_to_dto(avatar)

    def delete(self, entity_id: int) -> bool:
        """
        Delete an avatar.

        Args:
            entity_id: ID of the avatar to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When avatar deletion fails
        """
        self.logger.info(f"Deleting avatar id={entity_id}")
        result = self._perform_delete(entity_id)
        if result is None:
            raise ServiceError("Avatar delete failed, no avatar deleted.")
        return result

    def _perform_delete(self, entity_id: int) -> bool:
        avatar = BotAvatar.query.get(entity_id)
        if not avatar:
            self.logger.warning(f"Avatar delete failed: id={entity_id} not found")
            raise NotFoundError("Avatar", str(entity_id))

        db.session.delete(avatar)
        db.session.commit()
        self.logger.info(f"Avatar deleted id={entity_id}")
        return True

    def get_avatar_by_bot_id(self, bot_id: int) -> Optional[AvatarDto]:
        """
        Retrieve an avatar by its bot ID.

        Args:
            bot_id: ID of the bot owning the avatar

        Returns:
            AvatarDto instance if found, None otherwise

        Raises:
            ServiceError: When avatar retrieval fails
        """
        self.logger.debug(f"Fetching avatar for bot_id={bot_id}")
        return self._perform_get_by_bot_id(bot_id)

    def _perform_get_by_bot_id(self, bot_id: int) -> Optional[AvatarDto]:
        avatar = BotAvatar.query.filter_by(bot_id=bot_id).first()
        if avatar:
            return self._avatar_to_dto(avatar)
        # A bot legitimately may not have an avatar yet - not an error case.
        self.logger.debug(f"No avatar found for bot_id={bot_id}")
        return None

    def delete_avatar_by_bot_id(self, bot_id: int) -> bool:
        """
        Delete an avatar by its bot ID.

        Args:
            bot_id: ID of the bot owning the avatar

        Returns:
            True if deletion was successful, False if avatar not found

        Raises:
            ServiceError: When avatar deletion fails
        """
        self.logger.info(f"Deleting avatar for bot_id={bot_id}")
        result = self._perform_delete_by_bot_id(bot_id)
        if result is None:
            return False
        return result

    def _perform_delete_by_bot_id(self, bot_id: int) -> bool:
        avatar_to_delete = BotAvatar.query.filter_by(bot_id=bot_id).first()
        if not avatar_to_delete:
            self.logger.debug(f"No avatar to delete for bot_id={bot_id}")
            return False

        db.session.delete(avatar_to_delete)
        db.session.commit()
        self.logger.info(f"Avatar deleted for bot_id={bot_id}")
        return True
