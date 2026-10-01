from datetime import datetime
from typing import Optional

from sqlalchemy import select, update

from src.models import MagicLink
from src.repositories.base import BaseRepository


class MagicLinkRepository(BaseRepository):
    def add(self, magic_link: MagicLink) -> None:
        self.session.add(magic_link)

    async def consume(self, token_hash: str, now: datetime) -> Optional[int]:
        """Marks the link used and returns its user_id, or None if there is
        no such link, or it is expired or already used.

        A single conditional UPDATE rather than SELECT-then-UPDATE: two
        concurrent redemptions of the same link can't both see it unused --
        only one of them gets rowcount == 1."""
        result = await self.session.execute(
            update(MagicLink)
            .where(
                MagicLink.token_hash == token_hash,
                MagicLink.used_at.is_(None),
                MagicLink.expires_at > now,
            )
            .values(used_at=now)
        )
        if result.rowcount != 1:
            return None
        stmt = select(MagicLink.user_id).where(MagicLink.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one()
