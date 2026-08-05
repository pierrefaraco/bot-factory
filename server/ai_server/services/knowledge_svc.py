import pprint
import uuid
from ai_server.config.config import flask_config
from abc import ABCMeta
from ai_server.services.rag_svc import RagService
from ai_server.dao.database import Knowledge, User, db, ROOT_CHAPTER_ID
from ai_server.dto.knowledge_dto import KnowledgeDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from ai_server.decorators.singleton import singleton
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import os

logger = BotFactoryLogger()

ENUMERATIONS = {"CHAPTER_DAD_ID": -1, "CHILDREN_REF_ID": uuid.uuid4(), "INDICE": 0}


@singleton
class KnowledgeSvc(BaseService[KnowledgeDto]):
    """Service for managing knowledge/context entities"""

    def __init__(self, rag_svc: RagService):
        super().__init__()
        self.upload_folder = flask_config.UPLOAD_FOLDER
        self.config = flask_config
        self.rag_svc = rag_svc
        os.makedirs(self.upload_folder, exist_ok=True)

    def _knowledge_to_dto(self, knowledge: Knowledge) -> KnowledgeDto:
        """
        Convert Chapter entity to ChapterDto.

        Args:
            knowledge: Chapter entity to convert

        Returns:
            ChapterDto representation of the knowledge
        """
        return KnowledgeDto(
            knowledge.id,
            knowledge.name,
            knowledge.date,
            knowledge.content,
            knowledge.knowledge_dad_id,
            knowledge.indice,
            knowledge.children_ref_id,
            knowledge.pdf_file,
        )

    def save_pdf(self, pdf_file: str, file) -> str:
        """
        Save PDF file to upload folder.

        Args:
            pdf_file: PDF filename
            file: File object to save

        Returns:
            Path to saved file

        Raises:
            ValueError: If file is not a PDF
        """
        if file and pdf_file.endswith(".pdf"):
            pdf_file_path = os.path.join(self.upload_folder, pdf_file)
            file.save(pdf_file_path)
            return pdf_file_path
        else:
            raise ValueError("Le fichier doit être un PDF.")

    def save_knowledges_dto(
        self, bot_id: int, knowledges_dto: List[KnowledgeDto]
    ) -> None:
        """
        Save multiple knowledges from DTOs.

        Args:
            bot_id: ID of the bot owning the knowledges
            knowledges_dto: List of knowledge DTOs to save

        Raises:
            ServiceError: When knowledge saving fails
        """
        result = self._safe_execute(
            "_perform_save_knowledges_dto",
            self._perform_save_knowledges_dto,
            bot_id,
            knowledges_dto,
        )

    def _perform_save_knowledges_dto(
        self, bot_id: int, knowledges_dto: List[KnowledgeDto]
    ) -> None:
        for dto in knowledges_dto:
            knowledge_date = (
                dto.date
                if isinstance(dto.date, datetime)
                else datetime.strptime(dto.date, "%d/%m/%Y %H:%M:%S")
            )
            knowledge = Knowledge(
                bot_id,
                dto.name,
                knowledge_date,
                dto.content,
                dto.knowledge_dad_id,
                dto.indice,
                dto.children_ref_id,
            )
            db.session.add(knowledge)
        db.session.commit()

    def save_imported_knowledges(
        self, bot_id: int, imported_knowledges: List[Dict]
    ) -> List[KnowledgeDto]:
        """
        Save imported knowledges and return as DTOs.

        Args:
            bot_id: ID of the bot owning the knowledges
            imported_knowledges: List of knowledge dictionaries

        Returns:
            List of saved ChapterDto instances

        Raises:
            ServiceError: When knowledge saving fails
        """
        result = self._safe_execute(
            "_perform_save_imported_knowledges",
            self._perform_save_imported_knowledges,
            bot_id,
            imported_knowledges,
        )
        if result is None:
            raise ServiceError("Save imported knowledges failed.")
        return result

    def _perform_save_imported_knowledges(
        self, bot_id: int, imported_knowledges: List[Dict]
    ) -> List[KnowledgeDto]:
        for knowledge in imported_knowledges:
            knowledge_entity = Knowledge(
                bot_id,
                knowledge["knowledge_name"],
                datetime.now(timezone.utc),
                knowledge["knowledge_content"],
                knowledge["knowledge_dad_id"],
                knowledge["indice"],
                knowledge["children_ref_id"],
            )
            db.session.add(knowledge_entity)
        db.session.commit()

        knowledges: List[Knowledge] = Knowledge.query.filter_by(bot_id=bot_id).all()
        return [self._knowledge_to_dto(ch) for ch in knowledges]

    def save_knowledge(
        self,
        pdf_file: str,
        bot_id: int,
        knowledge_id: int,
        knowledge_name: str,
        knowledge_content: str = "",
        knowledge_dad_id: str = "",
        indice: int = 0,
        file=None,
    ) -> KnowledgeDto:
        """
        Save (create or update) a knowledge.

        Args:
            pdf_file: PDF filename
            bot_id: ID of the bot owning the knowledge
            knowledge_id: ID of the knowledge (for updates)
            knowledge_name: Name of the knowledge
            knowledge_content: Content of the knowledge
            knowledge_dad_id: ID of parent knowledge
            indice: Order index
            file: File object

        Returns:
            ChapterDto instance

        Raises:
            ServiceError: When knowledge saving fails
        """
        result = self._safe_execute(
            "_perform_save_knowledge",
            self._perform_save_knowledge,
            pdf_file,
            bot_id,
            knowledge_id,
            knowledge_name,
            knowledge_content,
            knowledge_dad_id,
            indice,
            file,
        )
        if result is None:
            raise ServiceError("Save knowledge failed.")
        return result

    def _perform_save_knowledge(
        self,
        pdf_file: str,
        bot_id: int,
        knowledge_id: int,
        knowledge_name: str,
        knowledge_content: str,
        knowledge_dad_id: str,
        indice: int,
        file,
    ) -> KnowledgeDto:
        knowledge = self.get_knowledge_if_exist(bot_id, knowledge_id)

        if knowledge:
            return self.update_knowledge_entity(
                bot_id,
                knowledge,
                knowledge_name,
                knowledge_content,
                pdf_file,
                knowledge_dad_id,
                indice,
                file,
            )
        else:
            return self.create_knowledge_entity(
                bot_id,
                knowledge_name,
                knowledge_content,
                pdf_file,
                knowledge_dad_id,
                indice,
                file,
            )

    def create_knowledge_entity(
        self,
        bot_id: int,
        knowledge_name: str,
        knowledge_content: str = "",
        pdf_file: str = "",
        knowledge_dad_id: str = "",
        indice: int = -1,
        file=None,
    ) -> KnowledgeDto:
        """
        Create a new knowledge entity.

        Args:
            bot_id: ID of the bot owning the knowledge
            knowledge_name: Name of the knowledge
            knowledge_content: Content of the knowledge
            pdf_file: PDF filename
            knowledge_dad_id: ID of parent knowledge
            indice: Order index
            file: File object

        Returns:
            ChapterDto instance

        Raises:
            ServiceError: When knowledge creation fails
        """
        result = self._safe_execute(
            "_perform_create_knowledge",
            self._perform_create_knowledge,
            bot_id,
            knowledge_name,
            knowledge_content,
            pdf_file,
            knowledge_dad_id,
            indice,
            file,
        )
        if result is None:
            raise ServiceError("Create knowledge failed.")
        return result

    def _perform_create_knowledge(
        self,
        bot_id: int,
        knowledge_name: str,
        knowledge_content: str,
        pdf_file: str,
        knowledge_dad_id: str,
        indice: int,
        file,
    ) -> KnowledgeDto:
        if file:
            self.save_pdf(pdf_file, file)

        if indice == -1:
            indice = self._compute_indice(bot_id, knowledge_dad_id)

        knowledge = Knowledge(
            bot_id,
            knowledge_name,
            datetime.now(timezone.utc),
            knowledge_content,
            knowledge_dad_id,
            indice,
            f"{uuid.uuid4()}",
            pdf_file,
        )
        db.session.add(knowledge)
        db.session.commit()

        created_knowledge: Knowledge = Knowledge.query.filter_by(
            name=knowledge_name, bot_id=bot_id
        ).first()
        return self._knowledge_to_dto(created_knowledge)

    def create_empty_knowledge(self, bot_id, knowledge_dad_id) -> KnowledgeDto:
        indice = self._compute_indice(bot_id, knowledge_dad_id)

        knowledge = Knowledge(
            bot_id=bot_id,
            name="",
            date=datetime.now(timezone.utc),
            content="",
            knowledge_dad_id=knowledge_dad_id,
            indice=indice,
            children_ref_id=f"{uuid.uuid4()}",
            pdf_file="",
        )
        db.session.add(knowledge)
        db.session.commit()
        return self._knowledge_to_dto(knowledge)

    def create(self, data: Dict[str, Any]) -> KnowledgeDto:
        """
        Create a new knowledge.

        Args:
            data: Chapter creation data

        Returns:
            Created ChapterDto instance

        Raises:
            ServiceError: When knowledge creation fails
        """
        result = self._safe_execute("_perform_create", self._perform_create, data)
        if result is None:
            raise ServiceError("Chapter creation failed, no ChapterDto returned.")
        return result

    def _perform_create(self, data: Dict[str, Any]) -> KnowledgeDto:
        if data.get("indice", -1) == -1:
            data["indice"] = self._compute_indice(
                data["bot_id"], data.get("knowledge_dad_id", -1)
            )

        knowledge = Knowledge(
            bot_id=data["bot_id"],
            name=data["knowledge_name"],
            date=datetime.now(timezone.utc),
            content=data.get("knowledge_content", ""),
            knowledge_dad_id=data.get("knowledge_dad_id", ""),
            indice=data["indice"],
            children_ref_id=f"{uuid.uuid4()}",
            pdf_file=data.get("pdf_file", ""),
        )
        db.session.add(knowledge)
        db.session.commit()
        return self._knowledge_to_dto(knowledge)

    def _compute_indice(self, bot_id: int, knowledge_dad_id: str) -> int:
        """Compute next available index for a knowledge at the same level."""
        indice = 1
        existing_knowledges_at_same_lvl: List[Knowledge] = Knowledge.query.filter_by(
            knowledge_dad_id=knowledge_dad_id, bot_id=bot_id
        ).all()
        for knowledge in existing_knowledges_at_same_lvl:
            if knowledge.indice >= indice:
                indice = knowledge.indice + 1
        return indice

    def update_knowledge_entity(
        self,
        bot_id: int,
        knowledge: Knowledge,
        new_name: str,
        new_content: str,
        pdf_file: str = "",
        knowledge_dad_id: str = "",
        indice: int = 0,
        file=None,
    ) -> KnowledgeDto:
        """
        Update an existing knowledge entity.

        Args:
            bot_id: ID of the bot owning the knowledge
            knowledge: Chapter entity to update
            new_name: New knowledge name
            new_content: New knowledge content
            pdf_file: PDF filename
            knowledge_dad_id: ID of parent knowledge
            indice: Order index
            file: File object

        Returns:
            ChapterDto instance

        Raises:
            ServiceError: When knowledge update fails
        """
        result = self._safe_execute(
            "_perform_update_knowledge",
            self._perform_update_knowledge,
            bot_id,
            knowledge,
            new_name,
            new_content,
            pdf_file,
            knowledge_dad_id,
            indice,
            file,
        )
        if result is None:
            raise ServiceError("Update knowledge failed.")
        return result

    def _perform_update_knowledge(
        self,
        bot_id: int,
        knowledge: Knowledge,
        new_name: str,
        new_content: str,
        pdf_file: str,
        knowledge_dad_id: str,
        indice: int,
        file,
    ) -> KnowledgeDto:
        if file:
            self.save_pdf(pdf_file, file)

        knowledge.date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
        knowledge.content = new_content
        knowledge.name = new_name
        if knowledge_dad_id is not None:
            knowledge.knowledge_dad_id = knowledge_dad_id
        knowledge.indice = indice
        knowledge.pdf_file = pdf_file
        db.session.commit()
        return self._knowledge_to_dto(knowledge)

    def get_dto_by_id(self, entity_id: int) -> KnowledgeDto:
        """
        Retrieve a knowledge by its ID.

        Args:
            entity_id: ID of the knowledge to retrieve

        Returns:
            ChapterDto instance if found

        Raises:
            ServiceError: When knowledge retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_by_id", self._perform_get_by_id, entity_id
        )
        if result is None:
            raise ServiceError("Get knowledge by id failed, no ChapterDto returned.")
        return result

    def _perform_get_by_id(self, entity_id: int) -> KnowledgeDto:
        knowledge = Knowledge.query.get(entity_id)
        if not knowledge:
            raise NotFoundError("Chapter", str(entity_id))
        return self._knowledge_to_dto(knowledge)

    def get_all(self) -> List[KnowledgeDto]:
        """
        Retrieve all knowledges.

        Returns:
            List of ChapterDto instances

        Raises:
            ServiceError: When knowledge retrieval fails
        """
        result = self._safe_execute("_perform_get_all", self._perform_get_all)
        if result is None:
            raise ServiceError("Chapter get_all failed, no list returned.")
        return result

    def _perform_get_all(self) -> List[KnowledgeDto]:
        knowledges: List[Knowledge] = Knowledge.query.filter_by().all()
        return [self._knowledge_to_dto(knowledge) for knowledge in knowledges]

    def get_knowledges(self, bot_id: int) -> List[KnowledgeDto]:
        """
        Get all knowledges for a specific bot.

        Args:
            bot_id: ID of the bot

        Returns:
            List of ChapterDto instances

        Raises:
            ServiceError: When knowledge retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_knowledges", self._perform_get_knowledges, bot_id
        )
        if result is None:
            raise ServiceError("Get knowledges failed.")
        return result

    def _perform_get_knowledges(self, bot_id: int) -> List[KnowledgeDto]:
        knowledges: List[Knowledge] = Knowledge.query.filter_by(bot_id=bot_id).all()
        db.session.commit()
        return [self._knowledge_to_dto(ch) for ch in knowledges]

    def get_knowledge(self, bot_id: int, knowledge_id: int) -> KnowledgeDto:
        """
        Get a specific knowledge by bot and knowledge ID.

        Args:
            bot_id: ID of the bot
            knowledge_id: ID of the knowledge

        Returns:
            ChapterDto instance

        Raises:
            ServiceError: When knowledge retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_knowledge", self._perform_get_knowledge, bot_id, knowledge_id
        )
        if result is None:
            raise ServiceError("Get knowledge failed.")
        return result

    def _perform_get_knowledge(self, bot_id: int, knowledge_id: int) -> KnowledgeDto:
        ch: Knowledge = Knowledge.query.filter_by(
            bot_id=bot_id, id=knowledge_id
        ).first()
        if not ch:
            raise NotFoundError("Chapter", f"{bot_id}_{knowledge_id}")
        return self._knowledge_to_dto(ch)

    def get_knowledge_if_exist(
        self, bot_id: int, knowledge_id: int
    ) -> Optional[Knowledge]:
        """
        Get knowledge entity if it exists.

        Args:
            bot_id: ID of the bot
            knowledge_id: ID of the knowledge

        Returns:
            Chapter entity if found, None otherwise
        """
        result = self._safe_execute(
            "_perform_get_knowledge_if_exist",
            self._perform_get_knowledge_if_exist,
            bot_id,
            knowledge_id,
        )
        return result

    def _perform_get_knowledge_if_exist(
        self, bot_id: int, knowledge_id: int
    ) -> Optional[Knowledge]:
        return Knowledge.query.filter_by(id=knowledge_id, bot_id=bot_id).first()

    def update(self, entity_id: int, data: Dict[str, Any]) -> KnowledgeDto:
        """
        Update knowledge information.

        Args:
            entity_id: ID of the knowledge to update
            data: Fields to update

        Returns:
            Updated ChapterDto instance

        Raises:
            ServiceError: When knowledge update fails
        """
        result = self._safe_execute(
            "_perform_update", self._perform_update, entity_id, data
        )
        if result is None:
            raise ServiceError("Chapter update failed, no ChapterDto returned.")
        return result

    def _perform_update(self, entity_id: int, data: Dict[str, Any]) -> KnowledgeDto:
        knowledge = Knowledge.query.get(entity_id)
        if not knowledge:
            raise NotFoundError("Chapter", str(entity_id))

        for key, value in data.items():
            if hasattr(knowledge, key) and value is not None:
                setattr(knowledge, key, value)

        knowledge.date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
        db.session.commit()
        return self._knowledge_to_dto(knowledge)

    def delete(self, entity_id: int) -> bool:
        """
        Delete a knowledge.

        Args:
            entity_id: ID of the knowledge to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When knowledge deletion fails
        """
        result = self._safe_execute("_perform_delete", self._perform_delete, entity_id)
        if result is None:
            raise ServiceError("Chapter delete failed, no knowledge deleted.")
        return result

    def _perform_delete(self, entity_id: int) -> bool:
        knowledge = Knowledge.query.get(entity_id)
        if not knowledge:
            raise NotFoundError("Chapter", str(entity_id))

        self._delete_knowledge(knowledge)
        return True

    def compare_fn(self, knowledge: Knowledge) -> int:
        """Helper function for sorting knowledges by index."""
        return knowledge.indice

    def delete_knowledge(self, knowledge_id: int) -> bool:
        """
        Delete a knowledge by ID.

        Args:
            knowledge_id: ID of the knowledge to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            return self.delete(knowledge_id)
        except (ServiceError, NotFoundError):
            return False

    def _delete_knowledge(self, knowledge_to_delete: Knowledge) -> None:
        """Recursively delete a knowledge and its children."""
        for knowledge_child in Knowledge.query.filter_by(
            knowledge_dad_id=knowledge_to_delete.children_ref_id
        ):
            self._delete_knowledge(knowledge_child)
        knowledge_dad_id = knowledge_to_delete.knowledge_dad_id
        db.session.delete(knowledge_to_delete)
        db.session.commit()
        self._re_compute_indices(knowledge_dad_id)

    def _re_compute_indices(self, knowledge_dad_id: str) -> None:
        """Recompute indices for knowledges at the same level."""
        sorted_knowledges: List[Knowledge] = sorted(
            [
                knowledge
                for knowledge in Knowledge.query.filter_by(
                    knowledge_dad_id=knowledge_dad_id
                )
            ],
            key=self.compare_fn,
        )
        indice = 1
        for knowledge in sorted_knowledges:
            knowledge.indice = indice
            indice = indice + 1
        db.session.commit()

    def delete_all(self, bot_id: int) -> bool:
        """
        Delete all knowledges for a bot.

        Args:
            bot_id: ID of the bot

        Returns:
            True if deletion was successful, False otherwise
        """
        result = self._safe_execute(
            "_perform_delete_all", self._perform_delete_all, bot_id
        )
        if result is None:
            return False
        return result

    def _perform_delete_all(self, bot_id: int) -> bool:
        try:
            # Delete associated collection from vector database
            self.rag_svc.db_service.delete_all(f"Collection{bot_id}")

            # Get and delete all knowledges associated with the bot
            knowledges = Knowledge.query.filter_by(bot_id=bot_id).all()
            for knowledge in knowledges:
                db.session.delete(knowledge)

            # Commit the transaction
            db.session.commit()
            logger.info(
                f"All data associated with bot {bot_id} has been successfully deleted."
            )
            return True
        except Exception as e:
            # Handle exceptions and rollback transaction on error
            db.session.rollback()
            logger.error(f"An error occurred while deleting data: {e}")
            return False

    def recordChaptersToVectorDB(self, bot_id: int) -> None:
        """
        Record knowledges to vector database.

        Args:
            bot_id: ID of the bot

        Raises:
            ServiceError: When recording fails
        """
        result = self._safe_execute(
            "_perform_record_knowledges", self._perform_record_knowledges, bot_id
        )

    def _perform_record_knowledges(self, bot_id: int) -> None:
        knowledges: List[Knowledge] = Knowledge.query.filter_by(bot_id=bot_id).all()
        sorted_knowledges = []
        self.get_sorted_knowledges(knowledges, sorted_knowledges, ROOT_CHAPTER_ID, 0)
        to_save_in_vector_db = ""
        pdf_file_paths = []
        logger.info(f"knowledges number: {len(sorted_knowledges)}")

        for sch in sorted_knowledges:
            indent_str = "#"
            for a in range(sch["indent"]):
                indent_str = indent_str + "#"
            to_save_in_vector_db = (
                to_save_in_vector_db
                + f"{indent_str} {sch['knowledge'].indice}. {sch['knowledge'].name}"
                + "\n"
            )
            to_save_in_vector_db = (
                to_save_in_vector_db + sch["knowledge"].content + "\n"
            )
            to_save_in_vector_db = to_save_in_vector_db + "\n" + "\n"
            if sch["knowledge"].pdf_file:
                pdf_file_paths.append(
                    os.path.join(self.upload_folder, sch["knowledge"].pdf_file)
                )

        fichier = open("data_for_alfred.md", "a")
        fichier.write(to_save_in_vector_db)
        fichier.close()

        self.rag_svc.db_service.delete_all(f"Collection{bot_id}")
        if to_save_in_vector_db:
            self.rag_svc.db_service.ingest_text(
                to_save_in_vector_db, f"Collection{bot_id}"
            )
        for pdf_file_path in pdf_file_paths:
            self.rag_svc.db_service.ingest_pdf(
                pdf_file_path, collection_name=f"Collection{bot_id}"
            )

    def get_sorted_knowledges(
        self,
        knowledges: List[Knowledge],
        sorted_knowledges: List,
        dad_id: Any,
        indent: int,
    ) -> List:
        """
        Get knowledges sorted by hierarchy.

        Args:
            knowledges: List of knowledges to sort
            sorted_knowledges: List to store sorted knowledges
            dad_id: Parent ID
            indent: Indentation level

        Returns:
            List of sorted knowledges
        """
        knowledges_dad = sorted(
            [
                knowledge
                for knowledge in knowledges
                if knowledge.knowledge_dad_id == dad_id
            ],
            key=self.compare_fn,
        )
        if knowledges_dad:
            for knowledge_dad in knowledges_dad:
                sorted_knowledges.append({"knowledge": knowledge_dad, "indent": indent})
                self.get_sorted_knowledges(
                    knowledges,
                    sorted_knowledges,
                    knowledge_dad.children_ref_id,
                    indent + 1,
                )
        return sorted_knowledges
