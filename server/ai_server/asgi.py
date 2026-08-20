"""ASGI entrypoint for ai-server.

Every REST endpoint that used to live in Flask blueprints under
ai_server/rest/*.py has been ported to a native FastAPI router in
ai_server/routers/*.py, registered below. There is no Flask app left
anywhere in this process: the last two things that needed one --
Model.query/db.session (see ai_server/dao/database.py) and JWT issuing
(see ai_server/dependencies/auth.py's create_access_token) -- have both
been moved onto framework-independent replacements.

CORS used to be handled twice on the old Flask side (Flask-CORS's
CORS(app, ...) plus a manual after_request adding a second, wider set of
allowed headers). Both are merged into the single CORSMiddleware config
below so a request gets exactly one set of CORS headers, not two
independently-configured ones.

Startup here fails fast (refuses to start serving) the same way the old
Flask create_app() did at import time: raising inside a FastAPI lifespan
before its `yield` stops uvicorn from ever accepting a connection, same
as the old code raising during ai_server.main's module import used to.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_server.config.config import AppConfig
from ai_server.config.constant import ADMIN_ROLE
from ai_server.dao.database import db_session_scope
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.log.log_config import LogManager
from ai_server.routers import (
    authent_router,
    avatar_router,
    bot_assignment_router,
    bot_parameters_router,
    bot_router,
    knowledge_router,
    rag_router,
    token_stats_router,
    users_admin_router,
)
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.services.user_admin_svc import UserAdminService

LogManager().setup_logger(AppConfig.LOGGER_LVL)
logger = BotFactoryLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{AppConfig.APP_NAME} version {AppConfig.APP_VERSION} starting...")

    with db_session_scope():
        # Fail fast if the vector store RAG depends on isn't reachable,
        # instead of starting up and only failing later on the first chat.
        ChromaDbService().check_connection()

        user_admin_svc = UserAdminService()
        super_admin_login = os.getenv("SUPER_ADMIN_LOGIN")
        if super_admin_login and not user_admin_svc.get_user_by_email(super_admin_login):
            logger.info(f"Creating super admin user: {super_admin_login}")
            user_admin_svc.register_user(
                mail=super_admin_login,
                user_name=super_admin_login,
                password=os.getenv("SUPER_ADMIN_PASSWORD"),
                roles=ADMIN_ROLE,
                parent_id=-1,
                is_active=True,
            )

    logger.info(f"{AppConfig.APP_NAME} version {AppConfig.APP_VERSION} started and ready.")
    yield
    logger.info(f"{AppConfig.APP_NAME} version {AppConfig.APP_VERSION} stopped.")


app = FastAPI(
    title=AppConfig.APP_NAME,
    version=AppConfig.APP_VERSION,
    # Nothing publishes a doc page today: SpecTree's self-hosted Swagger UI
    # was Flask-only and is gone along with Flask; FastAPI's own hasn't
    # been wired up as a replacement.
    docs_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "X-Frame-Token",
        "X-CSRF-Token",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Client-Security-Token",
        "Accept-Encoding",
        "X-Auth-Token",
    ],
)


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


def _format_validation_error(exc: RequestValidationError) -> str:
    """FastAPI's RequestValidationError.errors() takes no kwargs (unlike
    pydantic's own ValidationError.errors()), so this can't reuse
    config/validation.py's pydantic_error_messages() -- same idea,
    adapted."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return "; ".join(parts)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """{"error": "..."} instead of FastAPI's default {"detail": [...]}."""
    return JSONResponse(
        status_code=400,
        content={"error": _format_validation_error(exc)},
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


app.include_router(authent_router.router)
app.include_router(token_stats_router.router)
app.include_router(avatar_router.router)
app.include_router(bot_parameters_router.router)
app.include_router(bot_router.router)
app.include_router(bot_assignment_router.router)
app.include_router(knowledge_router.router)
app.include_router(users_admin_router.router)
app.include_router(rag_router.router)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Every migrated Flask handler ended with the same
    `except Exception: return {"error": "Internal server error"}, 500` --
    one catch-all here instead of repeating it in each native route.
    Only reached for genuinely unhandled exceptions: FastAPI's own
    HTTPException handling and the two handlers above take priority."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
