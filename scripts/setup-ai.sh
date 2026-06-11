#!/bin/bash
# 快速配置 AI 增强查询

cd /Users/lucian/workspace/ops-assistant-fastapi

echo "🤖 Ops Assistant - AI 增强配置工具"
echo "===================================="
echo ""
echo "当前状态：.env 文件已创建，但未配置 API Key"
echo ""
echo "AI 增强功能说明："
echo "- 当本地知识库匹配度 < 50% 时自动触发"
echo "- 使用 LangChain + OpenAI 补充答案"
echo "- 提升置信度到 ~70%"
echo ""
echo "请选择 API 提供商："
echo "----------------------------------------"
echo "1) OpenAI 官方          (推荐海外用户)"
echo "2) DeepSeek             (推荐国内用户，性价比高)"
echo "3) 智谱 GLM             (国内，中文优化)"
echo "4) 暂不配置             (跳过 AI 功能)"
echo "5) 手动配置             (自定义配置)"
echo ""
read -p "请选择 [1-5]: " choice

case $choice in
  1)
    echo ""
    echo "📌 OpenAI 配置"
    echo "获取 API Key: https://platform.openai.com/api-keys"
    echo ""
    read -p "输入 OpenAI API Key: " api_key

    if [ -z "$api_key" ]; then
      echo "❌ API Key 不能为空"
      exit 1
    fi

    cat > .env << EOF
# OpenAI 配置
OPENAI_API_KEY=$api_key
OPENAI_MODEL=gpt-4

# 数据源（可选）
# OPS_ASSISTANT_DATA_DIR=/path/to/your/data
EOF

    echo "✅ 已配置 OpenAI"
    echo "   模型: gpt-4"
    ;;

  2)
    echo ""
    echo "📌 DeepSeek 配置"
    echo "获取 API Key: https://platform.deepseek.com/"
    echo "特点: 性价比高，速度快，中文支持好"
    echo ""
    read -p "输入 DeepSeek API Key: " api_key

    if [ -z "$api_key" ]; then
      echo "❌ API Key 不能为空"
      exit 1
    fi

    cat > .env << EOF
# DeepSeek 配置
OPENAI_API_KEY=$api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 数据源（可选）
# OPS_ASSISTANT_DATA_DIR=/path/to/your/data
EOF

    echo "✅ 已配置 DeepSeek"
    echo "   模型: deepseek-chat"
    ;;

  3)
    echo ""
    echo "📌 智谱 GLM 配置"
    echo "获取 API Key: https://open.bigmodel.cn/"
    echo "特点: 国内服务，中文优化"
    echo ""
    read -p "输入智谱 GLM API Key: " api_key

    if [ -z "$api_key" ]; then
      echo "❌ API Key 不能为空"
      exit 1
    fi

    cat > .env << EOF
# 智谱 GLM 配置
OPENAI_API_KEY=$api_key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4

# 数据源（可选）
# OPS_ASSISTANT_DATA_DIR=/path/to/your/data
EOF

    echo "✅ 已配置智谱 GLM"
    echo "   模型: glm-4"
    ;;

  4)
    echo ""
    echo "⏭️  跳过 AI 配置"
    echo ""
    echo "系统将只使用本地知识库，AI 增强功能不会触发。"
    echo "你随时可以运行此脚本进行配置。"
    exit 0
    ;;

  5)
    echo ""
    echo "📝 手动配置模式"
    echo ""
    echo "请编辑文件: /Users/lucian/workspace/ops-assistant-fastapi/.env"
    echo ""
    echo "示例配置："
    echo "  OPENAI_API_KEY=your-key-here"
    echo "  OPENAI_BASE_URL=https://api.openai.com/v1  # 可选"
    echo "  OPENAI_MODEL=gpt-4                         # 可选"
    exit 0
    ;;

  *)
    echo "❌ 无效选择"
    exit 1
    ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ AI 增强配置完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 下一步操作："
echo ""
echo "1. 重启后端服务"
echo "   cd /Users/lucian/workspace/ops-assistant-fastapi"
echo "   source .venv/bin/activate"
echo "   uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012"
echo ""
echo "2. 访问前端: http://localhost:5174"
echo ""
echo "3. 测试 AI 增强（提问知识库没有的问题）："
echo "   - \"Kubernetes Pod 一直重启怎么排查？\""
echo "   - \"数据库连接池耗尽如何处理？\""
echo "   - \"Redis 内存占用过高的原因？\""
echo ""
echo "4. 观察 AI 增强标识："
echo "   - 加载提示: \"正在使用 AI 增强查询...\""
echo "   - 结果标识: 🟣 紫色 \"AI 增强\" 徽章"
echo ""
echo "💡 提示："
echo "   只有当本地知识库匹配度 < 50% 时，AI 才会自动触发"
echo "   这意味着你的知识库已经很完善了！"
echo ""
echo "📖 详细文档: /Users/lucian/workspace/AI_ENHANCEMENT_GUIDE.md"
echo ""
