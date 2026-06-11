from functools import lru_cache

from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.service import OpsAssistantService
from app.core.agent.agent_service import AgentService
from app.core.agent.action_generator import ActionGenerator


@lru_cache
def get_repository() -> InMemoryRepository:
    return InMemoryRepository()


@lru_cache
def get_service() -> OpsAssistantService:
    return OpsAssistantService(repository=get_repository())


@lru_cache
def get_agent_service() -> AgentService:
    action_generator = ActionGenerator()
    return AgentService(action_generator=action_generator)
