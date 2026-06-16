"""测试 Tool Use 系统"""
import pytest
from app.core.agent.tools.base import ToolCategory
from app.core.agent.tools.knowledge_query import KnowledgeQueryTool
from app.core.agent.tools.metric_check import MetricCheckTool
from app.core.agent.tools.shell_command import ShellCommandTool
from app.core.agent.tools.registry import ToolRegistry


class TestToolUse:
    """测试工具系统"""

    def test_knowledge_query_tool(self):
        """测试知识库查询工具"""
        tool = KnowledgeQueryTool()

        assert tool.definition.name == "knowledge_query"
        assert tool.definition.category == ToolCategory.QUERY
        assert tool.definition.dangerous is False

    @pytest.mark.asyncio
    async def test_knowledge_query_execute(self):
        """测试知识库查询执行"""
        tool = KnowledgeQueryTool()
        result = await tool.execute(query="CPU", top_k=3)

        assert result.success is True
        assert result.execution_time >= 0  # 允许 0（太快了）

    def test_metric_check_tool(self):
        """测试指标检查工具"""
        tool = MetricCheckTool()

        assert tool.definition.name == "metric_check"
        assert tool.definition.category == ToolCategory.QUERY

    @pytest.mark.asyncio
    async def test_metric_check_execute(self):
        """测试指标检查执行"""
        tool = MetricCheckTool()
        result = await tool.execute(metric_name="CPU使用率")

        assert result.success is True
        assert "metric" in result.output

    def test_shell_command_tool(self):
        """测试 Shell 命令工具"""
        tool = ShellCommandTool()

        assert tool.definition.name == "shell_command"
        assert tool.definition.category == ToolCategory.COMMAND
        assert tool.definition.dangerous is True
        assert tool.definition.requires_approval is True

    def test_shell_command_whitelist(self):
        """测试命令白名单"""
        tool = ShellCommandTool()

        # 安全命令
        is_safe, reason = tool._is_safe("ps aux")
        assert is_safe is True

        # 危险命令
        is_safe, reason = tool._is_safe("rm -rf /")
        assert is_safe is False
        assert "禁止" in reason

    @pytest.mark.asyncio
    async def test_shell_command_execute_safe(self):
        """测试执行安全命令"""
        tool = ShellCommandTool()
        result = await tool.execute(command="whoami")

        assert result.success is True
        assert "stdout" in result.output

    @pytest.mark.asyncio
    async def test_shell_command_execute_dangerous(self):
        """测试拒绝危险命令"""
        tool = ShellCommandTool()
        result = await tool.execute(command="rm test.txt")

        assert result.success is False
        assert "拒绝" in result.error

    def test_tool_registry(self):
        """测试工具注册中心"""
        registry = ToolRegistry()
        tool = KnowledgeQueryTool()

        registry.register(tool)

        assert registry.get("knowledge_query") is not None
        assert len(registry.list_tools()) == 1

    def test_list_safe_tools(self):
        """测试列出安全工具"""
        registry = ToolRegistry()
        registry.register(KnowledgeQueryTool())
        registry.register(ShellCommandTool())

        safe_tools = registry.list_safe_tools()
        # knowledge_query 是安全的，shell_command 不是
        assert len(safe_tools) == 1
        assert safe_tools[0].name == "knowledge_query"
