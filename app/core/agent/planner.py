"""Planning 系统"""
import uuid
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.common.logging import get_logger

logger = get_logger(__name__)


class PlanStep(BaseModel):
    """计划步骤"""
    step_id: str
    description: str
    tool_name: Optional[str] = None
    tool_params: dict = {}
    dependencies: List[str] = []  # 依赖的步骤 ID
    status: str = "pending"  # pending/running/completed/failed
    result: Optional[Any] = None


class Plan(BaseModel):
    """执行计划"""
    plan_id: str
    question: str
    steps: List[PlanStep]
    created_at: datetime = datetime.now()


class Planner:
    """规划器"""

    def __init__(self, llm_client=None, memory_manager=None):
        self.llm_client = llm_client
        self.memory = memory_manager

    async def create_plan(self, question: str, context: dict, available_tools: List[dict]) -> Plan:
        """创建执行计划"""

        # 回忆相关记忆
        memory_context = ""
        if self.memory:
            memories = await self.memory.recall(question, top_k=3)
            memory_context = "\n".join([m.content for m in memories])

        # 可用工具描述
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in available_tools
        ])

        # 如果有 LLM，用 LLM 生成计划
        if self.llm_client:
            plan = await self._create_plan_with_llm(
                question, memory_context, tools_desc
            )
        else:
            # Mock 计划
            plan = self._create_plan_mock(question, available_tools)

        return plan

    async def _create_plan_with_llm(self, question: str, memory_context: str, tools_desc: str) -> Plan:
        """用 LLM 生成计划"""
        prompt = f"""
问题：{question}

相关历史：
{memory_context if memory_context else "（无）"}

可用工具：
{tools_desc}

请制定一个多步执行计划，用 JSON 格式回复（只返回 JSON）：
{{
  "steps": [
    {{
      "description": "步骤描述",
      "tool_name": "工具名称（或 null）",
      "tool_params": {{"参数": "值"}},
      "dependencies": []
    }}
  ]
}}

要求：
1. 步骤之间要有逻辑顺序
2. 后续步骤可以依赖前面步骤的结果（用索引表示，如 [0, 1]）
3. 最后一步应该是生成答案
4. 保持简洁，3-5 步即可
"""

        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            # 提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan_data = json.loads(content)

            # 构建 Plan 对象
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                question=question,
                steps=[
                    PlanStep(
                        step_id=str(i),
                        description=step['description'],
                        tool_name=step.get('tool_name'),
                        tool_params=step.get('tool_params', {}),
                        dependencies=[str(d) for d in step.get('dependencies', [])]
                    )
                    for i, step in enumerate(plan_data['steps'])
                ]
            )

            return plan

        except Exception as e:
            logger.warning(f"LLM planning error: {e}, falling back to mock")
            return self._create_plan_mock(question, [])

    def _create_plan_mock(self, question: str, available_tools: List[dict]) -> Plan:
        """Mock 计划生成"""
        steps = [
            PlanStep(
                step_id="0",
                description="查询知识库获取相关信息",
                tool_name="knowledge_query" if available_tools else None,
                tool_params={"query": question, "top_k": 3},
                dependencies=[]
            ),
            PlanStep(
                step_id="1",
                description="检查相关指标状态",
                tool_name="metric_check" if available_tools else None,
                tool_params={"metric_name": "相关指标"},
                dependencies=["0"]
            ),
            PlanStep(
                step_id="2",
                description="综合分析并生成答案",
                tool_name=None,
                tool_params={},
                dependencies=["0", "1"]
            )
        ]

        return Plan(
            plan_id=str(uuid.uuid4()),
            question=question,
            steps=steps
        )

    async def execute_plan(self, plan: Plan, tool_registry=None) -> dict:
        """执行计划"""
        results = {}

        for step in plan.steps:
            # 检查依赖是否完成
            for dep_id in step.dependencies:
                dep_step = next((s for s in plan.steps if s.step_id == dep_id), None)
                if not dep_step or dep_step.status != "completed":
                    step.status = "failed"
                    step.result = f"依赖步骤 {dep_id} 未完成"
                    continue

            # 执行步骤
            step.status = "running"

            if step.tool_name and tool_registry:
                tool = tool_registry.get(step.tool_name)
                if tool:
                    try:
                        result = await tool.execute(**step.tool_params)
                        step.result = result.output
                        step.status = "completed" if result.success else "failed"
                    except Exception as e:
                        step.status = "failed"
                        step.result = f"执行错误: {str(e)}"
                else:
                    step.status = "failed"
                    step.result = f"工具 {step.tool_name} 不存在"
            else:
                # 无工具，直接标记完成
                step.status = "completed"
                step.result = "步骤完成（无工具调用）"

            # 记录到记忆
            if self.memory:
                await self.memory.remember(
                    content=f"执行了 {step.description}，结果：{str(step.result)[:100]}",
                    memory_type="short_term",
                    importance=0.6
                )

            results[step.step_id] = step.result

        return results
