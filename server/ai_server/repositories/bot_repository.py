from typing import Optional, Sequence

from sqlalchemy import delete, func, select

from ai_server.models import Bot
from ai_server.repositories.base import BaseRepository


class BotRepository(BaseRepository):
    def add(self, bot: Bot) -> None:
        self.session.add(bot)

    async def delete(self, bot: Bot) -> None:
        """Bot's own children (BotParameters/BotAvatar/Knowledge/
        BotAssignment rows) go with it through ondelete=CASCADE."""
        await self.session.delete(bot)

    async def get(self, bot_id: int) -> Optional[Bot]:
        return await self.session.get(Bot, bot_id)

    async def list_all(self) -> Sequence[Bot]:
        return (await self.session.execute(select(Bot))).scalars().all()

    async def list_by_owner(self, user_id: int) -> Sequence[Bot]:
        stmt = select(Bot).where(Bot.user_account_id == user_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def count_by_owner(self, user_id: int) -> int:
        stmt = (
            select(func.count()).select_from(Bot).where(Bot.user_account_id == user_id)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def delete_by_owner(self, user_id: int) -> None:
        """Same cascade as delete()."""
        await self.session.execute(delete(Bot).where(Bot.user_account_id == user_id))
