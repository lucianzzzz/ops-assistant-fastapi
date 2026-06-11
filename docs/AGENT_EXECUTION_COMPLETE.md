# 🤖 Ops Assistant Agent 执行能力 - 完整升级文档

## 🎉 升级完成

你的 ops-assistant 现在不仅能提供诊断建议，还能**自动执行运维操作**！

---

## ✨ 新增功能概览

### 核心能力
- ✅ **智能动作生成**：根据问题自动生成可执行的诊断和修复动作
- ✅ **安全执行**：命令白名单 + 风险分级 + 用户确认
- ✅ **实时反馈**：执行进度和结果实时展示
- ✅ **执行历史**：所有操作记录可追溯

### 支持的动作类型
1. **命令执行**（Command）：Shell 命令
2. **脚本执行**（Script）：预定义脚本 *(待实现)*
3. **API 调用**（API）：外部 API *(待实现)*
4. **SSH 远程执行**（SSH）：远程服务器命令 *(待实现)*

**当前版本**：Phase 1 - 命令执行（MVP）✅

---

## 🏗️ 架构设计

### 完整流程

```
用户查询
    ↓
分析问题（本地知识库 + AI）
    ↓
生成可执行动作列表
    ↓
前端展示动作卡片（带风险标识）
    ↓
用户选择动作 → 点击执行
    ↓
高风险动作？ → 二次确认
    ↓
后端执行器执行命令
    ↓
实时返回执行结果
    ↓
前端展示结果 + 记录历史
```

### 安全机制

#### 1. 命令白名单
只允许执行预定义的安全命令：

**低风险（自动执行）：**
- 查看类：`ps`, `top`, `df`, `free`, `uptime`
- 日志类：`tail`, `cat`, `grep`, `journalctl`
- 网络类：`ip`, `netstat`, `ping`, `curl`

**中/高风险（需要确认）：**
- 服务管理：`systemctl restart`, `systemctl stop`
- 容器管理：`docker restart`

#### 2. 风险分级

| 等级 | 颜色 | 操作类型 | 控制措施 |
|-----|------|---------|---------|
| 🟢 Low | 绿色 | 查看日志、检查状态 | 直接执行 |
| 🟡 Medium | 黄色 | 重启服务、清理缓存 | 用户确认 |
| 🔴 High | 红色 | 删除数据、修改配置 | 双重确认 + 回滚 |

#### 3. 执行控制
- **超时保护**：每个命令有超时限制（默认 30 秒）
- **参数验证**：严格校验命令参数
- **审计日志**：所有执行记录（待实现）

---

## 📂 项目结构

### 后端新增文件

```
ops-assistant-fastapi/
├── app/
│   ├── core/
│   │   ├── agent_models.py        ⭐ 动作和执行结果模型
│   │   ├── executor.py            ⭐ 执行器（命令执行）
│   │   ├── action_generator.py   ⭐ 动作生成器
│   │   ├── agent_service.py       ⭐ Agent 服务层
│   │   ├── service.py             ✏️  集成动作生成
│   │   ├── models.py              ✏️  添加 executable_actions
│   │   └── dependencies.py        ✏️  注册 AgentService
│   └── api/routes/
│       └── agent.py               ⭐ Agent API 路由
└── main.py                        ✏️  注册 Agent 路由
```

### 前端新增文件

```
ops-assistant-client/
├── src/
│   ├── components/
│   │   ├── ActionCard.vue         ⭐ 动作卡片组件
│   │   └── ResultCard.vue         ✏️  集成动作展示
│   └── services/
│       └── api.ts                 ✏️  添加执行 API
```

---

## 🎯 使用示例

### 场景一：系统诊断

**用户输入：**
```
系统负载很高
```

**系统生成动作：**
1. 🟢 查看系统负载 - `uptime` (2s)
2. 🟢 查看内存使用 - `free -h` (2s)
3. 🟢 查看进程列表 - `ps aux --sort=-%mem | head -20` (3s)

