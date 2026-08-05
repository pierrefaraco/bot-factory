from enum import Enum


class LogCategory(Enum):
    AUTH = "Authentication"
    USER = "User"
    SYSTEM = "System"


class ErrorCode(Enum):
    NONE = 0
    HANDLER = "ErrorHandler"
    ERR1 = "Err-1"
    ERR2 = "Err-2"
    ERR3 = "Err-3"
