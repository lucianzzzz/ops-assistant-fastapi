from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """动作类型"""
    COMMAND = "command"      # Shell 命令
    SCRIPT = "script"        # 脚本执行
    API = "api"             # API 调用
    SSH = "ssh"             # SSH 远程执行


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"             # 低风险：查看类操作
    MEDIUM = "medium"       # 中风险：重启服务等
    HIGH = "high"           # 高风险：删除数据等


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    SUCCESS = "success"     # 成功
    FAILED = "failed"       # 失败
    TIMEOUT = "timeout"     # 超时
    CANCELLED = "cancelled" # 取消


class Action(BaseModel):
    """可执行动作"""
    id: str = Field(description="动作唯一标识")
    type: ActionType = Field(description="动作类型")
    title: str = Field(description="动作标题")
    description: str = Field(description="详细描述")
    command: str = Field(description="执行命令/脚本")
    risk_level: RiskLevel = Field(description="风险等级")
    requires_approval: bool = Field(default=True, description="是否需要用户确认")
    timeout: int = Field(default=30, description="超时时间（秒）")
    estimated_duration: int = Field(default=5, description="预计耗时（秒）")
    rollback_command: Optional[str] = Field(default=None, description="回滚命令")
    metadata: dict = Field(default_factory=dict, description="额外元数据")


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: str = Field(description="执行ID")
    action_id: str = Field(description="动作ID")
    status: ExecutionStatus = Field(description="执行状态")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    duration: Optional[float] = Field(default=None, description="执行时长（秒）")
    stdout: str = Field(default="", description="标准输出")
    stderr: str = Field(default="", description="标准错误")
    exit_code: Optional[int] = Field(default=None, description="退出码")
    error: Optional[str] = Field(default=None, description="错误信息")


class PlanStep(BaseModel):
    order: int = Field(description="步骤顺序")
    title: str = Field(description="步骤标题")
    rationale: str = Field(description="步骤目的")
    tool_name: str = Field(default="manual_review", description="建议使用的工具")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="步骤状态")
    depends_on: list[int] = Field(default_factory=list, description="依赖步骤")
    requires_approval: bool = Field(default=False, description="是否需要人工确认")


class AgentPlan(BaseModel):
    plan_id: str = Field(description="计划ID")
    session_id: str = Field(description="会话ID")
    question: str = Field(description="用户问题")
    goal: str = Field(description="Agent 目标")
    context_summary: str = Field(description="上下文摘要")
    steps: list[PlanStep] = Field(description="多步执行计划")
    recommended_actions: list[Action] = Field(default_factory=list, description="推荐执行动作")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class ConversationMemory(BaseModel):
    session_id: str = Field(description="会话ID")
    facts: list[str] = Field(default_factory=list, description="会话事实记忆")
    last_question: str = Field(default="", description="最近一次问题")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class AuditEvent(BaseModel):
    event_id: str = Field(description="审计事件ID")
    event_type: str = Field(description="事件类型")
    summary: str = Field(description="事件摘要")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    plan_id: Optional[str] = Field(default=None, description="计划ID")
    action_id: Optional[str] = Field(default=None, description="动作ID")
    metadata: dict = Field(default_factory=dict, description="事件元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class ExecuteActionRequest(BaseModel):
    """执行动作请求"""
    action_id: str = Field(description="动作ID")
    parameters: dict = Field(default_factory=dict, description="执行参数")
    user_confirmation: bool = Field(default=False, description="用户确认")


class GenerateActionsRequest(BaseModel):
    """生成动作请求"""
    question: str = Field(description="用户问题")
    analysis_result: dict = Field(description="分析结果")


class GenerateActionsResponse(BaseModel):
    """生成动作响应"""
    actions: list[Action] = Field(description="可执行动作列表")


class CreatePlanRequest(BaseModel):
    question: str = Field(description="用户问题")
    analysis_result: dict = Field(default_factory=dict, description="问答分析结果")
    session_id: str = Field(default="default", description="会话ID")


class CreatePlanResponse(BaseModel):
    plan: AgentPlan = Field(description="Agent 多步计划")
    memory: ConversationMemory = Field(description="更新后的会话记忆")


class AppendMemoryRequest(BaseModel):
    session_id: str = Field(description="会话ID")
    facts: list[str] = Field(default_factory=list, description="需要写入的事实")
    question: str = Field(default="", description="最近问题")


class EvaluationCase(BaseModel):
    case_id: str = Field(description="评测用例ID")
    question: str = Field(description="评测问题")
    expected_keywords: list[str] = Field(default_factory=list, description="期望命中的关键词")


class EvaluationCaseResult(BaseModel):
    case_id: str = Field(description="评测用例ID")
    score: float = Field(description="用例得分")
    matched_keywords: list[str] = Field(description="命中的关键词")
    plan_id: str = Field(description="生成的计划ID")


class EvaluateAgentRequest(BaseModel):
    cases: list[EvaluationCase] = Field(description="评测用例列表")


class EvaluationReport(BaseModel):
    total_cases: int = Field(description="评测用例总数")
    average_score: float = Field(description="平均得分")
    results: list[EvaluationCaseResult] = Field(description="逐用例结果")
