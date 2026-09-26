from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import Row, case, delete, func, select

from ai_server.models import TokenUsage
from ai_server.repositories.base import BaseRepository


class TokenUsageRepository(BaseRepository):
    """Queries on token_usage. Aggregates come back as SQLAlchemy Rows whose
    attributes are the labels below (total_prompt_tokens, total_tokens, ...);
    SUM() over no row is NULL, so callers get None rather than 0 there."""

    def add(self, token_usage: TokenUsage) -> None:
        self.session.add(token_usage)

    async def delete_by_user_id(self, user_id: int) -> None:
        await self.session.execute(
            delete(TokenUsage).where(TokenUsage.user_id == user_id)
        )

    async def sum_total_tokens(
        self, user_id: int, since: Optional[datetime] = None
    ) -> Optional[int]:
        stmt = select(func.sum(TokenUsage.total_tokens)).where(
            TokenUsage.user_id == user_id
        )
        if since is not None:
            stmt = stmt.where(TokenUsage.timestamp >= since)
        return (await self.session.execute(stmt)).scalar()

    async def totals_for_user(
        self, user_id: int, since: Optional[datetime] = None
    ) -> Row:
        stmt = select(*self._totals_columns()).where(TokenUsage.user_id == user_id)
        if since is not None:
            stmt = stmt.where(TokenUsage.timestamp >= since)
        return (await self.session.execute(stmt)).first()

    async def totals_for_bot(self, bot_id: int) -> Row:
        stmt = select(
            *self._totals_columns(),
            func.count(func.distinct(TokenUsage.user_id)).label("unique_users"),
        ).where(TokenUsage.bot_id == bot_id)
        return (await self.session.execute(stmt)).first()

    async def totals_per_user(self) -> Sequence[Row]:
        """One row per user_id (with a user_id column), heaviest users first."""
        stmt = (
            select(TokenUsage.user_id, *self._totals_columns())
            .group_by(TokenUsage.user_id)
            .order_by(func.sum(TokenUsage.total_tokens).desc())
        )
        return (await self.session.execute(stmt)).all()

    async def list_for_user(
        self, user_id: int, limit: int, since: Optional[datetime] = None
    ) -> Sequence[TokenUsage]:
        """Newest first."""
        stmt = select(TokenUsage).where(TokenUsage.user_id == user_id)
        if since is not None:
            stmt = stmt.where(TokenUsage.timestamp >= since)
        stmt = stmt.order_by(TokenUsage.id.desc()).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def usage_windows_per_account(
        self, since_24h: datetime, since_30d: datetime, user_id: Optional[int] = None
    ) -> Sequence[Row]:
        """(user_id, tokens_24h, tokens_30d) per billed account, over the last
        30 days. tokens_24h comes from a CASE-based SUM, which PyMySQL
        returns as Decimal."""
        stmt = select(TokenUsage.user_id, *self._window_columns(since_24h)).where(
            TokenUsage.timestamp >= since_30d
        )
        if user_id is not None:
            stmt = stmt.where(TokenUsage.user_id == user_id)
        return (await self.session.execute(stmt.group_by(TokenUsage.user_id))).all()

    async def usage_windows_per_guest(
        self, since_24h: datetime, since_30d: datetime, user_id: Optional[int] = None
    ) -> Sequence[Row]:
        """(user_guest_id, tokens_24h, tokens_30d) per guest, over the last
        30 days; user_id restricts to one billed account's guests."""
        stmt = select(TokenUsage.user_guest_id, *self._window_columns(since_24h)).where(
            TokenUsage.timestamp >= since_30d,
            TokenUsage.user_guest_id.isnot(None),
            TokenUsage.user_guest_id != -1,
        )
        if user_id is not None:
            stmt = stmt.where(TokenUsage.user_id == user_id)
        return (
            await self.session.execute(stmt.group_by(TokenUsage.user_guest_id))
        ).all()

    @staticmethod
    def _totals_columns():
        return (
            func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.count(TokenUsage.id).label("total_requests"),
        )

    @staticmethod
    def _window_columns(since_24h: datetime):
        return (
            func.sum(
                case(
                    (TokenUsage.timestamp >= since_24h, TokenUsage.total_tokens),
                    else_=0,
                )
            ).label("tokens_24h"),
            func.sum(TokenUsage.total_tokens).label("tokens_30d"),
        )
