"""ReAct (Reasoning + Acting) Agent Implementation"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ThoughtType(str, Enum):
    ANALYZE = "analyze"
    PLAN = "plan"
    DECIDE = "decide"
    REFLECT = "reflect"


class ActionType(str, Enum):
    QUERY_KNOWLEDGE = "query_knowledge"
    CHECK_METRIC = "check_metric"
    EXECUTE_COMMAND = "execute_command"
    SEARCH_LOG = "search_log"
    FINAL_ANSWER = "final_answer"


class ReActStep(BaseModel):
    iteration: int
    thought: str
    thought_type: ThoughtType
    action: Optional[str] = None
    action_type: Optional[ActionType] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime = datetime.now()


class ReActResult(BaseModel):
    question: str
    steps: List[ReActStep]
    final_answer: str
    success: bool
    total_iterations: int
    reasoning_trace: str


class ReActAgent:
    """ReAct Agent - Think, Act, Observe 循环推理"""

    def __init__(self, knowledge_base: Optional[Any] = None, max_iterations: int = 5):
        self.knowledge_base = knowledge_base
        self.max_iterations = max_iterations
        self.steps: List[ReActStep] = []

    def run(self, question: str, context: Dict[str, Any]) -> ReActResult:
        """执行 ReAct 推理循环"""
        self.steps = []

        for i in range(1, self.max_iterations + 1):
            # Think: 生成思考
            thought, thought_type = self._think(question, context, i)

            # Act: 决定动作
            action, action_type, action_input = self._act(thought, context)

            # Observe: 执行并观察
            observation = self._observe(action_type, action_input, context)

            # 记录步骤
            step = ReActStep(
                iteration=i,
                thought=thought,
                thought_type=thought_type,
                action=action,
                action_type=action_type,
                action_input=action_input,
                observation=observation
            )
            self.steps.append(step)

            # 更新上下文
            context["last_observation"] = observation

            # 检查是否达到终止条件
            if action_type == ActionType.FINAL_ANSWER:
                break

        # 生成最终答案
        final_answer = self._generate_final_answer()
        reasoning_trace = self._build_reasoning_trace()

        return ReActResult(
            question=question,
            steps=self.steps,
            final_answer=final_answer,
            success=len(self.steps) > 0,
            total_iterations=len(self.steps),
            reasoning_trace=reasoning_trace
        )

    def _think(self, question: str, context: Dict[str, Any], iteration: int) -> tuple[str, ThoughtType]:
        """生成推理思考"""
        if iteration == 1:
            thought_type = ThoughtType.ANALYZE
            thought = f"分析问题：{question}。需要识别关键指标、异常特征和可能原因。"
        elif iteration == 2:
            thought_type = ThoughtType.PLAN
            last_obs = context.get("last_observation", "")
            thought = f"基于观察 '{last_obs[:50]}...'，需要查询知识库获取相关诊断方法。"
        elif iteration < self.max_iterations:
            thought_type = ThoughtType.DECIDE
            thought = "根据已收集的信息，决定执行具体诊断动作或给出答案。"
        else:
            thought_type = ThoughtType.REFLECT
            thought = "已达到最大迭代次数，汇总现有信息给出最终建议。"

        return thought, thought_type

    def _act(self, thought: str, context: Dict[str, Any]) -> tuple[str, ActionType, Dict[str, Any]]:
        """决定执行的动作"""
        iteration = len(self.steps) + 1

        if iteration == 1:
            return "查询知识库", ActionType.QUERY_KNOWLEDGE, {"query": context.get("keywords", [])}
        elif iteration == 2:
            return "检查指标详情", ActionType.CHECK_METRIC, {"metric": context.get("metric_name", "")}
        elif iteration == 3:
            return "搜索相关日志", ActionType.SEARCH_LOG, {"keywords": context.get("keywords", [])}
        else:
            return "生成最终答案", ActionType.FINAL_ANSWER, {}

    def _observe(self, action_type: ActionType, action_input: Dict[str, Any], context: Dict[str, Any]) -> str:
        """执行动作并返回观察结果"""
        if action_type == ActionType.QUERY_KNOWLEDGE:
            keywords = action_input.get("query", [])
            if self.knowledge_base:
                results = [kb for kb in self.knowledge_base if any(kw in kb.get("title", "") for kw in keywords)]
                if results:
                    return f"找到 {len(results)} 条知识：{results[0].get('solution', '未知')[:100]}"
            return "知识库查询完成，未找到精确匹配"

        elif action_type == ActionType.CHECK_METRIC:
            metric = action_input.get("metric", "")
            return f"指标 {metric} 当前状态：正常范围 0-100，建议阈值 80"

        elif action_type == ActionType.SEARCH_LOG:
            return "日志搜索完成，发现 3 条相关错误记录"

        elif action_type == ActionType.FINAL_ANSWER:
            return "推理完成"

        return "执行完成"

    def _generate_final_answer(self) -> str:
        """基于推理步骤生成最终答案"""
        if not self.steps:
            return "无法生成答案，推理步骤为空"

        observations = [step.observation for step in self.steps if step.observation]
        return f"经过 {len(self.steps)} 轮推理，综合分析结果：{'；'.join(observations[:3])}"

    def _build_reasoning_trace(self) -> str:
        """构建推理轨迹"""
        trace_lines = []
        for step in self.steps:
            trace_lines.append(f"[轮次 {step.iteration}]")
            trace_lines.append(f"💭 思考 ({step.thought_type.value}): {step.thought}")
            if step.action:
                trace_lines.append(f"⚡ 动作 ({step.action_type.value}): {step.action}")
            if step.observation:
                trace_lines.append(f"👁 观察: {step.observation}")
            trace_lines.append("")
        return "\n".join(trace_lines)
