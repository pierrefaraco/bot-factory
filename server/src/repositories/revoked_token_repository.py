from datetime import datetime

from sqlalchemy import delete, select

from src.models import RevokedToken
from src.repositories.base import BaseRepository


class RevokedTokenRepository(BaseRepository):
    async def revoke(self, jti: str, expires_at: datetime) -> None:
        # merge: logging out twice with the same token is not an error.
        await self.session.merge(RevokedToken(jti, expires_at))

    async def is_revoked(self, jti: str) -> bool:
        stmt = select(RevokedToken.jti).where(RevokedToken.jti == jti)
        return (await self.session.execute(stmt)).first() is not None

    async def purge_expired(self, now: datetime) -> None:
        """Expired tokens are refused on their exp claim alone."""
        await self.session.execute(
            delete(RevokedToken).where(RevokedToken.expires_at < now)
        )
