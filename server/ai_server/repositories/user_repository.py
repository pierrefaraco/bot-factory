from typing import Optional, Sequence

from sqlalchemy import or_, select, update

from ai_server.config.constant import ADMIN_ROLE
from ai_server.models import User
from ai_server.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def add(self, user: User) -> None:
        self.session.add(user)

    async def delete(self, user: User) -> None:
        await self.session.delete(user)

    async def get(self, user_id: int) -> Optional[User]:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.mail == email)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_non_admins(self) -> Sequence[User]:
        stmt = select(User).where(User.roles != ADMIN_ROLE)
        return (await self.session.execute(stmt)).scalars().all()

    async def list_by_role(self, role: str, visible_admin_id: int) -> Sequence[User]:
        """Users whose roles contain `role`, excluding every Admin account
        except visible_admin_id's own."""
        stmt = select(User).where(
            User.roles.contains(role),
            or_(User.roles != ADMIN_ROLE, User.id == visible_admin_id),
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_children(self, parent_id: int) -> Sequence[User]:
        stmt = select(User).where(User.parent_id == parent_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def clear_selected_bot(self, bot_id: int) -> None:
        """Unselect bot_id for every user that selected it. Done explicitly
        rather than left to the FK's ON DELETE SET NULL: user_account.
        selected_bot_id references bot.id via a use_alter FK that MySQL
        never created as a real constraint (see models/user.py), so it
        can't be trusted to null this out on its own."""
        await self.session.execute(
            update(User)
            .where(User.selected_bot_id == bot_id)
            .values(selected_bot_id=None)
        )
