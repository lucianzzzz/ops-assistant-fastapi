# Ops Assistant FastAPI

智能运维问答服务 - FastAPI 独立版本

## 功能特性

- 基于知识库的智能问答
- 指标识别与关联
- 多省份支持
- 灵活的数据源配置
- 实时数据源状态监控
- **AI 增强查询**：当本地知识库匹配度不足时，自动使用 LangChain + OpenAI 提供智能补充

## 快速开始

### 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 运行服务

```bash
# 1. 复制环境变量配置文件
cp .env.example .env

# 2. 编辑 .env 文件，配置数据源和 AI（可选）
# OPS_ASSISTANT_DATA_DIR=/path/to/your/export
# OPENAI_API_KEY=sk-your-api-key  # 可选，启用 AI 增强查询

# 3. 启动服务
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012

# 或使用内置脚本
./start.sh
```

### AI 增强查询（可选）

当本地知识库匹配度低于 50% 时，系统会自动使用 AI 进行补充查询。

**配置步骤：**

1. 在 `.env` 文件中设置 `OPENAI_API_KEY`
2. （可选）如果使用自定义 API 端点，设置 `OPENAI_BASE_URL`
3. 重启服务

**工作原理：**

- 优先使用本地知识库匹配
- 当置信度 < 50% 时，自动触发 AI 查询
- AI 结果会追加到本地知识库结果中
- 响应中包含 `ai_fallback` 字段，标识是否使用了 AI
```

### 运行测试

```bash
pytest
```

## 数据导出与接入规范

### 从 ngs-oplatform 导出数据

本服务支持直接消费从 ngs-oplatform 导出的知识库、指标和标签数据。

### 导出目录结构

导出目录应包含以下三个 JSON 文件：

```
export_dir/
├── knowledge.json       # 知识库导出
├── metrics.json         # 指标导出
└── public_tags.json     # 公共标签导出
```

### 文件格式规范

#### 1. knowledge.json

知识库导出文件，包含问题描述、原因、解决方案等信息。

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

**必需字段：**
- `问题描述`：问题的文字描述
- `问题分类`：问题类型分类
- `问题原因`：问题产生的原因
- `解决办法描述`：解决步骤和方法

**可选字段：**
- `省份`：适用省份，为空则表示全国通用

#### 2. metrics.json

指标导出文件，包含指标名称、字段、单位等元数据。

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

**必需字段：**
- `名称`：指标显示名称
- `字段名`：数据库字段名
- `存储分区`：数据存储位置

**可选字段：**
- `单位`：指标单位
- `描述信息`：详细说明

#### 3. public_tags.json

公共标签导出文件，包含系统中使用的标签定义。

```json
[
  {
    "名称": "device_id",
    "字段名": "device_id",
    "描述": "设备标识"
  }
]
```

**必需字段：**
- `名称`：标签显示名称
- `字段名`：标签字段名

**可选字段：**
- `描述`：标签说明

### 配置数据源

有两种方式配置数据源：

#### 方式 1：环境变量（推荐）

```bash
# 设置数据目录
export OPS_ASSISTANT_DATA_DIR=/path/to/your/export

# 可选：自定义文件名
export OPS_ASSISTANT_KNOWLEDGE_FILE=my_knowledge.json
export OPS_ASSISTANT_METRICS_FILE=my_metrics.json
export OPS_ASSISTANT_PUBLIC_TAGS_FILE=my_tags.json

# 启动服务
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```

#### 方式 2：.env 文件

创建 `.env` 文件：

```env
OPS_ASSISTANT_DATA_DIR=/Users/yourname/exports
OPS_ASSISTANT_KNOWLEDGE_FILE=knowledge.json
OPS_ASSISTANT_METRICS_FILE=metrics.json
OPS_ASSISTANT_PUBLIC_TAGS_FILE=public_tags.json
```

### 验证数据加载

启动服务后，访问首页查看数据源状态：

```bash
open http://127.0.0.1:8012
```

或通过 API 检查：

```bash
curl http://127.0.0.1:8012/api/v1/data-source/status | jq
```

返回示例：

```json
{
  "data_dir": "/path/to/your/export",
  "knowledge": {
    "file_name": "knowledge.json",
    "file_path": "/path/to/your/export/knowledge.json",
    "exists": true,
    "loaded_count": 42
  },
  "metrics": {
    "file_name": "metrics.json",
    "file_path": "/path/to/your/export/metrics.json",
    "exists": true,
    "loaded_count": 15
  },
  "public_tags": {
    "file_name": "public_tags.json",
    "file_path": "/path/to/your/export/public_tags.json",
    "exists": true,
    "loaded_count": 8
  }
}
```

### 示例文件

项目内置了完整的示例文件，位于 `app/seed/` 目录：

- `knowledge_export_example.json` - 知识库导出示例
- `metrics_export_example.json` - 指标导出示例
- `public_tags_export_example.json` - 公共标签导出示例

## API 接口

### 问答接口

```bash
POST /api/v1/assistant/ask
Content-Type: application/json

{
  "question": "IF1接收时延异常怎么处理",
  "province": "浙江",
  "top_k": 3
}
```

### 健康检查

```bash
GET /api/v1/health
```

### 数据源状态

```bash
GET /api/v1/data-source/status
```

## 项目结构

```
ops-assistant-fastapi/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── assistant.py      # API 路由
│   ├── core/
│   │   ├── config.py             # 配置管理
│   │   ├── dependencies.py       # 依赖注入
│   │   ├── models.py             # 数据模型
│   │   ├── repository.py         # 数据访问层
│   │   └── service.py            # 业务逻辑层
│   ├── seed/                     # 内置种子数据与示例
│   │   ├── knowledge.json
│   │   ├── metrics.json
│   │   ├── public_tags.json
│   │   ├── knowledge_export_example.json
│   │   ├── metrics_export_example.json
│   │   └── public_tags_export_example.json
│   ├── web/
│   │   ├── static/               # 静态资源
│   │   └── templates/            # HTML 模板
│   │       └── index.html
│   └── main.py                   # 应用入口
├── tests/
│   ├── test_api.py               # API 测试
│   └── test_service.py           # 服务层测试
├── pyproject.toml                # 项目配置
└── README.md                     # 本文档
```

## 开发

### 代码风格

```bash
# 运行测试
pytest -v

# 查看覆盖率
pytest --cov=app
```

### 添加新功能

1. 在 `app/core/` 中添加核心逻辑
2. 在 `app/api/routes/` 中添加 API 端点
3. 在 `tests/` 中添加对应测试
4. 运行测试确保通过

## 常见问题

### Q: 为什么数据源状态显示文件不存在？

A: 检查以下几点：
1. 确认 `OPS_ASSISTANT_DATA_DIR` 路径正确
2. 确认目录中存在对应的 JSON 文件
3. 确认文件名匹配（默认为 `knowledge.json`, `metrics.json`, `public_tags.json`）
4. 确认文件格式正确（有效的 JSON 数组）

### Q: 如何切换回种子数据？

A: 删除 `OPS_ASSISTANT_DATA_DIR` 环境变量，或设置为默认的 seed 目录：

```bash
unset OPS_ASSISTANT_DATA_DIR
# 或
export OPS_ASSISTANT_DATA_DIR=/path/to/ops-assistant-fastapi/app/seed
```

### Q: 支持热重载数据吗？

A: 当前版本在服务启动时加载数据。如需重新加载，请重启服务。

## License

Internal use only.
