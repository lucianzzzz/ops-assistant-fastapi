# Ops Assistant Agent 执行能力架构设计

## 1. 总体架构

```
用户查询
    ↓
本地知识库/AI 查询
    ↓
生成解决方案 + 可执行动作
    ↓
用户确认执行
    ↓
Agent 执行器
    ↓
    ├─ 命令执行器（Shell Command）
    ├─ 脚本执行器（Python/Bash Script）
    ├─ API 调用器（HTTP/REST API）
    └─ SSH 远程执行器（Remote Command）
    ↓
执行结果反馈
    ↓
结果展示 + 日志记录
```

## 2. 核心组件

### 2.1 Action 动作定义

```python
class Action:
    id: str                      # 唯一标识
    type: ActionType             # command, script, api, ssh
    title: str                   # 动作标题："重启 Nginx 服务"
    description: str             # 详细描述
    command: str                 # 执行命令/脚本
    risk_level: RiskLevel        # low, medium, high
    requires_approval: bool      # 是否需要用户确认
    timeout: int                 # 超时时间（秒）
    rollback: Optional[Action]   # 回滚动作
    metadata: dict               # 额外元数据
```

### 2.2 执行器接口

```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, action: Action) -> ExecutionResult:
        """执行动作"""
        pass
    
    @abstractmethod
    async def validate(self, action: Action) -> bool:
        """验证动作是否可执行"""
        pass
    
    @abstractmethod
    async def rollback(self, action: Action) -> ExecutionResult:
        """回滚动作"""
        pass
```

### 2.3 执行结果

```python
class ExecutionResult:
    action_id: str
    status: ExecutionStatus      # pending, running, success, failed, timeout
    start_time: datetime
    end_time: Optional[datetime]
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    error: Optional[str]
```

## 3. 安全控制

### 3.1 权限控制
- **白名单机制**：只允许执行预定义的命令/脚本
- **参数验证**：严格校验命令参数，防止注入
- **用户确认**：高风险操作必须用户确认
- **审计日志**：所有执行记录日志

### 3.2 风险等级定义

| 风险等级 | 示例操作 | 控制措施 |
|---------|---------|---------|
| Low | 查看日志、检查状态 | 自动执行 |
| Medium | 重启服务、清理缓存 | 用户确认 |
| High | 删除数据、修改配置 | 双重确认 + 回滚 |

### 3.3 沙箱隔离
- 限制执行环境（容器/虚拟环境）
- 资源限制（CPU、内存、磁盘）
- 网络隔离（只允许特定 IP/端口）

## 4. 执行器类型

### 4.1 命令执行器（CommandExecutor）
**用途**：执行简单的 Shell 命令

**示例**：
```python
action = Action(
    type=ActionType.COMMAND,
    title="检查 Nginx 状态",
    command="systemctl status nginx",
    risk_level=RiskLevel.LOW,
    requires_approval=False
)
```

### 4.2 脚本执行器（ScriptExecutor）
**用途**：执行预定义的脚本文件

**示例**：
```python
action = Action(
    type=ActionType.SCRIPT,
    title="清理日志文件",
    command="/opt/scripts/clean_logs.sh",
    risk_level=RiskLevel.MEDIUM,
    requires_approval=True
)
```

### 4.3 API 调用器（APIExecutor）
**用途**：调用外部 API（如监控平台、云平台）

**示例**：
```python
action = Action(
    type=ActionType.API,
    title="重启 ECS 实例",
    command="POST /api/v1/instances/{id}/restart",
    metadata={
        "url": "https://api.cloud.com",
        "method": "POST",
        "headers": {"Authorization": "Bearer ..."}
    },
    risk_level=RiskLevel.HIGH,
    requires_approval=True
)
```

### 4.4 SSH 远程执行器（SSHExecutor）
**用途**：通过 SSH 在远程服务器执行命令

**示例**：
```python
action = Action(
    type=ActionType.SSH,
    title="远程重启服务",
    command="systemctl restart app-service",
    metadata={
        "host": "192.168.1.100",
        "port": 22,
        "username": "ops"
    },
    risk_level=RiskLevel.MEDIUM,
    requires_approval=True
)
```

## 5. 智能动作生成

### 5.1 基于知识库的动作映射

```python
knowledge_to_actions = {
    "IF1接收时延异常": [
        Action(
            type=ActionType.COMMAND,
            title="查看网络接口状态",
            command="ip -s link show",
            risk_level=RiskLevel.LOW
        ),
        Action(
            type=ActionType.COMMAND,
            title="查看链路质量",
            command="ping -c 10 {target_ip}",
            risk_level=RiskLevel.LOW
        ),
        Action(
            type=ActionType.SCRIPT,
            title="重启网络服务",
            command="/opt/scripts/restart_network.sh",
            risk_level=RiskLevel.MEDIUM,
            requires_approval=True
        )
    ]
}
```

### 5.2 基于 AI 的动作生成

LangChain 可以根据问题描述生成可执行动作：

```python
prompt = f"""
根据运维问题生成可执行动作：

问题：{question}
分析：{analysis}

生成 3-5 个可执行的运维动作，包括：
1. 诊断性动作（查看日志、检查状态）
2. 修复性动作（重启服务、清理缓存）

每个动作包含：
- 标题
- 命令
- 风险等级（low/medium/high）

输出 JSON 格式。
"""
```

## 6. 执行流程

### 6.1 基本执行流程

