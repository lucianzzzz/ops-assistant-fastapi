"""Agent Service 集成测试"""
import pytest
from app.core.agent.agent_service import AgentService
from app.core.agent.action_generator import ActionGenerator


class TestAgentServiceWithReAct:
    """测试集成 ReAct 的 Agent Service"""

    @pytest.fixture
    def knowledge_base(self):
        """测试知识库"""
        return [
            {
                "id": "kb1",
                "title": "CPU 使用率告警处理",
                "description": "当 CPU 使用率超过阈值时的处理方法",
                "solution": "1. top 查看进程 2. 分析占用最高的进程 3. 优化或重启",
                "tags": ["CPU", "性能"],
                "category": "性能"
            }
        ]

    @pytest.fixture
    def service(self, knowledge_base):
        """创建 Agent Service"""
        action_gen = ActionGenerator(knowledge_base)
        return AgentService(action_gen, knowledge_base)

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.action_generator is not None
        assert service.knowledge_base is not None

    def test_create_plan_with_react(self, service):
        """测试使用 ReAct 创建计划"""
        question = "CPU 使用率过高怎么办？"
        analysis_result = {
            "keywords": ["CPU", "使用率"],
            "normalized_metric": "cpu_usage",
            "confidence": 0.9
        }

        plan = service.create_plan(question, analysis_result, use_react=True)

        assert plan.plan_id is not None
        assert plan.question == question
        assert len(plan.steps) > 0
        assert "ReAct 推理" in plan.steps[2].title or "推理" in plan.steps[2].rationale

    def test_create_plan_without_react(self, service):
        """测试不使用 ReAct 创建计划（降级模式）"""
        question = "内存告警"
        analysis_result = {
            "keywords": ["内存"],
            "normalized_metric": "memory_usage"
        }

        plan = service.create_plan(question, analysis_result, use_react=False)

        assert plan.plan_id is not None
        assert len(plan.steps) > 0

    def test_memory_with_react_facts(self, service):
        """测试记忆包含 ReAct 信息"""
        question = "测试问题"
        analysis_result = {"keywords": ["测试"], "normalized_metric": "test_metric"}

        plan = service.create_plan(question, analysis_result, session_id="test_session", use_react=True)
        memory = service.get_memory("test_session")

        assert memory.session_id == "test_session"
        assert len(memory.facts) > 0

    def test_audit_events_tracking(self, service):
        """测试审计事件追踪"""
        initial_count = len(service.audit_events)

        service.create_plan(
            "测试",
            {"keywords": ["测试"], "normalized_metric": "test"},
            use_react=True
        )

        assert len(service.audit_events) > initial_count
        # 应该有 plan_created 事件
        assert any(e.event_type == "plan_created" for e in service.audit_events)

    def test_get_react_result(self, service):
        """测试获取 ReAct 推理结果"""
        question = "CPU 问题"
        analysis_result = {"keywords": ["CPU"], "normalized_metric": "cpu_usage"}
        session_id = "react_test"

        service.create_plan(question, analysis_result, session_id=session_id, use_react=True)

        react_result = service.get_react_result(session_id)
        # 如果 ReAct 初始化成功，应该有结果
        if service.react_agent:
            assert react_result is not None
            assert react_result.question == question
