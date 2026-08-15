from abc import ABC
from typing import Optional, List, Dict, Any, TypeVar, Generic
from ai_server.log.bot_factory_logger import BotFactoryLogger

T = TypeVar("T")


class ServiceError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class BaseService(ABC, Generic[T]):
    def __init__(self, logger: Optional[BotFactoryLogger] = None):
        self.logger = logger or BotFactoryLogger()

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
