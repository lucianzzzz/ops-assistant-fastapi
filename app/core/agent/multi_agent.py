"""Multi-Agent 协作系统"""
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class AgentRole(str, Enum):
    """Agent 角色"""
    COORDINATOR = "coordinator"  # 协调者
    NETWORK = "network"  # 网络专家
    DATABASE = "database"  # 数据库专家
    SYSTEM = "system"  # 系统专家
    SECURITY = "security"  # 安全专家


class AgentMessage(BaseModel):
    """Agent 消息"""
    from_agent: AgentRole
    to_agent: AgentRole
    message_type: str  # request, response, notification
    content: Dict[str, Any]
    timestamp: datetime = datetime.now()


class AgentTask(BaseModel):
    """Agent 任务"""
    task_id: str
    assigned_to: AgentRole
    description: str
    context: Dict[str, Any]
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None


class BaseAgent:
    """基础 Agent"""

    def __init__(self, role: AgentRole, name: str):
        self.role = role
        self.name = name
        self.capabilities: List[str] = []
        self.message_queue: List[AgentMessage] = []

    def can_handle(self, task: AgentTask) -> bool:
        """判断是否能处理任务"""
        return False

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行任务"""
        raise NotImplementedError

    def send_message(self, to_agent: AgentRole, message_type: str, content: Dict[str, Any]) -> AgentMessage:
        """发送消息"""
        message = AgentMessage(
            from_agent=self.role,
            to_agent=to_agent,
            message_type=message_type,
            content=content
        )
        return message


class NetworkAgent(BaseAgent):
    """网络诊断专家"""

    def __init__(self):
        super().__init__(AgentRole.NETWORK, "网络诊断专家")
        self.capabilities = ["网络连接", "延迟分析", "带宽检查", "路由诊断"]

    def can_handle(self, task: AgentTask) -> bool:
        keywords = ["网络", "连接", "延迟", "带宽", "ping", "路由"]
        description = task.description.lower()
        return any(kw in description for kw in keywords)

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行网络诊断"""
        return {
            "status": "success",
            "findings": ["网络延迟正常", "带宽充足"],
            "recommendations": ["建议定期监控"]
        }


class DatabaseAgent(BaseAgent):
    """数据库诊断专家"""

    def __init__(self):
        super().__init__(AgentRole.DATABASE, "数据库诊断专家")
        self.capabilities = ["慢查询分析", "连接池检查", "锁等待分析", "索引优化"]

    def can_handle(self, task: AgentTask) -> bool:
        keywords = ["数据库", "查询", "连接池", "锁", "索引", "sql", "mysql", "postgres"]
        description = task.description.lower()
        return any(kw in description for kw in keywords)

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行数据库诊断"""
        return {
            "status": "success",
            "findings": ["发现 3 条慢查询", "连接池使用率 75%"],
            "recommendations": ["优化查询索引", "增加连接池大小"]
        }


class SystemAgent(BaseAgent):
    """系统资源专家"""

    def __init__(self):
        super().__init__(AgentRole.SYSTEM, "系统资源专家")
        self.capabilities = ["CPU 分析", "内存分析", "磁盘检查", "进程监控"]

    def can_handle(self, task: AgentTask) -> bool:
        keywords = ["cpu", "内存", "磁盘", "进程", "资源", "system"]
        description = task.description.lower()
        return any(kw in description for kw in keywords)

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行系统诊断"""
        return {
            "status": "success",
            "findings": ["CPU 使用率 85%", "内存充足"],
            "recommendations": ["检查高负载进程"]
        }


class CoordinatorAgent(BaseAgent):
    """协调者 Agent - 分配任务和汇总结果"""

    def __init__(self):
        super().__init__(AgentRole.COORDINATOR, "协调者")
        self.specialists: Dict[AgentRole, BaseAgent] = {
            AgentRole.NETWORK: NetworkAgent(),
            AgentRole.DATABASE: DatabaseAgent(),
            AgentRole.SYSTEM: SystemAgent(),
        }
        self.task_assignments: Dict[str, AgentRole] = {}

    def decompose_question(self, question: str) -> List[AgentTask]:
        """将问题分解为子任务"""
        tasks = []

        # 简单的关键词分析
        question_lower = question.lower()

        if any(kw in question_lower for kw in ["网络", "连接", "延迟"]):
            tasks.append(AgentTask(
                task_id=f"task_net_{len(tasks)}",
                assigned_to=AgentRole.NETWORK,
                description=f"网络诊断: {question}",
                context={"question": question}
            ))

        if any(kw in question_lower for kw in ["数据库", "查询", "sql"]):
            tasks.append(AgentTask(
                task_id=f"task_db_{len(tasks)}",
                assigned_to=AgentRole.DATABASE,
                description=f"数据库诊断: {question}",
                context={"question": question}
            ))

        if any(kw in question_lower for kw in ["cpu", "内存", "磁盘", "系统"]):
            tasks.append(AgentTask(
                task_id=f"task_sys_{len(tasks)}",
                assigned_to=AgentRole.SYSTEM,
                description=f"系统诊断: {question}",
                context={"question": question}
            ))

        # 如果没有匹配，创建通用任务
        if not tasks:
            tasks.append(AgentTask(
                task_id=f"task_general_{len(tasks)}",
                assigned_to=AgentRole.SYSTEM,
                description=f"通用诊断: {question}",
                context={"question": question}
            ))

        return tasks

    async def coordinate(self, question: str) -> Dict[str, Any]:
        """协调多个 Agent 完成任务"""
        # 分解任务
        tasks = self.decompose_question(question)

        # 分配并执行
        results = []
        for task in tasks:
            agent = self.specialists.get(task.assigned_to)
            if agent and agent.can_handle(task):
                task.status = "in_progress"
                result = await agent.execute_task(task)
                task.status = "completed"
                task.result = result
                results.append({
                    "agent": agent.name,
                    "task_id": task.task_id,
                    "result": result
                })

        # 汇总结果
        summary = self._synthesize_results(question, results)
        return summary

    def _synthesize_results(self, question: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """综合多个 Agent 的结果"""
        all_findings = []
        all_recommendations = []

        for result in results:
            agent_result = result.get("result", {})
            all_findings.extend(agent_result.get("findings", []))
            all_recommendations.extend(agent_result.get("recommendations", []))

        return {
            "question": question,
            "agents_involved": [r["agent"] for r in results],
            "findings": all_findings,
            "recommendations": all_recommendations,
            "summary": f"共 {len(results)} 个专家参与诊断，发现 {len(all_findings)} 个问题"
        }


class MultiAgentSystem:
    """Multi-Agent 系统"""

    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.execution_history: List[Dict[str, Any]] = []

    async def solve(self, question: str) -> Dict[str, Any]:
        """使用多 Agent 协作解决问题"""
        result = await self.coordinator.coordinate(question)
        self.execution_history.append({
            "question": question,
            "result": result,
            "timestamp": datetime.now()
        })
        return result

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]
