# 🤖 AI 增强查询 - 配置和测试指南

## 为什么没有看到 AI 增强？

AI 增强功能需要满足**两个条件**才会触发：

### 条件 1：配置 API Key ✅ 
已创建 `.env` 文件，但需要填写 API Key

### 条件 2：低置信度查询 ⚠️
本地知识库匹配度 < 50% 时才会自动启用 AI

**问题所在：** 你测试的问题可能都被本地知识库很好地匹配了（置信度 > 50%），所以 AI 没有触发！

---

## 🔧 配置 AI 增强

### 步骤 1：获取 API Key

**选项 A：使用 OpenAI 官方**
1. 访问：https://platform.openai.com/api-keys
2. 注册/登录账号
3. 创建 API Key

**选项 B：使用兼容服务**
- DeepSeek：https://platform.deepseek.com/
- 智谱 GLM：https://open.bigmodel.cn/
- 阿里百炼：https://bailian.console.aliyun.com/
- 国内其他 OpenAI 兼容服务

### 步骤 2：配置 .env

编辑文件：`/Users/lucian/workspace/ops-assistant-fastapi/.env`

**使用 OpenAI：**
```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
```

**使用 DeepSeek（推荐国内用户）：**
```bash
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

**使用智谱 GLM：**
```bash
OPENAI_API_KEY=your-glm-key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4
```

### 步骤 3：重启后端

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate

# 重启服务
# 如果之前在运行，先 Ctrl+C 停止，再重新启动
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```

---

## 🧪 测试 AI 增强

### 方法 1：提问知识库没有的问题

这些问题会触发 AI（置信度会很低）：

```
❌ 好问题（本地知识库有） → 不会触发 AI
✅ 新问题（本地知识库没有） → 会触发 AI
```

**测试问题（这些应该会触发 AI）：**

1. **边缘场景：**
   ```
   服务器突然响应变慢了，怎么办？
   ```

2. **新技术栈：**
   ```
   Kubernetes Pod 一直重启怎么排查？
   ```

3. **通用问题：**
   ```
   数据库连接池耗尽了如何处理？
   ```

4. **模糊描述：**
   ```
   系统不稳定，时好时坏
   ```

### 方法 2：查看触发标识

当 AI 增强触发时，你会看到：

#### 加载阶段
```
正在查询...
↓ (5 秒后)
知识库匹配度较低，正在使用 AI 增强查询...
```

#### 结果阶段
```
┌─────────────────────────────┐
│ 置信度: 70%  [🟣 AI 增强]  │  ← 紫色徽章
└─────────────────────────────┘
```

### 方法 3：API 测试

直接测试 AI 功能：

```bash
# 测试一个本地知识库可能没有的问题
curl -X POST http://localhost:8012/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Kubernetes Pod 一直重启怎么排查",
    "top_k": 3
  }' | jq '{
    confidence,
    ai_fallback: .ai_fallback | {used, confidence_too_low, error}
  }'
```

**预期输出：**
```json
{
  "confidence": 0.35,  // 低置信度
  "ai_fallback": {
    "used": true,      // AI 被使用了
    "confidence_too_low": true,
    "error": null
  }
}
```

---

## 📊 AI 增强工作流程

```
用户提问
    ↓
本地知识库搜索
    ↓
计算置信度
    ↓
置信度 ≥ 50%?
    ├─ 是 → 直接返回本地结果（不使用 AI）
    │
    └─ 否 → 检查 AI 配置
        ├─ 未配置 → 返回低置信度本地结果
        │
        └─ 已配置 → 启用 AI 查询
            ↓
        调用 LangChain + OpenAI
            ↓
        解析 AI 响应
            ↓
        合并本地 + AI 结果
            ↓
        置信度提升到 ~70%
            ↓
        返回完整结果（带 AI 徽章）
```

---

## 🎯 为什么本地匹配度通常很高？

你的知识库可能覆盖得很好！查看一下：

```bash
# 查看知识库内容
cat /Users/lucian/workspace/ops-assistant-fastapi/app/seed/export_knowledge.json | jq '.[] | .question' | head -20
```

**如果知识库包含的问题类型：**
- IF1 相关问题 ✅
- 网络相关问题 ✅
- 服务相关问题 ✅
- 系统资源问题 ✅

