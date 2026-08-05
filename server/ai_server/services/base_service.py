from abc import ABC
from typing import Optional, List, Dict, Any, TypeVar, Generic, Callable
from sqlalchemy.exc import SQLAlchemyError
from ai_server.dao.database import db
from ai_server.exceptions.api_error import ApiError
from ai_server.log.app_logger import AppLogger

T = TypeVar("T")
R = TypeVar("R")


class ServiceError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class BaseService(ABC, Generic[T]):
    def __init__(self, logger: Optional[AppLogger] = None):
        self.logger = logger or AppLogger()

    def _handle_error(self, operation_name: str, error: Exception) -> None:
        if isinstance(error, SQLAlchemyError):
            self.logger.error(f"Database error in {operation_name}: {str(error)}")
            db.session.rollback()
            raise ServiceError(f"Database operation failed: {operation_name}", error)
        if isinstance(error, ApiError):
            self.logger.error(f"ApiError error in {operation_name}: {str(error)}")
            raise error
        else:
            self.logger.error(f"Unexpected error in {operation_name}: {str(error)}")
            raise ServiceError(f"Service operation failed: {operation_name}", error)

    def _safe_execute(
        self, operation_name: str, operation_func: Callable[..., R], *args, **kwargs
    ) -> R:
        try:
            self.logger.debug(f"Executing {operation_name}")
            result = operation_func(*args, **kwargs)
            self.logger.debug(
                f"Successfully executed {operation_name} with result={result}."
            )
            return result
        except Exception as e:
            self._handle_error(operation_name, e)
            raise

    def get_dto_by_id(self, entity_id: int) -> Optional[T]:
        raise NotImplementedError("Subclasses must implement get_by_id")

    def get_all(self) -> List[T]:
        raise NotImplementedError("Subclasses must implement get_all")

    def create(self, data: Dict[str, Any]) -> T:
        raise NotImplementedError("Subclasses must implement create")

    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[T]:
        raise NotImplementedError("Subclasses must implement update")

    def delete(self, entity_id: int) -> bool:
        raise NotImplementedError("Subclasses must implement delete")

    def exists(self, entity_id: int) -> bool:
        return self.get_dto_by_id(entity_id) is not None
