"""Unit tests for VectorStoreFacade against an in-process ephemeral
ChromaDB and deterministic fake embeddings: no Chroma container, no
embedding model download."""

import uuid
from types import SimpleNamespace

from langchain_core.embeddings import DeterministicFakeEmbedding

from ai_server.services import vector_store_facade
from ai_server.services.vector_store_facade import PrefixedEmbeddings, VectorStoreFacade


def _facade():
    facade = VectorStoreFacade(embedding_function=DeterministicFakeEmbedding(size=16))
    facade.config = SimpleNamespace(
        CHROMA_CONTAINER=False,
        PERSIST=False,
        PERSIST_DIRECTORY="",
        RAG_RETRIEVER_K=10,
    )
    return facade


def _collection():
    # The ephemeral client is shared process-wide: one fresh name per test.
    return f"Collection{uuid.uuid4().hex}"


def _stored(facade, collection):
    return facade.build_retriever(collection).invoke("anything")


def test_ingest_text_tags_every_chunk_with_the_metadata():
    facade, collection = _facade(), _collection()

    ids = facade.ingest_text("x" * 3000, collection, metadata={"knowledge_id": 1})

    docs = _stored(facade, collection)
    assert len(ids) == len(docs) > 1  # long text split into several chunks
    assert all(doc.metadata == {"knowledge_id": 1} for doc in docs)


def test_delete_documents_by_metadata_only_removes_the_matching_chunks():
    facade, collection = _facade(), _collection()
    facade.ingest_text("chapitre un", collection, metadata={"knowledge_id": 1})
    facade.ingest_text("chapitre deux", collection, metadata={"knowledge_id": 2})

    facade.delete_documents_by_metadata(collection, {"knowledge_id": 1})

    assert [d.page_content for d in _stored(facade, collection)] == ["chapitre deux"]


def test_delete_all_empties_only_its_own_collection():
    facade, bot_a, bot_b = _facade(), _collection(), _collection()
    facade.ingest_text("bot a", bot_a)
    facade.ingest_text("bot b", bot_b)

    assert facade.delete_all(bot_a) is True
    assert facade.delete_all(bot_a) is True  # already empty: still fine

    assert _stored(facade, bot_a) == []
    assert [d.page_content for d in _stored(facade, bot_b)] == ["bot b"]


class RecordingEmbeddings(DeterministicFakeEmbedding):
    """Fake embeddings that remember the exact texts they were asked to embed."""

    seen: list = []

    def embed_documents(self, texts):
        self.seen.extend(texts)
        return super().embed_documents(texts)

    def embed_query(self, text):
        self.seen.append(text)
        return super().embed_query(text)


def test_prefixed_embeddings_prefix_what_is_embedded_not_what_is_stored():
    inner = RecordingEmbeddings(size=16, seen=[])
    facade = VectorStoreFacade(
        embedding_function=PrefixedEmbeddings(inner, "query: ", "passage: ")
    )
    facade.config = _facade().config
    collection = _collection()

    facade.ingest_text("Le spa ouvre à 10h.", collection)
    docs = _stored(facade, collection)

    assert inner.seen == ["passage: Le spa ouvre à 10h.", "query: anything"]
    assert [d.page_content for d in docs] == ["Le spa ouvre à 10h."]


def test_build_embeddings_only_wraps_models_that_expect_prefixes(monkeypatch):
    monkeypatch.setattr(
        vector_store_facade,
        "FastEmbedEmbeddings",
        lambda model_name: SimpleNamespace(model_name=model_name),
    )

    e5 = vector_store_facade.build_embeddings("intfloat/multilingual-e5-large")
    bge = vector_store_facade.build_embeddings("BAAI/bge-small-en-v1.5")

    assert isinstance(e5, PrefixedEmbeddings)
    assert (e5.query_prefix, e5.document_prefix) == ("query: ", "passage: ")
    assert not isinstance(bge, PrefixedEmbeddings)
