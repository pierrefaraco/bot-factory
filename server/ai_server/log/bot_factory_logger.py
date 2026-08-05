import logging
import os
from inspect import currentframe

from ai_server.log.log_manager import BOT_FACTORY_LOGGER
from ai_server.decorators.singleton import singleton

@singleton
class BotFactoryLogger():
    def __init__(self):
        logger = logging.getLogger("chardet.charsetprober")
        logger.disabled = True
        logger = logging.getLogger("chardet.universaldetector")
        logger.disabled = True
        self.logger = logging.getLogger(BOT_FACTORY_LOGGER)


    def debug(self, message, *args, **kwargs):
        # message = self.get_lineo_and_file_number() + message
        self.logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        # message = self.get_lineo_and_file_number() + message
        self.logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        # message = self.get_lineo_and_file_number() + message
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        # message = self.get_lineo_and_file_number() + message
        self.logger.error(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        # message = self.get_lineo_and_file_number() + message
        self.logger.critical(message, *args, **kwargs)
