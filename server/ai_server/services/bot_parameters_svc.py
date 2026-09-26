from typing import List, Dict, Any, Optional
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.services.prompt_svc import PromptService
from ai_server.services.yaml_svc import YamlSvc
from ai_server.models import BotParameters, InterlocutorIdentity
from ai_server.repositories import BotParametersRepository
from ai_server.services.base_service import BaseService


class BotParametersService(BaseService[BotParametersDto]):
    """Service for managing bot parameters entities"""

    def __init__(
        self,
        yaml_svc: YamlSvc,
        prompt_svc: PromptService,
        bot_parameters_repo: BotParametersRepository,
    ):
        super().__init__()
        self.yaml_svc = yaml_svc
        self.prompt_svc = prompt_svc
        self.bot_parameters_repo = bot_parameters_repo

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
            answer_format=bot_parameters.answer_format,
            voice_output=bot_parameters.voice_output,
            persona_description=bot_parameters.persona_description,
        )

    def get_bot_parameters_description(self) -> dict:
        """get_bot_parameters_description"""
        return (
            self.yaml_svc.answer_dict
            | self.yaml_svc.behaviour_dict
            | self.yaml_svc.qualities_flaws_dict
        )

    def _bot_parameters_creation_data(self, bot_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
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
            "interlocutor_identity": str(
                params.get("interlocutor_identity") or InterlocutorIdentity.USER.value
            ),
            "answer_format": str(params.get("answer_format") or ""),
            "voice_output": bool(params.get("voice_output")),
            "persona_description": str(params.get("persona_description") or ""),
        }

    async def create_bot_parameters(
        self, user_name: str, bot_id: int, params: Dict[str, Any]
    ) -> BotParametersDto:
        """
        Create the parameters of bot_id from params, then regenerate the
        bot's prompt from them.

        Returns:
            Created BotParametersDto instance
        """
        self.logger.info(
            f"create_bot_parameters bot_id={bot_id} requested by user_name={user_name}"
        )
        data = self._bot_parameters_creation_data(bot_id, params)
        result = await self.create(data)
        await self.update_prompt(user_name, data["bot_id"])
        return result

    async def create(self, data: Dict[str, Any]) -> BotParametersDto:
        """
        Create new bot parameters.

        Args:
            data: Bot parameters creation data

        Returns:
            Created BotParametersDto instance
        """
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
            interlocutor_identity=data.get("interlocutor_identity")
            or InterlocutorIdentity.USER.value,
            answer_format=data.get("answer_format", ""),
            voice_output=bool(data.get("voice_output", False)),
            persona_description=data.get("persona_description", ""),
        )
        self.bot_parameters_repo.add(bot_params)
        await self.bot_parameters_repo.commit()
        self.logger.info(
            f"BotParameters created id={bot_params.id} bot_id={bot_params.bot_id}"
        )
        return self._bot_parameters_to_dto(bot_params)

    # 10 coherent bot personas used by create_random_parameters. Every value taken
    # from answer.yaml / behaviour.yaml must match one of the "label" entries there,
    # since prompt_svc looks up the description text by that label.
    RANDOM_BOT_PROFILES: List[Dict[str, Any]] = [
        # {
        #     "bot_name": "Professor Aurelian",
        #     "bot_type": "History professor",
        #     "main_personality_trait_1": "passionate",
        #     "main_personality_trait_2": "patient",
        #     "main_personality_trait_3": "rigorous",
        #     "used_sources": "only context",
        #     "context_type": "manual",
        #     "answer_style": "informative",
        #     "answer_length": "medium",
        #     "interlocutor_type": "Students",
        #     "goal": "Add usefull responses to your interlocutor's question",
        #     "behaviour_when_ignore": "mention",
        #     "behaviour_with_language": "adapt",
        #     "localisation": "Paris, France",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "Chef Marco",
        #     "bot_type": "Head chef",
        #     "main_personality_trait_1": "creative",
        #     "main_personality_trait_2": "food-loving",
        #     "main_personality_trait_3": "warm",
        #     "used_sources": "inside and outside context",
        #     "context_type": "manual",
        #     "answer_style": "conversational",
        #     "answer_length": "short",
        #     "interlocutor_type": "Cooking enthusiasts",
        #     "goal": "Be helpful for your interlocutor",
        #     "behaviour_when_ignore": "elaborate_alternative",
        #     "behaviour_with_language": "adapt",
        #     "localisation": "Lyon, France",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "TechBot Nova",
        #     "bot_type": "Technical support",
        #     "main_personality_trait_1": "precise",
        #     "main_personality_trait_2": "patient",
        #     "main_personality_trait_3": "methodical",
        #     "used_sources": "only context",
        #     "context_type": "Technical documentation",
        #     "answer_style": "technical",
        #     "answer_length": "long",
        #     "interlocutor_type": "Developers",
        #     "goal": "Add usefull responses to your interlocutor's question",
        #     "behaviour_when_ignore": "mention",
        #     "behaviour_with_language": "english",
        #     "localisation": "San Francisco, USA",
        #     "interlocutor_identity": "ANONYME",
        # },
        # {
        #     "bot_name": "Luna",
        #     "bot_type": "Storyteller",
        #     "main_personality_trait_1": "imaginative",
        #     "main_personality_trait_2": "poetic",
        #     "main_personality_trait_3": "gentle",
        #     "used_sources": "only outside context",
        #     "context_type": "A story",
        #     "answer_style": "mytho",
        #     "answer_length": "long",
        #     "interlocutor_type": "Children",
        #     "goal": "Be friend with interlocutor",
        #     "behaviour_when_ignore": "mytho",
        #     "behaviour_with_language": "adapt",
        #     "localisation": "Quebec, Canada",
        #     "interlocutor_identity": "GROUP",
        # },
        # {
        #     "bot_name": "Coach Max",
        #     "bot_type": "Sports coach",
        #     "main_personality_trait_1": "motivating",
        #     "main_personality_trait_2": "energetic",
        #     "main_personality_trait_3": "disciplined",
        #     "used_sources": "inside and outside context",
        #     "context_type": "manual",
        #     "answer_style": "conversational",
        #     "answer_length": "short",
        #     "interlocutor_type": "Amateur athletes",
        #     "goal": "Be helpful for your interlocutor",
        #     "behaviour_when_ignore": "elaborate_alternative",
        #     "behaviour_with_language": "english",
        #     "localisation": "Los Angeles, USA",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "Elena Voyage",
        #     "bot_type": "Travel guide",
        #     "main_personality_trait_1": "curious",
        #     "main_personality_trait_2": "adventurous",
        #     "main_personality_trait_3": "cultured",
        #     "used_sources": "inside and outside context",
        #     "context_type": "journal",
        #     "answer_style": "informative",
        #     "answer_length": "medium",
        #     "interlocutor_type": "Travelers",
        #     "goal": "Add usefull responses to your interlocutor's question",
        #     "behaviour_when_ignore": "elaborate_alternative",
        #     "behaviour_with_language": "spanish",
        #     "localisation": "Barcelona, Spain",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "Sage Confucius",
        #     "bot_type": "Philosopher",
        #     "main_personality_trait_1": "wise",
        #     "main_personality_trait_2": "thoughtful",
        #     "main_personality_trait_3": "kind",
        #     "used_sources": "only context",
        #     "context_type": "your memories",
        #     "answer_style": "simplified",
        #     "answer_length": "exhaustive",
        #     "interlocutor_type": "Seekers of wisdom",
        #     "goal": "Be neutral with interlocutor",
        #     "behaviour_when_ignore": "mention",
        #     "behaviour_with_language": "chinese",
        #     "localisation": "Beijing, China",
        #     "interlocutor_identity": "ANONYME",
        # },
        # {
        #     "bot_name": "Robo Friend",
        #     "bot_type": "Virtual companion",
        #     "main_personality_trait_1": "empathetic",
        #     "main_personality_trait_2": "funny",
        #     "main_personality_trait_3": "loyal",
        #     "used_sources": "only outside context",
        #     "context_type": "role-play guide",
        #     "answer_style": "comical",
        #     "answer_length": "very-short",
        #     "interlocutor_type": "Teenagers",
        #     "goal": "Be friend with interlocutor",
        #     "behaviour_when_ignore": "mytho",
        #     "behaviour_with_language": "adapt",
        #     "localisation": "Berlin, Germany",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "AI Financial Advisor",
        #     "bot_type": "Financial advisor",
        #     "main_personality_trait_1": "rigorous",
        #     "main_personality_trait_2": "analytical",
        #     "main_personality_trait_3": "prudent",
        #     "used_sources": "only context",
        #     "context_type": "Technical documentation",
        #     "answer_style": "technical",
        #     "answer_length": "long",
        #     "interlocutor_type": "Investors",
        #     "goal": "Add usefull responses to your interlocutor's question",
        #     "behaviour_when_ignore": "mention",
        #     "behaviour_with_language": "english",
        #     "localisation": "London, United Kingdom",
        #     "interlocutor_identity": "USER",
        # },
        # {
        #     "bot_name": "Sensei Hiro",
        #     "bot_type": "Language tutor",
        #     "main_personality_trait_1": "patient",
        #     "main_personality_trait_2": "encouraging",
        #     "main_personality_trait_3": "methodical",
        #     "used_sources": "inside and outside context",
        #     "context_type": "manual",
        #     "answer_style": "simplified",
        #     "answer_length": "medium",
        #     "interlocutor_type": "Learners",
        #     "goal": "Be helpful for your interlocutor",
        #     "behaviour_when_ignore": "elaborate_alternative",
        #     "behaviour_with_language": "japanese",
        #     "localisation": "Tokyo, Japan",
        #     "interlocutor_identity": "USER",
        # },
        {
            "bot_name": "Pierre",
            "bot_type": "Développeur",
            "main_personality_trait_1": "creative",
            "main_personality_trait_2": "respectful",
            "main_personality_trait_3": "curious",
            "used_sources": "only context",
            "context_type": "what is needed to speak about Pierre's career",
            "answer_style": "simplified",
            "answer_length": "medium",
            "interlocutor_type": "Un recruteur technique ou des ressources Humaines",
            "goal": "Add usefull responses to your interlocutor's question",
            "behaviour_when_ignore": "mention",
            "behaviour_with_language": "adapt",
            "localisation": "France, Paris",
            "interlocutor_identity": "ANONYME",
            "persona_description": "respectueux qui vouvoie toujours son interlocuteur",
            "voice_output": False
        },
    ]

    async def create_random_parameters(
        self, user_name: str, bot_id: int
    ) -> BotParametersDto:
        import random

        profile = random.choice(self.RANDOM_BOT_PROFILES)
        data: Dict[str, Any] = {"bot_id": bot_id, **profile}
        self.logger.info(
            f"create_random_parameters bot_id={bot_id} selected profile "
            f"bot_name={profile['bot_name']!r} bot_type={profile['bot_type']!r}"
        )

        result = await self.create(data)
        await self.update_prompt(user_name, bot_id)
        return result

    def get_random_value_from_dict(self, cat, data: dict):
        import random

        label_list = data.get(cat)
        if label_list and isinstance(label_list, list) and len(label_list) > 0:
            return random.choice(label_list)["label"]
        return ""

    async def get_welcome_message(self, user_name: str, bot_id: int) -> str:
        """
        Get the message that triggers a bot's first contact with user_name.
        """
        self.logger.debug(f"get_welcome_message bot_id={bot_id} user_name={user_name}")
        params = await self.bot_parameters_repo.get_by_bot_id(bot_id)
        return self.prompt_svc.welcome_message_trigger(
            user_name, params, self.yaml_svc.behaviour_dict
        )

    async def get_by_bot_id(self, bot_id: int) -> Optional[BotParametersDto]:
        """
        Get bot parameters by bot ID, None if the bot has none.
        """
        bot_params = await self.bot_parameters_repo.get_by_bot_id(bot_id)
        if not bot_params:
            return None
        return self._bot_parameters_to_dto(bot_params)

    async def patch_bot_parameters(
        self, bot_id: int, data: dict, user_name: str
    ) -> Optional[BotParametersDto]:
        """
        Patch bot parameters with specific logic for each field, then
        regenerate the bot's prompt.

        Returns:
            Updated BotParametersDto instance, or None if not found
        """
        bot_params = await self.bot_parameters_repo.get_by_bot_id(bot_id)
        if not bot_params:
            return None

        # Only overwrite fields that are present in the payload. Empty strings
        # are ignored except for optional fields the user may want to clear,
        # and False is a valid value (e.g. voice_output).
        clearable_fields = {"persona_description", "answer_format"}
        applied_fields = []
        for key, value in data.items():
            if (
                key != "user_name"
                and value is not None
                and (value != "" or key in clearable_fields)
                and hasattr(bot_params, key)
            ):
                setattr(bot_params, key, value)
                applied_fields.append(key)

        self.logger.debug(
            f"patch_bot_parameters bot_id={bot_id} applied_fields={applied_fields} "
            f"skipped_fields={[k for k in data if k not in applied_fields and k != 'user_name']}"
        )
        await self.bot_parameters_repo.commit()
        self.logger.info(f"BotParameters patched bot_id={bot_id}")
        await self.update_prompt(user_name, bot_id)
        return self._bot_parameters_to_dto(bot_params)

    async def delete_by_bot_id(self, bot_id: int) -> bool:
        """
        Delete bot parameters by bot ID.

        Returns:
            True if deletion was successful, False if not found
        """
        bot_params = await self.bot_parameters_repo.get_by_bot_id(bot_id)
        if not bot_params:
            self.logger.warning(f"delete_by_bot_id bot_id={bot_id} not found")
            return False

        await self.bot_parameters_repo.delete(bot_params)
        await self.bot_parameters_repo.commit()
        self.logger.info(f"BotParameters deleted bot_id={bot_id}")
        return True

    async def update_prompt(self, user_name: str, bot_id: int):
        """
        Regenerate bot_id's prompt from its current parameters.
        """
        params = await self.bot_parameters_repo.get_by_bot_id(bot_id)
        if params:
            await self.prompt_svc.update_prompt(
                user_name,
                bot_id,
                params,
                self.yaml_svc.behaviour_dict,
                self.yaml_svc.answer_dict,
            )
            self.logger.debug(f"Prompt updated for bot_id={bot_id} by user_name={user_name}")
        else:
            self.logger.warning(
                f"No BotParameters found for bot_id {bot_id}, prompt not updated"
            )
