from typing import Any

from fastapi import APIRouter, Depends

from app.core.common.dependencies import get_repository, get_service
from app.core.models.base import AskRequest, AskResponse, DataSourceStatusResponse
from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.service import OpsAssistantService

router = APIRouter(prefix="/api/v1", tags=["assistant"])


@router.get("/health")
def health() -> dict[str, str]:
    """健康检查 (liveness)"""
    return {"status": "ok"}


@router.get("/ready")
def ready(repository: InMemoryRepository = Depends(get_repository)) -> dict[str, Any]:
    """就绪检查 (readiness)"""
    try:
        # 检查数据是否加载
        knowledge_count = len(repository.knowledge_items)
        metrics_count = len(repository.metric_items)

        if knowledge_count == 0:
            return {
                "status": "not_ready",
                "reason": "知识库未加载"
            }

        return {
            "status": "ready",
            "knowledge_count": knowledge_count,
            "metrics_count": metrics_count
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "reason": str(e)
        }


@router.get("/data-source/status", response_model=DataSourceStatusResponse)
def data_source_status(repository: InMemoryRepository = Depends(get_repository)) -> DataSourceStatusResponse:
    return repository.get_data_source_status()


@router.post("/assistant/ask", response_model=AskResponse)
async def ask(payload: AskRequest, service: OpsAssistantService = Depends(get_service)) -> AskResponse:
    result = await service.ask_with_ai(
        question=payload.question.strip(),
        province=payload.province.strip(),
        top_k=payload.top_k,
    )
    return AskResponse(**result)


@router.get("/seed/knowledge_base")
def get_knowledge_base(repository: InMemoryRepository = Depends(get_repository)):
    return repository.list_knowledge()


@router.get("/seed/metrics_meta")
def get_metrics_meta(repository: InMemoryRepository = Depends(get_repository)):
    return repository.list_metrics()


@router.get("/seed/public_tags")
def get_public_tags(repository: InMemoryRepository = Depends(get_repository)):
    return repository.list_public_tags()
