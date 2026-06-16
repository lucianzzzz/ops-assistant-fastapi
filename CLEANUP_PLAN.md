# 未使用代码清理计划

## 🔍 分析结果

### ❌ 完全未使用（建议删除）

1. **adaptive_planner.py** - 自适应规划器（未使用）
2. **multi_agent.py** - 多 Agent 协作（未使用）
3. **executor.py** - 执行器（未使用）
4. **memory/** - 整个 memory 目录（未使用）
   - base.py
   - short_term.py
   - long_term.py
   - manager.py
   - __init__.py

### ⚠️ 仅在测试中使用（保留）

这些模块虽然在主代码中未使用，但有对应的测试，说明是探索性代码：

1. **react_agent.py** - 在 `tests/test_react_agent.py` 中测试
2. **real_react_agent.py** - 在 `tests/test_real_react_agent.py` 中测试
3. **planner.py** - 在 `tests/test_planner.py` 中测试

**建议**：移动到 `examples/` 或 `experiments/` 目录，保留作为学习材料

### ✅ 正在使用（保留）

1. **action_generator.py** - 在 service.py 和 enhanced_service.py 中使用
2. **agent_service.py** - 在 API 路由中使用
3. **tools/** - 在 main.py 中注册和使用

---

## 🗑️ 清理方案

### 方案 A：彻底清理（推荐生产环境）

删除所有未使用的代码，包括仅在测试中使用的：

```bash
# 删除完全未使用的
rm app/core/agent/adaptive_planner.py
rm app/core/agent/multi_agent.py
rm app/core/agent/executor.py
rm -rf app/core/agent/memory/

# 删除仅在测试中使用的
rm app/core/agent/react_agent.py
rm app/core/agent/real_react_agent.py
rm app/core/agent/planner.py

# 删除对应的测试
rm tests/test_react_agent.py
rm tests/test_real_react_agent.py
rm tests/test_planner.py
rm tests/test_memory.py
rm tests/test_tool_use.py
```

**影响**：
- 减少 ~500 行代码
- 简化项目结构
- 无功能影响（这些代码未被使用）

---

### 方案 B：保留探索性代码（推荐面试）

将探索性代码移到 `examples/` 目录：

```bash
# 创建 examples 目录
mkdir -p examples/agent_exploration

# 移动探索性代码
mv app/core/agent/react_agent.py examples/agent_exploration/
mv app/core/agent/real_react_agent.py examples/agent_exploration/
mv app/core/agent/planner.py examples/agent_exploration/
mv app/core/agent/memory examples/agent_exploration/

# 移动对应测试
mv tests/test_react_agent.py examples/agent_exploration/
mv tests/test_real_react_agent.py examples/agent_exploration/
mv tests/test_planner.py examples/agent_exploration/
mv tests/test_memory.py examples/agent_exploration/

# 删除完全未使用的
rm app/core/agent/adaptive_planner.py
rm app/core/agent/multi_agent.py
rm app/core/agent/executor.py
rm tests/test_tool_use.py

# 添加说明文档
cat > examples/agent_exploration/README.md << 'EOF'
# Agent 探索性代码

这些是早期探索 Agent 架构时编写的原型代码。

虽然在生产代码中未使用，但保留作为学习材料和技术储备。

## 模块说明

- `react_agent.py` - ReAct (Reasoning + Acting) 循环原型
- `real_react_agent.py` - 完整的 ReAct Agent 实现
- `planner.py` - 任务规划器原型
- `memory/` - 记忆管理系统原型

## 为什么没有使用

当前项目是 **RAG 系统**（知识问答），不需要复杂的 Agent：

- RAG：单次问答，检索 + 生成
- Agent：多步推理，工具调用，动态决策

如果未来需要自动化运维操作（执行型任务），可以参考这些代码。
EOF
```

**优势**：
- 面试时可以展示"我研究过 Agent，但评估后不需要"
- 代码保留作为技术储备
- 项目结构更清晰（production vs exploration）

---

## 📊 清理统计

### 方案 A（彻底清理）

| 类型 | 数量 | 代码行数 |
|-----|-----|---------|
| 删除文件 | 12 个 | ~500 行 |
| 保留文件 | 3 个 | ~300 行 |

### 方案 B（保留探索）

| 类型 | 数量 | 代码行数 |
|-----|-----|---------|
| 删除文件 | 4 个 | ~200 行 |
| 移动文件 | 8 个 | ~300 行 |
| 保留文件 | 3 个 | ~300 行 |

---

## 💡 推荐方案

### 如果你的目标是**面试**：选择 **方案 B**

**理由**：
1. 可以展示你研究过 Agent（有代码证明）
2. 可以讲清楚"为什么不用 Agent"（架构判断力）
3. 代码保留作为技术深度的证明

**面试话术**：
> "我研究过 ReAct Agent 和 Planning 系统（展示 examples/ 目录），
> 但评估后发现当前业务是知识问答，不需要多步推理和工具调用，
> 引入 Agent 会增加复杂度和延迟，违反 KISS 原则。
> 所以选择了更合适的 RAG 架构。
> 这些代码保留在 examples/ 作为技术储备。"

### 如果你的目标是**生产部署**：选择 **方案 A**

**理由**：
1. 减少依赖和维护成本
2. 简化项目结构
3. 降低新人理解成本

---

## 🚀 执行计划

我可以帮你执行任一方案，请选择：

- **方案 A**：彻底清理（生产环境）
- **方案 B**：保留探索性代码（面试）

选择后，我会：
1. 执行文件移动/删除操作
2. 更新相关导入
3. 运行测试确保没有破坏
4. 提交 Git（清晰的 commit message）
5. 更新文档
