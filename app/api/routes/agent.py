from fastapi import APIRouter, Depends, HTTPException

from app.core.common.dependencies import get_agent_service
from app.core.agent.agent_service import AgentService
from app.core.models.agent import (
    Action,
    AgentPlan,
    AuditEvent,
    AppendMemoryRequest,
    ConversationMemory,
    CreatePlanRequest,
    CreatePlanResponse,
    EvaluateAgentRequest,
    EvaluationReport,
    ExecutionResult,
    ExecuteActionRequest,
    GenerateActionsRequest,
    GenerateActionsResponse,
)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/actions/generate", response_model=GenerateActionsResponse)
def generate_actions(
    payload: GenerateActionsRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> GenerateActionsResponse:
    """生成可执行动作列表"""
    keywords = payload.analysis_result.get("keywords", [])
    metric_name = payload.analysis_result.get("normalized_metric", "")
    actions = agent_service.generate_actions(keywords, metric_name)
    return GenerateActionsResponse(actions=actions)


@router.post("/plans", response_model=CreatePlanResponse)
def create_plan(
    payload: CreatePlanRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> CreatePlanResponse:
    plan = agent_service.create_plan(
        question=payload.question,
        analysis_result=payload.analysis_result,
        session_id=payload.session_id,
    )
    memory = agent_service.get_memory(payload.session_id)
    return CreatePlanResponse(plan=plan, memory=memory)


@router.get("/plans/{plan_id}", response_model=AgentPlan)
def get_plan(
    plan_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentPlan:
    plan = agent_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/memory", response_model=ConversationMemory)
def append_memory(
    payload: AppendMemoryRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> ConversationMemory:
    return agent_service.append_memory(
        session_id=payload.session_id,
        facts=payload.facts,
        question=payload.question,
    )


@router.get("/memory/{session_id}", response_model=ConversationMemory)
def get_memory(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> ConversationMemory:
    return agent_service.get_memory(session_id)


@router.post("/evaluate", response_model=EvaluationReport)
def evaluate_agent(
    payload: EvaluateAgentRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> EvaluationReport:
    return agent_service.evaluate(payload.cases)


@router.get("/audit", response_model=list[AuditEvent])
def get_audit_events(
    limit: int = 50,
    agent_service: AgentService = Depends(get_agent_service)
) -> list[AuditEvent]:
    return agent_service.list_audit_events(limit)


@router.post("/actions/{action_id}/execute", response_model=ExecutionResult)
async def execute_action(
    action_id: str,
    payload: ExecuteActionRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> ExecutionResult:
    """执行指定的动作"""
    action_dict = payload.parameters.get("action")
    if not action_dict:
        raise HTTPException(status_code=400, detail="Missing action definition")

    try:
        action = Action(**action_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid action definition: {str(e)}")

    if action.id != action_id:
        raise HTTPException(status_code=400, detail="Action ID mismatch")

    if action.requires_approval and not payload.user_confirmation:
        raise HTTPException(
            status_code=403,
            detail="This action requires user confirmation"
        )

    result = await agent_service.execute_action(action, payload.parameters)
    return result


@router.get("/executions/{execution_id}", response_model=ExecutionResult)
def get_execution(
    execution_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> ExecutionResult:
    """获取执行结果"""
    result = agent_service.get_execution_result(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@router.get("/executions", response_model=list[ExecutionResult])
def get_execution_history(
    limit: int = 20,
    agent_service: AgentService = Depends(get_agent_service)
) -> list[ExecutionResult]:
    """获取执行历史"""
    return agent_service.get_execution_history(limit)
