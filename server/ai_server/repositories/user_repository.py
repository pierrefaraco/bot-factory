from typing import Optional

from ai_server.models import User
from ai_server.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Only what already-migrated aggregates need so far; the rest of the
    User queries still live in user_admin_svc.py until that aggregate
    migrates."""

    async def get(self, user_id: int) -> Optional[User]:
        return await self.session.get(User, user_id)
