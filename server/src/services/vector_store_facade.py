"""Facade over the vector store: one collection per bot
(f"Collection{bot_id}"), holding its knowledge chunks.

Hides the chromadb client (container / persistent / ephemeral mode, per
config), LangChain's Chroma wrapper, the PDF loader, the text splitter,
the chunk metadata filtering and the FastEmbed embedding model behind six
methods: check_connection() at startup, build_retriever() for
LangChainFacade, and ingest_text() / ingest_pdf() / delete_all() /
delete_documents_by_metadata() for KnowledgeSvc.

One instance per app, shared by every concurrent request: no method keeps
a collection on `self`. Each call opens its own client + collection as
local values, so two requests on two different bots can never end up
reading or writing each other's collection.

Every method is blocking (chromadb client I/O, embedding computation)
with no async equivalent: async callers run them via run_in_threadpool.
"""

import os
import time
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.config import app_config
from src.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()

# Some embedding models are trained to embed a question and a passage
# differently, told apart by a text prefix -- and neither FastEmbed nor
# LangChain adds it. Without it, e5 models still run but retrieve noticeably
# worse. Keyed by model-name prefix: (query prefix, document prefix).
EMBEDDING_PREFIXES = {
    "intfloat/": ("query: ", "passage: "),  # the e5 family
}


class PrefixedEmbeddings(Embeddings):
    """Wraps an embedding model to prepend `query_prefix` to questions
    (embed_query, at retrieval) and `document_prefix` to stored chunks
    (embed_documents, at ingestion). The chunks' stored text is unchanged:
    only what gets embedded is prefixed."""

    def __init__(self, inner: Embeddings, query_prefix: str, document_prefix: str):
        self.inner = inner
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.inner.embed_documents([self.document_prefix + t for t in texts])

    def embed_query(self, text: str) -> List[float]:
        return self.inner.embed_query(self.query_prefix + text)


def build_embeddings(model_name: str) -> Embeddings:
    """FastEmbed model `model_name`, wrapped in PrefixedEmbeddings when
    the model expects prefixes (see EMBEDDING_PREFIXES)."""
    embeddings = FastEmbedEmbeddings(model_name=model_name)
    for name_prefix, (query_prefix, document_prefix) in EMBEDDING_PREFIXES.items():
        if model_name.startswith(name_prefix):
            logger.info(
                f"Embedding model {model_name}: prefixes {query_prefix!r} (questions) "
                f"/ {document_prefix!r} (chunks)"
            )
            return PrefixedEmbeddings(embeddings, query_prefix, document_prefix)
    return embeddings


