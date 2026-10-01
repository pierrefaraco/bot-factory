"""ORM models, grouped by aggregate.

Every model module is imported here so that importing anything from
src.models registers all tables on Base.metadata -- Alembic
(db/alembic/env.py) relies on that for autogenerate, and the string
foreign keys ("user_account.id", "bot.id") are only resolvable once
every table is registered.
"""

from src.models.base import Base
from src.models.bot import Bot, BotAvatar, BotParameters, InterlocutorIdentity
from src.models.bot_assignment import BotAssignment
from src.models.conversation import Message, Session
from src.models.knowledge import ROOT_CHAPTER_ID, Knowledge
from src.models.magic_link import MagicLink
from src.models.revoked_token import RevokedToken
from src.models.token_usage import TokenUsage
from src.models.user import User

__all__ = [
    "Base",
    "Bot",
    "BotAssignment",
    "BotAvatar",
    "BotParameters",
    "InterlocutorIdentity",
    "Knowledge",
    "MagicLink",
    "Message",
    "ROOT_CHAPTER_ID",
    "RevokedToken",
    "Session",
    "TokenUsage",
    "User",
]
