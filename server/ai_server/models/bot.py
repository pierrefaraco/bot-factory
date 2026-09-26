from enum import Enum
from typing import Optional

import sqlalchemy
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base


class InterlocutorIdentity(Enum):
    USER = "USER"
    GROUP = "GROUP"
    ANONYME = "ANONYME"


class Bot(Base):
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


class BotParameters(Base):
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


class BotAvatar(Base):
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
