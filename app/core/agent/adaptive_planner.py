"""动态重规划模块 - 执行失败时自动调整计划"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.core.models.agent import AgentPlan, PlanStep, Action, ExecutionResult, ExecutionStatus


class ReplanStrategy(str, Enum):
    """重规划策略"""
    RETRY = "retry"  # 重试相同步骤
    SKIP = "skip"  # 跳过失败步骤
    ALTERNATIVE = "alternative"  # 使用替代方案
    ESCALATE = "escalate"  # 升级到人工


class ReplanReason(BaseModel):
    """重规划原因"""
    failed_step: int
    error_message: str
    strategy: ReplanStrategy
    rationale: str


class AdaptivePlanner:
    """自适应规划器 - 根据执行反馈动态调整"""

    def __init__(self, max_replans: int = 3):
        self.max_replans = max_replans
        self.replan_history: List[ReplanReason] = []

    def should_replan(self, execution_result: ExecutionResult, current_plan: AgentPlan) -> bool:
        """判断是否需要重规划"""
        # 成功执行不需要重规划
        if execution_result.status == ExecutionStatus.SUCCESS:
            return False

        # 达到重规划上限
        if len(self.replan_history) >= self.max_replans:
            return False

        # 失败或超时需要重规划
        return execution_result.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]

    def generate_replan(
        self,
        original_plan: AgentPlan,
        failed_execution: ExecutionResult,
        context: Dict[str, Any]
    ) -> Optional[AgentPlan]:
        """生成新计划"""
        # 确定重规划策略
        strategy = self._determine_strategy(failed_execution, context)

        reason = ReplanReason(
            failed_step=context.get("current_step", 0),
            error_message=failed_execution.error or "Unknown error",
            strategy=strategy,
            rationale=self._explain_strategy(strategy, failed_execution)
        )
        self.replan_history.append(reason)

        # 根据策略生成新计划
        if strategy == ReplanStrategy.RETRY:
            return self._retry_plan(original_plan, failed_execution)
        elif strategy == ReplanStrategy.SKIP:
            return self._skip_step_plan(original_plan, context.get("current_step", 0))
        elif strategy == ReplanStrategy.ALTERNATIVE:
            return self._alternative_plan(original_plan, context)
        elif strategy == ReplanStrategy.ESCALATE:
            return None  # 需要人工介入

        return None

    def _determine_strategy(self, execution: ExecutionResult, context: Dict[str, Any]) -> ReplanStrategy:
        """决定重规划策略"""
        error_msg = (execution.error or "").lower()

        # 超时或临时错误 -> 重试
        if execution.status == ExecutionStatus.TIMEOUT or "timeout" in error_msg:
            return ReplanStrategy.RETRY

        # 权限错误或高风险 -> 升级
        if "permission" in error_msg or "denied" in error_msg:
            return ReplanStrategy.ESCALATE

        # 资源不存在 -> 跳过
        if "not found" in error_msg or "does not exist" in error_msg:
            return ReplanStrategy.SKIP

        # 默认尝试替代方案
        return ReplanStrategy.ALTERNATIVE

    def _retry_plan(self, original_plan: AgentPlan, execution: ExecutionResult) -> AgentPlan:
        """生成重试计划"""
        new_plan = original_plan.model_copy(deep=True)
        new_plan.plan_id = f"{original_plan.plan_id}_retry_{len(self.replan_history)}"

        # 调整超时时间
        if execution.status == ExecutionStatus.TIMEOUT:
            new_plan.context_summary += " (已调整执行超时)"

        return new_plan

    def _skip_step_plan(self, original_plan: AgentPlan, failed_step: int) -> AgentPlan:
        """生成跳过步骤的计划"""
        new_plan = original_plan.model_copy(deep=True)
        new_plan.plan_id = f"{original_plan.plan_id}_skip_{failed_step}"

        # 移除失败的步骤
        new_plan.steps = [s for s in new_plan.steps if s.order != failed_step]

        # 重新排序
        for i, step in enumerate(new_plan.steps, start=1):
            step.order = i
            # 移除对已跳过步骤的依赖
            if step.depends_on:
                step.depends_on = [d for d in step.depends_on if d != failed_step]

        new_plan.context_summary += f" (已跳过步骤 {failed_step})"
        return new_plan

    def _alternative_plan(self, original_plan: AgentPlan, context: Dict[str, Any]) -> AgentPlan:
        """生成替代方案计划"""
        new_plan = original_plan.model_copy(deep=True)
        new_plan.plan_id = f"{original_plan.plan_id}_alt_{len(self.replan_history)}"

        # 调整步骤：添加更多验证
        fallback_step = PlanStep(
            order=len(new_plan.steps) + 1,
            title="执行替代诊断方法",
            rationale="原方案失败，使用更保守的检查手段收集信息",
            tool_name="safe_inspection",
            depends_on=[1],
            requires_approval=False
        )
        new_plan.steps.append(fallback_step)

        new_plan.context_summary += " (已切换到替代方案)"
        return new_plan

    def _explain_strategy(self, strategy: ReplanStrategy, execution: ExecutionResult) -> str:
        """解释策略选择"""
        explanations = {
            ReplanStrategy.RETRY: f"临时错误或超时，重试执行",
            ReplanStrategy.SKIP: f"资源不存在或不可用，跳过此步骤",
            ReplanStrategy.ALTERNATIVE: f"执行失败，切换替代方案",
            ReplanStrategy.ESCALATE: f"权限不足或高风险操作，需要人工介入"
        }
        return explanations.get(strategy, "未知策略")

    def get_replan_summary(self) -> str:
        """获取重规划摘要"""
        if not self.replan_history:
            return "未发生重规划"

        lines = [f"共重规划 {len(self.replan_history)} 次:"]
        for i, reason in enumerate(self.replan_history, 1):
            lines.append(f"{i}. 步骤 {reason.failed_step} 失败 -> {reason.strategy.value}: {reason.rationale}")

        return "\n".join(lines)
