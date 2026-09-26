"""Service wiring and the FastAPI dependencies that hand services to routes.

Every service is built exactly once, by build_services() below, from the
app lifespan (asgi.py), and stored on app.state.services. Routes receive
them through Depends -- e.g. `bot_svc: BotServiceDep` -- instead of
importing a module-level instance, so a test can swap any of them with
`app.dependency_overrides[get_bot_service] = lambda: fake_bot_svc`.

One instance per app, not per request: several services hold state that
must outlive a request -- RagService.store (in-memory chat histories +
its asyncio.Lock), ChromaDbService's FastEmbed model (slow to load),
YamlSvc's parsed YAML, LlmService's ChatMistralAI client.

Services get their collaborators through their constructors; the order
below is the dependency order, and it has no cycle (PromptService reads
and writes Bot.prompt itself instead of going through BotService for
exactly that reason -- see prompt_svc.py).

The providers are `async def` on purpose: FastAPI calls an async
dependency inline, whereas a plain `def` one is dispatched to the
threadpool on every request -- pointless for an attribute lookup.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from ai_server.services.authent_svc import AuthenticationService
from ai_server.services.avatar_svc import AvatarService
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.services.bot_svc import BotService
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.services.google_authent_svc import GoogleAuthentSvc
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.llm_svc import LlmService
from ai_server.services.message_svc import MessageService
from ai_server.services.prompt_svc import PromptService
from ai_server.services.rag_svc import RagService
from ai_server.services.template_svc import TemplateSvc
from ai_server.services.token_tracking_svc import TokenTrackingService
from ai_server.services.user_admin_svc import UserAdminService
from ai_server.services.yaml_svc import YamlSvc


@dataclass(frozen=True)
class Services:
    avatar: AvatarService
    bot_assignment: BotAssignmentService
    token_tracking: TokenTrackingService
    message: MessageService
    yaml: YamlSvc
    chroma_db: ChromaDbService
    prompt: PromptService
    knowledge: KnowledgeSvc
    template: TemplateSvc
    bot_parameters: BotParametersService
    bot: BotService
    user_admin: UserAdminService
    llm: LlmService
    rag: RagService
    authent: AuthenticationService
    google_authent: GoogleAuthentSvc


def build_services() -> Services:
    avatar = AvatarService()
    bot_assignment = BotAssignmentService()
    token_tracking = TokenTrackingService()
    message = MessageService()
    yaml = YamlSvc()
    chroma_db = ChromaDbService()
    prompt = PromptService()
    knowledge = KnowledgeSvc(chroma_db)
    template = TemplateSvc(knowledge)
    bot_parameters = BotParametersService(yaml, prompt)
    bot = BotService(avatar, bot_assignment, bot_parameters, knowledge, template)
    user_admin = UserAdminService(bot_assignment, bot)
    llm = LlmService(token_tracking, user_admin)
    rag = RagService(llm, chroma_db, prompt, message)
    return Services(
        avatar=avatar,
        bot_assignment=bot_assignment,
        token_tracking=token_tracking,
        message=message,
        yaml=yaml,
        chroma_db=chroma_db,
        prompt=prompt,
        knowledge=knowledge,
        template=template,
        bot_parameters=bot_parameters,
        bot=bot,
        user_admin=user_admin,
        llm=llm,
        rag=rag,
        authent=AuthenticationService(user_admin),
        google_authent=GoogleAuthentSvc(user_admin),
    )


def _services(request: Request) -> Services:
    return request.app.state.services


async def get_avatar_service(request: Request) -> AvatarService:
    return _services(request).avatar


async def get_bot_assignment_service(request: Request) -> BotAssignmentService:
    return _services(request).bot_assignment


async def get_token_tracking_service(request: Request) -> TokenTrackingService:
    return _services(request).token_tracking


async def get_message_service(request: Request) -> MessageService:
    return _services(request).message


async def get_knowledge_service(request: Request) -> KnowledgeSvc:
    return _services(request).knowledge


async def get_template_service(request: Request) -> TemplateSvc:
    return _services(request).template


async def get_bot_parameters_service(request: Request) -> BotParametersService:
    return _services(request).bot_parameters


async def get_bot_service(request: Request) -> BotService:
    return _services(request).bot


async def get_user_admin_service(request: Request) -> UserAdminService:
    return _services(request).user_admin


async def get_rag_service(request: Request) -> RagService:
    return _services(request).rag


async def get_authentication_service(request: Request) -> AuthenticationService:
    return _services(request).authent


async def get_google_authent_service(request: Request) -> GoogleAuthentSvc:
    return _services(request).google_authent


AvatarServiceDep = Annotated[AvatarService, Depends(get_avatar_service)]
BotAssignmentServiceDep = Annotated[
    BotAssignmentService, Depends(get_bot_assignment_service)
]
TokenTrackingServiceDep = Annotated[
    TokenTrackingService, Depends(get_token_tracking_service)
]
MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
KnowledgeServiceDep = Annotated[KnowledgeSvc, Depends(get_knowledge_service)]
TemplateServiceDep = Annotated[TemplateSvc, Depends(get_template_service)]
BotParametersServiceDep = Annotated[
    BotParametersService, Depends(get_bot_parameters_service)
]
BotServiceDep = Annotated[BotService, Depends(get_bot_service)]
UserAdminServiceDep = Annotated[UserAdminService, Depends(get_user_admin_service)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
AuthenticationServiceDep = Annotated[
    AuthenticationService, Depends(get_authentication_service)
]
GoogleAuthentServiceDep = Annotated[
    GoogleAuthentSvc, Depends(get_google_authent_service)
]