**用户操作：**
- 点击"执行"按钮
- 立即看到输出结果

---

### 场景二：服务重启

**用户输入：**
```
Nginx 服务异常
```

**系统生成动作：**
1. 🟢 查看服务状态 - `systemctl status nginx` (5s)
2. 🟢 查看错误日志 - `journalctl -u nginx -n 50 --no-pager` (10s)
3. 🟡 重启服务 - `systemctl restart nginx` (15s) ⚠️ 需要确认

**用户操作：**
- 先执行诊断动作（1、2）
- 确认问题后，点击"重启服务"
- 弹出确认框：

```
此操作风险等级：中风险

命令：systemctl restart nginx

确定要执行吗？
```

- 确认后执行，显示结果

---

## 🚀 API 接口

### 1. 生成可执行动作

```http
POST /api/v1/agent/actions/generate
Content-Type: application/json

{
  "question": "系统负载很高",
  "analysis_result": {
    "keywords": ["系统", "负载"],
    "normalized_metric": "cpu_usage"
  }
}
```

**响应：**
```json
{
  "actions": [
    {
      "id": "act_abc123",
      "type": "command",
      "title": "查看系统负载",
      "description": "检查系统当前的负载情况",
      "command": "uptime",
      "risk_level": "low",
      "requires_approval": false,
      "timeout": 5,
      "estimated_duration": 2
    }
  ]
}
```

### 2. 执行动作

```http
POST /api/v1/agent/actions/{action_id}/execute
Content-Type: application/json

{
  "action_id": "act_abc123",
  "parameters": {
    "action": { /* 完整的 action 对象 */ }
  },
  "user_confirmation": true
}
```

**响应：**
```json
{
  "execution_id": "exec_xyz789",
  "action_id": "act_abc123",
  "status": "success",
  "start_time": "2026-06-09T10:00:00Z",
  "end_time": "2026-06-09T10:00:02Z",
  "duration": 2.1,
  "stdout": " 10:00:02 up 5 days,  3:24,  2 users,  load average: 0.52, 0.58, 0.59\n",
  "stderr": "",
  "exit_code": 0
}
```

### 3. 查询执行历史

```http
GET /api/v1/agent/executions?limit=20
```

---

## 🎨 前端界面

### 动作卡片

```
┌─────────────────────────────────────────────┐
│ 🟢  查看系统负载                            │
│     检查系统当前的负载情况                  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ uptime                                  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ 🟢 低风险  ⏱️ ~2s              [执行]      │
└─────────────────────────────────────────────┘
```

### 执行中

```
┌─────────────────────────────────────────────┐
│ 🟢  查看系统负载                            │
│     检查系统当前的负载情况                  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ uptime                                  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ 🟢 低风险  ⏱️ ~2s       [⚙️ 执行中...]     │
└─────────────────────────────────────────────┘
```

### 执行结果

```
┌─────────────────────────────────────────────┐
│ 🟢  查看系统负载                            │
│     检查系统当前的负载情况                  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ uptime                                  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ 🟢 低风险  ⏱️ ~2s              [执行]      │
│                                             │
│ ┌───────────────────────────────────────┐   │
│ │ ✅ 执行成功              耗时: 2.1s   │   │
│ │                                       │   │
│ │ 输出：                                │   │
│ │ ┌───────────────────────────────────┐ │   │
│ │ │ 10:00:02 up 5 days, 3:24, 2 use...│ │   │
│ │ │ load average: 0.52, 0.58, 0.59   │ │   │
│ │ └───────────────────────────────────┘ │   │
│ └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🔧 配置与部署

### 后端配置

无需额外配置，开箱即用。

**自定义白名单**（可选）：

编辑 `app/core/executor.py`：

```python
class CommandExecutor(BaseExecutor):
    ALLOWED_COMMANDS = {
        # 添加你的命令
        "your-custom-command",
        ...
    }
