#!/bin/bash

# Ops Assistant Agent 执行能力 - 快速测试脚本

echo "🤖 测试 Ops Assistant Agent 执行能力"
echo ""

# 测试 1: 生成动作
echo "📝 测试 1: 生成可执行动作"
echo "----------------------------------------"

curl -s -X POST http://localhost:8012/api/v1/agent/actions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "系统负载很高",
    "analysis_result": {
      "keywords": ["系统", "负载"],
      "normalized_metric": "cpu_usage"
    }
  }' | jq '.actions[] | {id, title, command, risk_level}'

echo ""
echo ""

# 测试 2: 完整查询（包含动作生成）
echo "📝 测试 2: 完整查询流程（自动生成动作）"
echo "----------------------------------------"

curl -s -X POST http://localhost:8012/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "系统负载很高",
    "top_k": 3
  }' | jq '{
    question,
    confidence,
    keywords,
    executable_actions: .executable_actions[] | {id, title, command, risk_level}
  }'

echo ""
echo ""

# 测试说明
echo "✅ 测试完成！"
echo ""
echo "📋 下一步："
echo "1. 访问前端: http://localhost:5174"
echo "2. 提交查询: \"系统负载很高\""
echo "3. 查看\"可执行动作\"部分"
echo "4. 点击\"执行\"按钮测试"
echo ""
echo "💡 提示："
echo "- 🟢 绿色标签 = 低风险，直接执行"
echo "- 🟡 黄色标签 = 中风险，需要确认"
echo "- 🔴 红色标签 = 高风险，双重确认"
