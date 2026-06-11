from pydantic import BaseModel, Field


class KnowledgeItem(BaseModel):
    id: int = 0
    question: str
    reason: str = ""
    method: str = ""
    sort: str = ""
    province: str = ""


class MetricItem(BaseModel):
    metric: str = ""
    name: str
    measurement: str
    field_name: str
    desc: str = ""
    unit: str = ""


class PublicTagItem(BaseModel):
    name: str
    field_name: str
    desc: str = ""


class AIFallbackResult(BaseModel):
    """AI 后备查询结果"""
    enabled: bool = Field(description="AI 查询是否启用")
    used: bool = Field(default=False, description="本次查询是否使用了 AI")
    confidence_too_low: bool = Field(default=False, description="是否因为置信度过低触发 AI")
    raw_response: str | None = Field(default=None, description="AI 原始响应")
    error: str | None = Field(default=None, description="AI 查询错误信息")
    message: str | None = Field(default=None, description="提示信息")


class DataSourceFileStatus(BaseModel):
    file_name: str
    file_path: str
    exists: bool
    loaded_count: int


class DataSourceStatusResponse(BaseModel):
    data_dir: str
    knowledge: DataSourceFileStatus
    metrics: DataSourceFileStatus
    public_tags: DataSourceFileStatus


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="运维人员输入的问题")
    province: str = Field(default="", description="可选省份，用于缩小知识库范围")
    top_k: int = Field(default=3, ge=1, le=10)


class ReasoningStep(BaseModel):
    """推理步骤"""
    iteration: int
    thought: str
    thought_type: str
    action: str | None = None
    action_type: str | None = None
    observation: str | None = None


class AskResponse(BaseModel):
    question: str
    normalized_question: str
    normalized_metric: str
    keywords: list[str]
    matched_knowledge: list[dict]
    possible_reason: list[str]
    suggested_steps: list[str]
    related_objects: dict
    confidence: float
    next_actions: list[str]
    fallback_questions: list[dict] = []
    ai_fallback: AIFallbackResult | None = Field(default=None, description="AI 后备查询结果")
    executable_actions: list[dict] = Field(default_factory=list, description="可执行动作列表")
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list, description="ReAct 推理步骤")
