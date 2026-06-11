# Ops Assistant FastAPI 接口文档与使用说明

## 1. 项目说明

`ops-assistant-fastapi` 是 Ops Assistant 智能运维助手的后端服务，提供：

- 智能运维问答
- 知识库匹配
- 指标识别与关联
- 数据源状态检查
- 低置信度场景下的 AI 增强查询
- Agent 可执行动作生成与执行

默认服务地址：

```text
http://127.0.0.1:8012
```

FastAPI 自动文档：

```text
http://127.0.0.1:8012/docs
http://127.0.0.1:8012/redoc
```

## 2. 环境准备

### 2.1 安装依赖

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

开发测试依赖：

```bash
pip install -e '.[dev]'
```

### 2.2 启动服务

方式一：直接启动。

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```

方式二：使用内置脚本。

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
./start.sh
```

`start.sh` 会自动创建 `.venv`、安装依赖，并启动服务。默认端口是 `8012`，可通过环境变量覆盖：

```bash
OPS_ASSISTANT_PORT=8013 ./start.sh
```

## 3. 配置说明

### 3.1 数据源配置

默认使用项目内置种子数据：

```text
app/seed/
├── knowledge.json
├── metrics.json
└── public_tags.json
```

如果要使用外部导出数据，配置环境变量：

```bash
export OPS_ASSISTANT_DATA_DIR=/path/to/export
export OPS_ASSISTANT_KNOWLEDGE_FILE=knowledge.json
export OPS_ASSISTANT_METRICS_FILE=metrics.json
export OPS_ASSISTANT_PUBLIC_TAGS_FILE=public_tags.json
```

也可以复制 `.env.example` 为 `.env` 后编辑：

```bash
cp .env.example .env
```

### 3.2 AI 增强查询配置

当本地知识库匹配置信度低于 `0.5` 且配置了 AI Key 时，系统会自动触发 AI 增强查询。

环境变量：

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

如果使用 DeepSeek 等 OpenAI 兼容接口，可配置：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## 4. 通用响应约定

- 请求和响应均使用 JSON。
- 主要 API 前缀为 `/api/v1`。
- Agent 执行能力 API 前缀为 `/api/v1/agent`。
- 时间字段使用 ISO datetime 字符串。
- 执行动作只支持白名单命令，且中高风险动作需要 `user_confirmation=true`。

## 5. 接口列表

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/` | 内置首页，展示数据源状态 |
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/data-source/status` | 查看数据源加载状态 |
| `POST` | `/api/v1/assistant/ask` | 智能问答 |
| `POST` | `/api/v1/agent/actions/generate` | 根据分析结果生成可执行动作 |
| `POST` | `/api/v1/agent/actions/{action_id}/execute` | 执行动作 |
| `GET` | `/api/v1/agent/executions/{execution_id}` | 查询单次执行结果 |
| `GET` | `/api/v1/agent/executions` | 查询执行历史 |

## 6. 基础接口

### 6.1 健康检查

```http
GET /api/v1/health
```

示例：

```bash
curl http://127.0.0.1:8012/api/v1/health
```

响应：

```json
{
  "status": "ok"
}
```

### 6.2 数据源状态

```http
GET /api/v1/data-source/status
```

示例：

```bash
curl http://127.0.0.1:8012/api/v1/data-source/status | jq
```

响应字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `data_dir` | string | 当前数据源目录 |
| `knowledge` | object | 知识库文件状态 |
| `metrics` | object | 指标库文件状态 |
| `public_tags` | object | 公共标签文件状态 |

文件状态对象字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `file_name` | string | 文件名 |
| `file_path` | string | 文件完整路径 |
| `exists` | boolean | 文件是否存在 |
| `loaded_count` | integer | 已加载记录数 |

响应示例：

```json
{
  "data_dir": "/Users/lucian/workspace/ops-assistant-fastapi/app/seed",
  "knowledge": {
    "file_name": "knowledge.json",
    "file_path": "/Users/lucian/workspace/ops-assistant-fastapi/app/seed/knowledge.json",
    "exists": true,
    "loaded_count": 20
  },
  "metrics": {
    "file_name": "metrics.json",
    "file_path": "/Users/lucian/workspace/ops-assistant-fastapi/app/seed/metrics.json",
    "exists": true,
    "loaded_count": 18
  },
  "public_tags": {
    "file_name": "public_tags.json",
    "file_path": "/Users/lucian/workspace/ops-assistant-fastapi/app/seed/public_tags.json",
    "exists": true,
    "loaded_count": 10
  }
}
```

## 7. 智能问答接口

### 7.1 提交问题

