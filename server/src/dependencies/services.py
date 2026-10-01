"""Service wiring and the FastAPI dependencies that hand services to routes.

Every service is built exactly once, by build_services() below, from the
app lifespan (asgi.py), and stored on app.state.services. Routes receive
them through Depends -- e.g. `bot_svc: BotServiceDep` -- instead of
importing a module-level instance, so a test can swap any of them with
`app.dependency_overrides[get_bot_service] = lambda: fake_bot_svc`.

One instance per app, not per request: several services hold state that
must outlive a request -- RagService.store (in-memory chat histories +
its asyncio.Lock), VectorStoreFacade's FastEmbed model (slow to load),
YamlSvc's parsed YAML, LlmService's ChatMistralAI client.

Services get their collaborators -- other services and repositories (see
repositories/) -- through their constructors; the order below is the
dependency order, and it has no cycle (PromptService reads and writes
Bot.prompt itself instead of going through BotService for exactly that
reason -- see prompt_svc.py). Repositories are stateless (the session
comes from the request, see repositories/base.py), so one instance each
is shared the same way.

The providers are `async def` on purpose: FastAPI calls an async
dependency inline, whereas a plain `def` one is dispatched to the
threadpool on every request -- pointless for an attribute lookup.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from src.repositories import (
    BotAssignmentRepository,
    BotAvatarRepository,
    BotParametersRepository,
    BotRepository,
    ConversationRepository,
    KnowledgeRepository,
    MagicLinkRepository,
    TokenUsageRepository,
    UserRepository,
)
from src.services.authent_svc import AuthenticationService
from src.services.avatar_svc import AvatarService
from src.services.bot_assignment_svc import BotAssignmentService
from src.services.bot_parameters_svc import BotParametersService
from src.services.bot_svc import BotService
from src.services.chat_facade import ChatFacade
from src.services.google_authent_svc import GoogleAuthentSvc
from src.services.knowledge_svc import KnowledgeSvc
from src.services.langchain_facade import LangChainFacade
from src.services.llm_svc import LlmService
from src.services.magic_link_svc import MagicLinkService
from src.services.message_svc import MessageService
from src.services.prompt_svc import PromptService
from src.services.rag_svc import RagService
from src.services.template_svc import TemplateSvc
from src.services.token_tracking_svc import TokenTrackingService
from src.services.user_admin_svc import UserAdminService
from src.services.vector_store_facade import VectorStoreFacade
from src.services.yaml_svc import YamlSvc


@dataclass(frozen=True)
class Services:
    avatar: AvatarService
    bot_assignment: BotAssignmentService
    token_tracking: TokenTrackingService
    message: MessageService
    yaml: YamlSvc
    vector_store: VectorStoreFacade
    prompt: PromptService
    knowledge: KnowledgeSvc
    template: TemplateSvc
    bot_parameters: BotParametersService
    bot: BotService
    user_admin: UserAdminService
    llm: LlmService
    langchain: LangChainFacade
    rag: RagService
    chat: ChatFacade
    authent: AuthenticationService
    google_authent: GoogleAuthentSvc
    magic_link: MagicLinkService


def build_services() -> Services:
    token_usage_repo = TokenUsageRepository()
    bot_assignment_repo = BotAssignmentRepository()
    bot_repo = BotRepository()
    user_repo = UserRepository()
    conversation_repo = ConversationRepository()
    avatar_repo = BotAvatarRepository()
    knowledge_repo = KnowledgeRepository()
    bot_parameters_repo = BotParametersRepository()

    avatar = AvatarService(avatar_repo)
    bot_assignment = BotAssignmentService(bot_assignment_repo, bot_repo, user_repo)
    token_tracking = TokenTrackingService(token_usage_repo)
    message = MessageService(conversation_repo)
    yaml = YamlSvc()
    vector_store = VectorStoreFacade()
    prompt = PromptService(bot_repo)
    knowledge = KnowledgeSvc(vector_store, knowledge_repo)
    template = TemplateSvc(knowledge)
    bot_parameters = BotParametersService(yaml, prompt, bot_parameters_repo)
    bot = BotService(
        avatar,
        bot_assignment,
        bot_parameters,
        knowledge,
        template,
        bot_repo,
        user_repo,
    )
    user_admin = UserAdminService(
        bot_assignment,
        user_repo,
        bot_repo,
        conversation_repo,
        token_usage_repo,
        bot_assignment_repo,
    )
    llm = LlmService(token_tracking, user_admin)
    langchain = LangChainFacade(llm, vector_store)
    rag = RagService(langchain, prompt, message)
    chat = ChatFacade(
        rag, user_admin, bot, bot_assignment, bot_parameters, message, token_tracking
    )
    return Services(
        avatar=avatar,
        bot_assignment=bot_assignment,
        token_tracking=token_tracking,
        message=message,
        yaml=yaml,
        vector_store=vector_store,
        prompt=prompt,
        knowledge=knowledge,
        template=template,
        bot_parameters=bot_parameters,
        bot=bot,
        user_admin=user_admin,
        llm=llm,
        langchain=langchain,
        rag=rag,
        chat=chat,
        authent=AuthenticationService(user_admin, user_repo),
        google_authent=GoogleAuthentSvc(user_admin),
        magic_link=MagicLinkService(MagicLinkRepository(), user_repo),
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


async def get_chat_facade(request: Request) -> ChatFacade:
    return _services(request).chat


async def get_authentication_service(request: Request) -> AuthenticationService:
    return _services(request).authent


async def get_google_authent_service(request: Request) -> GoogleAuthentSvc:
    return _services(request).google_authent


async def get_magic_link_service(request: Request) -> MagicLinkService:
    return _services(request).magic_link


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
ChatFacadeDep = Annotated[ChatFacade, Depends(get_chat_facade)]
AuthenticationServiceDep = Annotated[
    AuthenticationService, Depends(get_authentication_service)
]
GoogleAuthentServiceDep = Annotated[
    GoogleAuthentSvc, Depends(get_google_authent_service)
]
MagicLinkServiceDep = Annotated[MagicLinkService, Depends(get_magic_link_service)]
