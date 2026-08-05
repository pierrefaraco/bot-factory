# import
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader,
)
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document  # Fixed: moved to langchain_core
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.vectorstores import VectorStoreRetriever
from chromadb.config import Settings
from ai_server.log.app_logger import AppLogger
from ai_server.config.config import flask_config
from ai_server.dto.document_dto import DocumentDto
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.services.base_service import BaseService
from ai_server.decorators.singleton import singleton
from typing import List, Optional, Dict, Any
import chromadb
import os

logger = AppLogger()


@singleton
class ChromaDbService(BaseService[DocumentDto]):
    """Service for managing vector database operations"""

    def __init__(self):
        super().__init__()
        self.config = flask_config
        logger.info(f"{self.config.CHROMA_CONTAINER}")
        logger.info(f"{self.config.COLLECTION}")
        logger.info(f"{self.config.PERSIST}")
        logger.info(f"{self.config.PERSIST_DIRECTORY}")
        self.embedding_function = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
        self.db = None
        self.client = None
        self.retriever = None

    def _document_to_dto(
        self, document: Document, collection_name: str = ""
    ) -> DocumentDto:
        """
        Convert Document to DocumentDto.

        Args:
            document: Document to convert
            collection_name: Name of the collection

        Returns:
            DocumentDto representation of the document
        """
        return DocumentDto(
            id=getattr(document, "id", None),
            content=document.page_content,
            metadata=document.metadata,
            collection_name=collection_name,
        )

    def build_collection(self, collection_name: str) -> None:
        """
        Build and initialize a collection.

        Args:
            collection_name: Name of the collection to build

        Raises:
            ServiceError: When collection building fails
        """
        result = self._safe_execute(
            "_perform_build", self._perform_build, collection_name
        )

    def _perform_build(self, collection_name: str) -> None:
        logger.info(f"Building ChromaDB collection: {collection_name}")
        if self.config.CHROMA_CONTAINER:
            logger.info(
                "The chromadb is in a container, chromadb is set on client mode."
            )
            self.client = chromadb.HttpClient(
                host=self.config.CHROMA_HOST,
                port=self.config.CHROMA_PORT,
                settings=Settings(allow_reset=True),
            )
            self.db = Chroma(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )

        if self.config.PERSIST and not self.config.CHROMA_CONTAINER:
            logger.info(
                f"The chroma db is on local machine, persistant folder is: {self.config.PERSIST_DIRECTORY}."
            )

            self.client = chromadb.PersistentClient(settings=Settings(allow_reset=True))

            self.db = Chroma(
                client=self.client,
                persist_directory=self.config.PERSIST_DIRECTORY,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )

        if not self.config.PERSIST and not self.config.CHROMA_CONTAINER:
            logger.info(
                "Chroma db on local machine is without persistence, PERSIST is set to false collection stored won't be saved"
            )
            self.client = chromadb.EphemeralClient()
            self.db = Chroma(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )
        self.retriever = self.db.as_retriever()

    def create(self, data: Dict[str, Any]) -> DocumentDto:
        """
        Create a new document in the vector database.

        Args:
            data: Document creation data containing content and collection_name

        Returns:
            Created DocumentDto instance

        Raises:
            ServiceError: When document creation fails
        """
        result = self._safe_execute("_perform_create", self._perform_create, data)
        if result is None:
            raise ServiceError("Document creation failed, no DocumentDto returned.")
        return result

    def _perform_create(self, data: Dict[str, Any]) -> DocumentDto:
        collection_name = data["collection_name"]
        self.build_collection(collection_name)

        doc = Document(page_content=data["content"], metadata=data.get("metadata", {}))
        doc_ids = self.db.add_documents([doc])

        return DocumentDto(
            id=doc_ids[0] if doc_ids else None,
            content=data["content"],
            metadata=data.get("metadata", {}),
            collection_name=collection_name,
        )

    def save_documents(self, docs: List[Document], collection_name: str) -> List[str]:
        """
        Save documents to a collection.

        Args:
            docs: List of documents to save
            collection_name: Name of the collection

        Returns:
            List of document IDs

        Raises:
            ServiceError: When document saving fails
        """
        result = self._safe_execute(
            "_perform_save_documents",
            self._perform_save_documents,
            docs,
            collection_name,
        )
        if result is None:
            raise ServiceError("Save documents failed.")
        return result

    def _perform_save_documents(
        self, docs: List[Document], collection_name: str
    ) -> List[str]:
        self.build_collection(collection_name)
        return self.db.add_documents(docs)

    def ingest_pdf_file(self, pdf_file_path: str, collection_name: str) -> List[str]:
        """
        Ingest a PDF file into the vector database.

        Args:
            pdf_file_path: Path to the PDF file
            collection_name: Name of the collection

        Returns:
            List of document IDs

        Raises:
            ServiceError: When PDF ingestion fails
        """
        result = self._safe_execute(
            "_perform_ingest_pdf",
            self._perform_ingest_pdf,
            pdf_file_path,
            collection_name,
        )
        if result is None:
            raise ServiceError("PDF ingestion failed.")
        return result

    def _perform_ingest_pdf(
        self, pdf_file_path: str, collection_name: str
    ) -> List[str]:
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024, chunk_overlap=100
        )
        chunks = text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)
        embedding_function = FastEmbedEmbeddings()

        return self.save_documents(docs, collection_name)

    def ingest_directory_files(
        self, directory_path: str, collection_name: str
    ) -> List[str]:
        """
        Ingest all files from a directory into the vector database.

        Args:
            directory_path: Path to the directory
            collection_name: Name of the collection

        Returns:
            List of document IDs

        Raises:
            ServiceError: When directory ingestion fails
        """
        result = self._safe_execute(
            "_perform_ingest_directory",
            self._perform_ingest_directory,
            directory_path,
            collection_name,
        )
        if result is None:
            raise ServiceError("Directory ingestion failed.")
        return result

    def _perform_ingest_directory(
        self, directory_path: str, collection_name: str
    ) -> List[str]:
        docs = DirectoryLoader(path=directory_path).load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024, chunk_overlap=100
        )
        chunks = text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)
        embedding_function = FastEmbedEmbeddings()
        return self.save_documents(docs, collection_name)

    def ingest_text_content(self, content: str, collection_name: str) -> List[str]:
        """
        Ingest text content into the vector database.

        Args:
            content: Text content to ingest
            collection_name: Name of the collection

        Returns:
            List of document IDs

        Raises:
            ServiceError: When text ingestion fails
        """
        result = self._safe_execute(
            "_perform_ingest_text", self._perform_ingest_text, content, collection_name
        )
        if result is None:
            raise ServiceError("Text ingestion failed.")
        return result

    def _perform_ingest_text(self, content: str, collection_name: str) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024, chunk_overlap=100
        )
        texts = text_splitter.split_text(content)
        docs = [Document(page_content=t) for t in texts]
        logger.info(f"About to save {len(docs)} documents")
        return self.save_documents(docs, collection_name)

    def get_dto_by_id(self, entity_id: str) -> DocumentDto:
        """
        Retrieve a document by its ID.

        Args:
            entity_id: ID of the document to retrieve

        Returns:
            DocumentDto instance if found

        Raises:
            ServiceError: When document retrieval fails
        """
        result = self._safe_execute(
            "_perform_get_by_id", self._perform_get_by_id, entity_id
        )
        if result is None:
            raise ServiceError("Get document by id failed, no DocumentDto returned.")
        return result

    def _perform_get_by_id(self, entity_id: str) -> DocumentDto:
        if not self.db:
            raise ServiceError("Database not initialized. Call build_collection first.")

        # ChromaDB doesn't have direct get by ID, so we'll search in the current collection
        results = self.db.get(ids=[entity_id])
        if not results["documents"]:
            raise NotFoundError("Document", str(entity_id))

        return DocumentDto(
            id=entity_id,
            content=results["documents"][0],
            metadata=results["metadatas"][0] if results["metadatas"] else {},
            collection_name="",  # We don't store collection name in the document
        )

    def get_all(self) -> List[DocumentDto]:
        """
        Retrieve all documents from the current collection.

        Returns:
            List of DocumentDto instances

        Raises:
            ServiceError: When document retrieval fails
        """
        result = self._safe_execute("_perform_get_all", self._perform_get_all)
        if result is None:
            raise ServiceError("Document get_all failed, no list returned.")
        return result

    def _perform_get_all(self) -> List[DocumentDto]:
        if not self.db:
            raise ServiceError("Database not initialized. Call build_collection first.")

        results = self.db.get()
        documents = []

        for i, doc_id in enumerate(results["ids"]):
            documents.append(
                DocumentDto(
                    id=doc_id,
                    content=results["documents"][i],
                    metadata=results["metadatas"][i] if results["metadatas"] else {},
                    collection_name="",
                )
            )

        return documents

    def update(self, entity_id: str, data: Dict[str, Any]) -> DocumentDto:
        """
        Update document information.

        Args:
            entity_id: ID of the document to update
            data: Fields to update

        Returns:
            Updated DocumentDto instance

        Raises:
            ServiceError: When document update fails
        """
        result = self._safe_execute(
            "_perform_update", self._perform_update, entity_id, data
        )
        if result is None:
            raise ServiceError("Document update failed, no DocumentDto returned.")
        return result

    def _perform_update(self, entity_id: str, data: Dict[str, Any]) -> DocumentDto:
        # ChromaDB doesn't support direct updates, so we delete and recreate
        self.delete(entity_id)
        return self.create(
            {
                "content": data.get("content", ""),
                "metadata": data.get("metadata", {}),
                "collection_name": data.get("collection_name", ""),
            }
        )

    def delete(self, entity_id: str) -> bool:
        """
        Delete a document.

        Args:
            entity_id: ID of the document to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When document deletion fails
        """
        result = self._safe_execute("_perform_delete", self._perform_delete, entity_id)
        if result is None:
            raise ServiceError("Document delete failed, no document deleted.")
        return result

    def _perform_delete(self, entity_id: str) -> bool:
        if not self.db:
            raise ServiceError("Database not initialized. Call build_collection first.")

        self.db.delete([entity_id])
        return True

    def delete_all_documents(self, collection_name: str) -> bool:
        """
        Delete all documents from a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When deletion fails
        """
        result = self._safe_execute(
            "_perform_delete_all", self._perform_delete_all, collection_name
        )
        if result is None:
            return False
        return result

    def _perform_delete_all(self, collection_name: str) -> bool:
        self.build_collection(collection_name)
        ids = []
        for doc_id in self.db.get()["ids"]:
            logger.info(doc_id)
            ids.append(doc_id)
        if ids:
            self.db.delete(ids)
        return True

    def delete_documents_by_ids(self, collection_name: str, ids: List[str]) -> bool:
        """
        Delete documents by their IDs.

        Args:
            collection_name: Name of the collection
            ids: List of document IDs to delete

        Returns:
            True if deletion was successful

        Raises:
            ServiceError: When deletion fails
        """
        result = self._safe_execute(
            "_perform_delete_by_ids", self._perform_delete_by_ids, collection_name, ids
        )
        if result is None:
            return False
        return result

    def _perform_delete_by_ids(self, collection_name: str, ids: List[str]) -> bool:
        self.build_collection(collection_name)
        logger.info(f"About to delete {len(ids)} documents in {collection_name}")
        self.db.delete(ids)
        logger.info(f"{len(ids)} docs deleted from collection {collection_name}.")
        return True

    def get_database(self) -> Chroma:
        """
        Get the Chroma database instance.

        Returns:
            Chroma database instance
        """
        return self.db

    def get_retriever_instance(self) -> VectorStoreRetriever:
        """
        Get the vector store retriever.

        Returns:
            VectorStoreRetriever instance
        """
        return self.retriever

    # Backward compatibility methods
    def build(self, collection_name: str) -> None:
        """Build collection (backward compatibility)"""
        self.build_collection(collection_name)

    def save_doc(self, docs: List[Document], collection_name: str) -> List[str]:
        """Save documents (backward compatibility)"""
        return self.save_documents(docs, collection_name)

    def ingest_pdf(self, pdf_file_path: str, collection_name: str) -> List[str]:
        """Ingest PDF (backward compatibility)"""
        return self.ingest_pdf_file(pdf_file_path, collection_name)

    def ingest_directory(self, directory_path: str, collection_name: str) -> List[str]:
        """Ingest directory (backward compatibility)"""
        return self.ingest_directory_files(directory_path, collection_name)

    def ingest_text(self, content: str, collection_name: str) -> List[str]:
        """Ingest text (backward compatibility)"""
        return self.ingest_text_content(content, collection_name)

    def delete_all(self, collection_name: str) -> bool:
        """Delete all documents (backward compatibility)"""
        return self.delete_all_documents(collection_name)

    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """Delete documents by IDs (backward compatibility)"""
        return self.delete_documents_by_ids(collection_name, ids)

    def get_db(self) -> Chroma:
        """Get database (backward compatibility)"""
        return self.get_database()

    def get_retriever(self) -> VectorStoreRetriever:
        """Get retriever (backward compatibility)"""
        return self.get_retriever_instance()

    # Missing method that rag_svc calls
    def ingest(self, file_path: str, collection_name: str) -> List[str]:
        """
        Generic ingest method that determines file type and calls appropriate method.

        Args:
            file_path: Path to the file to ingest
            collection_name: Name of the collection

        Returns:
            List of document IDs
        """
        if file_path.lower().endswith(".pdf"):
            return self.ingest_pdf(file_path, collection_name)
        else:
            # Assume it's a text file or directory
            if os.path.isdir(file_path):
                return self.ingest_directory(file_path, collection_name)
            else:
                # Read as text file
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return self.ingest_text(content, collection_name)