```http
POST /api/v1/assistant/ask
Content-Type: application/json
```

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `question` | string | 是 | - | 运维人员输入的问题，最少 1 个字符 |
| `province` | string | 否 | `""` | 省份筛选，用于缩小知识库范围 |
| `top_k` | integer | 否 | `3` | 返回匹配条数，范围 `1-10` |

请求示例：

```bash
curl -X POST http://127.0.0.1:8012/api/v1/assistant/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "IF1接收时延异常怎么排查",
    "province": "浙江",
    "top_k": 3
  }' | jq
```

响应字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `question` | string | 原始问题 |
| `normalized_question` | string | 归一化后的问题 |
| `normalized_metric` | string | 识别出的主要指标名称 |
| `keywords` | string[] | 提取出的关键词 |
| `matched_knowledge` | object[] | 匹配到的知识库条目 |
| `possible_reason` | string[] | 可能原因 |
| `suggested_steps` | string[] | 建议排查步骤 |
| `related_objects` | object | 关联对象，包括指标和公共标签 |
| `confidence` | number | 匹配置信度，范围 `0-1` |
| `next_actions` | string[] | 后续建议动作 |
| `fallback_questions` | object[] | 无命中时的候选问题 |
| `ai_fallback` | object/null | AI 增强查询状态 |
| `executable_actions` | object[] | 可执行动作列表 |

响应示例：

```json
{
  "question": "IF1接收时延异常怎么排查",
  "normalized_question": "if1接收时延异常怎么排查",
  "normalized_metric": "IF1接收时延",
  "keywords": ["if1接收时延异常怎么排查"],
  "matched_knowledge": [
    {
      "id": 1,
      "question": "IF1接收时延异常怎么处理",
      "reason": "通常由采集链路拥塞、源端发送抖动或处理队列堆积导致。",
      "method": "先检查采集链路状态；再核对对应服务进程；最后查看最近告警与巡检结果。",
      "sort": "指标异常",
      "province": "浙江",
      "score": 0.85
    }
  ],
  "possible_reason": [
    "通常由采集链路拥塞、源端发送抖动或处理队列堆积导致。"
  ],
  "suggested_steps": [
    "先检查采集链路状态",
    "再核对对应服务进程",
    "最后查看最近告警与巡检结果"
  ],
  "related_objects": {
    "metrics": [
      {
        "metric": "if1_delay",
        "name": "IF1接收时延",
        "measurement": "dpi",
        "field_name": "if1_delay",
        "desc": "用于衡量 IF1 链路接收时延情况",
        "unit": "ms",
        "score": 0.7
      }
    ],
    "public_tags": []
  },
  "confidence": 0.773,
  "next_actions": [
    "查看指标 IF1接收时延 的最近趋势与关联告警。"
  ],
  "fallback_questions": [],
  "ai_fallback": null,
  "executable_actions": [
    {
      "id": "act_xxxxxxxx",
      "type": "command",
      "title": "查看系统负载",
      "description": "检查系统当前的负载情况",
      "command": "uptime",
      "risk_level": "low",
      "requires_approval": false,
      "timeout": 5,
      "estimated_duration": 2,
      "rollback_command": null,
      "metadata": {}
    }
  ]
}
```

### 7.2 AI 增强查询响应

当本地匹配置信度低于 `0.5` 且 AI 已配置时，响应中的 `ai_fallback.used` 会是 `true`。

示例请求：

```bash
curl -X POST http://127.0.0.1:8012/api/v1/assistant/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Kubernetes Pod 一直重启怎么排查",
    "top_k": 3
  }' | jq '{question, confidence, ai_fallback}'
```

响应片段：

```json
{
  "question": "Kubernetes Pod 一直重启怎么排查",
  "confidence": 0.7,
  "ai_fallback": {
    "enabled": true,
    "used": true,
    "confidence_too_low": false,
    "raw_response": "AI 返回的详细分析...",
    "error": null,
    "message": null
  }
}
```

## 8. Agent 动作接口

Agent 动作能力用于把问答结果转换为可执行的诊断命令，并允许用户确认后执行。

### 8.1 动作对象结构

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 动作唯一标识 |
| `type` | string | 动作类型，当前主要支持 `command` |
| `title` | string | 动作标题 |
| `description` | string | 动作描述 |
| `command` | string | 要执行的命令 |
| `risk_level` | string | 风险等级：`low`、`medium`、`high` |
| `requires_approval` | boolean | 是否需要用户确认 |
| `timeout` | integer | 超时时间，单位秒 |
| `estimated_duration` | integer | 预估耗时，单位秒 |
| `rollback_command` | string/null | 回滚命令 |
| `metadata` | object | 额外元数据 |

### 8.2 生成动作

