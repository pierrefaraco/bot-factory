# from typing import Text
import contextvars
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
from sqlalchemy import Enum
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import DateTime

from ai_server.config.config import AppConfig

ROOT_CHAPTER_ID = "this_is_a_root_chapter"


class Base(DeclarativeBase):
    pass


# Flask-SQLAlchemy previously backed Model.query/db.session with a
# scoped_session tied to Flask's own app-context contextvar, torn down
# automatically when that context popped. Every route is now native
# FastAPI, so this scopes the same way but on a contextvar this module
# owns directly instead: db_session_scope() (used by
# ai_server/dependencies/db_session.py's with_db_session /
# stream_with_db_session) sets it to a fresh, unique value for one
# request -- or one streamed chunk, for a long-lived streaming response --
# and calls SessionLocal.remove() when that unit of work ends, so a
# Session never survives past the request that created it, same lifecycle
# as before without needing a Flask app context to provide it.
_db_scope_id = contextvars.ContextVar("db_scope_id", default=None)


def _scopefunc():
    return _db_scope_id.get()


_engine = None


def _get_engine():
    # Lazy: Flask-SQLAlchemy didn't build its engine until db.init_app(app)
    # ran against a real app's already-loaded config, so importing this
    # module on its own (e.g. test/factories.py, for the model classes)
    # never required DATABASE_URL to be set. create_engine(None) fails
    # immediately (invalid URL), so building it eagerly at import time here
    # would newly require every such import to have DATABASE_URL set too --
    # deferring to first actual use preserves the original laziness.
    global _engine
    if _engine is None:
        _engine = create_engine(AppConfig.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    return _engine


def _session_factory():
    return sessionmaker(bind=_get_engine())()


SessionLocal = scoped_session(_session_factory, scopefunc=_scopefunc)


@contextmanager
def db_session_scope():
    token = _db_scope_id.set(object())
    try:
        yield
    finally:
        SessionLocal.remove()
        _db_scope_id.reset(token)


class _DbCompat:
    """Minimal flask_sqlalchemy.SQLAlchemy drop-in exposing only what this
    codebase's Model.query / db.session call sites actually use, so none
    of them need to change."""

    Model = Base
    session = SessionLocal


db = _DbCompat()

Base.query = SessionLocal.query_property()


class InterlocutorIdentity(Enum):
    USER = "USER"
    GROUP = "GROUP"
    ANONYME = "ANONYME"


class Bot(db.Model):
    __tablename__ = "bot"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.id"), nullable=False
    )
    prompt: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)

    def __repr__(self) -> str:
        return f"Bot(id={self.id!r}, user_account_id={self.user_account_id!r}, prompt={self.prompt!r})"

    def __init__(self, user_account_id: int, prompt: str):
        self.user_account_id = user_account_id

        self.prompt = prompt


