from typing import Optional

from sqlalchemy import delete, func, select

from ai_server.models import Bot
from ai_server.repositories.base import BaseRepository


class BotRepository(BaseRepository):
    """Only what already-migrated aggregates need so far; the rest of the
    Bot queries still live in bot_svc.py until that aggregate migrates."""

    async def get(self, bot_id: int) -> Optional[Bot]:
        return await self.session.get(Bot, bot_id)

    async def count_by_owner(self, user_id: int) -> int:
        stmt = (
            select(func.count()).select_from(Bot).where(Bot.user_account_id == user_id)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def delete_by_owner(self, user_id: int) -> None:
        """Bot's own children (BotParameters/BotAvatar/Knowledge rows) go
        with it through ondelete=CASCADE."""
        await self.session.execute(delete(Bot).where(Bot.user_account_id == user_id))
