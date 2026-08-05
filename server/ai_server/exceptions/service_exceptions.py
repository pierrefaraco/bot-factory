from typing import Optional


class ServiceError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class ValidationError(ServiceError):
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class NotFoundError(ServiceError):
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} with id '{entity_id}' not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateError(ServiceError):
    def __init__(self, entity_type: str, field: str, value: str):
        super().__init__(f"{entity_type} with {field} '{value}' already exists")
        self.entity_type = entity_type
        self.field = field
        self.value = value


class AuthenticationError(ServiceError):
    pass


class AuthorizationError(ServiceError):
    pass
