"""ASGI entrypoint: the FastAPI app, its routers, CORS and error handlers.

Startup (lifespan) fails fast, before serving any request, on unsafe
configuration (ConfigValidator), an unreachable vector store, or a
failure to create the super admin account.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.config import AppConfig
from src.config.constant import ADMIN_ROLE
from src.config.validator import ConfigValidator
from src.database.session import async_db_session_scope
from src.dependencies.services import build_services
from src.exceptions.api_error import ApiError
from src.log.bot_factory_logger import BotFactoryLogger
from src.log.log_config import LogManager
from src.routers import (
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

LogManager().setup_logger(AppConfig.LOGGER_LVL, AppConfig.PROMPT_DEBUG_LVL)
logger = BotFactoryLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{AppConfig.APP_NAME} version {AppConfig.APP_VERSION} starting...")
    ConfigValidator.validate_all(AppConfig)

    # Built before serving so routes' Depends(get_*_service) (see
    # dependencies/services.py) always find them, and so a broken service
    # constructor fails startup instead of the first request.
    services = build_services()
    app.state.services = services

    # Fail fast if the vector store RAG depends on isn't reachable,
    # instead of starting up and only failing later on the first chat.
    services.vector_store.check_connection()

    async with async_db_session_scope():
        user_admin_svc = services.user_admin
        super_admin_login = os.getenv("SUPER_ADMIN_LOGIN")
        if super_admin_login and not await user_admin_svc.get_user_by_email(
            super_admin_login
        ):
            super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "")
            ConfigValidator.raise_if_any(
                ConfigValidator.super_admin_password_errors(super_admin_password)
            )
            logger.info(f"Creating super admin user: {super_admin_login}")
            await user_admin_svc.register_user(
                mail=super_admin_login,
                user_name=super_admin_login,
                password=super_admin_password,
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
    """Generic 500 for unhandled exceptions, without leaking their text.
    FastAPI's HTTPException handling and the two handlers above take
    priority."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
