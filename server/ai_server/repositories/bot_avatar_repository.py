from typing import Optional

from sqlalchemy import select

from ai_server.models import BotAvatar
from ai_server.repositories.base import BaseRepository


class BotAvatarRepository(BaseRepository):
    def add(self, avatar: BotAvatar) -> None:
        self.session.add(avatar)

    async def delete(self, avatar: BotAvatar) -> None:
        await self.session.delete(avatar)

    async def get(self, avatar_id: int) -> Optional[BotAvatar]:
        return await self.session.get(BotAvatar, avatar_id)

    async def get_by_bot_id(self, bot_id: int) -> Optional[BotAvatar]:
        stmt = select(BotAvatar).where(BotAvatar.bot_id == bot_id)
        return (await self.session.execute(stmt)).scalars().first()