那么这些类型的查询都会有高置信度，**不会触发 AI**。

---

## 💡 强制测试 AI（调试用）

如果你想强制测试 AI，可以临时修改触发阈值：

编辑：`/Users/lucian/workspace/ops-assistant-fastapi/app/core/service.py`

找到这一行（大约第 90 行）：
```python
if confidence < 0.5 and self.ai_assistant.enabled:
```

改为：
```python
if confidence < 0.99 and self.ai_assistant.enabled:  # 强制触发 AI
```

重启后端，现在**所有查询都会使用 AI 增强**。

**记得测试完改回去！**

---

## 🔍 检查 AI 是否正确配置

### 1. 检查环境变量

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('API Key:', 'Configured' if os.getenv('OPENAI_API_KEY') else 'Not configured')
print('Base URL:', os.getenv('OPENAI_BASE_URL', 'default'))
print('Model:', os.getenv('OPENAI_MODEL', 'default'))
"
```

### 2. 检查 AI 助手状态

```bash
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
python -c "
from app.core.ai_assistant import AIAssistant
ai = AIAssistant()
print('AI Enabled:', ai.enabled)
"
```

**预期输出：**
- 配置了 API Key：`AI Enabled: True`
- 未配置：`AI Enabled: False`

---

## 📝 快速配置脚本

创建一个快速配置脚本：

```bash
#!/bin/bash
# 快速配置 AI 增强

cd /Users/lucian/workspace/ops-assistant-fastapi

echo "🤖 配置 AI 增强查询"
echo ""
echo "请选择 API 提供商："
echo "1) OpenAI 官方"
echo "2) DeepSeek（推荐国内）"
echo "3) 智谱 GLM"
echo "4) 手动配置"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
  1)
    read -p "输入 OpenAI API Key: " api_key
    echo "OPENAI_API_KEY=$api_key" > .env
    echo "OPENAI_MODEL=gpt-4" >> .env
    echo "✅ 已配置 OpenAI"
    ;;
  2)
    read -p "输入 DeepSeek API Key: " api_key
    echo "OPENAI_API_KEY=$api_key" > .env
    echo "OPENAI_BASE_URL=https://api.deepseek.com/v1" >> .env
    echo "OPENAI_MODEL=deepseek-chat" >> .env
    echo "✅ 已配置 DeepSeek"
    ;;
  3)
    read -p "输入智谱 GLM API Key: " api_key
    echo "OPENAI_API_KEY=$api_key" > .env
    echo "OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4" >> .env
    echo "OPENAI_MODEL=glm-4" >> .env
    echo "✅ 已配置智谱 GLM"
    ;;
  4)
    echo "请手动编辑 .env 文件"
    ;;
esac

echo ""
echo "📝 下一步："
echo "1. 重启后端服务"
echo "2. 提问知识库没有的问题"
echo "3. 观察紫色 'AI 增强' 徽章"
```

保存为 `/Users/lucian/workspace/setup-ai.sh` 并运行：
```bash
chmod +x /Users/lucian/workspace/setup-ai.sh
/Users/lucian/workspace/setup-ai.sh
```

---

## 🎯 总结

### AI 增强没有触发的原因：

1. ❌ **未配置 API Key**（主要原因）
2. ✅ **本地知识库匹配度太高**（说明知识库很完善）

### 解决方案：

1. **配置 API Key**
   ```bash
   # 编辑 .env 文件
   vim /Users/lucian/workspace/ops-assistant-fastapi/.env
   # 添加 OPENAI_API_KEY=your-key
   ```

2. **重启后端**
   ```bash
   cd /Users/lucian/workspace/ops-assistant-fastapi
   source .venv/bin/activate
   uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
   ```

3. **测试边缘问题**
   ```
   "Kubernetes Pod 一直重启怎么排查？"
   "数据库连接池耗尽如何处理？"
   "Redis 内存占用过高的原因？"
   ```

4. **观察 AI 徽章**
   - 🟣 紫色 "AI 增强" 徽章
   - 加载提示："正在使用 AI 增强查询..."

---

**配置后立即测试：**
```bash
# 1. 配置 .env
# 2. 重启后端
# 3. 访问前端：http://localhost:5174
# 4. 提问："Kubernetes Pod 一直重启怎么排查？"
# 5. 观察紫色 AI 增强徽章 ✨
```
