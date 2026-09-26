import time
import uuid
from ai_server.config.config import app_config
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.models import Knowledge
from ai_server.dto.knowledge_dto import KnowledgeDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.repositories import KnowledgeRepository
from ai_server.services.base_service import BaseService
from datetime import datetime, timezone
from typing import List, Optional, Dict
from starlette.concurrency import run_in_threadpool
from werkzeug.utils import secure_filename
import os

logger = BotFactoryLogger()

ENUMERATIONS = {"CHAPTER_DAD_ID": -1, "CHILDREN_REF_ID": uuid.uuid4(), "INDICE": 0}


class KnowledgeSvc(BaseService[KnowledgeDto]):
    """Service for managing a bot's knowledge chapters and their ChromaDB
    vectors (collection `Collection{bot_id}`, one entry set per chapter,
    tagged with its knowledge_id).

    Async throughout. ChromaDB (HTTP client + FastEmbed embeddings) and
    PDF file writes are blocking with no async equivalent: each such call
    goes through run_in_threadpool, off the event loop. DB changes are
    committed before the matching vector write, as before."""

    def __init__(
        self, chroma_db_svc: ChromaDbService, knowledge_repo: KnowledgeRepository
    ):
        super().__init__()
        self.upload_folder = app_config.UPLOAD_FOLDER
        self.config = app_config
        self.chroma_db_svc = chroma_db_svc
        self.knowledge_repo = knowledge_repo
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
            knowledge.updated_at.isoformat() if knowledge.updated_at else "",
            knowledge.vector_synced_at.isoformat()
            if knowledge.vector_synced_at
            else None,
        )

    def save_pdf(self, pdf_file: str, file) -> str:
        """
        Save PDF file to upload folder. Blocking (file I/O): callers run it
        through run_in_threadpool.

        Args:
            pdf_file: PDF filename
            file: File object to save

        Returns:
            Path to saved file

        Raises:
            ValueError: If file is missing, not named as a PDF, too large,
                or its content is not actually a PDF.
        """
        if not file or not pdf_file or not pdf_file.lower().endswith(".pdf"):
            raise ValueError("Le fichier doit être un PDF.")

        safe_filename = secure_filename(pdf_file)
        if not safe_filename or not safe_filename.lower().endswith(".pdf"):
            raise ValueError("Nom de fichier PDF invalide.")

        pdf_file_path = os.path.join(self.upload_folder, safe_filename)
        file.save(pdf_file_path)

        try:
            if os.path.getsize(pdf_file_path) > self.config.MAX_PDF_SIZE_BYTES:
                raise ValueError("Le fichier PDF dépasse la taille maximale autorisée.")
            with open(pdf_file_path, "rb") as saved_file:
                if saved_file.read(5) != b"%PDF-":
                    raise ValueError("Le contenu du fichier n'est pas un PDF valide.")
        except ValueError:
            os.remove(pdf_file_path)
            raise

        logger.debug(f"save_pdf: saved {safe_filename} to {pdf_file_path}")
        return pdf_file_path

    async def save_knowledges_dto(
        self, bot_id: int, knowledges_dto: List[KnowledgeDto]
    ) -> None:
        """
        Save multiple knowledges from DTOs (no vector indexing: see
        recordChaptersToVectorDB).
        """
        for dto in knowledges_dto:
            knowledge_date = (
                dto.date
                if isinstance(dto.date, datetime)
                else datetime.strptime(dto.date, "%d/%m/%Y %H:%M:%S")
            )
            self.knowledge_repo.add(
                Knowledge(
                    bot_id,
                    dto.name,
                    knowledge_date,
                    dto.content,
                    dto.knowledge_dad_id,
                    dto.indice,
                    dto.children_ref_id,
                )
            )
        await self.knowledge_repo.commit()
        logger.info(
            f"save_knowledges_dto: saved {len(knowledges_dto)} knowledges for bot_id={bot_id}"
        )

    async def save_imported_knowledges(
        self, bot_id: int, imported_knowledges: List[Dict]
    ) -> List[KnowledgeDto]:
        """
        Save imported knowledges, index them, and return all of the bot's
        knowledges as DTOs.
        """
        logger.info(
            f"save_imported_knowledges: importing {len(imported_knowledges)} "
            f"knowledges for bot_id={bot_id}"
        )
        created_entities = []
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
            self.knowledge_repo.add(knowledge_entity)
            created_entities.append(knowledge_entity)
        await self.knowledge_repo.commit()
        for knowledge_entity in created_entities:
            await self._ingest_knowledge_node(knowledge_entity)

        knowledges = await self.knowledge_repo.list_for_bot(bot_id)
        for knowledge in knowledges:
            await self.knowledge_repo.refresh(knowledge)
        logger.info(
            f"save_imported_knowledges: imported {len(imported_knowledges)} knowledges "
            f"for bot_id={bot_id}, total now {len(knowledges)}"
        )
        return [self._knowledge_to_dto(ch) for ch in knowledges]

    async def save_knowledge(
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
        Save (create or update) a knowledge, and re-index it.

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
        """
        knowledge = await self.knowledge_repo.get_for_bot(bot_id, knowledge_id)
        if knowledge:
            return await self.update_knowledge_entity(
                bot_id,
                knowledge,
                knowledge_name,
                knowledge_content,
                pdf_file,
                knowledge_dad_id,
                indice,
                file,
            )
        return await self.create_knowledge_entity(
            bot_id,
            knowledge_name,
            knowledge_content,
            pdf_file,
            knowledge_dad_id,
            indice,
            file,
        )

    async def create_knowledge_entity(
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
        Create a new knowledge (indice -1: next free one at its level), and
        index it.
        """
        if file:
            pdf_file = os.path.basename(
                await run_in_threadpool(self.save_pdf, pdf_file, file)
            )

        if indice == -1:
            indice = await self._compute_indice(bot_id, knowledge_dad_id)

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
        self.knowledge_repo.add(knowledge)
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(knowledge)
        logger.info(
            f"create_knowledge_entity: created knowledge_id={knowledge.id} "
            f"bot_id={bot_id} dad_id={knowledge_dad_id} indice={indice}"
        )
        await self.sync_knowledge_to_vector_db(knowledge)
        return self._knowledge_to_dto(knowledge)

    async def create_empty_knowledge(self, bot_id, knowledge_dad_id) -> KnowledgeDto:
        """Create an empty chapter at the end of knowledge_dad_id's level."""
        indice = await self._compute_indice(bot_id, knowledge_dad_id)

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
        self.knowledge_repo.add(knowledge)
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(knowledge)
        logger.info(
            f"create_empty_knowledge: created knowledge_id={knowledge.id} "
            f"bot_id={bot_id} dad_id={knowledge_dad_id} indice={indice}"
        )
        await self.sync_knowledge_to_vector_db(knowledge)
        return self._knowledge_to_dto(knowledge)

    async def _compute_indice(self, bot_id: int, knowledge_dad_id: str) -> int:
        """Compute next available index for a knowledge at the same level."""
        indice = 1
        for knowledge in await self.knowledge_repo.list_children(
            bot_id, knowledge_dad_id
        ):
            if knowledge.indice >= indice:
                indice = knowledge.indice + 1
        return indice

    async def update_knowledge_entity(
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
        Update an existing knowledge, and re-index it.
        """
        if file:
            pdf_file = os.path.basename(
                await run_in_threadpool(self.save_pdf, pdf_file, file)
            )

        knowledge.date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
        knowledge.updated_at = datetime.now(timezone.utc)
        knowledge.content = new_content
        knowledge.name = new_name
        if knowledge_dad_id is not None:
            knowledge.knowledge_dad_id = knowledge_dad_id
        knowledge.indice = indice
        knowledge.pdf_file = pdf_file
        await self.knowledge_repo.commit()
        logger.info(
            f"update_knowledge_entity: updated knowledge_id={knowledge.id} bot_id={bot_id}"
        )
        await self.sync_knowledge_to_vector_db(knowledge)
        return self._knowledge_to_dto(knowledge)

    async def get_knowledges(self, bot_id: int) -> List[KnowledgeDto]:
        """
        Get all knowledges for a specific bot.
        """
        knowledges = await self.knowledge_repo.list_for_bot(bot_id)
        return [self._knowledge_to_dto(ch) for ch in knowledges]

    async def get_knowledge(
        self, bot_id: int, knowledge_id: int
    ) -> Optional[KnowledgeDto]:
        """
        Get a specific knowledge by bot and knowledge ID, None if not found.
        """
        knowledge = await self.knowledge_repo.get_for_bot(bot_id, knowledge_id)
        if not knowledge:
            return None
        return self._knowledge_to_dto(knowledge)

    def compare_fn(self, knowledge: Knowledge) -> int:
        """Helper function for sorting knowledges by index."""
        return knowledge.indice

    async def delete_knowledge(self, knowledge_id: int) -> bool:
        """
        Delete a knowledge, its whole subtree and their vectors, then
        renumber its remaining siblings.

        Returns:
            True if deletion was successful, False if not found
        """
        knowledge = await self.knowledge_repo.get(knowledge_id)
        if not knowledge:
            logger.warning(f"delete_knowledge({knowledge_id}) failed: not found")
            return False

        bot_id = knowledge.bot_id
        deleted_ids = await self._delete_subtree(knowledge)
        await self._re_compute_indices(bot_id, knowledge.knowledge_dad_id)
        await self.knowledge_repo.commit()
        for deleted_id in deleted_ids:
            await self._remove_knowledge_from_vector_db(bot_id, deleted_id)
        logger.info(
            f"delete: deleted knowledge_id={knowledge_id} bot_id={bot_id} "
            f"({len(deleted_ids)} chapter(s) with its subtree)"
        )
        return True

    async def _delete_subtree(self, knowledge: Knowledge) -> List[int]:
        """Delete knowledge and, recursively, its children (same bot only).
        Returns the deleted ids."""
        deleted_ids = []
        for child in await self.knowledge_repo.list_children(
            knowledge.bot_id, knowledge.children_ref_id
        ):
            deleted_ids += await self._delete_subtree(child)
        deleted_ids.append(knowledge.id)
        await self.knowledge_repo.delete(knowledge)
        return deleted_ids

    async def _re_compute_indices(self, bot_id: int, knowledge_dad_id: str) -> None:
        """Renumber bot_id's knowledges at the knowledge_dad_id level 1..n."""
        siblings = sorted(
            await self.knowledge_repo.list_children(bot_id, knowledge_dad_id),
            key=self.compare_fn,
        )
        for indice, knowledge in enumerate(siblings, start=1):
            knowledge.indice = indice

    async def delete_all(self, bot_id: int) -> bool:
        """
        Delete all knowledges of a bot and its vector collection.

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            start = time.perf_counter()
            await run_in_threadpool(
                self.chroma_db_svc.delete_all, f"Collection{bot_id}"
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                f"delete_all: vector DB collection Collection{bot_id} deleted in {elapsed_ms:.1f}ms"
            )

            deleted_count = await self.knowledge_repo.delete_for_bot(bot_id)
            await self.knowledge_repo.commit()
            logger.info(
                f"delete_all: deleted {deleted_count} knowledges and vector data "
                f"for bot_id={bot_id}"
            )
            return True
        except Exception as e:
            await self.knowledge_repo.rollback()
            logger.exception(
                f"delete_all: failed to delete data for bot_id={bot_id}: {e}"
            )
            return False

    async def _ingest_knowledge_node(self, knowledge: Knowledge) -> None:
        """Ingest a single knowledge node's text and optional PDF, tagged by
        knowledge_id so it can later be targeted for deletion/update without
        touching the rest of the bot's collection."""
        collection_name = f"Collection{knowledge.bot_id}"
        metadata = {
            "knowledge_id": knowledge.id,
            "bot_id": knowledge.bot_id,
            "name": knowledge.name,
        }
        text = f"{knowledge.name}\n{knowledge.content}".strip()
        if text:
            await run_in_threadpool(
                self.chroma_db_svc.ingest_text, text, collection_name, metadata=metadata
            )
        if knowledge.pdf_file:
            pdf_path = os.path.join(self.upload_folder, knowledge.pdf_file)
            await run_in_threadpool(
                self.chroma_db_svc.ingest_pdf,
                pdf_path,
                collection_name=collection_name,
                metadata=metadata,
            )
        knowledge.vector_synced_at = datetime.now(timezone.utc)
        await self.knowledge_repo.commit()

    async def _remove_knowledge_from_vector_db(
        self, bot_id: int, knowledge_id: int
    ) -> None:
        await run_in_threadpool(
            self.chroma_db_svc.delete_documents_by_metadata,
            f"Collection{bot_id}",
            {"knowledge_id": knowledge_id},
        )

    async def sync_knowledge_to_vector_db(self, knowledge: Knowledge) -> None:
        """Incrementally re-sync a single knowledge node: remove its old
        vectors, then re-ingest its current content."""
        await self._remove_knowledge_from_vector_db(knowledge.bot_id, knowledge.id)
        await self._ingest_knowledge_node(knowledge)

    async def recordChaptersToVectorDB(self, bot_id: int) -> None:
        """
        Rebuild the bot's whole vector collection from its knowledges.
        """
        start = time.perf_counter()
        knowledges = await self.knowledge_repo.list_for_bot(bot_id)
        logger.info(
            f"recordChaptersToVectorDB: resyncing {len(knowledges)} knowledges "
            f"for bot_id={bot_id}"
        )

        await run_in_threadpool(self.chroma_db_svc.delete_all, f"Collection{bot_id}")
        for knowledge in knowledges:
            await self._ingest_knowledge_node(knowledge)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"recordChaptersToVectorDB: bot_id={bot_id} - "
            f"resynced {len(knowledges)} knowledges in {elapsed_ms:.1f}ms"
        )
