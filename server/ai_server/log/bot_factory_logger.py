import logging
from inspect import currentframe

from ai_server.log.log_config import BOT_FACTORY_LOGGER
from ai_server.decorators.singleton import singleton

# stacklevel to pass to the stdlib logger so that %(filename)s/%(lineno)d in
# LOG_FORMAT point to the code calling BotFactoryLogger, not to this wrapper.
_CALLER_STACKLEVEL = 2

@singleton
class BotFactoryLogger():
    def __init__(self):
        logger = logging.getLogger("chardet.charsetprober")
        logger.disabled = True
        logger = logging.getLogger("chardet.universaldetector")
        logger.disabled = True
        self.logger = logging.getLogger(BOT_FACTORY_LOGGER)

    def _get_caller_class_name(self):
        """Inspect the call stack to find the class (self/cls) of whoever called
        debug/info/warning/error/critical, for the %(class_name)s log field."""
        caller = currentframe().f_back.f_back
        caller_self = caller.f_locals.get("self")
        if caller_self is not None:
            return type(caller_self).__name__
        caller_cls = caller.f_locals.get("cls")
        return caller_cls.__name__ if caller_cls is not None else "-"

    def debug(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.debug(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)

    def info(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.info(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)

    def warning(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.warning(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)

    def error(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.error(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)

    def critical(self, message, *args, **kwargs):
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.critical(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)

    def exception(self, message, *args, **kwargs):
        """Log an ERROR-level message with the current exception's stack trace.
        Must be called from inside an `except` block."""
        kwargs.setdefault("extra", {})["class_name"] = self._get_caller_class_name()
        self.logger.exception(message, *args, stacklevel=_CALLER_STACKLEVEL, **kwargs)