```
1. 用户查询
2. 系统分析 → 生成可执行动作列表
3. 前端展示动作列表（带风险标识）
4. 用户选择要执行的动作
5. 高风险动作 → 确认弹窗
6. 后端执行器执行
7. 实时输出流式返回前端
8. 执行完成 → 展示结果
9. 记录审计日志
```

### 6.2 执行状态机

```
PENDING (等待执行)
    ↓
RUNNING (执行中)
    ↓
    ├─ SUCCESS (成功)
    ├─ FAILED (失败) → ROLLBACK (回滚)
    └─ TIMEOUT (超时) → ROLLBACK (回滚)
```

## 7. 前端界面设计

### 7.1 动作卡片

```
┌─────────────────────────────────────┐
│ 🔍 查看 Nginx 日志                  │
│                                     │
│ tail -n 100 /var/log/nginx/error.log│
│                                     │
│ 🟢 低风险  ⏱️ 5s                   │
│                          [执行] 按钮 │
└─────────────────────────────────────┘
```

### 7.2 执行进度

```
┌─────────────────────────────────────┐
│ ⚙️ 正在执行：重启 Nginx 服务...     │
│                                     │
│ ████████████░░░░░░░░ 60%            │
│                                     │
│ 已用时：3.2s / 预计：5s              │
└─────────────────────────────────────┘
```

### 7.3 执行结果

```
┌─────────────────────────────────────┐
│ ✅ 执行成功                          │
│                                     │
│ 命令：systemctl restart nginx       │
│ 耗时：2.3s                          │
│                                     │
│ 输出：                              │
│ ┌─────────────────────────────────┐│
│ │ nginx.service - A high perfor...││
│ │ Active: active (running) since..││
│ └─────────────────────────────────┘│
│                                     │
│ [查看完整日志] [再次执行]           │
└─────────────────────────────────────┘
```

## 8. 数据库设计

### 8.1 执行历史表

```sql
CREATE TABLE execution_history (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    command TEXT NOT NULL,
    risk_level VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration FLOAT,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    error TEXT,
    user_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_execution_status ON execution_history(status);
CREATE INDEX idx_execution_time ON execution_history(start_time);
```

### 8.2 审计日志表

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER REFERENCES execution_history(id),
    event_type VARCHAR(32) NOT NULL,  -- start, approve, execute, success, failed, rollback
    user_id VARCHAR(64),
    ip_address VARCHAR(64),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_execution ON audit_logs(execution_id);
CREATE INDEX idx_audit_time ON audit_logs(created_at);
```

## 9. API 接口设计

### 9.1 生成可执行动作

```
POST /api/v1/actions/generate
Content-Type: application/json

{
  "question": "IF1接收时延异常怎么处理",
  "analysis_result": {...}
}

Response:
{
  "actions": [
    {
      "id": "act_xxx",
      "type": "command",
      "title": "查看网络接口状态",
      "command": "ip -s link show",
      "risk_level": "low",
      "requires_approval": false,
      "estimated_duration": 5
    },
    ...
  ]
}
```

### 9.2 执行动作

```
POST /api/v1/actions/{action_id}/execute
Content-Type: application/json

{
  "parameters": {...}
}

Response (流式):
{
  "execution_id": "exec_xxx",
  "status": "running",
  "stdout": "...",
  "stderr": "..."
}
```

### 9.3 查询执行状态

```
GET /api/v1/executions/{execution_id}

Response:
{
  "execution_id": "exec_xxx",
  "action_id": "act_xxx",
  "status": "success",
  "start_time": "2026-06-09T10:00:00Z",
  "end_time": "2026-06-09T10:00:05Z",
  "duration": 5.2,
  "stdout": "...",
  "stderr": "",
  "exit_code": 0
}
```

### 9.4 执行历史

```
GET /api/v1/executions?page=1&limit=20

Response:
{
  "total": 100,
  "page": 1,
  "limit": 20,
  "items": [...]
}
```

## 10. 技术选型

### 10.1 后端
- **任务队列**：Celery（异步执行）
- **SSH 库**：Paramiko（远程执行）
- **进程管理**：asyncio.subprocess（本地执行）
- **日志**：structlog（结构化日志）

### 10.2 前端
- **WebSocket**：实时输出流
- **状态管理**：Pinia（执行状态）
- **动画**：CSS + GSAP（进度动画）

## 11. 实施路线图

### Phase 1：基础执行能力（MVP）
- [x] 架构设计
- [ ] CommandExecutor 实现
- [ ] 基础 API 接口
- [ ] 前端执行按钮 + 结果展示
- [ ] 本地命令白名单

### Phase 2：安全增强
- [ ] 权限控制
- [ ] 审计日志
- [ ] 回滚机制
- [ ] 风险确认弹窗

### Phase 3：高级功能
- [ ] ScriptExecutor
- [ ] SSHExecutor
- [ ] WebSocket 实时输出
- [ ] 执行历史查询

### Phase 4：智能化
- [ ] AI 生成动作
- [ ] 自动参数推断
- [ ] 智能回滚
- [ ] 异常检测

## 12. 安全最佳实践

1. **最小权限原则**：Agent 只能执行预定义的命令
2. **命令白名单**：严格限制可执行的命令集合
3. **参数验证**：所有参数必须经过验证和清理
4. **审计日志**：记录所有执行操作和结果
5. **超时保护**：所有操作设置合理的超时时间
6. **资源限制**：限制 CPU、内存、磁盘使用
7. **错误处理**：优雅处理所有异常情况
8. **回滚机制**：高风险操作支持一键回滚

---

**设计完成时间**：2026年6月9日  
**下一步**：实现 Phase 1 - 基础执行能力