class BotParameters(db.Model):
    __tablename__ = "bot_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bot.id", ondelete="CASCADE"), nullable=False
    )
    bot_name: Mapped[str] = mapped_column(String(64))
    bot_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    interlocutor_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    interlocutor_identity: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    main_personality_trait_1: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    main_personality_trait_2: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    main_personality_trait_3: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )

    used_sources: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    context_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    answer_style: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    answer_length: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    goal: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    behaviour_when_ignore: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    behaviour_with_language: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    localisation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    answer_format: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    voice_output: Mapped[bool] = mapped_column(
        default=False, nullable=False, server_default=sqlalchemy.text("0")
    )
    persona_description: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"BotParameters(id={self.id!r},bot_id={self.bot_id!r}, bot_name={self.bot_name!r}, "
            f"bot_type={self.bot_type!r}, main_personality_trait_1={self.main_personality_trait_1!r}, "
            f"main_personality_trait_2={self.main_personality_trait_2!r}, "
            f"main_personality_trait_3={self.main_personality_trait_3!r}, "
            f"used_sources={self.used_sources!r}, context_type={self.context_type!r}, "
            f"answer_style={self.answer_style!r}, "
            f"answer_length={self.answer_length!r}, interlocutor_type={self.interlocutor_type!r}, "
            f"goal={self.goal!r}, behaviour={self.behaviour!r}, "
            f"behaviour_when_ignore={self.behaviour_when_ignore!r}, "
            f"behaviour_with_language={self.behaviour_with_language!r}, "
            f"localisation={self.localisation!r}, "
            f"interlocutor_identity={self.interlocutor_identity!r} "
        )

    def __init__(
        self,
        bot_id: int,
        bot_name: str,
        bot_type: str = "",
        main_personality_trait_1: str = "",
        main_personality_trait_2: str = "",
        main_personality_trait_3: str = "",
        used_sources: str = "",
        context_type: str = "",
        answer_style: str = "",
        answer_length: str = "",
        interlocutor_type: str = "",
        goal: str = "",
        behaviour_when_ignore: str = "",
        behaviour_with_language: str = "",
        localisation: str = "",
        interlocutor_identity: str = InterlocutorIdentity.USER.value,
        answer_format: str = "",
        voice_output: bool = False,
        persona_description: str = "",
    ):

        self.bot_id = bot_id
        self.bot_name = bot_name
        self.bot_type = bot_type
        self.main_personality_trait_1 = main_personality_trait_1
        self.main_personality_trait_2 = main_personality_trait_2
        self.main_personality_trait_3 = main_personality_trait_3
        self.used_sources = used_sources
        self.context_type = context_type
        self.answer_style = answer_style
        self.answer_length = answer_length
        self.interlocutor_type = interlocutor_type
        self.goal = goal
        self.behaviour_when_ignore = behaviour_when_ignore
        self.behaviour_with_language = behaviour_with_language
        self.localisation = localisation
        self.answer_format = answer_format
        self.voice_output = voice_output
        self.persona_description = persona_description
        if interlocutor_identity not in [e.value for e in InterlocutorIdentity]:
            raise ValueError(
                f"interlocutor_identity '{interlocutor_identity}' is not valid. Allowed values: {[e.value for e in InterlocutorIdentity]}"
            )

        self.interlocutor_identity = interlocutor_identity


class BotAvatar(db.Model):
    __tablename__ = "bot_avatar"
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bot.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[int] = mapped_column()
    body_color: Mapped[int] = mapped_column()
    hat: Mapped[int] = mapped_column()
    hat_color: Mapped[int] = mapped_column()
    eyes: Mapped[int] = mapped_column()
    eyes_color: Mapped[int] = mapped_column()
    mouth: Mapped[int] = mapped_column()
    mouth_color: Mapped[int] = mapped_column()

    def __repr__(self) -> str:
        return f"BotAvatar(id={self.id!r}, bot_id={self.bot_id!r}, body={self.body!r}, body_color={self.body_color!r}, hat={self.hat!r}, hat_color={self.hat_color!r}, eyes={self.eyes!r}, eyes_color={self.eyes_color!r}, mouth={self.mouth!r}, mouth_color={self.mouth_color!r})"

    def __init__(
        self,
        bot_id: int,
        body: int,
        body_color: str,
        hat: int,
        hat_color: str,
        eyes: int,
        eyes_color: str,
        mouth: int,
        mouth_color: str,
    ):
        self.bot_id = bot_id
        self.body = body
        self.body_color = body_color
        self.hat = hat
        self.hat_color = hat_color
        self.eyes = eyes
        self.eyes_color = eyes_color
        self.mouth = mouth
        self.mouth_color = mouth_color


class User(db.Model):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(256))
    mail: Mapped[str] = mapped_column(String(128))
    roles: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column()
    # use_alter=True: 'bot' and 'user_account' reference each other
    # (bot.user_account_id <-> user_account.selected_bot_id). Without this,
    # SQLAlchemy/Alembic can't order CREATE TABLE statements (circular FK)
    # and autogenerate emits an unresolved-cycle warning. use_alter tells
    # SQLAlchemy to create/drop this specific constraint via a separate
    # ALTER TABLE, after both tables already exist.
    selected_bot_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "bot.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_user_account_selected_bot_id",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, password_hash={self.password_hash!r}, mail={self.mail!r}), roles={self.roles!r}, parent_id={self.parent_id!r}, is_active={self.is_active!r}, selected_bot_id={self.selected_bot_id!r}, created_at={self.created_at!r})"

    def __init__(
        self,
        name: str,
        password_hash: str,
        mail: str,
        roles: str,
        parent_id: int,
        is_active: bool,
        selected_bot_id: Optional[int] = None,
    ):
        self.name = name
        self.password_hash = password_hash
        self.mail = mail
        self.roles = roles
        self.parent_id = parent_id
        self.is_active = is_active
        self.selected_bot_id = selected_bot_id


