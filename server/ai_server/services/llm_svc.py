from ai_server.dao.database import User
from langchain_community.llms import Ollama

# from langchain.embeddings.ollama import OllamaEmbeddings
from langchain_mistralai.chat_models import ChatMistralAI
from ai_server.config.config import flask_config
from ai_server.decorators.singleton import singleton
from langchain_core.callbacks.base import BaseCallbackHandler
from typing import Any, Optional, Dict
from ai_server.services.token_tracking_svc import TokenTrackingService
from ai_server.log.app_logger import AppLogger
import json



class TokenCountingCallback(BaseCallbackHandler):
    """Callback pour compter les tokens consommés lors des appels LLM"""

    def __init__(self, user_id: int, bot_id: int, session_id: Optional[int] = None):
        # Import lazy pour éviter l'importation circulaire
        from ai_server.services.user_admin_svc import UserAdminService
       
        self.user_id = user_id
        self.bot_id = bot_id
        self.session_id = session_id
        self.token_tracking_service = TokenTrackingService()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.model_name = None
        self.user_svc = UserAdminService()
        self.logger = AppLogger()

    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Appelé à la fin d'un appel LLM"""
        self.logger.debug("On LLM end, tracking tokens...")
        try:
            # Pour ChatMistralAI, les tokens sont dans les generations
            if hasattr(response, "generations") and response.generations:
                # Prendre la première génération
                self.logger.debug("Response generations found, extracting token usage")
                generation = (
                    response.generations[0][0] if response.generations[0] else None
                )
                if generation and hasattr(generation, "generation_info"):
                    message = generation.message
                    self.logger.debug(
                        f"Response message found, extracting usage from message"
                    )
                    if message and message.usage_metadata:
                        usage_metadata = message.usage_metadata
                        self.logger.debug(
                            f"Recording token usage - input: {usage_metadata.get('input_tokens')}, output: {usage_metadata.get('output_tokens')}, total: {usage_metadata.get('total_tokens')}"
                        )
                        self.prompt_tokens = usage_metadata.get("output_tokens", 0)
                        self.completion_tokens = usage_metadata.get("input_tokens", 0)
                        self.total_tokens = usage_metadata.get("total_tokens", 0)
                        self.model_name = "mistral-medium"
                        if message and "response_metadata" in message:
                            response_metadata = message["response_metadata"]
                            self.logger.debug(
                                f"Response metadata found, model: {response_metadata.get('model')}"
                            )
                            self.model_name = response_metadata.get("model")

                        user: User = self.user_svc.get_user_by_id(
                            self.user_id
                        )  # Just to ensure user exists
                        user_guest_id = -1
                        if user.parent_id > 0:
                            self.user_id = user.parent_id
                            user_guest_id = user.id
                        # Enregistrer l'utilisation des tokens
                        self.token_tracking_service.record_token_usage(
                            user_id=self.user_id,
                            user_guest_id=user_guest_id,
                            bot_id=self.bot_id,
                            prompt_tokens=self.prompt_tokens,
                            completion_tokens=self.completion_tokens,
                            total_tokens=self.total_tokens,
                            session_id=self.session_id,
                            model_name=self.model_name,
                        )
                        return

            # Fallback: essayer l'ancienne méthode avec llm_output (pour compatibilité)
            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                if token_usage:
                    self.prompt_tokens = token_usage.get("prompt_tokens", 0)
                    self.completion_tokens = token_usage.get("completion_tokens", 0)
                    self.total_tokens = token_usage.get("total_tokens", 0)
                    self.model_name = response.llm_output.get("model_name")

                    # Enregistrer l'utilisation des tokens
                    self.token_tracking_service.record_token_usage(
                        user_id=self.user_id,
                        bot_id=self.bot_id,
                        prompt_tokens=self.prompt_tokens,
                        completion_tokens=self.completion_tokens,
                        total_tokens=self.total_tokens,
                        session_id=self.session_id,
                        model_name=self.model_name,
                    )
        except Exception as e:
            # Logger l'erreur mais ne pas faire échouer l'appel LLM
            self.logger.error(f"Error tracking tokens: {e}")
            import traceback

            self.logger.error(traceback.format_exc())


@singleton
class LlmService:
    def __init__(self):    
        self.logger = AppLogger()
        # assuming you have Ollama installed and have llama3 model pulled with `ollama pull llama3 `
        # embeddings = MistralAIEmbeddings(model="mistral-embed", mistral_api_key=api_key)
        self.llm = ChatMistralAI(mistral_api_key=flask_config.MISTRAL_API_KEY, model_name=flask_config.MISTRAL_MODEL)


    def get_llm(
        self,
        user_id: Optional[int] = None,
        bot_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> ChatMistralAI:
        """
        Retourne une instance du LLM avec un callback de tracking de tokens si les IDs sont fournis

        Args:
            user_id: ID de l'utilisateur (optionnel)
            bot_id: ID du bot (optionnel)
            session_id: ID de la session (optionnel)

        Returns:
            Instance de ChatMistralAI
        """
        # Si user_id et bot_id sont fournis, créer un callback de tracking
        if user_id is not None and bot_id is not None:
            callback = TokenCountingCallback(
                user_id=user_id, bot_id=bot_id, session_id=session_id
            )
            # Créer une nouvelle instance avec le callback
            return ChatMistralAI(
                mistral_api_key=flask_config.MISTRAL_API_KEY,
                model_name="mistral-medium",
                callbacks=[callback],
            )

        return self.llm

    def system_ask_question(self, question: str) -> Dict[str, Any]:
        """
        Pose une question au LLM et retourne la réponse en tant que dictionnaire

        Args:
            question: La question à poser au LLM

        Returns:
            La réponse du LLM parsée en dictionnaire (si JSON valide)
        """
        # Invoquer le LLM avec la question
        response = self.llm.invoke(question)

        # Extraire le contenu de la réponse
        content = ""
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)

        # Tenter de parser la réponse en JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response from LLM: {e}")
            self.logger.debug(
                f"Raw content received: {content[:200]}..."
            )  # Limiter à 200 caractères pour éviter le spam
            # En cas d'erreur, retourner un dictionnaire avec la réponse brute
            return {"raw_response": content, "error": "Invalid JSON format"}
