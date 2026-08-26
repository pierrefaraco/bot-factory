import logging
from inspect import currentframe

from ai_server.log.log_config import PROMPT_DEBUG_LOGGER
from ai_server.decorators.singleton import singleton

# stacklevel to pass to the stdlib logger so that %(filename)s/%(lineno)d in
# LOG_FORMAT point to the code calling PromptDebugLogger, not to this wrapper.
_CALLER_STACKLEVEL = 2


@singleton
class PromptDebugLogger:
    """Dedicated logger for tracing prompt construction step by step (see
    RagService.build and server/doc/LANGCHAIN_ARCHITECTURE.md#3), kept
    separate from BotFactoryLogger's general-purpose app logging.

    Routed through its own named logger (PROMPT_DEBUG_LOGGER) controlled by
    the PROMPT_DEBUG_LVL env var, so prompt tracing can be turned on/off
    independently of LOGGER_LVL — no need to enable full app-wide DEBUG
    logging (SQL, HTTP, ...) just to watch a prompt take shape.
    """

    def __init__(self):
        self.logger = logging.getLogger(PROMPT_DEBUG_LOGGER)

    def _get_caller_class_name(self):
        """Inspect the call stack to find the class (self/cls) of whoever
        called debug(), for the %(class_name)s log field."""
        caller = currentframe().f_back.f_back
        caller_self = caller.f_locals.get("self")
        if caller_self is not None:
            return type(caller_self).__name__
        caller_cls = caller.f_locals.get("cls")
        return caller_cls.__name__ if caller_cls is not None else "-"

    def debug(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.debug(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)
