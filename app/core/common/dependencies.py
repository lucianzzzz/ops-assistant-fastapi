from functools import lru_cache

from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.service import OpsAssistantService


@lru_cache
def get_repository() -> InMemoryRepository:
    return InMemoryRepository()


@lru_cache
def get_service() -> OpsAssistantService:
    return OpsAssistantService(repository=get_repository())

