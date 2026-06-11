#!/bin/bash

# Ops Assistant 快速启动脚本

echo "🚀 启动 Ops Assistant..."
echo ""

# 检查后端
if [ ! -d "/Users/lucian/workspace/ops-assistant-fastapi/.venv" ]; then
    echo "❌ 后端虚拟环境不存在，请先安装依赖："
    echo "   cd /Users/lucian/workspace/ops-assistant-fastapi"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -e ."
    exit 1
fi

# 检查前端
if [ ! -d "/Users/lucian/workspace/ops-assistant-client/node_modules" ]; then
    echo "❌ 前端依赖未安装，请先运行："
    echo "   cd /Users/lucian/workspace/ops-assistant-client"
    echo "   npm install"
    exit 1
fi

# 启动后端
echo "📦 启动后端服务 (端口 8012)..."
cd /Users/lucian/workspace/ops-assistant-fastapi
source .venv/bin/activate
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012 > /tmp/ops-backend.log 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 2

# 启动前端
echo "🎨 启动前端服务 (端口 5174)..."
cd /Users/lucian/workspace/ops-assistant-client
npm run dev > /tmp/ops-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "📍 访问地址："
echo "   前端: http://localhost:5174"
echo "   后端: http://localhost:8012"
echo "   API 文档: http://localhost:8012/docs"
echo ""
echo "📝 日志文件："
echo "   后端: /tmp/ops-backend.log"
echo "   前端: /tmp/ops-frontend.log"
echo ""
echo "🛑 停止服务："
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "💡 提示："
echo "   - 如需启用 AI 增强，请在后端目录配置 .env 文件"
echo "   - 查看完整升级说明: /Users/lucian/workspace/UPGRADE_SUMMARY.md"
echo ""
