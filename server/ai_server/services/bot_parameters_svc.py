from typing import List, Optional, Dict, Any, Union
from ai_server.config.prompt_constants import GOAL
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.services.prompt_svc import PromptService
from ai_server.services.yaml_svc import YamlSvc
from ai_server.dao.database import BotParameters, db
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from ai_server.decorators.singleton import singleton
from ai_server.services.llm_svc import LlmService
import pprint

yaml_svc = YamlSvc()
prompt_svc = PromptService()


@singleton
class BotParametersService(BaseService[BotParametersDto]):
    """Service for managing bot parameters entities"""

    def __init__(self):
        self.llm_svc = LlmService()
        super().__init__()

    def _bot_parameters_to_dto(self, bot_parameters: BotParameters) -> BotParametersDto:
        """
        Convert a BotParameters model object to a BotParametersDto object.

        Args:
            bot_parameters: BotParameters model instance

        Returns:
            BotParametersDto: Data transfer object with the same values as the model
        """
        return BotParametersDto(
            id=bot_parameters.id,
            bot_id=bot_parameters.bot_id,
            bot_name=bot_parameters.bot_name,
            bot_type=bot_parameters.bot_type,
            main_personality_trait_1=bot_parameters.main_personality_trait_1,
            main_personality_trait_2=bot_parameters.main_personality_trait_2,
            main_personality_trait_3=bot_parameters.main_personality_trait_3,
            used_sources=bot_parameters.used_sources,
            context_type=bot_parameters.context_type,
            answer_style=bot_parameters.answer_style,
            answer_length=bot_parameters.answer_length,
            interlocutor_type=bot_parameters.interlocutor_type,
            goal=bot_parameters.goal,
            behaviour_when_ignore=bot_parameters.behaviour_when_ignore,
            behaviour_with_language=bot_parameters.behaviour_with_language,
            localisation=bot_parameters.localisation,
            interlocutor_identity=bot_parameters.interlocutor_identity,
        )

    @staticmethod
    def get_bot_parameters_description() -> dict:
        """get_bot_parameters_description"""
        return (
            yaml_svc.answer_dict
            | yaml_svc.behaviour_dict
            | yaml_svc.qualities_defauts_dict
        )

    def create_bot_parameters(
        self, user_name: str, bot_id: int, params: Dict[str, Any]
    ) -> BotParametersDto:
        """
        Create new bot parameters with additional logic.

        Args:
            user_name: Name of the user creating the parameters
            bot_id: The ID of the bot to which parameters belong
            params: Dictionary containing parameter values

        Returns:
            Created BotParametersDto instance

        Raises:
            ServiceError: When bot parameters creation fails
        """
        data = {
            "bot_id": bot_id,
            "bot_name": str(params.get("bot_name") or ""),
            "bot_type": str(params.get("bot_type") or ""),
            "main_personality_trait_1": str(
                params.get("main_personality_trait_1") or ""
            ),
            "main_personality_trait_2": str(
                params.get("main_personality_trait_2") or ""
            ),
            "main_personality_trait_3": str(
                params.get("main_personality_trait_3") or ""
            ),
            "used_sources": str(params.get("used_sources") or ""),
            "context_type": str(params.get("context_type") or ""),
            "answer_style": str(params.get("answer_style") or ""),
            "answer_length": str(params.get("answer_length") or ""),
            "interlocutor_type": str(params.get("interlocutor_type") or ""),
            "goal": str(params.get("goal") or ""),
            "behaviour_when_ignore": str(params.get("behaviour_when_ignore") or ""),
            "behaviour_with_language": str(params.get("behaviour_with_language") or ""),
            "localisation": str(params.get("localisation") or ""),
            "interlocutor_identity": str(params.get("interlocutor_identity") or ""),
        }
        self.create(data)
        self.update_prompt(user_name, data["bot_id"])
        return self.create(data)

    def create(self, data: Dict[str, Any]) -> BotParametersDto:
        """
        Create new bot parameters.

        Args:
            data: Bot parameters creation data

        Returns:
            Created BotParametersDto instance

        Raises:
            ServiceError: When bot parameters creation fails
        """
        result = self._safe_execute("_perform_create", self._perform_create, data)

        if result is None:
            raise ServiceError(
                "Bot parameters creation failed, no BotParametersDto returned."
            )
        return result

    def _perform_create(self, data: Dict[str, Any]) -> BotParametersDto:
        bot_params = BotParameters(
            bot_id=data["bot_id"],
            bot_name=data.get("bot_name", ""),
            bot_type=data.get("bot_type", ""),
            main_personality_trait_1=data.get("main_personality_trait_1", ""),
            main_personality_trait_2=data.get("main_personality_trait_2", ""),
            main_personality_trait_3=data.get("main_personality_trait_3", ""),
            used_sources=data.get("used_sources", ""),
            context_type=data.get("context_type", ""),
            answer_style=data.get("answer_style", ""),
            answer_length=data.get("answer_length", ""),
            interlocutor_type=data.get("interlocutor_type", ""),
            goal=data.get("goal", ""),
            behaviour_when_ignore=data.get("behaviour_when_ignore", ""),
            behaviour_with_language=data.get("behaviour_with_language", ""),
            localisation=data.get("localisation", ""),
            interlocutor_identity=data.get("interlocutor_identity", ""),
        )
        db.session.add(bot_params)
        db.session.commit()
        return self._bot_parameters_to_dto(bot_params)

    def create_random_parameters(self, user_name: str, bot_id: int) -> BotParametersDto:
        # print(f'yaml_svc.answer_dict {yaml_svc.answer_dict}')
        # print(f'yaml_svc.behaviour_dict {yaml_svc.behaviour_dict}')
        # print('###################################')
        # print('###################################')

        # prompts = yaml_svc.prompts
        # dict_bot  = self.llm_svc.system_ask_question(prompts['generate_random_bot'])

        # print('################### dict_bot')
        # print(dict_bot)
        # data: Dict[str, Any] ={
        #     'bot_id': bot_id,
        #     'bot_name': dict_bot.get('name',''),
        #     'bot_type': dict_bot.get('type',''),
        #     'main_personality_trait_1':dict_bot.get('trait1',''),
        #     'main_personality_trait_2': dict_bot.get('trait2',''),
        #     'main_personality_trait_3':dict_bot.get('trait3',''),
        #     'used_sources': self.get_random_value_from_dict('used_sources',yaml_svc.answer_dict),
        #     'context_type': self.get_random_value_from_dict('answer_style',yaml_svc.answer_dict),
        #     'answer_style': self.get_random_value_from_dict('answer_style',yaml_svc.answer_dict),
        #     'answer_length':self.get_random_value_from_dict('answer_length',yaml_svc.answer_dict),
        #     'interlocutor_type': dict_bot.get('audience',''),
        #     'goal': self.get_random_value_from_dict('goal',yaml_svc.behaviour_dict),
        #     'behaviour_when_ignore': self.get_random_value_from_dict('behaviour_when_ignore',yaml_svc.behaviour_dict),
        #     'behaviour_with_language': self.get_random_value_from_dict('behaviour_with_language',yaml_svc.behaviour_dict),
        #     'localisation': dict_bot.get('location',''),
        #     'interlocutor_identity': self.get_random_value_from_dict('interlocutor_identity',yaml_svc.behaviour_dict),
        # }
        data: Dict[str, Any] = {
            "bot_id": bot_id,
            "bot_name": self.generate_random_bot_name(),
            "bot_type": "",
            "main_personality_trait_1": "optimiste",
            "main_personality_trait_2": "patient",
            "main_personality_trait_3": "curieux",
            "used_sources": self.get_random_value_from_dict(
                "used_sources", yaml_svc.answer_dict
            ),
            "context_type": self.get_random_value_from_dict(
                "answer_style", yaml_svc.answer_dict
            ),
            "answer_style": self.get_random_value_from_dict(
                "answer_style", yaml_svc.answer_dict
            ),
            "answer_length": self.get_random_value_from_dict(
                "answer_length", yaml_svc.answer_dict
            ),
            "interlocutor_type": "",
            "goal": self.get_random_value_from_dict("goal", yaml_svc.behaviour_dict),
            "behaviour_when_ignore": self.get_random_value_from_dict(
                "behaviour_when_ignore", yaml_svc.behaviour_dict
            ),
            "behaviour_with_language": self.get_random_value_from_dict(
                "behaviour_with_language", yaml_svc.behaviour_dict
            ),
            "localisation": "Paris, France",
            "interlocutor_identity": self.get_random_value_from_dict(
                "interlocutor_identity", yaml_svc.behaviour_dict
            ),
        }
        self.update_prompt(user_name, data["bot_id"])
        return self._perform_create(data)

    def get_random_value_from_dict(self, cat, data: dict):
        import random

        label_list = data.get(cat)
        if label_list and isinstance(label_list, list) and len(label_list) > 0:
            return random.choice(label_list)["label"]
        return ""

    def generate_random_bot_name(self) -> str:
        """Generate a random bot name from predefined lists"""
        import random

        adjectives = [
            "Sage",
            "Brillant",
            "Rapide",
            "Astucieux",
            "Vaillant",
            "Noble",
            "Fidèle",
            "Audacieux",
            "Rusé",
            "Élégant",
            "Mystérieux",
            "Lumineux",
            "Puissant",
            "Agile",
            "Majestueux",
        ]

        nouns = [
            "Assistant",
            "Conseiller",
            "Guide",
            "Compagnon",
            "Oracle",
            "Mentor",
            "Explorateur",
            "Gardien",
            "Stratège",
            "Visionnaire",
            "Navigateur",
            "Érudit",
            "Penseur",
            "Créateur",
            "Innovateur",
        ]

        return f"{random.choice(adjectives)} {random.choice(nouns)}"

    def get_dto_by_id(self, entity_id: int) -> BotParametersDto:
        """
        Retrieve bot parameters by their ID.

        Args:
            entity_id: ID of the bot parameters to retrieve

        Returns:
            BotParametersDto instance if found

        Raises:
            ServiceError: When bot parameters retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_by_id", self._perform_get_by_id, entity_id
        )
        if result is None:
            raise ServiceError(
                "Get bot parameters by id failed, no BotParametersDto returned."
            )
        return result

    def _perform_get_by_id(self, entity_id: int) -> BotParametersDto:
        bot_params = BotParameters.query.get(entity_id)
        if not bot_params:
            raise NotFoundError("BotParameters", str(entity_id))
        return self._bot_parameters_to_dto(bot_params)

    def get_all(self) -> List[BotParametersDto]:
        """
        Retrieve all bot parameters.

        Returns:
            List of BotParametersDto instances

        Raises:
            ServiceError: When bot parameters retrieval fails
        """
        result = self._safe_execute("_perform_get_all", self._perform_get_all)
        if result is None:
            raise ServiceError("Bot parameters get_all failed, no list returned.")
        return result

    def _perform_get_all(self) -> List[BotParametersDto]:
        bot_params_list: List[BotParameters] = BotParameters.query.filter_by().all()
        return [
            self._bot_parameters_to_dto(bot_params) for bot_params in bot_params_list
        ]

    def update(self, entity_id: int, data: Dict[str, Any]) -> BotParametersDto:
        """
        Update bot parameters information.

        Args:
            entity_id: ID of the bot parameters to update
            data: Fields to update

        Returns:
            Updated BotParametersDto instance

        Raises:
            ServiceError: When bot parameters update fails
        """
        result = self._safe_execute(
            "_perform_update", self._perform_update, entity_id, data
        )
        if result is None:
            raise ServiceError(
                "Bot parameters update failed, no BotParametersDto returned."
            )
        return result

    def _perform_update(self, entity_id: int, data: Dict[str, Any]) -> BotParametersDto:
        bot_params = BotParameters.query.get(entity_id)
        if not bot_params:
            raise NotFoundError("BotParameters", str(entity_id))

        for key, value in data.items():
            if key != "user_name" and hasattr(bot_params, key):
                setattr(bot_params, key, value)

        db.session.commit()

        # Update prompt after update
        if "user_name" in data:
            self.update_prompt(data["user_name"], bot_params.bot_id)

        return self._bot_parameters_to_dto(bot_params)

    def delete(self, entity_id: int) -> bool:
        """
        Delete bot parameters.

        Args:
            entity_id: ID of the bot parameters to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When bot parameters deletion fails
        """
        result = self._safe_execute("_perform_delete", self._perform_delete, entity_id)
        if result is None:
            raise ServiceError(
                "Bot parameters delete failed, no bot parameters deleted."
            )
        return result

    def _perform_delete(self, entity_id: int) -> bool:
        bot_params = BotParameters.query.get(entity_id)
        if not bot_params:
            raise NotFoundError("BotParameters", str(entity_id))

        db.session.delete(bot_params)
        db.session.commit()
        return True

    def get_welcome_message(self, user_name: str, bot_id: int) -> str:
        """
        Get welcome message for a bot.

        Args:
            user_name: Name of the user
            bot_id: ID of the bot

        Returns:
            Welcome message string

        Raises:
            ServiceError: When welcome message generation fails
        """
        result = self._safe_execute(
            "_perform_get_welcome_message",
            self._perform_get_welcome_message,
            user_name,
            bot_id,
        )
        if result is None:
            raise ServiceError("Get welcome message failed.")
        return result

    def _perform_get_welcome_message(self, user_name: str, bot_id: int) -> str:
        # bot_params_dto = self.get_dto_by_id(bot_id)
        behaviour_dict = yaml_svc.behaviour_dict
        # Convert DTO back to entity for prompt service
        params = BotParameters.query.filter_by(bot_id=bot_id).first()
        question = prompt_svc.welcome_message_trigger(user_name, params, behaviour_dict)
        return question

    def get_by_bot_id(self, bot_id: int) -> BotParametersDto:
        """
        Get bot parameters by bot ID.

        Args:
            bot_id: The ID of the bot

        Returns:
            BotParametersDto instance if found

        Raises:
            ServiceError: When bot parameters retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_by_bot_id", self._perform_get_by_bot_id, bot_id
        )
        if result is None:
            raise ServiceError("Get bot parameters by bot_id failed.")
        return result

    def _perform_get_by_bot_id(self, bot_id: int) -> BotParametersDto:
        bot_params = BotParameters.query.filter_by(bot_id=bot_id).first()
        if not bot_params:
            raise NotFoundError("BotParameters", str(bot_id))
        return self._bot_parameters_to_dto(bot_params)

    def update_by_bot_id(
        self, user_name: str, bot_id: int, update_data: Dict[str, Any]
    ) -> BotParametersDto:
        """
        Update bot parameters by bot ID.

        Args:
            user_name: Name of the user updating the parameters
            bot_id: The ID of the bot
            update_data: Dictionary containing updated parameter values

        Returns:
            Updated BotParametersDto instance

        Raises:
            ServiceError: When bot parameters update fails
        """
        result = self._safe_execute(
            "_perform_update_by_bot_id",
            self._perform_update_by_bot_id,
            user_name,
            bot_id,
            update_data,
        )
        if result is None:
            raise ServiceError("Update bot parameters by bot_id failed.")
        return result

    def _perform_update_by_bot_id(
        self, user_name: str, bot_id: int, update_data: Dict[str, Any]
    ) -> BotParametersDto:
        bot_params = BotParameters.query.filter_by(bot_id=bot_id).first()
        if not bot_params:
            raise NotFoundError("BotParameters", str(bot_id))

        # Update all fields that are present in the update_data
        for key, value in update_data.items():
            if hasattr(bot_params, key):
                setattr(bot_params, key, value)

        db.session.commit()
        self.update_prompt(user_name, bot_id)
        return self._bot_parameters_to_dto(bot_params)

    def patch_bot_parameters(
        self, bot_id: int, data: dict, user_name: str
    ) -> BotParametersDto:
        """
        Patch bot parameters with specific logic for each field.

        Args:
            bot_id: ID of the bot
            data: Dictionary containing fields to patch
            user_name: Name of the user patching the parameters

        Returns:
            Updated BotParametersDto instance

        Raises:
            ServiceError: When bot parameters patch fails
        """
        result = self._safe_execute(
            "_perform_patch_bot_parameters",
            self._perform_patch_bot_parameters,
            bot_id,
            data,
            user_name,
        )
        if result is None:
            raise ServiceError("Patch bot parameters failed.")
        return result

    def _perform_patch_bot_parameters(
        self, bot_id: int, data: dict, user_name: str
    ) -> BotParametersDto:
        bot_params = BotParameters.query.filter_by(bot_id=bot_id).first()

        if not bot_params:
            raise NotFoundError("BotParameters", str(bot_id))

        # Update fields with specific logic (keeping original print statements for debugging)
        if bot_name := data.get("bot_name"):
            bot_params.bot_name = bot_name

        if bot_type := data.get("bot_type"):
            bot_params.bot_type = bot_type

        if main_personality_trait_1 := data.get("main_personality_trait_1"):
            bot_params.main_personality_trait_1 = main_personality_trait_1

        if main_personality_trait_2 := data.get("main_personality_trait_2"):
            bot_params.main_personality_trait_2 = main_personality_trait_2

        if main_personality_trait_3 := data.get("main_personality_trait_3"):
            bot_params.main_personality_trait_3 = main_personality_trait_3

        if used_sources := data.get("used_sources"):
            bot_params.used_sources = used_sources

        if context_type := data.get("context_type"):
            bot_params.context_type = context_type

        if answer_style := data.get("answer_style"):
            bot_params.answer_style = answer_style

        if answer_length := data.get("answer_length"):
            bot_params.answer_length = answer_length

        if interlocutor_type := data.get("interlocutor_type"):
            bot_params.interlocutor_type = interlocutor_type

        if goal := data.get("goal"):
            bot_params.goal = goal

        if behaviour_when_ignore := data.get("behaviour_when_ignore"):
            bot_params.behaviour_when_ignore = behaviour_when_ignore

        if behaviour_with_language := data.get("behaviour_with_language"):
            bot_params.behaviour_with_language = behaviour_with_language

        if localisation := data.get("localisation"):
            bot_params.localisation = localisation

        if interlocutor_identity := data.get("interlocutor_identity"):
            bot_params.interlocutor_identity = interlocutor_identity

        db.session.commit()
        self.update_prompt(user_name, bot_id)
        return self._bot_parameters_to_dto(bot_params)

    def delete_by_bot_id(self, bot_id: int) -> bool:
        """
        Delete bot parameters by bot ID.

        Args:
            bot_id: The ID of the bot

        Returns:
            True if deletion was successful, False if not found

        Raises:
            ServiceError: When bot parameters deletion fails
        """
        result = self._safe_execute(
            "_perform_delete_by_bot_id", self._perform_delete_by_bot_id, bot_id
        )
        if result is None:
            return False
        return result

    def _perform_delete_by_bot_id(self, bot_id: int) -> bool:
        bot_params = BotParameters.query.filter_by(bot_id=bot_id).first()
        if not bot_params:
            return False

        db.session.delete(bot_params)
        db.session.commit()
        return True

    def update_prompt(self, user_name: str, bot_id: int):
        """
        Update prompt for a bot.

        Args:
            user_name: Name of the user
            bot_id: ID of the bot

        Raises:
            ServiceError: When prompt update fails
        """
        result = self._safe_execute(
            "_perform_update_prompt", self._perform_update_prompt, user_name, bot_id
        )

    def _perform_update_prompt(self, user_name: str, bot_id: int):
        behaviour_dict = yaml_svc.behaviour_dict
        answer_dict = yaml_svc.answer_dict
        params = BotParameters.query.filter_by(bot_id=bot_id).first()
        if params:
            prompt_svc.update_prompt(
                user_name, bot_id, params, behaviour_dict, answer_dict
            )