```

### 前端配置

无需配置，自动连接后端 API。

---

## 📊 测试

### 1. 测试后端 API

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi

# 启动后端
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012

# 测试生成动作（另一个终端）
curl -X POST http://localhost:8012/api/v1/agent/actions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "系统负载高",
    "analysis_result": {"keywords": ["系统", "负载"], "normalized_metric": ""}
  }' | jq

# 测试执行（注意：需要真实的 action 对象）
```

### 2. 测试前端

```bash
cd /Users/lucian/workspace/ops-assistant-client
npm run dev

# 访问 http://localhost:5174
# 1. 提交一个查询
# 2. 查看"可执行动作"部分
# 3. 点击"执行"按钮
# 4. 查看执行结果
```

---

## 🎓 动作模板库

系统内置了丰富的动作模板，根据关键词自动匹配：

### 网络相关
- 查看网络接口状态
- 测试网络连通性
- 查看网络连接

### 服务相关
- 查看服务状态
- 查看服务日志
- 重启服务 ⚠️

### 系统资源
- 查看系统负载
- 查看内存使用
- 查看磁盘使用
- 查看进程列表

### 日志查看
- 查看系统日志
- 搜索错误日志

### Docker 相关
- 查看容器状态
- 查看容器日志
- 重启容器 ⚠️

---

## 🚦 后续路线图

### Phase 2：安全增强（计划中）
- [ ] 权限控制系统
- [ ] 完整的审计日志
- [ ] 回滚机制
- [ ] 更强大的风险评估

### Phase 3：高级功能（计划中）
- [ ] ScriptExecutor - 脚本执行
- [ ] SSHExecutor - 远程执行
- [ ] WebSocket 实时输出流
- [ ] 执行历史数据库存储

### Phase 4：智能化（计划中）
- [ ] AI 动态生成动作
- [ ] 自动参数推断
- [ ] 智能回滚建议
- [ ] 异常自动检测

---

## 💡 最佳实践

### 安全建议

1. **最小权限原则**
   - 只将必要的命令加入白名单
   - 生产环境禁用高风险命令

2. **审计追踪**
   - 记录所有执行操作
   - 定期审查执行日志

3. **环境隔离**
   - 开发/测试环境充分测试
   - 生产环境严格控制

### 使用建议

1. **先诊断，后修复**
   - 先执行查看类动作
   - 确认问题后再执行修复动作

2. **理解命令含义**
   - 执行前阅读命令
   - 不确定时先咨询

3. **关注执行结果**
   - 检查输出和错误信息
   - 必要时导出结果备查

---

## 📖 相关文档

1. **架构设计**：`/Users/lucian/workspace/AGENT_EXECUTION_ARCHITECTURE.md`
2. **升级总结**：`/Users/lucian/workspace/FINAL_SUMMARY.md`
3. **API 文档**：http://localhost:8012/docs

---

## 🎉 总结

### 已实现功能 ✅
- ✅ 命令执行器（白名单机制）
- ✅ 动作生成器（模板库匹配）
- ✅ 风险分级系统
- ✅ 前端动作卡片展示
- ✅ 实时执行反馈
- ✅ 执行历史查询

### 技术亮点
- 🔒 **安全第一**：白名单 + 风险分级
- 🎯 **智能生成**：自动匹配相关动作
- 🎨 **直观界面**：清晰的风险标识
- ⚡ **实时反馈**：执行状态实时更新

### 项目状态
**🚀 Phase 1 完成，Agent 执行能力已上线！**

---

**现在启动服务体验吧：**

```bash
# 后端
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012

# 前端（另一个终端）
cd /Users/lucian/workspace/ops-assistant-client
npm run dev

# 访问
http://localhost:5174
```

**测试步骤：**
1. 提交查询："系统负载很高"
2. 查看"可执行动作"部分
3. 点击"执行"按钮
4. 查看实时执行结果 ✨

---

**升级完成时间**：2026年6月9日  
**新增能力**：Agent 自动执行  
**当前状态**：✅ Phase 1 MVP 完成
