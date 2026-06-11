"""ReAct Agent 单元测试"""
import pytest
from app.core.react_agent import ReActAgent, ReActResult, ThoughtType, ActionType


class TestReActAgent:
    """测试 ReAct Agent"""

    @pytest.fixture
    def agent(self):
        """创建测试 Agent"""
        knowledge_base = [
            {"id": "kb1", "title": "CPU 告警", "solution": "检查进程占用"},
            {"id": "kb2", "title": "内存告警", "solution": "检查内存泄漏"},
        ]
        return ReActAgent(knowledge_base=knowledge_base, max_iterations=3)

    def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent.max_iterations == 3
        assert agent.knowledge_base is not None
        assert len(agent.steps) == 0

    def test_run_basic_question(self, agent):
        """测试基本问题推理"""
        question = "CPU 使用率过高怎么办？"
        context = {"keywords": ["CPU", "使用率"], "metric_name": "cpu_usage"}

        result = agent.run(question, context)

        assert isinstance(result, ReActResult)
        assert result.question == question
        assert result.success is True
        assert result.total_iterations > 0
        assert len(result.steps) > 0
        assert result.final_answer != ""

    def test_reasoning_steps(self, agent):
        """测试推理步骤"""
        question = "内存占用异常"
        context = {"keywords": ["内存"], "metric_name": "memory_usage"}

        result = agent.run(question, context)

        # 验证步骤结构
        for step in result.steps:
            assert step.iteration > 0
            assert step.thought != ""
            assert step.thought_type in ThoughtType
            if step.action_type:
                assert step.action_type in ActionType

    def test_max_iterations(self, agent):
        """测试最大迭代次数限制"""
        result = agent.run("测试问题", {"keywords": []})
        assert result.total_iterations <= agent.max_iterations

    def test_reasoning_trace(self, agent):
        """测试推理轨迹生成"""
        result = agent.run("测试推理轨迹", {"keywords": ["测试"]})
        assert result.reasoning_trace != ""
        assert "轮次" in result.reasoning_trace
        assert "思考" in result.reasoning_trace

    def test_empty_context(self, agent):
        """测试空上下文"""
        result = agent.run("空上下文测试", {})
        assert result.success is True
        assert result.total_iterations > 0


class TestReActStepTypes:
    """测试 ReAct 步骤类型"""

    def test_thought_types(self):
        """测试思考类型枚举"""
        assert ThoughtType.ANALYZE == "analyze"
        assert ThoughtType.PLAN == "plan"
        assert ThoughtType.DECIDE == "decide"
        assert ThoughtType.REFLECT == "reflect"

    def test_action_types(self):
        """测试动作类型枚举"""
        assert ActionType.QUERY_KNOWLEDGE == "query_knowledge"
        assert ActionType.CHECK_METRIC == "check_metric"
        assert ActionType.FINAL_ANSWER == "final_answer"
