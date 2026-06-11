# ✅ DeepSeek AI 增强已配置完成

## 配置信息

```
✅ API Key:   sk-42ed3ce57b9249d3b539c96ae8c07960
✅ Base URL:  https://api.deepseek.com/v1
✅ Model:     deepseek-chat
✅ 配置文件:  /Users/lucian/workspace/ops-assistant-fastapi/.env
```

---

## 🚀 立即测试

### 步骤 1: 重启后端（必须）

**⚠️ 重要：配置更改后必须重启后端才能生效！**

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate

# 如果后端正在运行，先按 Ctrl+C 停止
# 然后重新启动：
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```

启动成功后你会看到：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8012
```

### 步骤 2: 验证 AI 配置

在**另一个终端**运行：

```bash
/Users/lucian/workspace/test-deepseek-ai.sh
```

预期输出：
```
✅ DeepSeek API Key 已配置
✅ DeepSeek Base URL 已配置
✅ AI 助手初始化成功
   AI Enabled: True
   Model: deepseek-chat
   Base URL: https://api.deepseek.com/v1
```

### 步骤 3: 前端测试

1. **访问前端**：http://localhost:5174

2. **提交测试问题**（这些会触发 AI）：

   ```
   Kubernetes Pod 一直重启怎么排查？
   ```

3. **观察 AI 标识**：

   **加载阶段（5秒后）：**
   ```
   正在查询...
   ↓
   知识库匹配度较低，正在使用 AI 增强查询...
   ```

   **结果阶段：**
   ```
   ┌─────────────────────────────────────┐
   │ 置信度: 70%  [🟣 AI 增强]          │
   │                                     │
   │ DeepSeek 提供的分析和建议...        │
   └─────────────────────────────────────┘
   ```

---

## 🧪 推荐测试问题

### ✅ 会触发 AI 的问题（本地知识库可能没有）

1. **Kubernetes 相关：**
   - `Kubernetes Pod 一直重启怎么排查？`
   - `K8s 集群节点 NotReady 怎么办？`
   - `StatefulSet 无法扩容的原因？`

2. **数据库相关：**
   - `数据库连接池耗尽如何处理？`
   - `MySQL 主从延迟过大怎么解决？`
   - `PostgreSQL 慢查询优化方法？`

3. **缓存相关：**
   - `Redis 内存占用过高的原因？`
   - `Redis 集群脑裂如何处理？`
   - `Memcached 缓存雪崩怎么办？`

4. **中间件相关：**
   - `Elasticsearch 查询变慢了`
   - `Kafka 消息堆积如何处理？`
   - `RabbitMQ 队列阻塞的原因？`

5. **容器相关：**
   - `Docker 容器网络不通怎么办？`
   - `Docker 镜像构建失败的原因？`
   - `容器内存溢出如何排查？`

### ❌ 不会触发 AI 的问题（本地知识库有）

1. `IF1接收时延异常怎么处理` ← 置信度高，直接返回本地答案
2. `系统负载很高` ← 知识库有
3. `Nginx 服务异常` ← 知识库有

---

## 📊 AI 增强工作流程

```
用户提问："Kubernetes Pod 一直重启怎么排查？"
    ↓
本地知识库搜索
    ↓
匹配度计算：35%（低）
    ↓
触发条件检查：
  ✓ 置信度 < 50%
  ✓ AI 已配置（DeepSeek）
    ↓
显示加载提示："正在使用 AI 增强查询..."
    ↓
调用 DeepSeek API
    ↓
DeepSeek 生成答案（2-3秒）
    ↓
解析 AI 响应
    ↓
合并本地 + AI 结果
    ↓
置信度提升到 70%
    ↓
返回结果 + 显示 🟣 AI 增强徽章
```

---

## 🔍 如何确认 AI 真的在工作？

### 方法 1：查看前端标识

**必看标志：**
1. 加载提示："**正在使用 AI 增强查询...**"（5秒后出现）
2. 结果徽章：**🟣 AI 增强**（紫色）
3. 置信度：从低（< 50%）提升到中等（~70%）

### 方法 2：API 测试

```bash
curl -X POST http://localhost:8012/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Kubernetes Pod 一直重启怎么排查",
    "top_k": 3
  }' | jq '{
    question,
    confidence,
    ai_fallback: .ai_fallback | {
      used: .used,
      confidence_too_low: .confidence_too_low,
      response_length: (.raw_response | length)
    }
  }'
```

