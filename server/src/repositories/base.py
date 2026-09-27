from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session


class BaseRepository:
    """Runs on the current request's AsyncSession (get_async_session(), scoped
    by dependencies/db_session.py), so every repository used during one
    request shares one session and one transaction.

    A repository never commits on its own: the service that owns the use
    case decides when the unit of work ends. commit()/rollback() are exposed
    here for that -- called through any repository, they act on that same
    shared session.
    """

    @property
    def session(self) -> AsyncSession:
        return get_async_session()

    async def flush(self) -> None:
        """Send pending changes (e.g. to get generated ids) without ending
        the transaction."""
        await self.session.flush()

    async def refresh(self, row) -> None:
        """Reload row from the DB -- needed to read server-side defaults
        (e.g. CURRENT_TIMESTAMP columns) after an INSERT: the async session
        can't lazy-load them on attribute access like the sync one did."""
        await self.session.refresh(row)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
