from typing import Optional

from sqlalchemy import select

from ai_server.models import BotParameters
from ai_server.repositories.base import BaseRepository


class BotParametersRepository(BaseRepository):
    def add(self, bot_parameters: BotParameters) -> None:
        self.session.add(bot_parameters)

    async def delete(self, bot_parameters: BotParameters) -> None:
        await self.session.delete(bot_parameters)

    async def get_by_bot_id(self, bot_id: int) -> Optional[BotParameters]:
        stmt = select(BotParameters).where(BotParameters.bot_id == bot_id)
        return (await self.session.execute(stmt)).scalars().first()
