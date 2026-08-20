from importlib.resources import files
from ai_server.dto.knowledge_dto import KnowledgeDto
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.rag_svc import RagService
from datetime import datetime, timezone
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger

import re


REG_EXP = r"--- Chapter ID: (.*?) --- Name: (.*?) --- Dad ID: (.*?) --- Indice: (.*?) --- Children Ref Id: (.*?) ---\n([\s\S]*?)(?=(\n--- Chapter ID:|$))"

ENGLISH_TEMPLATE = "english-template.txt"
FRENCH_TEMPLATE = "start.txt"


@singleton
class TemplateSvc:
    def __init__(self):
        # KnowledgeSvc est @singleton : le décorateur n'exécute __init__ qu'au
        # tout premier appel et ignore les arguments des appels suivants (cf.
        # ai_server/decorators/singleton.py). Passer `None` ici revenait donc,
        # selon l'ordre d'import des controllers Flask (rest_bot avant
        # rest_rag dans main.py), à figer `rag_svc=None` pour TOUTE
        # l'application — d'où l'AttributeError 'NoneType' object has no
        # attribute 'db_service' côté rest_knowledge. RagService() est lui
        # aussi un singleton sans argument (même pattern que bot_svc.py,
        # property `context_svc`), donc toujours sûr à appeler ici quel que
        # soit l'ordre d'import.
        self.knowledge_svc = KnowledgeSvc(RagService())
        self.logger = BotFactoryLogger()

    def importTemplateInDB(self, bot_id, template_name):
        self.logger.info(f"Importing template '{template_name}' for bot_id={bot_id}")

        # Itemize data files under proj/resources/images:
        templates_dir = files("ai_server.resources.templates")
        templates = [entry.name for entry in templates_dir.iterdir()]
        self.logger.debug(f"Available templates: {templates}")
        # Get the data file bytes:
        template_to_load = templates_dir.joinpath(FRENCH_TEMPLATE).read_text(
            encoding="utf-8"
        )
        matches = re.findall(REG_EXP, template_to_load)
        if not matches:
            self.logger.warning(
                f"Template '{template_name}' parsed with 0 chapter matches for bot_id={bot_id} "
                "- resulting bot will have an empty knowledge base"
            )
        chapters_dto: list[KnowledgeDto] = []
        for match in matches:
            self.logger.debug(
                f"Template chapter match found with ID: {match[0]}, Name: {match[1]}"
            )
            chapter_dto = KnowledgeDto(
                match[0],
                match[1],
                datetime.now(timezone.utc),
                match[5],
                match[2],
                match[3],
                match[4],
            )
            chapters_dto.append(chapter_dto)
        self.knowledge_svc.save_knowledges_dto(bot_id, chapters_dto)
        self.logger.info(
            f"Template import completed for bot_id={bot_id}: {len(chapters_dto)} chapters saved"
        )
        return chapters_dto
