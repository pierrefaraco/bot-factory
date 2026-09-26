from typing import Optional

from ai_server.models import Bot
from ai_server.repositories.base import BaseRepository


class BotRepository(BaseRepository):
    """Only what already-migrated aggregates need so far; the rest of the
    Bot queries still live in bot_svc.py until that aggregate migrates."""

    async def get(self, bot_id: int) -> Optional[Bot]:
        return await self.session.get(Bot, bot_id)
