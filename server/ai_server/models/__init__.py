"""ORM models, grouped by aggregate.

Every model module is imported here so that importing anything from
ai_server.models registers all tables on Base.metadata -- Alembic
(db/alembic/env.py) relies on that for autogenerate, and the string
foreign keys ("user_account.id", "bot.id") are only resolvable once
every table is registered.
"""

from ai_server.models.base import Base
from ai_server.models.bot import Bot, BotAvatar, BotParameters, InterlocutorIdentity
from ai_server.models.bot_assignment import BotAssignment
from ai_server.models.conversation import Message, Session
from ai_server.models.knowledge import ROOT_CHAPTER_ID, Knowledge
from ai_server.models.token_usage import TokenUsage
from ai_server.models.user import User

__all__ = [
    "Base",
    "Bot",
    "BotAssignment",
    "BotAvatar",
    "BotParameters",
    "InterlocutorIdentity",
    "Knowledge",
    "Message",
    "ROOT_CHAPTER_ID",
    "Session",
    "TokenUsage",
    "User",
]
