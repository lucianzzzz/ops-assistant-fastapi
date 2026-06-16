"""工具注册中心"""
from typing import Optional, List
from app.core.agent.tools.base import BaseTool, ToolDefinition


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.definition.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """列出所有工具"""
        return [tool.definition for tool in self.tools.values()]

    def list_safe_tools(self) -> List[ToolDefinition]:
        """列出安全工具（不需要审批）"""
        return [
            tool.definition
            for tool in self.tools.values()
            if not tool.definition.requires_approval
        ]


# 全局注册中心
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry


def register_builtin_tools(repository=None):
    """注册内置工具"""
    from app.core.agent.tools.knowledge_query import KnowledgeQueryTool
    from app.core.agent.tools.metric_check import MetricCheckTool
    from app.core.agent.tools.shell_command import ShellCommandTool

    registry = get_tool_registry()
    registry.register(KnowledgeQueryTool(repository))
    registry.register(MetricCheckTool(repository))
    registry.register(ShellCommandTool())
