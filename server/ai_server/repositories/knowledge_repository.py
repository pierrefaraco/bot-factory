from typing import Optional, Sequence

from sqlalchemy import delete, select

from ai_server.models import Knowledge
from ai_server.repositories.base import BaseRepository


class KnowledgeRepository(BaseRepository):
    """A bot's knowledge chapters. Chapters form a tree per bot:
    knowledge_dad_id holds the parent's children_ref_id (or
    ROOT_CHAPTER_ID). Those ids are NOT unique across bots -- every root
    chapter shares ROOT_CHAPTER_ID, and importing the same exported tree
    into two bots duplicates its children_ref_ids -- so every tree query
    here is scoped by bot_id."""

    def add(self, knowledge: Knowledge) -> None:
        self.session.add(knowledge)

    async def delete(self, knowledge: Knowledge) -> None:
        await self.session.delete(knowledge)

    async def get(self, knowledge_id: int) -> Optional[Knowledge]:
        return await self.session.get(Knowledge, knowledge_id)

    async def get_for_bot(self, bot_id: int, knowledge_id: int) -> Optional[Knowledge]:
        stmt = select(Knowledge).where(
            Knowledge.id == knowledge_id, Knowledge.bot_id == bot_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_bot(self, bot_id: int) -> Sequence[Knowledge]:
        stmt = select(Knowledge).where(Knowledge.bot_id == bot_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def list_children(
        self, bot_id: int, knowledge_dad_id: str
    ) -> Sequence[Knowledge]:
        """bot_id's chapters directly under knowledge_dad_id."""
        stmt = select(Knowledge).where(
            Knowledge.bot_id == bot_id, Knowledge.knowledge_dad_id == knowledge_dad_id
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def delete_for_bot(self, bot_id: int) -> int:
        """Returns the number of deleted chapters."""
        result = await self.session.execute(
            delete(Knowledge).where(Knowledge.bot_id == bot_id)
        )
        return result.rowcount
