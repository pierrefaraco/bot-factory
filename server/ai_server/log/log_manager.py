from logging.config import dictConfig

BOT_FACTORY_LOGGER = "bot_factory_logger"
LOG_FORMAT = "%(asctime)s - %(name)s | %(levelname)s | %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S.%z"


class LogManager:
    def setup_logger(self, app):
        """Build a config object to setup the Python logging framework and inject it with the dictConfig method"""
        my_formats = self.__setup_formats(app)
        my_handlers = self.__setup_handlers(app)
        my_loggers = self.__setup_loggers(app)
        # *** Final object building.
        log_config = {
            "version": 1,
            "formatters": my_formats["formatters"],
            "handlers": my_handlers["handlers"],
            "loggers": my_loggers["loggers"],
        }
        # *** Injection of configuration.
        self.apply_log_config(log_config)
        return log_config

    def apply_log_config(self, log_config):
        dictConfig(log_config)

    def __setup_formats(self, app):
        """Define avaiable formats for handlers."""
        return {
            "formatters": {
                "standard_format": {
                    "format": LOG_FORMAT,
                    "datefmt": LOG_DATE_FMT,
                },
            }
        }

    def __setup_handlers(self, app):
        """Define avaiable handlers for loggers."""
        app.logger.handlers = []
        return {
            "handlers": {
                "default_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard_format",
                    "stream": "ext://sys.stdout",
                },
                "application_logs_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard_format",
                    "stream": "ext://sys.stdout",
                },
                "flask_log_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard_format",
                    "stream": "ext://sys.stdout",
                },
            }
        }

    def __setup_loggers(self, app):
        """Define a defaut logger, one for the application logs and configure existing flask loggers."""
        logging_level = app.config["LOGGER_LVL"]
        return {
            "loggers": {  # root logger
                "": {
                    "level": logging_level,
                    "handlers": ["default_handler"],
                    "propagate": False,
                },
                BOT_FACTORY_LOGGER: {
                    "level": logging_level,
                    "handlers": ["application_logs_handler"],
                    "propagate": False,
                },
                "werkzeug": {
                    "level": logging_level,
                    "handlers": ["flask_log_handler"],
                    "propagate": False,
                },
                "flaskr": {
                    "level": logging_level,
                    "handlers": ["flask_log_handler"],
                    "propagate": False,
                },
            }
        }