**预期输出：**
```json
{
  "question": "Kubernetes Pod 一直重启怎么排查",
  "confidence": 0.7,
  "ai_fallback": {
    "used": true,              // ✅ AI 被使用了
    "confidence_too_low": true,
    "response_length": 856     // AI 响应长度
  }
}
```

### 方法 3：后端日志

查看后端终端输出，应该能看到：
```
INFO:     POST /api/v1/assistant/ask
INFO:     AI Fallback triggered (confidence: 0.35)
INFO:     Calling DeepSeek API...
INFO:     AI response received (856 chars)
```

---

## 💰 DeepSeek 计费说明

### 价格（2026年6月）

| 项目 | 价格 |
|-----|------|
| 输入 | ¥1/百万 tokens |
| 输出 | ¥2/百万 tokens |

### 单次查询成本估算

假设每次 AI 查询：
- 输入：~500 tokens（问题 + 本地结果）
- 输出：~1000 tokens（AI 答案）

**成本 = (500 × ¥1 + 1000 × ¥2) / 1,000,000 ≈ ¥0.0025**

**约 0.25 分 / 次**

### 每日成本估算

| 每日 AI 查询次数 | 每日成本 | 每月成本 |
|----------------|---------|---------|
| 10 次 | ¥0.025 | ¥0.75 |
| 50 次 | ¥0.125 | ¥3.75 |
| 100 次 | ¥0.25 | ¥7.5 |
| 1000 次 | ¥2.5 | ¥75 |

**非常便宜！** 🎉

---

## ⚙️ 高级配置

### 切换模型

编辑 `.env`：

```bash
# 使用推理模型（更便宜，适合简单问题）
OPENAI_MODEL=deepseek-chat

# 使用 Coder 模型（代码相关更好）
OPENAI_MODEL=deepseek-coder
```

### 调整触发阈值

如果想让 AI 更容易触发，编辑：
`/Users/lucian/workspace/ops-assistant-fastapi/app/core/service.py`

找到：
```python
if confidence < 0.5 and self.ai_assistant.enabled:
```

改为：
```python
if confidence < 0.7 and self.ai_assistant.enabled:  # 提高阈值
```

---

## 🐛 故障排查

### 问题 1：AI 没有触发

**检查清单：**
1. ✅ 后端已重启？
2. ✅ `.env` 配置正确？
3. ✅ 提问的是边缘问题？
4. ✅ 置信度 < 50%？

**解决方法：**
```bash
# 1. 验证配置
/Users/lucian/workspace/test-deepseek-ai.sh

# 2. 重启后端
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012

# 3. 提问边缘问题（非知识库问题）
```

### 问题 2：API 错误

**检查 API Key 是否有效：**
```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-42ed3ce57b9249d3b539c96ae8c07960" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 问题 3：响应太慢

DeepSeek 通常很快（2-3秒），如果太慢：
1. 检查网络连接
2. 查看后端日志
3. 尝试切换模型

---

## 📖 相关文档

1. **完整配置指南**：`/Users/lucian/workspace/AI_ENHANCEMENT_GUIDE.md`
2. **测试脚本**：`/Users/lucian/workspace/test-deepseek-ai.sh`
3. **项目总览**：`/Users/lucian/workspace/PROJECT_OVERVIEW.md`
4. **DeepSeek 官方文档**：https://platform.deepseek.com/api-docs/

---

## 🎉 总结

### ✅ 已完成

- ✅ DeepSeek API Key 配置
- ✅ Base URL 和 Model 配置
- ✅ 测试脚本创建
- ✅ 完整文档准备

### 🚀 下一步

1. **重启后端**（必须）
   ```bash
   cd /Users/lucian/workspace/ops-assistant-fastapi
   source .venv/bin/activate
   uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
   ```

2. **测试配置**
   ```bash
   /Users/lucian/workspace/test-deepseek-ai.sh
   ```

3. **访问前端测试**
   - 前端：http://localhost:5174
   - 提问：`Kubernetes Pod 一直重启怎么排查？`
   - 观察：🟣 AI 增强徽章

---

**现在重启后端，开始体验 DeepSeek AI 增强吧！** 🚀

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```
