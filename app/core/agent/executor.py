import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.core.models.agent import Action, ExecutionResult, ExecutionStatus


class BaseExecutor(ABC):
    """执行器基类"""

    @abstractmethod
    async def execute(self, action: Action, parameters: dict = None) -> ExecutionResult:
        """执行动作"""
        pass

    @abstractmethod
    async def validate(self, action: Action) -> tuple[bool, Optional[str]]:
        """
        验证动作是否可执行

        Returns:
            (is_valid, error_message)
        """
        pass

    async def rollback(self, action: Action) -> ExecutionResult:
        """回滚动作（可选实现）"""
        raise NotImplementedError("Rollback not implemented for this executor")


class CommandExecutor(BaseExecutor):
    """命令执行器 - 执行简单的 Shell 命令"""

    # 命令白名单 - 只允许执行这些命令
    ALLOWED_COMMANDS = {
        # 查看类命令（低风险）
        "ps", "top", "df", "du", "free", "uptime", "whoami",
        "ls", "cat", "head", "tail", "grep", "find", "wc",
        "ip", "ifconfig", "netstat", "ss", "ping", "curl", "wget",
        "systemctl status", "service status", "journalctl",

        # 管理类命令（中/高风险）- 需要用户确认
        "systemctl restart", "systemctl start", "systemctl stop",
        "service restart", "service start", "service stop",
        "docker ps", "docker logs", "docker restart",
        "kubectl get", "kubectl describe", "kubectl logs",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def validate(self, action: Action) -> tuple[bool, Optional[str]]:
        """验证命令是否在白名单中"""
        command = action.command.strip()

        # 检查命令是否在白名单中
        command_base = command.split()[0] if command else ""

        # 检查完整命令或命令前缀是否在白名单中
        for allowed in self.ALLOWED_COMMANDS:
            if command.startswith(allowed):
                return True, None

        return False, f"Command '{command_base}' is not in the allowed list"

    async def execute(self, action: Action, parameters: dict = None) -> ExecutionResult:
        """执行命令"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        # 验证命令
        is_valid, error_msg = await self.validate(action)
        if not is_valid:
            return ExecutionResult(
                execution_id=execution_id,
                action_id=action.id,
                status=ExecutionStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=0,
                error=error_msg
            )

        # 处理参数替换
        command = action.command
        if parameters:
            for key, value in parameters.items():
                command = command.replace(f"{{{key}}}", str(value))

        try:
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            # 等待执行完成或超时
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=action.timeout
                )

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                stdout = stdout_data.decode('utf-8', errors='replace')
                stderr = stderr_data.decode('utf-8', errors='replace')
                exit_code = process.returncode

                status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED

                return ExecutionResult(
                    execution_id=execution_id,
                    action_id=action.id,
                    status=status,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    error=stderr if exit_code != 0 else None
                )

            except asyncio.TimeoutError:
                # 超时，杀死进程
                process.kill()
                await process.wait()

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                return ExecutionResult(
                    execution_id=execution_id,
                    action_id=action.id,
                    status=ExecutionStatus.TIMEOUT,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    error=f"Command execution timed out after {action.timeout} seconds"
                )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return ExecutionResult(
                execution_id=execution_id,
                action_id=action.id,
                status=ExecutionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error=str(e)
            )


class ExecutorFactory:
    """执行器工厂"""

    _executors = {
        "command": CommandExecutor,
    }

    @classmethod
    def get_executor(cls, action_type: str) -> BaseExecutor:
        """获取执行器实例"""
        executor_class = cls._executors.get(action_type)
        if not executor_class:
            raise ValueError(f"Unsupported action type: {action_type}")
        return executor_class()
