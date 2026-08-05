from typing import Optional, TYPE_CHECKING
from ai_server.dao.database import Bot

# from langchain import hub  # Deprecated in newer LangChain versions
# from langchain.prompts import PromptTemplate  # Moved to langchain_core
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)

from ai_server.dto.bot_dto import BotDto
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.config.prompt_constants import (
    LABEL,
    DESCRIPTION,
    GOAL,
    BEHAVIOUR_WHEN_IGNORE,
    BEHAVIOUR_WITH_LANGUAGE,
    USED_SOURCES,
    CONTEXT_TYPE,
    ANSWER_LENGTH,
    ANSWER_FORMAT,
    ANSWER_STYLE,
    USER_IDENTITY,
    ANONYME_IDENTITY,
    GROUP_IDENTITY,
    GAME_MASTER,
    SUPER_HOST,
    SPEAKER,
    contextualize_q_system_prompt,
)

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from ai_server.services.bot_svc import BotService


@singleton
class PromptService:
    def __init__(self):
        self._bot_service = None
        self.logger = BotFactoryLogger()
        self.build_prompt()

    @property
    def bot_service(self):
        """Lazy load BotService to avoid circular import."""
        if self._bot_service is None:
            from ai_server.services.bot_svc import BotService

            self._bot_service = BotService()
        return self._bot_service

    def build_prompt(self):

        self.contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

    def get_qa_promt(self, bot_id):
        # bot: BotDto = self.bot_service.get_by_id(bot_id)
        prompt = self.bot_service.get_prompt(bot_id)
        BOT_PROMPT = f"""
                        {prompt}

                        <context>
                        {{context}}
                        </context>
                    """
        self.logger.debug(f"QA prompt created for bot_id {bot_id}")
        self.qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", BOT_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        return self.qa_prompt

    def welcome_message_trigger(self, user_name, params, behaviour_dict) -> str:
        interlocutor_sentence = self.make_interlocutor_sentence(user_name, params)
        question = (
            f'As "{params.bot_type}",  you address your interlocutor for an initial contact. '
            + f"{interlocutor_sentence}. "
            + f"{self.get_desc(behaviour_dict[GOAL], params.goal)}. "
            + f"To answer use the langage used at '{params.localisation}'."
            + f"It's very important that you give a very short sentence. (about 2-10 words)."
        )
        return question

    def update_prompt(
        self, user_name: str, bot_id, params, behaviour_dict, answer_dict
    ):
        interlocutor_sentence = self.make_interlocutor_sentence(user_name, params)
        prompt = f"""
        You are {params.bot_name}, {params.bot_type} located at {params.localisation}.
        {interlocutor_sentence}
        {self.get_desc(behaviour_dict[GOAL], params.goal)}
        The context elements are retrieved from {params.context_type}.
        {self.get_desc(answer_dict[USED_SOURCES], params.used_sources)}
        {self.get_desc(answer_dict[ANSWER_LENGTH], params.answer_length)}
        Your answer must be {self.get_desc(answer_dict[ANSWER_STYLE], params.answer_style)}
        you're main character traits are {params.main_personality_trait_1},{params.main_personality_trait_2} and {params.main_personality_trait_3}
        But avoid to enumerate this character traits, be natural.
        If you have no idea about the answer, {self.get_desc(behaviour_dict[BEHAVIOUR_WHEN_IGNORE], params.behaviour_when_ignore)}
        If you have to say a number has more than 4 digits. Break it up into several groups of 2 numbers to give it.
        {self.get_desc(behaviour_dict[BEHAVIOUR_WITH_LANGUAGE], params.behaviour_with_language)}
        """

        self.logger.info(f"Updating prompt for bot_id {bot_id}")
        self.bot_service.update(bot_id, {"prompt": prompt})

    def make_interlocutor_sentence(self, user_name, params):
        interlocutor_sentence = f'Your interlocutor is "{params.interlocutor_type}".'
        if params.interlocutor_identity == USER_IDENTITY:
            interlocutor_sentence = (
                f'Your interlocutor, {user_name}, is "{params.interlocutor_type}".'
            )
        if params.interlocutor_identity == GROUP_IDENTITY:
            interlocutor_sentence = (
                f'Your interlocutors are a group of "{params.interlocutor_type}".'
            )
        return interlocutor_sentence

    def get_desc(self, my_dict, my_label: str) -> str:
        for item in my_dict:
            if item[LABEL] == my_label:
                return item[DESCRIPTION]
        self.logger.warning(f"Description not found for label: {my_label}")
        return "error"
