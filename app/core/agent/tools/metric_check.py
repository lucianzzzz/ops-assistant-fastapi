"""指标检查工具"""
import time
from app.core.agent.tools.base import BaseTool, ToolDefinition, ToolResult, ToolCategory


class MetricCheckTool(BaseTool):
    """指标检查工具"""

    def __init__(self, repository=None):
        self.repository = repository
        super().__init__()

    def _define(self) -> ToolDefinition:
        return ToolDefinition(
            name="metric_check",
            description="检查指标的当前状态、阈值、历史趋势",
            category=ToolCategory.QUERY,
            dangerous=False,
            parameters={
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                    "time_range": {"type": "string", "default": "1h"}
                },
                "required": ["metric_name"]
            }
        )

    async def execute(self, metric_name: str, time_range: str = "1h") -> ToolResult:
        start = time.time()

        try:
            # 从 repository 查找指标
            metric_info = None
            if self.repository:
                for item in self.repository.list_metrics():
                    if metric_name.lower() in item.name.lower():
                        metric_info = {
                            "name": item.name,
                            "metric": item.metric,
                            "measurement": item.measurement,
                            "field_name": item.field_name,
                            "desc": item.desc,
                            "unit": item.unit
                        }
                        break

            # Mock 数据（真实环境会调用 Prometheus API）
            result = {
                "metric": metric_name,
                "current_value": 85.3,
                "threshold": 80.0,
                "status": "warning",
                "trend": "increasing",
                "time_range": time_range,
                "metric_info": metric_info
            }

            return ToolResult(
                success=True,
                output=result,
                execution_time=time.time() - start
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start
            )
