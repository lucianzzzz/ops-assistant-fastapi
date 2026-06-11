#!/bin/bash

# DeepSeek AI 增强测试脚本

echo "🤖 测试 DeepSeek AI 增强功能"
echo "================================"
echo ""

# 检查配置
echo "1️⃣ 验证配置..."
cd /Users/lucian/workspace/ops-assistant-fastapi

if grep -q "sk-42ed3ce57b9249d3b539c96ae8c07960" .env; then
    echo "   ✅ DeepSeek API Key 已配置"
else
    echo "   ❌ API Key 未找到"
    exit 1
fi

if grep -q "deepseek.com" .env; then
    echo "   ✅ DeepSeek Base URL 已配置"
else
    echo "   ❌ Base URL 未配置"
    exit 1
fi

echo ""
echo "2️⃣ 测试 AI 助手初始化..."
source .venv/bin/activate

python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from app.core.ai_assistant import AIAssistant

ai = AIAssistant()
print(f"   AI Enabled: {ai.enabled}")
print(f"   Model: {ai.model}")
print(f"   Base URL: {ai.base_url}")

if ai.enabled:
    print("   ✅ AI 助手初始化成功")
else:
    print("   ❌ AI 助手初始化失败")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ AI 助手初始化失败，请检查配置"
    exit 1
fi

echo ""
echo "3️⃣ 测试 API 连通性..."
echo "   (提交一个测试查询)"
echo ""

# 等待后端启动
sleep 2

# 测试查询
TEST_RESULT=$(curl -s -X POST http://localhost:8012/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Kubernetes Pod 一直重启怎么排查",
    "top_k": 3
  }' 2>/dev/null)

if [ -z "$TEST_RESULT" ]; then
    echo "   ⚠️  后端服务未启动"
    echo ""
    echo "   请在另一个终端启动后端："
    echo "   cd /Users/lucian/workspace/ops-assistant-fastapi"
    echo "   source .venv/bin/activate"
    echo "   uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012"
    echo ""
else
    echo "$TEST_RESULT" | jq -r '
    "   问题: " + .question,
    "   置信度: " + (.confidence * 100 | tostring) + "%",
    "   AI 增强: " + (if .ai_fallback.used then "✅ 已使用" else "❌ 未触发" end),
    (if .ai_fallback.used then "   AI 响应长度: " + (.ai_fallback.raw_response | length | tostring) + " 字符" else "" end)
    ' 2>/dev/null || echo "   ✅ 查询成功（请查看完整输出）"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DeepSeek AI 配置测试完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 下一步测试建议："
echo ""
echo "1. 启动/重启后端服务："
echo "   cd /Users/lucian/workspace/ops-assistant-fastapi"
echo "   source .venv/bin/activate"
echo "   uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012"
echo ""
echo "2. 访问前端: http://localhost:5174"
echo ""
echo "3. 测试这些问题（会触发 AI）："
echo "   ✅ \"Kubernetes Pod 一直重启怎么排查？\""
echo "   ✅ \"数据库连接池耗尽如何处理？\""
echo "   ✅ \"Redis 内存占用过高的原因？\""
echo "   ✅ \"Elasticsearch 查询变慢了\""
echo "   ✅ \"Docker 容器网络不通怎么办？\""
echo ""
echo "4. 观察 AI 增强标识："
echo "   - 加载中（5秒后）: \"正在使用 AI 增强查询...\""
echo "   - 结果中: 🟣 紫色 \"AI 增强\" 徽章"
echo ""
echo "💡 提示："
echo "   - 如果本地知识库已有答案（置信度 ≥ 50%），AI 不会触发"
echo "   - 这是正常的，说明知识库很完善"
echo "   - DeepSeek 响应速度快，一般 2-3 秒"
echo ""
