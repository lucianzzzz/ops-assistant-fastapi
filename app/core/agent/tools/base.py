"""Tool Use 基础框架"""
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum
import time


class ToolCategory(str, Enum):
    """工具分类"""
    QUERY = "query"          # 查询类（安全）
    COMMAND = "command"      # 命令类（危险）
    API = "api"              # API 调用
    DATABASE = "database"    # 数据库操作


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str = Field(description="工具名称")
    description: str = Field(description="工具描述")
    category: ToolCategory
    parameters: dict = Field(description="参数 JSON Schema")
    dangerous: bool = Field(default=False, description="是否危险")
    requires_approval: bool = Field(default=False, description="是否需要人工确认")


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float


class BaseTool(ABC):
    """工具基类"""

    def __init__(self):
        self.definition = self._define()

    @abstractmethod
    def _define(self) -> ToolDefinition:
        """定义工具"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        # TODO: 用 JSON Schema 验证
        return True
