"""知识库查询工具"""
import time
from app.core.agent.tools.base import BaseTool, ToolDefinition, ToolResult, ToolCategory


class KnowledgeQueryTool(BaseTool):
    """知识库查询工具"""

    def __init__(self, repository=None):
        self.repository = repository
        super().__init__()

    def _define(self) -> ToolDefinition:
        return ToolDefinition(
            name="knowledge_query",
            description="查询运维知识库，找到相关故障案例和解决方案",
            category=ToolCategory.QUERY,
            dangerous=False,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询关键词"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(self, query: str, top_k: int = 3) -> ToolResult:
        start = time.time()

        try:
            results = []

            if self.repository:
                for item in self.repository.list_knowledge():
                    if query.lower() in item.question.lower():
                        results.append({
                            "question": item.question,
                            "reason": item.reason,
                            "method": item.method
                        })
                        if len(results) >= top_k:
                            break

            return ToolResult(
                success=True,
                output=results,
                execution_time=time.time() - start
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start
            )
