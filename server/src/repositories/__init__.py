"""Data access: one repository per aggregate root (see models/), plus one
per child entity that has a service of its own (bot parameters, bot
avatar).

Repositories hold query code only: no business rules, no response
formatting, and no transaction decisions -- see base.py.
"""

from src.repositories.bot_assignment_repository import BotAssignmentRepository
from src.repositories.bot_avatar_repository import BotAvatarRepository
from src.repositories.bot_parameters_repository import BotParametersRepository
from src.repositories.bot_repository import BotRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.knowledge_repository import KnowledgeRepository
from src.repositories.magic_link_repository import MagicLinkRepository
from src.repositories.revoked_token_repository import RevokedTokenRepository
from src.repositories.token_usage_repository import TokenUsageRepository
from src.repositories.user_repository import UserRepository

__all__ = [
    "BotAssignmentRepository",
    "BotAvatarRepository",
    "BotParametersRepository",
    "BotRepository",
    "ConversationRepository",
    "KnowledgeRepository",
    "MagicLinkRepository",
    "RevokedTokenRepository",
    "TokenUsageRepository",
    "UserRepository",
]