class Knowledge(db.Model):
    __tablename__ = "knowledge"
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(54))
    date: Mapped[datetime] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(String(4096))
    knowledge_dad_id: Mapped[str] = mapped_column(String(64))
    children_ref_id: Mapped[str] = mapped_column(String(64))
    indice: Mapped[int] = mapped_column()
    pdf_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    def __repr__(self) -> str:
        return f"Chapter(id={self.id!r}, bot_id={self.bot_id!r}, name={self.name!r},  date={self.date!r}, content={self.content!r},knowledge_dad_id={self.knowledge_dad_id!r},indice={self.indice!r},children_ref_id={self.children_ref_id!r}, pdf_file={self.pdf_file!r})"

    def __init__(
        self,
        bot_id: int,
        name: str,
        date: datetime,
        content: str = "empty",
        knowledge_dad_id=ROOT_CHAPTER_ID,
        indice=0,
        children_ref_id="",
        pdf_file: str = "",
    ):
        self.bot_id = bot_id
        self.name = name
        self.date = date
        self.content = content
        self.knowledge_dad_id = knowledge_dad_id
        self.children_ref_id = children_ref_id
        self.indice = indice
        self.pdf_file = pdf_file


# Define the Session model
class Session(db.Model):
    __tablename__ = "session"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))

    def __repr__(self) -> str:
        return (
            f"Session(id={self.id!r}, bot_id={self.bot_id!r}, user_id={self.user_id!r})"
        )

    def __init__(self, bot_id: int, user_id: int):
        self.bot_id = bot_id
        self.user_id = user_id


# Define the Message model
class Message(db.Model):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(String(4096), nullable=False)
    time: Mapped[datetime] = mapped_column(
        String(64), default=datetime.now(timezone.utc), nullable=False
    )
    hide: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"Message(id={self.id!r},order={self.order!r},session_id={self.session_id!r}, role={self.role!r}, content={self.content!r}, time={self.time!r}),hide={self.hide!r})"

    def __init__(
        self,
        order,
        session_id: int,
        role: str,
        content: str,
        time: Optional[datetime] = None,
        hide: bool = False,
    ):
        self.order = order
        self.session_id = session_id
        self.role = role
        self.content = content
        self.time = time
        self.hide = hide


class BotAssignment(db.Model):
    """Table de liaison pour assigner des bots spécifiques aux utilisateurs GUEST"""

    __tablename__ = "bot_guest_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bot.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.id"), nullable=False
    )
    assigned_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        String(64),
        default=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"BotAssignment(id={self.id!r}, bot_id={self.bot_id!r}, user_id={self.user_id!r}, assigned_by={self.assigned_by!r}, assigned_at={self.assigned_at!r}, is_active={self.is_active!r})"

    def __init__(
        self, bot_id: int, user_id: int, assigned_by: int, is_active: bool = True
    ):
        self.bot_id = bot_id
        self.user_id = user_id
        self.assigned_by = assigned_by
        self.assigned_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
        self.is_active = is_active


class TokenUsage(db.Model):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    user_guest_id: Mapped[int] = mapped_column(nullable=True)
    bot_id: Mapped[int] = mapped_column(nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    def __repr__(self) -> str:
        return (
            f"TokenUsage(id={self.id!r}, user_id={self.user_id!r}, user_guest_id={self.user_guest_id!r}, bot_id={self.bot_id!r}, "
            f"session_id={self.session_id!r}, prompt_tokens={self.prompt_tokens!r}, "
            f"completion_tokens={self.completion_tokens!r}, total_tokens={self.total_tokens!r}, "
            f"timestamp={self.timestamp!r}, model_name={self.model_name!r})"
        )

    def __init__(
        self,
        user_id: int,
        user_guest_id: int,
        bot_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        session_id: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        self.user_id = user_id
        self.user_guest_id = user_guest_id
        self.bot_id = bot_id
        self.session_id = session_id
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.model_name = model_name