```http
POST /api/v1/agent/actions/generate
Content-Type: application/json
```

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `question` | string | 是 | 用户问题 |
| `analysis_result` | object | 是 | 分析结果，通常包含 `keywords` 和 `normalized_metric` |

请求示例：

```bash
curl -X POST http://127.0.0.1:8012/api/v1/agent/actions/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "系统负载很高",
    "analysis_result": {
      "keywords": ["系统", "负载"],
      "normalized_metric": "cpu_usage"
    }
  }' | jq
```

响应：

```json
{
  "actions": [
    {
      "id": "act_xxxxxxxx",
      "type": "command",
      "title": "查看系统负载",
      "description": "查看系统运行时间和负载",
      "command": "uptime",
      "risk_level": "low",
      "requires_approval": false,
      "timeout": 5,
      "estimated_duration": 2,
      "rollback_command": null,
      "metadata": {}
    }
  ]
}
```

### 8.3 执行动作

```http
POST /api/v1/agent/actions/{action_id}/execute
Content-Type: application/json
```

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `action_id` | string | 是 | 动作 ID |
| `parameters` | object | 否 | 执行参数。必须包含完整 `action` 对象 |
| `user_confirmation` | boolean | 否 | 用户是否确认执行，默认 `false` |

低风险动作示例：

```bash
curl -X POST http://127.0.0.1:8012/api/v1/agent/actions/act_demo/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action_id": "act_demo",
    "parameters": {
      "action": {
        "id": "act_demo",
        "type": "command",
        "title": "查看系统负载",
        "description": "检查系统当前的负载情况",
        "command": "uptime",
        "risk_level": "low",
        "requires_approval": false,
        "timeout": 5,
        "estimated_duration": 2,
        "rollback_command": null,
        "metadata": {}
      }
    },
    "user_confirmation": false
  }' | jq
```

中高风险动作需要确认：

```json
{
  "user_confirmation": true
}
```

如果动作 `requires_approval=true` 但没有确认，接口返回：

```http
403 Forbidden
```

响应字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `execution_id` | string | 执行 ID |
| `action_id` | string | 动作 ID |
| `status` | string | `pending`、`running`、`success`、`failed`、`timeout`、`cancelled` |
| `start_time` | string | 开始时间 |
| `end_time` | string/null | 结束时间 |
| `duration` | number/null | 执行耗时，单位秒 |
| `stdout` | string | 标准输出 |
| `stderr` | string | 标准错误 |
| `exit_code` | integer/null | 退出码 |
| `error` | string/null | 错误信息 |

响应示例：

```json
{
  "execution_id": "9a8b7c6d-0000-0000-0000-123456789abc",
  "action_id": "act_demo",
  "status": "success",
  "start_time": "2026-06-09T16:30:00.000000",
  "end_time": "2026-06-09T16:30:00.050000",
  "duration": 0.05,
  "stdout": "16:30  up 1 day,  load averages: 1.23 1.45 1.67\n",
  "stderr": "",
  "exit_code": 0,
  "error": null
}
```

### 8.4 查询执行结果

```http
GET /api/v1/agent/executions/{execution_id}
```

示例：

```bash
curl http://127.0.0.1:8012/api/v1/agent/executions/9a8b7c6d-0000-0000-0000-123456789abc | jq
```

如果执行 ID 不存在，返回：

```http
404 Not Found
```

### 8.5 查询执行历史

```http
GET /api/v1/agent/executions?limit=20
```

参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `limit` | integer | `20` | 返回最近执行记录数量 |

示例：

```bash
curl 'http://127.0.0.1:8012/api/v1/agent/executions?limit=10' | jq
```

响应：

```json
[
  {
    "execution_id": "...",
    "action_id": "act_demo",
    "status": "success",
    "start_time": "2026-06-09T16:30:00.000000",
    "end_time": "2026-06-09T16:30:00.050000",
    "duration": 0.05,
    "stdout": "...",
    "stderr": "",
    "exit_code": 0,
    "error": null
  }
]
```

## 9. 命令执行安全规则

当前命令执行器只允许执行白名单命令。常见允许命令包括：

- 查看类：`ps`、`top`、`df`、`du`、`free`、`uptime`、`whoami`
- 文件查看类：`ls`、`cat`、`head`、`tail`、`grep`、`find`、`wc`
- 网络查看类：`ip`、`ifconfig`、`netstat`、`ss`、`ping`、`curl`、`wget`
- 服务状态类：`systemctl status`、`service status`、`journalctl`
- 管理类：`systemctl restart/start/stop`、`service restart/start/stop`
- 容器类：`docker ps`、`docker logs`、`docker restart`
- Kubernetes 查看类：`kubectl get`、`kubectl describe`、`kubectl logs`

