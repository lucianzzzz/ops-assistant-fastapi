#!/bin/bash
# Ops Assistant FastAPI 启动脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Ops Assistant FastAPI 启动 ===${NC}"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}未检测到虚拟环境，正在创建...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
if [ ! -f ".venv/installed" ]; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    pip install -e . > /dev/null 2>&1
    touch .venv/installed
    echo -e "${GREEN}✓ 依赖已安装${NC}"
fi

PORT=${OPS_ASSISTANT_PORT:-8012}

echo ""
echo -e "${GREEN}当前配置：${NC}"
if [ -n "$OPS_ASSISTANT_DATA_DIR" ]; then
    echo "  数据目录: $OPS_ASSISTANT_DATA_DIR"
else
    echo "  数据目录: app/seed (内置种子数据)"
fi
echo "  服务端口: $PORT"
echo ""

echo -e "${GREEN}正在启动服务...${NC}"
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port $PORT