class VectorStoreFacade:

    def __init__(self, embedding_function: Optional[Embeddings] = None):
        self.config = app_config
        if self.config.CHROMA_CONTAINER:
            logger.info(f"ChromaDB: server at {self.config.CHROMA_HOST}:{self.config.CHROMA_PORT}")
        elif self.config.PERSIST:
            logger.info(f"ChromaDB: in-process, persisted in dir {self.config.PERSIST_DIRECTORY}")
        else:
            logger.info("ChromaDB: in-process, in memory only (lost on restart)")
        # Loaded once here (slow, and downloaded on first use -- see
        # FASTEMBED_CACHE_PATH): shared by every collection opened below.
        self.embedding_function = embedding_function or build_embeddings(
            self.config.EMBEDDING_MODEL
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.RAG_CHUNK_SIZE,
            chunk_overlap=self.config.RAG_CHUNK_OVERLAP,
        )
        logger.info(
            f"Vector store settings: embedding_model={self.config.EMBEDDING_MODEL} "
            f"chunk_size={self.config.RAG_CHUNK_SIZE} "
            f"chunk_overlap={self.config.RAG_CHUNK_OVERLAP} "
            f"retriever_k={self.config.RAG_RETRIEVER_K}"
        )

    # ===== PUBLIC API =====

    def check_connection(self) -> None:
        """
        Verify that the configured ChromaDB backend is reachable.

        Raises:
            Exception: If ChromaDB cannot be reached. Left to propagate so
            the app fails to start rather than silently serving RAG
            requests against a dead vector store.
        """
        logger.info("Checking ChromaDB connectivity...")
        start = time.perf_counter()
        try:
            self._make_client().heartbeat()
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"ChromaDB connectivity check failed after {elapsed_ms:.1f}ms: {e}"
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"ChromaDB connection OK ({elapsed_ms:.1f}ms).")

    def build_retriever(self, collection_name: str) -> VectorStoreRetriever:
        """Retriever returning the RAG_RETRIEVER_K chunks of
        `collection_name` closest to a question."""
        logger.debug(f"Building retriever for ChromaDB collection: {collection_name}")
        start = time.perf_counter()
        try:
            db, mode = self._open_collection(collection_name)
            retriever = db.as_retriever(
                search_kwargs={"k": self.config.RAG_RETRIEVER_K}
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"Failed to build retriever for collection '{collection_name}' after {elapsed_ms:.1f}ms: {e}"
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Retriever for ChromaDB collection '{collection_name}' built - mode={mode} - {elapsed_ms:.1f}ms"
        )
        return retriever

    def ingest_text(
        self,
        content: str,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Split `content` into chunks, each tagged with `metadata` (e.g.
        knowledge_id), and store them; returns the new chunk ids."""
        texts = self.text_splitter.split_text(content)
        docs = [
            Document(page_content=t, metadata=dict(metadata) if metadata else {})
            for t in texts
        ]
        logger.debug(
            f"Text content split into {len(docs)} chunks - ingesting into collection '{collection_name}'"
        )
        return self._save(docs, collection_name)

    def ingest_pdf(
        self,
        pdf_file_path: str,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Same as ingest_text() for every page of a PDF file."""
        filename = os.path.basename(pdf_file_path)
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        if metadata:
            for doc in docs:
                doc.metadata.update(metadata)
        chunks = filter_complex_metadata(self.text_splitter.split_documents(docs))
        logger.debug(
            f"PDF '{filename}' loaded: {len(docs)} pages, {len(chunks)} chunks - "
            f"ingesting into collection '{collection_name}'"
        )
        return self._save(chunks, collection_name)

    def delete_all(self, collection_name: str) -> bool:
        """Empty `collection_name` (the collection itself is kept)."""
        db, _mode = self._open_collection(collection_name)
        ids = db.get()["ids"]
        if not ids:
            logger.debug(f"No documents to delete in collection '{collection_name}'")
            return True
        start = time.perf_counter()
        db.delete(ids)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Deleted all {len(ids)} documents from collection '{collection_name}' ({elapsed_ms:.1f}ms)"
        )
        return True

    def delete_documents_by_metadata(
        self, collection_name: str, where: Dict[str, Any]
    ) -> bool:
        """Delete the chunks matching a Chroma metadata filter, e.g.
        {"knowledge_id": 42}."""
        db, _mode = self._open_collection(collection_name)
        start = time.perf_counter()
        db.delete(where=where)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Deleted documents matching {where} from collection '{collection_name}' ({elapsed_ms:.1f}ms)"
        )
        return True

    # ===== INTERNALS =====

    def _make_client(self):
        if self.config.CHROMA_CONTAINER:
            return chromadb.HttpClient(
                host=self.config.CHROMA_HOST,
                port=self.config.CHROMA_PORT,
                settings=Settings(allow_reset=True),
            )
        if self.config.PERSIST:
            return chromadb.PersistentClient(
                path=self.config.PERSIST_DIRECTORY,
                settings=Settings(allow_reset=True),
            )
        return chromadb.EphemeralClient()

    def _open_collection(self, collection_name: str) -> tuple[Chroma, str]:
        """A fresh client + Chroma vector store for `collection_name`, as
        local values (see the module docstring), plus a label of the
        client mode for logging."""
        client = self._make_client()
        if self.config.CHROMA_CONTAINER:
            mode = "container (client mode)"
            db = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )
        elif self.config.PERSIST:
            mode = f"local persistent (dir={self.config.PERSIST_DIRECTORY})"
            db = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )
        else:
            mode = "local ephemeral (no persistence)"
            db = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )
        return db, mode

    def _save(self, docs: List[Document], collection_name: str) -> List[str]:
        db, _mode = self._open_collection(collection_name)
        start = time.perf_counter()
        try:
            doc_ids = db.add_documents(docs)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"ChromaDB add_documents failed for collection '{collection_name}' "
                f"({len(docs)} docs) after {elapsed_ms:.1f}ms: {e}"
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Saved {len(doc_ids)} documents to collection '{collection_name}' - {elapsed_ms:.1f}ms"
        )
        return doc_ids