未在白名单中的命令会执行失败，返回：

```json
{
  "status": "failed",
  "error": "Command 'xxx' is not in the allowed list"
}
```

## 10. 数据文件格式

### 10.1 knowledge.json

```json
[
  {
    "省份": "浙江",
    "问题描述": "IF1接收时延异常怎么处理",
    "问题分类": "指标异常",
    "问题原因": "链路拥塞",
    "解决办法描述": "检查链路状态；检查进程运行情况"
  }
]
```

必需字段：

- `问题描述`
- `问题分类`
- `问题原因`
- `解决办法描述`

可选字段：

- `省份`

### 10.2 metrics.json

```json
[
  {
    "名称": "IF1接收时延",
    "存储分区": "dpi",
    "字段名": "if1_delay",
    "单位": "ms",
    "描述信息": "用于衡量 IF1 链路接收时延情况"
  }
]
```

必需字段：

- `名称`
- `字段名`
- `存储分区`

可选字段：

- `单位`
- `描述信息`

### 10.3 public_tags.json

```json
[
  {
    "名称": "device_id",
    "字段名": "device_id",
    "描述": "设备标识"
  }
]
```

必需字段：

- `名称`
- `字段名`

可选字段：

- `描述`

## 11. 推荐使用流程

### 11.1 本地知识库问答

1. 启动后端服务。
2. 调用 `/api/v1/data-source/status` 确认数据源已加载。
3. 调用 `/api/v1/assistant/ask` 提交问题。
4. 根据 `confidence`、`possible_reason`、`suggested_steps` 展示结果。
5. 如果返回 `executable_actions`，前端可展示为可执行按钮。

### 11.2 AI 增强问答

1. 配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
2. 重启服务。
3. 提交知识库低匹配问题。
4. 查看响应中的 `ai_fallback.used` 是否为 `true`。
5. 将 `ai_fallback.raw_response` 展示为 AI 详细分析。

### 11.3 Agent 执行动作

1. 先调用 `/api/v1/assistant/ask` 获取 `executable_actions`。
2. 用户选择一个动作。
3. 如果 `requires_approval=true`，前端必须弹出确认。
4. 调用 `/api/v1/agent/actions/{action_id}/execute`，并传入完整 action 对象。
5. 展示 `stdout`、`stderr`、`status`、`duration`。
6. 可通过 `/api/v1/agent/executions` 查看历史。

## 12. 常见问题

### 12.1 数据源状态显示文件不存在

检查：

1. `OPS_ASSISTANT_DATA_DIR` 是否正确。
2. 目录中是否存在 `knowledge.json`、`metrics.json`、`public_tags.json`。
3. 文件名环境变量是否和真实文件名一致。
4. JSON 是否是合法数组格式。

### 12.2 AI 没有触发

可能原因：

1. 未配置 `OPENAI_API_KEY`。
2. 本地知识库匹配置信度不低于 `0.5`。
3. `OPENAI_BASE_URL` 或 `OPENAI_MODEL` 配置错误。
4. 服务未重启，配置未生效。

验证命令：

```bash
curl -X POST http://127.0.0.1:8012/api/v1/assistant/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Kubernetes Pod 一直重启怎么排查", "top_k":3}' \
  | jq '.confidence, .ai_fallback'
```

### 12.3 执行动作返回 403

原因：动作需要用户确认，但请求中 `user_confirmation=false`。

解决：用户确认后重新请求，并设置：

```json
{
  "user_confirmation": true
}
```

### 12.4 执行动作返回命令不在白名单

原因：命令执行器只允许白名单命令。

解决：修改后端 `app/core/executor.py` 中的 `ALLOWED_COMMANDS`，添加允许的命令前缀，并评估风险等级。

## 13. 测试

运行全部测试：

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
pytest
```

运行详细输出：

```bash
pytest -v
```

## 14. 相关文件

| 文件 | 说明 |
|---|---|
| `app/main.py` | FastAPI 应用入口、CORS、路由注册 |
| `app/api/routes/assistant.py` | 健康检查、数据源状态、问答接口 |
| `app/api/routes/agent.py` | Agent 动作生成、执行、历史查询接口 |
| `app/core/models.py` | 问答和数据源 Pydantic 模型 |
| `app/core/agent_models.py` | Agent 动作和执行结果模型 |
| `app/core/service.py` | 问答匹配、AI 增强合并、动作生成 |
| `app/core/action_generator.py` | 可执行动作模板生成 |
| `app/core/executor.py` | 命令执行器和命令白名单 |
| `app/core/config.py` | 数据源配置 |
| `app/seed/` | 内置示例数据 |
| `.env.example` | 环境变量示例 |
| `start.sh` | 后端启动脚本 |
