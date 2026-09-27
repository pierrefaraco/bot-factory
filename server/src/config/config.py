"""Configuration for the application"""

import os
import json
from logging import _nameToLevel

from src.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()

API_URL_PREFIX = "/api"


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    """Integer env var, falling back to `default` (with a warning) when
    it isn't a number or is below `minimum`."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        logger.warning(f"Invalid {name}={value!r}, using {default}")
        return default
    if parsed < minimum:
        logger.warning(f"{name}={parsed} is below {minimum}, using {default}")
        return default
    return parsed


class BaseConfig:
    """Core application properties (auth, database)."""

    # Application session secret key
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", '^ZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2x")sZQjGKyBVf2xx'
    )
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class AppConfig(BaseConfig):
    """Application properties."""

    # Server properties
    APP_NAME = os.environ.get("APP_NAME", default="src_BACKEND")
    HOSTNAME = os.environ.get("HOSTNAME", default="src_BACKEND")
    APP_ENV = os.environ.get("APP_ENV", default="production")
    APP_VERSION = os.environ.get("APP_VERSION", default="<LOCAL_TEST_VERSION>")

    value = os.environ.get("API_URL_PREFIX", default=API_URL_PREFIX)
    if not (isinstance(value, str) and value.strip()):
        value = API_URL_PREFIX
    if value.endswith("/"):
        value = value[:-1]

    URL_SUBDIRECTORY = value

    # Logger properties
    LOGGER_LVL = "INFO"
    value = os.environ.get("LOGGER_LVL", default="INFO").upper()
    if value in list(_nameToLevel.keys()):
        LOGGER_LVL = value

    # Prompt-construction tracing (LangChainFacade.build / PromptDebugLogger):
    # independent of LOGGER_LVL so it can be switched on/off without
    # enabling full app-wide DEBUG logging. Defaults to LOGGER_LVL.
    PROMPT_DEBUG_LVL = LOGGER_LVL
    value = os.environ.get("PROMPT_DEBUG_LVL", default="").upper()
    if value in list(_nameToLevel.keys()):
        PROMPT_DEBUG_LVL = value

    VERBOSE = False
    value = os.environ.get("VERBOSE", default="FALSE").upper()
    if value == "TRUE":
        VERBOSE = True


    OPERATIONAL_LOG_FILE = os.environ.get(
        "OPERATIONAL_LOG_FILE", default="/opt/ipc/logs/{}-src_hello.log"
    )

    OPERATIONAL_LOG_FILE_MAXSIZE = 100
    value = os.environ.get("OPERATIONAL_LOG_FILE_MAXSIZE", default="100")
    try:
        value = int(value)
        if value > 1:
            OPERATIONAL_LOG_FILE_MAXSIZE = value
    except ValueError:
        pass

    # if isinstance (value, str) and value.startswith("'[") and value.endswith("]'"):
    try:
        value_list = json.loads(value)
        if isinstance(value_list, list) and all(isinstance(x, str) for x in value_list):
            LDAP_GROUP_MEMBERSHIP = value_list
    except Exception:
        # Parsing failed
        pass

    # Local user
    LOCAL_USER = None
    value = os.environ.get("LOCAL_USER", default=None)
    if isinstance(value, str) and value.strip():
        LOCAL_USER = value

    LOCAL_USER_PASSWORD = None
    value = os.environ.get("LOCAL_USER_PASSWORD", default=None)
    if isinstance(value, str) and value.strip():
        LOCAL_USER_PASSWORD = value

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/pdf")
    MAX_PDF_SIZE_BYTES = int(os.environ.get("MAX_PDF_SIZE_BYTES", 20 * 1024 * 1024))

    # ===== Vector store (see services/vector_store_facade.py) =====

    # Where ChromaDB runs: CHROMA_CONTAINER=true -> a Chroma server at
    # CHROMA_HOST:CHROMA_PORT (docker compose's "chromadb" service);
    # otherwise in-process, persisted under PERSIST_DIRECTORY if
    # PERSIST=true, in memory only (lost on restart) if not.
    CHROMA_CONTAINER = os.environ.get("CHROMA_CONTAINER", "false").lower() == "true"
    CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
    CHROMA_PORT = _int_env("CHROMA_PORT", 8000)
    PERSIST = os.environ.get("PERSIST", "false").lower() == "true"
    PERSIST_DIRECTORY = os.environ.get("PERSIST_DIRECTORY", "./chroma_db")

    # FastEmbed model turning text into vectors, at ingestion and at query
    # time alike. multilingual-e5-large: multilingual (the knowledge bases
    # are in French; the former default, BAAI/bge-small-en-v1.5, was
    # English-only), 512-token input, 2.2 GB -- downloaded once into
    # FASTEMBED_CACHE_PATH. Changing it makes every existing collection
    # unusable (vectors from two models can't be compared -- and with the
    # same dimension, Chroma won't even complain, retrieval just silently
    # returns junk) until each bot is re-ingested (POST /api/rag/reindex/{bot_id}).
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

    # Chunking at ingestion, in characters. 1024 is ~270 tokens of French
    # text: well under the embedding model's 512-token input limit (longer
    # chunks get truncated before being embedded), yet long enough to hold
    # a full paragraph. The overlap repeats the end of a chunk at the start
    # of the next one, so a sentence cut at a boundary still appears whole
    # in one of them. Only applies to what gets ingested next.
    RAG_CHUNK_SIZE = _int_env("RAG_CHUNK_SIZE", 1024, minimum=100)
    RAG_CHUNK_OVERLAP = _int_env("RAG_CHUNK_OVERLAP", 150, minimum=0)
    if RAG_CHUNK_OVERLAP >= RAG_CHUNK_SIZE:
        logger.warning(
            f"RAG_CHUNK_OVERLAP={RAG_CHUNK_OVERLAP} must be < RAG_CHUNK_SIZE="
            f"{RAG_CHUNK_SIZE}, using {RAG_CHUNK_SIZE // 10}"
        )
        RAG_CHUNK_OVERLAP = RAG_CHUNK_SIZE // 10

    # Number of chunks the RAG retriever pulls per question. LangChain's
    # Chroma retriever defaults to 4, which is too small once a knowledge
    # base grows past a handful of chunks: on a real 26-page hotel PDF
    # (48 chunks at the default 1024-char chunk size), the chunk actually
    # answering a specific question ranked #11 by cosine similarity and
    # was silently dropped every time. Each chunk ends up in the prompt:
    # 12 x ~250 tokens is ~3k tokens of context per question.
    RAG_RETRIEVER_K = _int_env("RAG_RETRIEVER_K", 12, minimum=1)

    # Max tokens an account (itself + its guests, who are billed to their
    # parent -- see TokenCountingCallback in llm_svc.py) may consume over a
    # rolling 24h window before chat requests are refused with a 429.
    # 0 or unset = unlimited. Admins are never limited.
    TOKEN_LIMIT_PER_USER_24H = 0
    value = os.environ.get("TOKEN_LIMIT_PER_USER_24H", default="0")
    try:
        value = int(value)
        if value > 0:
            TOKEN_LIMIT_PER_USER_24H = value
    except ValueError:
        logger.warning(f"Invalid TOKEN_LIMIT_PER_USER_24H={value!r}, token limit disabled")

    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "your-secret-key-change-this-in-production"
    )


    MISTRAL_API_KEY  = os.environ.get(
        "MISTRAL_API_KEY", "your-secret-key-change-this-in-production"
    )
    MISTRAL_MODEL  = os.environ.get(
            "VIBE_MODEL", "your-secret-key-change-this-in-production"
        )

    # OAuth client ID Google (Google Identity Services) : doit être le même
    # sur le frontend (client/src/assets/env.js) et le backend, sinon
    # verify_oauth2_token() rejette le jeton ("Invalid email or password").
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID",
        "913568537440-clfeb4jvitdh7111s1j8cv6u8gb6t3dv.apps.googleusercontent.com",
    )

app_config = AppConfig()
