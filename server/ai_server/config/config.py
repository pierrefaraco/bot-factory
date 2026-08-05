"""Configuration for the application"""

import os
import json
from logging import _nameToLevel

from ai_server.log.app_logger import AppLogger

logger = AppLogger()

API_URL_PREFIX = "/api"


class FlaskConfig:
    """Flask properties."""

    # Application session secret key
    JWT_SECRET_KEY = '^ZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2x")sZQjGKyBVf2xx'
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class AppConfig(FlaskConfig):
    """Application properties."""

    # Server properties
    APP_NAME = os.environ.get("APP_NAME", default="AI_SERVER_BACKEND")
    HOSTNAME = os.environ.get("HOSTNAME", default="AI_SERVER_BACKEND")
    FLASK_ENV = os.environ.get("FLASK_ENV", default="production")
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

    VERBOSE = False
    value = os.environ.get("VERBOSE", default="FALSE").upper()
    if value == "TRUE":
        VERBOSE = True

    DEACTIVATE_SERVER_LOG = True
    value = os.environ.get("DEACTIVATE_SERVER_LOG", default="TRUE").upper()
    if value == "FALSE":
        DEACTIVATE_SERVER_LOG = False

    OPERATIONAL_LOG_FILE = os.environ.get(
        "OPERATIONAL_LOG_FILE", default="/opt/ipc/logs/{}-AI_SERVER_hello.log"
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

    CHROMA_CONTAINER = os.environ.get("CHROMA_CONTAINER", "false").lower() in ("true")
    CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
    CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
    COLLECTION = "BOOKS"
    PERSIST = os.environ.get("PERSIST", "false").lower() in ("true")
    PERSIST_DIRECTORY = os.environ.get("PERSIST_DIRECTORY", "./chroma_db")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/pdf")

    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "your-secret-key-change-this-in-production"
    )


    MISTRAL_API_KEY  = os.environ.get(
        "MISTRAL_API_KEY", "your-secret-key-change-this-in-production"
    )
    MISTRAL_MODEL  = os.environ.get(
            "VIBE_MODEL", "your-secret-key-change-this-in-production"
        )

flask_config = AppConfig()
