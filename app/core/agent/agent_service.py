import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime

from app.core.models.agent import (
    Action,
    AgentPlan,
    AuditEvent,
    ConversationMemory,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationReport,
    ExecutionResult,
    ExecutionStatus,
    PlanStep,
)
from app.core.agent.executor import ExecutorFactory
from app.core.agent.action_generator import ActionGenerator
from app.core.agent.react_agent import ReActAgent, ReActResult
from app.core.ai.semantic_retriever import HybridRetriever
from app.core.agent.adaptive_planner import AdaptivePlanner


class AgentService:
    """Agent 服务 - 管理动作生成、计划、记忆和执行审计 (集成 ReAct 推理)"""

    def __init__(self, action_generator: ActionGenerator, knowledge_base: Optional[List[Dict[str, Any]]] = None):
        self.action_generator = action_generator
        self.execution_history: Dict[str, ExecutionResult] = {}
        self.plans: Dict[str, AgentPlan] = {}
        self.memories: Dict[str, ConversationMemory] = {}
        self.audit_events: list[AuditEvent] = []

        # ReAct 和语义检索
        self.knowledge_base = knowledge_base or []
        self.react_agent: Optional[ReActAgent] = None
        self.retriever: Optional[HybridRetriever] = None
        self.react_results: Dict[str, ReActResult] = {}  # 存储 ReAct 推理结果
        self.adaptive_planner = AdaptivePlanner(max_replans=3)  # 动态重规划
        self._init_advanced_features()

    def _init_advanced_features(self):
        """初始化 ReAct 和语义检索"""
        try:
            self.react_agent = ReActAgent(knowledge_base=self.knowledge_base, max_iterations=5)
            self.retriever = HybridRetriever(self.knowledge_base, use_semantic=True)
            self._audit(
                event_type="advanced_features_initialized",
                summary="ReAct Agent and Semantic Retriever initialized",
                metadata={"kb_size": len(self.knowledge_base)}
            )
        except Exception as e:
            self._audit(
                event_type="advanced_features_failed",
                summary=f"Failed to initialize advanced features: {str(e)}",
                metadata={"error": str(e)}
            )
            # 降级到基础模式
            self.react_agent = None
            self.retriever = None

    def generate_actions(self, keywords: list[str], metric_name: str = "") -> list[Action]:
        return self.action_generator.generate_from_keywords(keywords, metric_name)

    def create_plan(self, question: str, analysis_result: dict, session_id: str = "default", use_react: bool = True) -> AgentPlan:
        """创建计划 - 支持 ReAct 推理模式"""
        keywords = analysis_result.get("keywords", [])
        metric_name = analysis_result.get("normalized_metric", "")

        # 如果启用 ReAct，先执行推理
        react_result = None
        if use_react and self.react_agent:
            try:
                context = {
                    "keywords": keywords,
                    "metric_name": metric_name,
                    "analysis": analysis_result
                }
                react_result = self.react_agent.run(question, context)
                self.react_results[session_id] = react_result
                self._audit(
                    event_type="react_reasoning_completed",
                    summary=f"ReAct reasoning completed in {react_result.total_iterations} iterations",
                    session_id=session_id,
                    metadata={"iterations": react_result.total_iterations, "success": react_result.success}
                )
            except Exception as e:
                self._audit(
                    event_type="react_reasoning_failed",
                    summary=f"ReAct reasoning failed: {str(e)}",
                    session_id=session_id,
                    metadata={"error": str(e)}
                )

        # 使用语义检索增强知识查询
        enhanced_keywords = keywords
        if self.retriever and keywords:
            try:
                retrieved = self.retriever.search(question, keywords, top_k=3)
                if retrieved:
                    enhanced_keywords = keywords + [r.get("title", "") for r in retrieved[:2]]
                    self._audit(
                        event_type="semantic_retrieval_completed",
                        summary=f"Retrieved {len(retrieved)} relevant documents",
                        session_id=session_id,
                        metadata={"retrieved_count": len(retrieved)}
                    )
            except Exception as e:
                pass  # 降级到关键词匹配

        actions = self.generate_actions(enhanced_keywords, metric_name)
        memory = self.append_memory(
            session_id=session_id,
            facts=self._extract_memory_facts(question, analysis_result, react_result),
            question=question,
        )
        steps = self._build_plan_steps(analysis_result, actions, react_result)
        plan = AgentPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            question=question,
            goal=self._build_goal(question, metric_name, react_result),
            context_summary="；".join(memory.facts[-5:]) or "暂无历史上下文",
            steps=steps,
            recommended_actions=actions,
        )
        self.plans[plan.plan_id] = plan
        self._audit(
            event_type="plan_created",
            summary=f"Created agent plan for session {session_id}",
            session_id=session_id,
            plan_id=plan.plan_id,
            metadata={"step_count": len(steps), "action_count": len(actions), "used_react": react_result is not None},
        )
        return plan

    def append_memory(self, session_id: str, facts: list[str], question: str = "") -> ConversationMemory:
        memory = self.memories.get(session_id) or ConversationMemory(session_id=session_id)
        for fact in facts:
            normalized = fact.strip()
            if normalized and normalized not in memory.facts:
                memory.facts.append(normalized)
        memory.facts = memory.facts[-20:]
        if question:
            memory.last_question = question
        memory.updated_at = datetime.now()
        self.memories[session_id] = memory
        self._audit(
            event_type="memory_updated",
            summary=f"Updated memory for session {session_id}",
            session_id=session_id,
            metadata={"fact_count": len(memory.facts)},
        )
        return memory

    def get_memory(self, session_id: str) -> ConversationMemory:
        return self.memories.get(session_id) or ConversationMemory(session_id=session_id)

    def get_plan(self, plan_id: str) -> Optional[AgentPlan]:
        return self.plans.get(plan_id)

    def list_audit_events(self, limit: int = 50) -> list[AuditEvent]:
        return sorted(self.audit_events, key=lambda event: event.created_at, reverse=True)[:limit]

    def evaluate(self, cases: list[EvaluationCase]) -> EvaluationReport:
        results: list[EvaluationCaseResult] = []
        for case in cases:
            keywords = [keyword for keyword in case.expected_keywords if keyword in case.question]
            analysis_result = {
                "keywords": keywords or case.expected_keywords,
                "normalized_metric": case.expected_keywords[0] if case.expected_keywords else "",
            }
            plan = self.create_plan(case.question, analysis_result, session_id=f"eval_{case.case_id}")
            matched_keywords = [keyword for keyword in case.expected_keywords if keyword in plan.goal or keyword in plan.context_summary]
            score = len(matched_keywords) / len(case.expected_keywords) if case.expected_keywords else 1.0
            results.append(
                EvaluationCaseResult(
                    case_id=case.case_id,
                    score=round(score, 4),
                    matched_keywords=matched_keywords,
                    plan_id=plan.plan_id,
                )
            )
        average_score = sum(result.score for result in results) / len(results) if results else 0.0
        report = EvaluationReport(
            total_cases=len(results),
            average_score=round(average_score, 4),
            results=results,
        )
        self._audit(
            event_type="evaluation_completed",
            summary="Completed agent evaluation",
            metadata={"total_cases": report.total_cases, "average_score": report.average_score},
        )
        return report

    async def execute_action(
        self,
        action: Action,
        parameters: Optional[dict] = None
    ) -> ExecutionResult:
        executor = ExecutorFactory.get_executor(action.type.value)
        self._audit(
            event_type="action_started",
            summary=f"Started action {action.title}",
            action_id=action.id,
            metadata={"risk_level": action.risk_level.value, "requires_approval": action.requires_approval},
        )
        result = await executor.execute(action, parameters or {})
        self.execution_history[result.execution_id] = result
        self._audit(
            event_type="action_completed",
            summary=f"Completed action {action.title} with status {result.status.value}",
            action_id=action.id,
            metadata={"execution_id": result.execution_id, "status": result.status.value},
        )
        return result

    def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        return self.execution_history.get(execution_id)

    def get_execution_history(self, limit: int = 20) -> list[ExecutionResult]:
        results = sorted(
            self.execution_history.values(),
            key=lambda x: x.start_time,
            reverse=True
        )
        return results[:limit]

    async def execute_with_replan(
        self,
        action: Action,
        current_plan: AgentPlan,
        parameters: Optional[dict] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[ExecutionResult, Optional[AgentPlan]]:
        """执行动作并支持自动重规划"""
        # 执行动作
        result = await self.execute_action(action, parameters)

        # 检查是否需要重规划
        if self.adaptive_planner.should_replan(result, current_plan):
            self._audit(
                event_type="replan_triggered",
                summary=f"Execution failed, triggering replan",
                plan_id=current_plan.plan_id,
                metadata={"execution_status": result.status.value, "error": result.error}
            )

            # 生成新计划
            new_plan = self.adaptive_planner.generate_replan(
                current_plan,
                result,
                context or {}
            )

            if new_plan:
                self.plans[new_plan.plan_id] = new_plan
                self._audit(
                    event_type="replan_generated",
                    summary=f"Generated new plan {new_plan.plan_id}",
                    plan_id=new_plan.plan_id,
                    metadata={"strategy": context.get("replan_strategy", "unknown")}
                )
                return result, new_plan

        return result, None

    def get_replan_summary(self) -> str:
        """获取重规划摘要"""
        return self.adaptive_planner.get_replan_summary()

    def _build_plan_steps(self, analysis_result: dict, actions: list[Action], react_result: Optional[ReActResult] = None) -> list[PlanStep]:
        """构建计划步骤 - 支持 ReAct 推理轨迹"""
        steps = [
            PlanStep(
                order=1,
                title="理解问题并确认上下文",
                rationale="提取指标、省份、告警对象和历史会话事实，避免直接执行不相关动作。",
                tool_name="memory_lookup",
            ),
            PlanStep(
                order=2,
                title="检索知识库和指标元数据 (语义检索)",
                rationale="使用向量检索优先匹配相似问题，再结合 NGS 指标定义生成可解释判断。",
                tool_name="semantic_retrieval",
                depends_on=[1],
            ),
            PlanStep(
                order=3,
                title="形成诊断假设 (ReAct 推理)",
                rationale="通过 Think-Act-Observe 循环，逐步推理根因并验证假设。",
                tool_name="react_reasoning",
                depends_on=[2],
            ),
            PlanStep(
                order=4,
                title="选择低风险诊断动作",
                rationale="优先选择查看类命令收集证据，高风险动作必须人工确认。",
                tool_name="tool_selection",
                depends_on=[3],
                requires_approval=any(action.requires_approval for action in actions),
            ),
            PlanStep(
                order=5,
                title="汇总结果并给出下一步",
                rationale="将执行结果、置信度和建议动作沉淀为可审计输出。",
                tool_name="final_answer",
                depends_on=[4],
            ),
        ]

        # 如果有 ReAct 结果，添加推理轨迹到第三步
        if react_result:
            steps[2].rationale += f" (已完成 {react_result.total_iterations} 轮推理)"

        if analysis_result.get("confidence", 1.0) < 0.5:
            steps.insert(
                3,
                PlanStep(
                    order=3,
                    title="低置信度时调用 AI 补强",
                    rationale="本地知识不足时使用 LLM 补充原因和排查路径，但不直接执行危险动作。",
                    tool_name="llm_fallback",
                    depends_on=[2],
                ),
            )
            for index, step in enumerate(steps, start=1):
                step.order = index
        return steps

    def _extract_memory_facts(self, question: str, analysis_result: dict, react_result: Optional[ReActResult] = None) -> list[str]:
        facts = []
        metric_name = analysis_result.get("normalized_metric")
        keywords = analysis_result.get("keywords", [])
        if metric_name:
            facts.append(f"最近关注指标：{metric_name}")
        if keywords:
            facts.append(f"最近问题关键词：{', '.join(keywords[:5])}")
        if question:
            facts.append(f"最近问题：{question}")
        if react_result:
            facts.append(f"ReAct 推理轮次：{react_result.total_iterations}")
        return facts

    def _build_goal(self, question: str, metric_name: str, react_result: Optional[ReActResult] = None) -> str:
        base_goal = f"定位 {metric_name} 相关异常并生成安全的诊断路径" if metric_name else f"分析运维问题并生成安全的诊断路径：{question}"
        if react_result and react_result.success:
            base_goal += f" (已通过 ReAct 推理验证)"
        return base_goal

    def get_react_result(self, session_id: str) -> Optional[ReActResult]:
        """获取 ReAct 推理结果"""
        return self.react_results.get(session_id)

    def _audit(
        self,
        event_type: str,
        summary: str,
        session_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        action_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.audit_events.append(
            AuditEvent(
                event_id=f"audit_{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                summary=summary,
                session_id=session_id,
                plan_id=plan_id,
                action_id=action_id,
                metadata=metadata or {},
            )
        )
        self.audit_events = self.audit_events[-200:]
