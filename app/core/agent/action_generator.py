import uuid
from typing import Optional

from app.core.models.agent import Action, ActionType, RiskLevel
from app.core.ai.ai_assistant import AIAssistant


class ActionGenerator:
    """动作生成器 - 根据问题和分析结果生成可执行动作"""

    # 预定义的动作模板库
    ACTION_TEMPLATES = {
        # 网络相关
        "网络": [
            {
                "title": "查看网络接口状态",
                "command": "ip -s link show",
                "description": "检查网络接口的状态和统计信息",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            },
            {
                "title": "测试网络连通性",
                "command": "ping -c 5 {target}",
                "description": "测试到目标地址的网络连通性",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 15
            },
            {
                "title": "查看网络连接",
                "command": "ss -tuln",
                "description": "查看当前所有网络连接",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            }
        ],

        # 服务相关
        "服务": [
            {
                "title": "查看服务状态",
                "command": "systemctl status {service}",
                "description": "检查服务的运行状态",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            },
            {
                "title": "查看服务日志",
                "command": "journalctl -u {service} -n 50 --no-pager",
                "description": "查看服务最近的日志",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 15
            },
            {
                "title": "重启服务",
                "command": "systemctl restart {service}",
                "description": "重启指定的系统服务",
                "risk_level": RiskLevel.MEDIUM,
                "requires_approval": True,
                "timeout": 30,
                "rollback_command": "systemctl start {service}"
            }
        ],

        # 系统资源
        "系统": [
            {
                "title": "查看系统负载",
                "command": "uptime",
                "description": "查看系统运行时间和负载",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 5
            },
            {
                "title": "查看内存使用",
                "command": "free -h",
                "description": "查看内存使用情况",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 5
            },
            {
                "title": "查看磁盘使用",
                "command": "df -h",
                "description": "查看磁盘空间使用情况",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            },
            {
                "title": "查看进程列表",
                "command": "ps aux --sort=-%mem | head -20",
                "description": "查看占用内存最多的进程",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            }
        ],

        # 日志查看
        "日志": [
            {
                "title": "查看系统日志",
                "command": "journalctl -n 50 --no-pager",
                "description": "查看系统最近的日志",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 15
            },
            {
                "title": "搜索错误日志",
                "command": "journalctl -p err -n 50 --no-pager",
                "description": "查看最近的错误日志",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 15
            }
        ],

        # Docker 相关
        "docker": [
            {
                "title": "查看容器状态",
                "command": "docker ps -a",
                "description": "查看所有 Docker 容器状态",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 10
            },
            {
                "title": "查看容器日志",
                "command": "docker logs --tail 50 {container}",
                "description": "查看容器日志",
                "risk_level": RiskLevel.LOW,
                "requires_approval": False,
                "timeout": 15
            },
            {
                "title": "重启容器",
                "command": "docker restart {container}",
                "description": "重启 Docker 容器",
                "risk_level": RiskLevel.MEDIUM,
                "requires_approval": True,
                "timeout": 30
            }
        ]
    }

    def __init__(self, ai_assistant: Optional[AIAssistant] = None):
        self.ai_assistant = ai_assistant or AIAssistant()

    def generate_from_keywords(self, keywords: list[str], metric_name: str = "") -> list[Action]:
        """根据关键词生成动作"""
        actions = []

        # 1. 根据关键词匹配模板
        for keyword in keywords:
            keyword_lower = keyword.lower()

            for category, templates in self.ACTION_TEMPLATES.items():
                if keyword_lower in category.lower():
                    for template in templates[:2]:
                        action = self._create_action_from_template(template, keyword, metric_name)
                        actions.append(action)

        # 2. 添加通用诊断动作
        if not actions or len(actions) < 3:
            actions.extend(self._get_default_diagnostic_actions())

        # 3. 去重并限制数量
        seen = set()
        unique_actions = []
        for action in actions:
            if action.title not in seen:
                seen.add(action.title)
                unique_actions.append(action)
                if len(unique_actions) >= 5:
                    break

        return unique_actions

    def _create_action_from_template(self, template: dict, keyword: str, metric_name: str) -> Action:
        """从模板创建动作实例"""
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        command = template["command"]
        description = template["description"]

        # 尝试填充参数
        if "{service}" in command and metric_name:
            service_name = metric_name.split("_")[0] if "_" in metric_name else "nginx"
            command = command.replace("{service}", service_name)

        if "{target}" in command:
            command = command.replace("{target}", "8.8.8.8")

        if "{container}" in command and metric_name:
            container_name = metric_name.split("_")[0] if "_" in metric_name else "app"
            command = command.replace("{container}", container_name)

        return Action(
            id=action_id,
            type=ActionType.COMMAND,
            title=template["title"],
            description=description,
            command=command,
            risk_level=template["risk_level"],
            requires_approval=template["requires_approval"],
            timeout=template["timeout"],
            estimated_duration=template.get("estimated_duration", template["timeout"] // 2),
            rollback_command=template.get("rollback_command")
        )

    def _get_default_diagnostic_actions(self) -> list[Action]:
        """获取默认的诊断动作"""
        return [
            Action(
                id=f"act_{uuid.uuid4().hex[:8]}",
                type=ActionType.COMMAND,
                title="查看系统负载",
                description="检查系统当前的负载情况",
                command="uptime",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                timeout=5,
                estimated_duration=2
            ),
            Action(
                id=f"act_{uuid.uuid4().hex[:8]}",
                type=ActionType.COMMAND,
                title="查看内存使用",
                description="检查内存使用情况",
                command="free -h",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                timeout=5,
                estimated_duration=2
            ),
            Action(
                id=f"act_{uuid.uuid4().hex[:8]}",
                type=ActionType.COMMAND,
                title="查看磁盘空间",
                description="检查磁盘空间使用情况",
                command="df -h",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                timeout=10,
                estimated_duration=3
            )
        ]
