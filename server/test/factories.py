"""Per-model DB factories for the HTTP regression suite.

Each factory inserts a row directly via the real ORM models (imported
straight from ai_server.dao.database, usable outside Flask's app context
since they're plain SQLAlchemy 2.0 Mapped[] models) and registers its id
for automatic cleanup at the end of the test.

Cleanup deletes explicitly, in reverse dependency order, rather than relying
on ondelete=CASCADE: Message/Session/TokenUsage reference bot_id as a plain
int with no foreign key at all (see ai_server/dao/database.py), so they
would be orphaned rather than cascade-deleted if we only removed the Bot.
"""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from ai_server.config.constant import USER_ROLE
from ai_server.dao.database import (
    Bot,
    BotAssignment,
    BotAvatar,
    BotParameters,
    Knowledge,
    Message,
    Session as SessionModel,
    TokenUsage,
    User,
)

from .helpers import unique

DEFAULT_PASSWORD = "Passw0rd!23"

# Children before parents.
_DELETE_ORDER = [
    TokenUsage,
    Message,
    SessionModel,
    BotAssignment,
    Knowledge,
    BotAvatar,
    BotParameters,
    Bot,
    User,
]


@pytest.fixture()
def registry(db_session):
    created = {model: [] for model in _DELETE_ORDER}
    yield created
    for model in _DELETE_ORDER:
        ids = created[model]
        if ids:
            db_session.query(model).filter(model.id.in_(ids)).delete(
                synchronize_session=False
            )
    db_session.commit()


@pytest.fixture()
def track(registry):
    """Registers a row created out-of-band (e.g. via an HTTP endpoint under
    test, rather than a create_* factory) for the same automatic cleanup."""

    def _track(model, row_id):
        registry[model].append(row_id)

    return _track
    db_session.commit()


@pytest.fixture()
def create_user(db_session, registry):
    def _create(role=USER_ROLE, password=DEFAULT_PASSWORD, parent_id=-1, is_active=True, **overrides):
        user = User(
            name=overrides.pop("name", unique("Name")),
            password_hash=generate_password_hash(password),
            mail=overrides.pop("mail", unique("user") + "@example.com"),
            roles=role,
            parent_id=parent_id,
            is_active=is_active,
            selected_bot_id=overrides.pop("selected_bot_id", None),
        )
        db_session.add(user)
        db_session.commit()
        registry[User].append(user.id)
        return user, password

    return _create


@pytest.fixture()
def create_bot(db_session, registry):
    def _create(user_account_id, prompt="test prompt"):
        bot = Bot(user_account_id=user_account_id, prompt=prompt)
        db_session.add(bot)
        db_session.commit()
        registry[Bot].append(bot.id)
        return bot

    return _create


@pytest.fixture()
def create_bot_parameters(db_session, registry):
    def _create(bot_id, bot_name=None, **overrides):
        params = BotParameters(
            bot_id=bot_id, bot_name=bot_name or unique("Bot"), **overrides
        )
        db_session.add(params)
        db_session.commit()
        registry[BotParameters].append(params.id)
        return params

    return _create


@pytest.fixture()
def create_avatar(db_session, registry):
    def _create(bot_id, **overrides):
        defaults = dict(
            body=1,
            body_color=1,
            hat=1,
            hat_color=1,
            eyes=1,
            eyes_color=1,
            mouth=1,
            mouth_color=1,
        )
        defaults.update(overrides)
        avatar = BotAvatar(bot_id=bot_id, **defaults)
        db_session.add(avatar)
        db_session.commit()
        registry[BotAvatar].append(avatar.id)
        return avatar

    return _create


@pytest.fixture()
def create_knowledge(db_session, registry):
    def _create(bot_id, name=None, **overrides):
        knowledge = Knowledge(
            bot_id=bot_id,
            name=name or unique("Chapter"),
            date=datetime.now(timezone.utc).isoformat(),
            **overrides,
        )
        db_session.add(knowledge)
        db_session.commit()
        registry[Knowledge].append(knowledge.id)
        return knowledge

    return _create


@pytest.fixture()
def create_bot_assignment(db_session, registry):
    def _create(bot_id, user_id, assigned_by, is_active=True):
        assignment = BotAssignment(
            bot_id=bot_id, user_id=user_id, assigned_by=assigned_by, is_active=is_active
        )
        db_session.add(assignment)
        db_session.commit()
        registry[BotAssignment].append(assignment.id)
        return assignment

    return _create


@pytest.fixture()
def create_session(db_session, registry):
    def _create(bot_id, user_id):
        session_row = SessionModel(bot_id=bot_id, user_id=user_id)
        db_session.add(session_row)
        db_session.commit()
        registry[SessionModel].append(session_row.id)
        return session_row

    return _create


@pytest.fixture()
def create_message(db_session, registry):
    def _create(session_id, order=0, role="user", content="hello", hide=False):
        message = Message(
            order=order, session_id=session_id, role=role, content=content, hide=hide
        )
        db_session.add(message)
        db_session.commit()
        registry[Message].append(message.id)
        return message

    return _create


@pytest.fixture()
def create_token_usage(db_session, registry):
    def _create(
        user_id,
        bot_id,
        user_guest_id=-1,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        session_id=None,
        model_name="mistral-medium",
    ):
        usage = TokenUsage(
            user_id=user_id,
            user_guest_id=user_guest_id,
            bot_id=bot_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            session_id=session_id,
            model_name=model_name,
        )
        db_session.add(usage)
        db_session.commit()
        registry[TokenUsage].append(usage.id)
        return usage

    return _create
