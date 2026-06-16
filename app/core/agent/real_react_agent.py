"""Real ReAct Agent - 使用 DeepSeek API 的真实推理版本"""
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from openai import OpenAI

from app.core.common.logging import get_logger

logger = get_logger(__name__)


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


class RealReActAgent:
    """ReAct Agent - 真实 LLM 版本"""

    # Few-Shot 示例
    FEW_SHOT_EXAMPLES = """
示例 1：
问题：CPU 使用率过高怎么处理？
思考：需要先了解当前 CPU 使用情况和占用最高的进程
动作类型：query_knowledge
观察：找到 3 条相关知识，建议先用 top 命令查看
思考：知识库建议很明确，可以给出答案了
动作类型：final_answer

示例 2：
问题：网络延迟大是什么原因？
思考：需要确定是内网还是外网延迟
动作类型：check_metric
观察：内网延迟正常 10ms，外网延迟 200ms
思考：外网延迟高，需要查询相关知识
动作类型：query_knowledge
观察：找到外网延迟相关知识，可能是 ISP 问题或带宽不足
思考：已有足够信息，可以给出答案
动作类型：final_answer
"""

    def __init__(self, knowledge_base: Optional[Any] = None, max_iterations: int = 5):
        self.knowledge_base = knowledge_base
        self.max_iterations = max_iterations
        self.steps: List[ReActStep] = []

        # 初始化 DeepSeek 客户端（兼容 OpenAI SDK）
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            self.use_llm = True
        else:
            self.client = None
            self.use_llm = False
            logger.warning("DEEPSEEK_API_KEY not set, falling back to mock mode")

    def run(self, question: str, context: Dict[str, Any]) -> ReActResult:
        """执行 ReAct 推理循环"""
        self.steps = []

        for i in range(1, self.max_iterations + 1):
            # Think: 生成思考
            thought, thought_type = self._think(question, context, i)

            # Act: 决定动作
            action, action_type, action_input = self._act(thought, context, i)

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
        final_answer = self._generate_final_answer(question, context)
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
        """生成推理思考（真实 LLM）"""
        if not self.use_llm:
            return self._think_mock(question, context, iteration)

        try:
            prompt = self._build_think_prompt(question, context, iteration)

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )

            result = self._parse_think_response(response.choices[0].message.content)
            return result["thought"], ThoughtType(result["thought_type"])

        except Exception as e:
            logger.warning(f"LLM think error: {e}, falling back to mock")
            return self._think_mock(question, context, iteration)

    def _build_think_prompt(self, question: str, context: Dict[str, Any], iteration: int) -> str:
        """构建思考 Prompt（包含 Few-Shot 和 CoT）"""
        # 获取已有推理步骤
        history = self._format_context(context)

        prompt = f"""你是一个运维诊断 Agent。

{self.FEW_SHOT_EXAMPLES}

现在轮到你：

问题：{question}

当前是第 {iteration} 轮推理。

已有推理历史：
{history}

请一步步思考：
1. 我现在掌握了什么信息？
2. 还缺少什么关键信息？
3. 下一步应该采取什么行动？

请用 JSON 格式回复（只返回 JSON，不要其他文字）：
{{
  "thought": "你的思考过程",
  "thought_type": "analyze/plan/decide/reflect"
}}
"""
        return prompt

    def _act(self, thought: str, context: Dict[str, Any], iteration: int) -> tuple[str, ActionType, Dict[str, Any]]:
        """决定动作（真实 LLM）"""
        if not self.use_llm:
            return self._act_mock(thought, context, iteration)

        try:
            prompt = self._build_act_prompt(thought, context, iteration)

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 动作决策用较低温度
                max_tokens=300
            )

            result = self._parse_act_response(response.choices[0].message.content)
            return (
                result["description"],
                ActionType(result["action_type"]),
                result.get("action_input", {})
            )

        except Exception as e:
            logger.warning(f"LLM act error: {e}, falling back to mock")
            return self._act_mock(thought, context, iteration)

    def _build_act_prompt(self, thought: str, context: Dict[str, Any], iteration: int) -> str:
        """构建动作 Prompt"""
        prompt = f"""基于思考：{thought}

可用动作：
- query_knowledge: 查询运维知识库（输入：query 关键词）
- check_metric: 检查指标详情（输入：metric_name 指标名）
- search_log: 搜索日志（输入：keywords 关键词列表）
- final_answer: 给出最终答案（当信息足够时）

当前轮次：{iteration}，最多 {self.max_iterations} 轮

请决定下一步动作，用 JSON 格式回复：
{{
  "action_type": "query_knowledge/check_metric/search_log/final_answer",
  "description": "动作描述",
  "action_input": {{"参数": "值"}}
}}

注意：如果已经有足够信息，应该选择 final_answer
"""
        return prompt

    def _observe(self, action_type: ActionType, action_input: Dict[str, Any], context: Dict[str, Any]) -> str:
        """执行动作并观察结果"""
        if action_type == ActionType.QUERY_KNOWLEDGE:
            query = action_input.get("query", "")
            if self.knowledge_base:
                results = [kb for kb in self.knowledge_base if query.lower() in kb.get("title", "").lower()]
                if results:
                    return f"找到 {len(results)} 条知识：{results[0].get('solution', '未知')[:100]}"
            return "知识库查询完成，未找到精确匹配"

        elif action_type == ActionType.CHECK_METRIC:
            metric = action_input.get("metric_name", "")
            return f"指标 {metric} 当前状态：正常范围 0-100，建议阈值 80"

        elif action_type == ActionType.SEARCH_LOG:
            return "日志搜索完成，发现 3 条相关错误记录"

        elif action_type == ActionType.FINAL_ANSWER:
            return "推理完成"

        return "执行完成"

    def _generate_final_answer(self, question: str, context: Dict[str, Any]) -> str:
        """生成最终答案（真实 LLM）"""
        if not self.use_llm:
            return self._generate_final_answer_mock()

        try:
            # 汇总所有推理步骤
            steps_summary = "\n".join([
                f"轮次 {step.iteration}: {step.thought} → {step.observation}"
                for step in self.steps
            ])

            prompt = f"""
问题：{question}

推理过程：
{steps_summary}

请基于以上推理过程，生成一个简洁的最终答案（100字以内）。
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=200
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"LLM generate answer error: {e}, falling back to mock")
            return self._generate_final_answer_mock()

    def _parse_think_response(self, content: str) -> dict:
        """解析思考响应"""
        try:
            # 尝试提取 JSON
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content)

            # 验证字段
            if "thought" not in result:
                result["thought"] = "继续推理"
            if "thought_type" not in result:
                result["thought_type"] = "analyze"

            return result
        except Exception as e:
            logger.error(f"Failed to parse think response: {e}")
            return {
                "thought": content[:200] if content else "继续推理",
                "thought_type": "analyze"
            }

    def _parse_act_response(self, content: str) -> dict:
        """解析动作响应"""
        try:
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content)

            if "action_type" not in result:
                result["action_type"] = "final_answer"
            if "description" not in result:
                result["description"] = "执行动作"

            return result
        except Exception as e:
            logger.error(f"Failed to parse act response: {e}")
            return {
                "action_type": "final_answer",
                "description": content[:100] if content else "执行动作",
                "action_input": {}
            }

    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        lines = []
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. 思考: {step.thought[:50]}")
            lines.append(f"   动作: {step.action_type}")
            lines.append(f"   观察: {step.observation[:50]}")
        return "\n".join(lines) if lines else "（无）"

    # Mock 版本（向后兼容）
    def _think_mock(self, question: str, context: Dict[str, Any], iteration: int) -> tuple[str, ThoughtType]:
        """Mock 版本的思考"""
        if iteration == 1:
            return f"分析问题：{question}。需要识别关键指标、异常特征和可能原因。", ThoughtType.ANALYZE
        elif iteration == 2:
            last_obs = context.get("last_observation", "")
            return f"基于观察 '{last_obs[:50]}...'，需要查询知识库获取相关诊断方法。", ThoughtType.PLAN
        elif iteration < self.max_iterations:
            return "根据已收集的信息，决定执行具体诊断动作或给出答案。", ThoughtType.DECIDE
        else:
            return "已达到最大迭代次数，汇总现有信息给出最终建议。", ThoughtType.REFLECT

    def _act_mock(self, thought: str, context: Dict[str, Any], iteration: int) -> tuple[str, ActionType, Dict[str, Any]]:
        """Mock 版本的动作"""
        if iteration == 1:
            return "查询知识库", ActionType.QUERY_KNOWLEDGE, {"query": context.get("keywords", [])}
        elif iteration == 2:
            return "检查指标详情", ActionType.CHECK_METRIC, {"metric": context.get("metric_name", "")}
        elif iteration == 3:
            return "搜索相关日志", ActionType.SEARCH_LOG, {"keywords": context.get("keywords", [])}
        else:
            return "生成最终答案", ActionType.FINAL_ANSWER, {}

    def _generate_final_answer_mock(self) -> str:
        """Mock 版本的答案生成"""
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
