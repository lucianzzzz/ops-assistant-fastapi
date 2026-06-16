"""Shell 命令工具（带安全沙箱）"""
import subprocess
import shlex
import time
from app.core.agent.tools.base import BaseTool, ToolDefinition, ToolResult, ToolCategory


class ShellCommandTool(BaseTool):
    """Shell 命令工具（危险，需要沙箱）"""

    # 白名单：允许的命令
    ALLOWED_COMMANDS = {
        "ps", "top", "df", "free", "netstat", "ping",
        "curl", "dig", "nslookup", "traceroute",
        "uptime", "whoami", "hostname", "date"
    }

    # 黑名单：禁止的命令
    FORBIDDEN_COMMANDS = {
        "rm", "rmdir", "mv", "dd", "mkfs",
        "shutdown", "reboot", "kill", "pkill",
        "chmod", "chown", "su", "sudo"
    }

    def _define(self) -> ToolDefinition:
        return ToolDefinition(
            name="shell_command",
            description="执行安全的 Shell 命令（只读操作）",
            category=ToolCategory.COMMAND,
            dangerous=True,
            requires_approval=True,
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"}
                },
                "required": ["command"]
            }
        )

    def _is_safe(self, command: str) -> tuple[bool, str]:
        """检查命令是否安全"""
        # 解析命令
        try:
            parts = shlex.split(command)
        except Exception as e:
            logger.error(f"Failed to parse command: {e}")
            return False, "命令解析失败"

        if not parts:
            return False, "空命令"

        base_cmd = parts[0]

        # 检查黑名单
        if base_cmd in self.FORBIDDEN_COMMANDS:
            return False, f"禁止的命令: {base_cmd}"

        # 检查白名单
        if base_cmd not in self.ALLOWED_COMMANDS:
            return False, f"命令不在白名单: {base_cmd}"

        # 检查危险字符
        dangerous_patterns = [
            "|", "&&", "||", ";", ">", "<", "`", "$("
        ]
        if any(p in command for p in dangerous_patterns):
            return False, "包含危险字符"

        return True, "安全"

    async def execute(self, command: str) -> ToolResult:
        start = time.time()

        # 安全检查
        is_safe, reason = self._is_safe(command)
        if not is_safe:
            return ToolResult(
                success=False,
                output=None,
                error=f"命令被拒绝: {reason}",
                execution_time=time.time() - start
            )

        try:
            # 执行命令（带超时）
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,  # 10秒超时
                check=False
            )

            return ToolResult(
                success=result.returncode == 0,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                },
                execution_time=time.time() - start
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error="命令执行超时",
                execution_time=time.time() - start
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start
            )
