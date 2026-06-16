"""测试 Planning 系统"""
import pytest
from app.core.agent.planner import Planner, Plan, PlanStep
from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.tools.knowledge_query import KnowledgeQueryTool
from app.core.agent.memory.manager import MemoryManager


class TestPlanner:
    """测试规划器"""

    @pytest.fixture
    def planner(self):
        """创建规划器"""
        return Planner()

    @pytest.mark.asyncio
    async def test_create_plan_mock(self, planner):
        """测试创建计划（Mock 模式）"""
        plan = await planner.create_plan(
            question="IF1接收时延异常怎么处理？",
            context={},
            available_tools=[
                {"name": "knowledge_query", "description": "查询知识库"},
                {"name": "metric_check", "description": "检查指标"}
            ]
        )

        assert plan.question == "IF1接收时延异常怎么处理？"
        assert len(plan.steps) > 0
        assert plan.plan_id is not None

    @pytest.mark.asyncio
    async def test_plan_steps_structure(self, planner):
        """测试计划步骤结构"""
        plan = await planner.create_plan(
            question="测试问题",
            context={},
            available_tools=[]
        )

        for step in plan.steps:
            assert step.step_id is not None
            assert step.description != ""
            assert step.status == "pending"

    @pytest.mark.asyncio
    async def test_plan_dependencies(self, planner):
        """测试步骤依赖"""
        plan = await planner.create_plan(
            question="测试依赖",
            context={},
            available_tools=[]
        )

        # 检查依赖关系
        for step in plan.steps:
            # 所有依赖的步骤 ID 应该小于当前步骤 ID
            for dep_id in step.dependencies:
                assert int(dep_id) < int(step.step_id)

    @pytest.mark.asyncio
    async def test_execute_plan_without_tools(self, planner):
        """测试执行计划（无工具）"""
        plan = await planner.create_plan(
            question="测试执行",
            context={},
            available_tools=[]
        )

        results = await planner.execute_plan(plan, tool_registry=None)

        # 所有步骤应该完成（虽然无工具调用）
        for step in plan.steps:
            assert step.status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_execute_plan_with_tools(self, planner):
        """测试执行计划（有工具）"""
        # 创建工具注册中心
        registry = ToolRegistry()
        registry.register(KnowledgeQueryTool())

        # 手动创建一个简单计划
        plan = Plan(
            plan_id="test_plan",
            question="测试工具调用",
            steps=[
                PlanStep(
                    step_id="0",
                    description="查询知识库",
                    tool_name="knowledge_query",
                    tool_params={"query": "CPU", "top_k": 3},
                    dependencies=[]
                )
            ]
        )

        results = await planner.execute_plan(plan, tool_registry=registry)

        # 验证执行结果
        assert "0" in results
        assert plan.steps[0].status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_execute_plan_with_dependencies(self, planner):
        """测试带依赖的计划执行"""
        plan = Plan(
            plan_id="test_plan",
            question="测试依赖执行",
            steps=[
                PlanStep(
                    step_id="0",
                    description="步骤1",
                    dependencies=[]
                ),
                PlanStep(
                    step_id="1",
                    description="步骤2（依赖步骤1）",
                    dependencies=["0"]
                )
            ]
        )

        results = await planner.execute_plan(plan, tool_registry=None)

        # 步骤 1 应该完成
        assert plan.steps[0].status == "completed"
        # 步骤 2 应该在步骤 1 之后执行
        assert plan.steps[1].status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_planner_with_memory(self):
        """测试规划器使用记忆"""
        memory_mgr = MemoryManager(session_id="test_session")

        # 添加相关记忆
        await memory_mgr.remember(
            content="之前处理过 IF1 接收时延问题，是链路故障",
            memory_type="short_term",
            importance=0.8
        )

        # 创建带记忆的规划器
        planner = Planner(memory_manager=memory_mgr)

        plan = await planner.create_plan(
            question="IF1接收时延异常",
            context={},
            available_tools=[]
        )

        # 计划应该成功创建
        assert plan is not None
        assert len(plan.steps) > 0

    @pytest.mark.asyncio
    async def test_plan_execution_failure_handling(self, planner):
        """测试计划执行失败处理"""
        plan = Plan(
            plan_id="test_plan",
            question="测试失败处理",
            steps=[
                PlanStep(
                    step_id="0",
                    description="调用不存在的工具",
                    tool_name="non_existent_tool",
                    dependencies=[]
                ),
                PlanStep(
                    step_id="1",
                    description="依赖失败的步骤",
                    dependencies=["0"]
                )
            ]
        )

        registry = ToolRegistry()
        results = await planner.execute_plan(plan, tool_registry=registry)

        # 步骤 0 应该失败
        assert plan.steps[0].status == "failed"
