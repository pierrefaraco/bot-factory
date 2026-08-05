from logging.config import dictConfig

APPLICATION_LOGGER = "genius-server"
OPERATIONAL_LOGGER = "op-log"
SECURITY_LOGGER = "security"
# LOG_FORMAT = '%(asctime)s - %(name)s | %(levelname)s | %(module)s:%(lineno)-4s | %(message)s'
LOG_FORMAT = "%(asctime)s - %(name)s | %(levelname)s | %(message)s"
# LOG_VERBOSE_FORMAT = '%(asctime)s - %(name)s | %(levelname)s | %(module)s:%(lineno)-4s | %(message)s | %(threadName)s - %(thread)d | %(processName)s | %(filename)s - %(funcName)s'
LOG_VERBOSE_FORMAT = "%(asctime)s - %(name)s | %(levelname)s | %(message)s | %(threadName)s - %(thread)d | %(processName)s | %(filename)s - %(funcName)s"
OPERATIONAL_LOG_FORMAT = "%(asctime)s - %(name)s | %(levelname)s | %(message)s"
SECURITY_LOG_FORMAT = "%(asctime)s - %(name)s | %(levelname)s | %(message)s"
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
        log_format = LOG_VERBOSE_FORMAT if app.config["VERBOSE"] else LOG_FORMAT
        return {
            "formatters": {
                "standard_format": {
                    "format": log_format,
                    "datefmt": LOG_DATE_FMT,
                },
                "operational_log_format": {
                    "format": OPERATIONAL_LOG_FORMAT,
                    "datefmt": LOG_DATE_FMT,
                },
                "security_log_format": {
                    "format": SECURITY_LOG_FORMAT,
                    "datefmt": LOG_DATE_FMT,
                },
            }
        }

    def __setup_handlers(self, app):
        """Define avaiable handlers for loggers."""
        operational_log_file = app.config["OPERATIONAL_LOG_FILE"].format(
            app.config["HOSTNAME"]
        )
        app.logger.handlers = []
        return {
            "handlers": {
                "default_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard_format",
                    "stream": "ext://sys.stdout",
                },
                "operational_logs_filehandler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "operational_log_format",
                    "filename": operational_log_file,
                    "maxBytes": 1024 * app.config["OPERATIONAL_LOG_FILE_MAXSIZE"],
                    "backupCount": 10,
                },
                "security_logs_filehandler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "security_log_format",
                    "filename": operational_log_file,
                    "maxBytes": 1024 * app.config["OPERATIONAL_LOG_FILE_MAXSIZE"],
                    "backupCount": 10,
                },
                "operational_logs_streamhandler": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard_format",
                    "stream": "ext://sys.stdout",
                },
                "security_logs_streamhandler": {
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
                "null_handler": {
                    "class": "logging.NullHandler",
                    "formatter": "standard_format",
                },
            }
        }

    def __setup_loggers(self, app):
        """Define a defaut logger, one for the application logs, one for the operational logs and configure existing flask loggers."""
        logging_level = app.config["LOGGER_LVL"]
        # *** This permit to deactive flask logs .
        server_handler = (
            "null_handler"
            if app.config["DEACTIVATE_SERVER_LOG"]
            else "flask_log_handler"
        )
        return {
            "loggers": {  # root logger
                "": {
                    "level": logging_level,
                    "handlers": ["default_handler"],
                    "propagate": False,
                },
                OPERATIONAL_LOGGER: {
                    "level": logging_level,
                    "handlers": ["operational_logs_streamhandler"],
                    "propagate": False,
                },
                SECURITY_LOGGER: {
                    "level": logging_level,
                    "handlers": ["security_logs_streamhandler"],
                    "propagate": False,
                },
                APPLICATION_LOGGER: {
                    "level": logging_level,
                    "handlers": ["application_logs_handler"],
                    "propagate": False,
                },
                "werkzeug": {
                    "level": logging_level,
                    "handlers": [server_handler],
                    "propagate": False,
                },
                "flaskr": {
                    "level": logging_level,
                    "handlers": [server_handler],
                    "propagate": False,
                },
            }
        }
