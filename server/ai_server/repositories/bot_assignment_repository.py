from typing import Optional, Sequence

from sqlalchemy import delete, select

from ai_server.models import BotAssignment
from ai_server.repositories.base import BaseRepository


class BotAssignmentRepository(BaseRepository):
    def add(self, assignment: BotAssignment) -> None:
        self.session.add(assignment)

    async def get(self, assignment_id: int) -> Optional[BotAssignment]:
        return await self.session.get(BotAssignment, assignment_id)

    async def find(
        self, bot_id: int, user_id: int, active_only: bool = False
    ) -> Optional[BotAssignment]:
        stmt = select(BotAssignment).where(
            BotAssignment.bot_id == bot_id, BotAssignment.user_id == user_id
        )
        if active_only:
            stmt = stmt.where(BotAssignment.is_active.is_(True))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(
        self, user_id: int, active_only: bool = True
    ) -> Sequence[BotAssignment]:
        stmt = select(BotAssignment).where(BotAssignment.user_id == user_id)
        if active_only:
            stmt = stmt.where(BotAssignment.is_active.is_(True))
        return (await self.session.execute(stmt)).scalars().all()

    async def list_active_by_assigner(
        self, assigned_by: int
    ) -> Sequence[BotAssignment]:
        stmt = select(BotAssignment).where(
            BotAssignment.assigned_by == assigned_by,
            BotAssignment.is_active.is_(True),
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def delete(self, assignment: BotAssignment) -> None:
        await self.session.delete(assignment)

    async def delete_for_user(self, user_id: int) -> None:
        """Every assignment of user_id, active or not -- issued right away,
        so rows added afterwards in the same transaction are unaffected."""
        await self.session.execute(
            delete(BotAssignment).where(BotAssignment.user_id == user_id)
        )

    async def delete_involving_user(self, user_id: int) -> None:
        """Assignments where user_id is either the assignee or the assigner."""
        await self.session.execute(
            delete(BotAssignment).where(
                (BotAssignment.user_id == user_id)
                | (BotAssignment.assigned_by == user_id)
            )
        )
