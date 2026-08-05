import logging
import os
from inspect import currentframe

from ai_server.abstract.singleton_meta import SingletonMeta
from ai_server.log.log_manager import APPLICATION_LOGGER


class AppLogger(metaclass=SingletonMeta):
    def __init__(self):
        logger = logging.getLogger("chardet.charsetprober")
        logger.disabled = True
        logger = logging.getLogger("chardet.universaldetector")
        logger.disabled = True

        self.logger = logging.getLogger(APPLICATION_LOGGER)

    # replace  get_lineo_and_file_number() by stacklevel=2  in log parameter when build will be in 3.8
    # https://docs.python.org/3.8/library/logging.html#logging.Logger.debug
    # self.logger.info(message, *args, **kwargs, stacklevel=2 )
    # In LogManager class re-add  %(module)s:%(lineno)-4s in logs formats

    def get_lineo_and_file_number(self):
        cf = currentframe()
        lineno = cf.f_back.f_back.f_lineno
        co = cf.f_back.f_back.f_code
        module = os.path.splitext(os.path.basename(co.co_filename))[0]
        return f"{module}:{lineno} | "

    def debug(self, message, *args, **kwargs):
        message = self.get_lineo_and_file_number() + message
        self.logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        message = self.get_lineo_and_file_number() + message
        self.logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        message = self.get_lineo_and_file_number() + message
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        message = self.get_lineo_and_file_number() + message
        self.logger.error(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        message = self.get_lineo_and_file_number() + message
        self.logger.critical(message, *args, **kwargs)
