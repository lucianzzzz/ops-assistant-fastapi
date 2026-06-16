"""测试真实 ReAct Agent"""
import pytest
import os
from app.core.agent.real_react_agent import RealReActAgent


class TestRealReActAgent:
    """测试真实 ReAct Agent"""

    @pytest.fixture
    def agent(self):
        """创建 Agent（会检测环境变量决定是否用 LLM）"""
        return RealReActAgent(max_iterations=3)

    def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent.max_iterations == 3
        assert len(agent.steps) == 0

    def test_run_basic_question(self, agent):
        """测试基本问题推理"""
        question = "IF1接收时延异常怎么处理？"
        context = {"keywords": ["IF1", "时延"], "metric_name": "IF1接收时延"}

        result = agent.run(question, context)

        assert result.question == question
        assert result.success is True
        assert result.total_iterations > 0
        assert len(result.steps) > 0
        assert result.final_answer != ""

    def test_reasoning_steps(self, agent):
        """测试推理步骤"""
        question = "CPU使用率过高"
        context = {"keywords": ["CPU"], "metric_name": "CPU使用率"}

        result = agent.run(question, context)

        # 验证步骤结构
        for step in result.steps:
            assert step.iteration > 0
            assert step.thought != ""
            assert step.thought_type in ["analyze", "plan", "decide", "reflect"]
            if step.action_type:
                assert step.action_type in [
                    "query_knowledge", "check_metric",
                    "execute_command", "search_log", "final_answer"
                ]

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

    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="需要 DEEPSEEK_API_KEY 环境变量"
    )
    def test_with_real_llm(self, agent):
        """测试真实 LLM（需要 API Key）"""
        if agent.use_llm:
            question = "IF1接收时延异常怎么处理？"
            result = agent.run(question, {"keywords": ["IF1", "时延"]})

            # 验证 LLM 生成的内容不是固定的 Mock 文本
            assert "分析问题" not in result.steps[0].thought or len(result.steps[0].thought) > 50
            print(f"\n=== LLM 推理结果 ===")
            print(result.reasoning_trace)
