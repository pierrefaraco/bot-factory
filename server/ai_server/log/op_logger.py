import logging

from ai_server.abstract.singleton_meta import SingletonMeta
from ai_server.log.categories import ErrorCode, LogCategory
from ai_server.log.log_manager import OPERATIONAL_LOGGER


CAT_FORMAT = "%s | %s | "
ECODE_FORMAT = "%s | %s | "


class OpLogger(metaclass=SingletonMeta):
    def __init__(self):
        self.logger = logging.getLogger(OPERATIONAL_LOGGER)
        self.authSvc = None

    def info(self, CATEGORY: LogCategory, message, *args, in_thread=False, **kwargs):
        self.logger.info(
            CAT_FORMAT + message, CATEGORY.value, self.get_user(), *args, **kwargs
        )

    def warning(self, CATEGORY: LogCategory, message, *args, in_thread=False, **kwargs):
        self.logger.warning(
            CAT_FORMAT + message, CATEGORY.value, self.get_user(), *args, **kwargs
        )

    def error(self, CATEGORY: ErrorCode, message, *args, in_thread=False, **kwargs):
        self.logger.error(
            ECODE_FORMAT + message, CATEGORY.value, self.get_user(), *args, **kwargs
        )

    def critical(
        self, CATEGORY: LogCategory, message, *args, in_thread=False, **kwargs
    ):
        self.logger.critical(
            CAT_FORMAT + message, CATEGORY.value, self.get_user(), *args, **kwargs
        )

    def get_user(self):
        return "SYSTEM"
