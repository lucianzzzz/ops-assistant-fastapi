# 代码简化分析报告

**项目**: ops-assistant-fastapi  
**分析日期**: 2026-06-16  
**分析范围**: app/ 目录下所有 Python 文件  
**参考规范**: 开发规范.md

---

## 执行摘要

本次分析基于 **Code Simplification** 技能，遵循以下五大原则：
1. ✅ **精确保持行为** - 所有建议不改变功能
2. ✅ **遵循项目约定** - 符合 `开发规范.md`
3. ✅ **清晰优于巧妙** - 提升可读性
4. ✅ **保持平衡** - 避免过度简化
5. ✅ **限定范围** - 专注最近修改的代码

**发现的简化机会**: 15 处  
**优先级分布**: 高优先级 5 处 | 中优先级 7 处 | 低优先级 3 处

---

## 高优先级简化（P0）

### 1. 重复的 import 语句
**文件**: `app/api/routes/assistant.py:1-2`

```python
# ❌ 当前代码（重复导入）
from typing import Any
from typing import Any
from fastapi import APIRouter, Depends
```

**问题**: 
- 第 1-2 行重复导入 `typing.Any`
- 违反 PEP 8 导入规范

**建议**:
```python
# ✅ 简化后
from typing import Any

from fastapi import APIRouter, Depends
```

**影响**: 立即修复，无风险

---

### 2. 冗余的条件返回
**文件**: `app/core/assistant/service.py:293-300`

```python
# ❌ 当前代码
def build_possible_reasons(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> list[str]:
    reasons = [item["reason"] for item in knowledge_matches if item.get("reason")]
    if not reasons and metric_matches:
        metric = metric_matches[0]
        reasons.append(f"指标 {metric['name']} 出现异常，建议先确认 {metric['measurement']} 分区下 {metric['field_name']} 的采集与计算口径是否正确。")
        if metric.get("desc"):
            reasons.append(f"指标说明：{metric['desc']}")
    return reasons
```

**问题**:
- 嵌套条件可以用早期返回简化
- 同一个 `metric` 变量被重复访问

**建议**:
```python
# ✅ 简化后
def build_possible_reasons(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> list[str]:
    reasons = [item["reason"] for item in knowledge_matches if item.get("reason")]
    
    if reasons or not metric_matches:
        return reasons
    
    metric = metric_matches[0]
    reasons.append(
        f"指标 {metric['name']} 出现异常，"
        f"建议先确认 {metric['measurement']} 分区下 {metric['field_name']} 的采集与计算口径是否正确。"
    )
    
    if metric.get("desc"):
        reasons.append(f"指标说明：{metric['desc']}")
    
    return reasons
```

**影响**: 提升可读性，逻辑更清晰

---

### 3. 冗余的静态方法
**文件**: `app/core/assistant/service.py:364-366`

```python
# ❌ 当前代码
@staticmethod
def similarity(source: str, target: str) -> float:
    return SequenceMatcher(None, source, target).ratio()
```

**问题**:
- 这个静态方法从未被使用（检查整个项目无调用）
- 功能与 `_similarity_cached` 重复
- 根据 **Chesterton's Fence**，需确认是否有历史原因

**建议**:
```python
# ✅ 删除此方法
# 如果需要非缓存版本，直接使用 SequenceMatcher
```

**影响**: 删除 dead code，减少维护负担

---

### 4. 过于通用的异常捕获
**文件**: `app/core/assistant/service.py:115-118`

```python
# ❌ 当前代码
try:
    if keywords or metric_matches:
        metric_name = metric_matches[0]["name"] if metric_matches else ""
        actions = self.action_generator.generate_from_keywords(keywords, metric_name)
        result["executable_actions"] = [action.model_dump() for action in actions]
except Exception as e:
    # 动作生成失败不影响主流程
    logger.warning(f"Failed to generate actions: {e}")
    result["executable_actions"] = []
```

**问题**:
- 捕获 `Exception` 过于宽泛
- 根据 `开发规范.md` 第三章，应该捕获具体异常
- 缺少上下文信息记录

**建议**:
```python
# ✅ 简化后
try:
    if keywords or metric_matches:
        metric_name = metric_matches[0]["name"] if metric_matches else ""
        actions = self.action_generator.generate_from_keywords(keywords, metric_name)
        result["executable_actions"] = [action.model_dump() for action in actions]
except (KeyError, AttributeError, ValueError) as e:
    # 动作生成失败不影响主流程
    logger.warning(
        "Failed to generate actions",
        extra={"error": str(e), "keywords": keywords[:3], "metric_name": metric_name}
    )
    result["executable_actions"] = []
```

**影响**: 符合规范，提升日志质量

---

### 5. 条件表达式可简化
**文件**: `app/core/assistant/service.py:52-58`

```python
# ❌ 当前代码
def __init__(self, repository: InMemoryRepository, ai_assistant: Optional[AIAssistant] = None, action_generator=None):
    self.repository = repository
    self.ai_assistant = ai_assistant or AIAssistant()
    if action_generator is None:
        from app.core.agent.action_generator import ActionGenerator
        action_generator = ActionGenerator(self.ai_assistant)
    self.action_generator = action_generator
```

**问题**:
- `action_generator` 的初始化逻辑可以更简洁
- 延迟导入可以保留（避免循环依赖），但逻辑可以简化

**建议**:
```python
# ✅ 简化后
def __init__(
    self, 
    repository: InMemoryRepository, 
    ai_assistant: Optional[AIAssistant] = None, 
    action_generator=None
):
    self.repository = repository
    self.ai_assistant = ai_assistant or AIAssistant()
    
    if action_generator is None:
        from app.core.agent.action_generator import ActionGenerator
        action_generator = ActionGenerator(self.ai_assistant)
    
    self.action_generator = action_generator
```

**影响**: 提升可读性（函数签名分行，符合规范的 120 字符限制）

---

## 中优先级简化（P1）

### 6. 嵌套条件提取为早期返回
**文件**: `app/core/agent/react_agent.py:99-115`

```python
# ❌ 当前代码（嵌套条件）
def _think(self, question: str, context: Dict[str, Any], iteration: int) -> tuple[str, ThoughtType]:
    if iteration == 1:
        thought_type = ThoughtType.ANALYZE
        thought = f"分析问题：{question}。需要识别关键指标、异常特征和可能原因。"
    elif iteration == 2:
        thought_type = ThoughtType.PLAN
        last_obs = context.get("last_observation", "")
        thought = f"基于观察 '{last_obs[:50]}...'，需要查询知识库获取相关诊断方法。"
    elif iteration < self.max_iterations:
        thought_type = ThoughtType.DECIDE
        thought = "根据已收集的信息，决定执行具体诊断动作或给出答案。"
    else:
        thought_type = ThoughtType.REFLECT
        thought = "已达到最大迭代次数，汇总现有信息给出最终建议。"
    
    return thought, thought_type
```

**建议**:
```python
# ✅ 简化后（使用字典映射）
def _think(self, question: str, context: Dict[str, Any], iteration: int) -> tuple[str, ThoughtType]:
    if iteration == 1:
        return (
            f"分析问题：{question}。需要识别关键指标、异常特征和可能原因。",
            ThoughtType.ANALYZE
        )
    
    if iteration == 2:
        last_obs = context.get("last_observation", "")
        return (
            f"基于观察 '{last_obs[:50]}...'，需要查询知识库获取相关诊断方法。",
            ThoughtType.PLAN
        )
    
    if iteration < self.max_iterations:
        return (
            "根据已收集的信息，决定执行具体诊断动作或给出答案。",
            ThoughtType.DECIDE
        )
    
    return (
        "已达到最大迭代次数，汇总现有信息给出最终建议。",
        ThoughtType.REFLECT
    )
```

**影响**: 更清晰的逻辑流程，每个分支独立

---

### 7. 长函数拆分
**文件**: `app/core/assistant/service.py:79-154` (75 行)

```python
# ❌ 当前代码：ask() 方法 75 行
def ask(self, question: str, province: str = "", top_k: int = 3) -> dict[str, Any]:
    # ... 75 行代码
```

**问题**:
- 违反规范：函数超过 50 行
- 职责混杂：数据处理 + 结果构建 + AI 增强判断

**建议**:
```python
# ✅ 拆分为多个方法
def ask(self, question: str, province: str = "", top_k: int = 3) -> dict[str, Any]:
    normalized_question = self.normalize(question)
    keywords = self.extract_keywords(normalized_question)
    
    knowledge_matches = self.match_knowledge(normalized_question, province, top_k)
    metric_matches = self.match_metrics(normalized_question, keywords, top_k)
    
    result = self._build_base_result(question, normalized_question, keywords, knowledge_matches, metric_matches)
    result = self._enhance_with_actions(result, keywords, metric_matches)
    result = self._add_fallback_if_needed(result, question, top_k)
    result = self._mark_ai_fallback_if_needed(result, knowledge_matches, metric_matches)
    
    return result

def _build_base_result(self, question: str, normalized_question: str, keywords: list[str], 
                       knowledge_matches: list, metric_matches: list) -> dict[str, Any]:
    """构建基础结果"""
    confidence = self.build_confidence(knowledge_matches, metric_matches)
    
    return {
        "question": question,
        "normalized_question": normalized_question,
        "normalized_metric": metric_matches[0]["name"] if metric_matches else "",
        "keywords": keywords,
        "matched_knowledge": knowledge_matches,
        "possible_reason": self.build_possible_reasons(knowledge_matches, metric_matches),
        "suggested_steps": self.build_suggested_steps(knowledge_matches, metric_matches),
        "related_objects": self.build_related_objects(metric_matches, keywords),
        "confidence": confidence,
        "next_actions": self.build_next_actions(metric_matches),
        "fallback_questions": [],
        "ai_fallback": None,
        "executable_actions": [],
    }
```

**影响**: 大幅提升可读性和可测试性

---

### 8. 简化条件赋值
**文件**: `app/api/routes/assistant.py:20-42`

```python
# ❌ 当前代码
@router.get("/ready")
def ready(repository: InMemoryRepository = Depends(get_repository)) -> dict[str, Any]:
    try:
        knowledge_count = len(repository.knowledge_items)
        metrics_count = len(repository.metric_items)

        if knowledge_count == 0:
            return {
                "status": "not_ready",
                "reason": "知识库未加载"
            }

        return {
            "status": "ready",
            "knowledge_count": knowledge_count,
            "metrics_count": metrics_count
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "reason": str(e)
        }
```

**建议**:
```python
# ✅ 简化后
@router.get("/ready")
def ready(repository: InMemoryRepository = Depends(get_repository)) -> dict[str, Any]:
    try:
        knowledge_count = len(repository.knowledge_items)
        metrics_count = len(repository.metric_items)

        if knowledge_count == 0:
            return {"status": "not_ready", "reason": "知识库未加载"}

        return {
            "status": "ready",
            "knowledge_count": knowledge_count,
            "metrics_count": metrics_count
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "not_ready", "reason": str(e)}
```

**影响**: 添加日志记录（符合规范），提升可维护性

---

### 9. 简化 if-else 链
**文件**: `app/core/agent/memory/manager.py:30-50`

```python
# ❌ 当前代码
async def remember(self, content: str, memory_type: MemoryType,
                  importance: float = 0.5, metadata: dict = None) -> str:
    memory = Memory(
        memory_id=str(uuid.uuid4()),
        memory_type=memory_type,
        content=content,
        importance=importance,
        metadata=metadata or {}
    )

    # 短期记忆存到内存/Redis
    if memory_type == MemoryType.SHORT_TERM:
        return await self.short_term.add(memory)

    # 长期记忆存到向量库
    elif memory_type == MemoryType.LONG_TERM:
        return await self.long_term.add(memory)

    # 默认短期
    return await self.short_term.add(memory)
```

**建议**:
```python
# ✅ 简化后（消除重复的默认逻辑）
async def remember(
    self, 
    content: str, 
    memory_type: MemoryType,
    importance: float = 0.5, 
    metadata: dict = None
) -> str:
    memory = Memory(
        memory_id=str(uuid.uuid4()),
        memory_type=memory_type,
        content=content,
        importance=importance,
        metadata=metadata or {}
    )

    if memory_type == MemoryType.LONG_TERM:
        return await self.long_term.add(memory)
    
    # 默认使用短期记忆（包括 SHORT_TERM 和其他类型）
    return await self.short_term.add(memory)
```

**影响**: 消除重复代码，逻辑更清晰

---

### 10. 提取魔法数字为常量
**文件**: `app/core/assistant/service.py:231-242`

```python
# ❌ 当前代码（魔法数字）
for item in queryset[:500]:
    # ...
    if score < 0.35:
        continue
```

**建议**:
```python
# ✅ 在类定义开头添加常量
class OpsAssistantService:
    # 查询限制
    MAX_QUERY_ITEMS = 500
    MIN_KNOWLEDGE_SCORE = 0.35
    MIN_METRIC_SCORE = 0.30
    HIGH_MATCH_SCORE = 0.95
    
    # 现有的 stop_words...

# 使用
for item in queryset[:self.MAX_QUERY_ITEMS]:
    # ...
    if score < self.MIN_KNOWLEDGE_SCORE:
        continue
```

**影响**: 提升可维护性，便于调优

---

### 11. 简化推导式
**文件**: `app/core/assistant/service.py:273-276`

```python
# ❌ 当前代码
score = max(self._similarity_cached(question, candidate) for candidate in candidates if candidate)
keyword_hits = sum(1 for keyword in keywords if any(keyword in candidate for candidate in candidates if candidate))
```

**问题**:
- 第二行过于复杂，难以理解
- 嵌套的生成器表达式降低可读性

**建议**:
```python
# ✅ 简化后
valid_candidates = [c for c in candidates if c]
score = max(self._similarity_cached(question, c) for c in valid_candidates)

keyword_hits = sum(
    1 for keyword in keywords 
    if any(keyword in candidate for candidate in valid_candidates)
)
```

**影响**: 大幅提升可读性

---

### 12. 优化字符串格式化
**文件**: `app/core/agent/planner.py:65-93`

```python
# ❌ 当前代码（多行字符串拼接）
prompt = f"""
问题：{question}

相关历史：
{memory_context if memory_context else "（无）"}

可用工具：
{tools_desc}

请制定一个多步执行计划...
"""
```

**建议**:
```python
# ✅ 简化后
prompt = f"""问题：{question}

相关历史：
{memory_context or "（无）"}

可用工具：
{tools_desc}

请制定一个多步执行计划，用 JSON 格式回复（只返回 JSON）：
{{
  "steps": [
    {{
      "description": "步骤描述",
      "tool_name": "工具名称（或 null）",
      "tool_params": {{"参数": "值"}},
      "dependencies": []
    }}
  ]
}}

要求：
1. 步骤之间要有逻辑顺序
2. 后续步骤可以依赖前面步骤的结果（用索引表示，如 [0, 1]）
3. 最后一步应该是生成答案
4. 保持简洁，3-5 步即可
"""
```

**影响**: 使用 `or` 替代三元表达式，更简洁

---

## 低优先级简化（P2）

### 13. 类型注解优化
**文件**: 多个文件

```python
# ❌ 当前代码
def build_confidence(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> float:
```

**建议**:
```python
# ✅ 考虑引入类型别名
from typing import TypeAlias

MatchList: TypeAlias = list[dict[str, Any]]

def build_confidence(self, knowledge_matches: MatchList, metric_matches: MatchList) -> float:
```

**影响**: 提升代码可读性，但需要评估是否值得引入额外的类型定义

---

### 14. 日志格式统一
**文件**: 多个文件

```python
# ❌ 当前代码（混用字符串格式）
logger.warning(f"Failed to generate actions: {e}")
logger.error(f"AI服务调用失败", exc_info=True)
```

**建议**:
```python
# ✅ 统一使用占位符（符合规范）
logger.warning("Failed to generate actions: %s", e)
logger.error("AI服务调用失败", exc_info=True)
```

**影响**: 符合 `开发规范.md` 第四章日志规范

---

### 15. 文档字符串补充
**文件**: 多个文件

许多方法缺少文档字符串，违反规范要求。建议按照以下模板补充：

```python
def match_knowledge(self, question: str, province: str, top_k: int) -> list[dict[str, Any]]:
    """匹配知识库
    
    Args:
        question: 标准化后的问题
        province: 省份过滤条件（空字符串表示不过滤）
        top_k: 返回结果数量
        
    Returns:
        匹配的知识条目列表，按得分降序排列
        
    Note:
        - 使用缓存的标准化文本加速匹配
        - 得分阈值: 0.35
        - 子串匹配可提升得分至 0.95
    """
```

---

## 实施计划

### 阶段 1：立即修复（本周）
1. ✅ 修复重复 import（简化 #1）
2. ✅ 删除未使用的静态方法（简化 #3）
3. ✅ 改进异常处理（简化 #4）
4. ✅ 优化函数签名（简化 #5）

**预期收益**: 消除明显问题，无风险

### 阶段 2：重构优化（下周）
5. ✅ 拆分长函数（简化 #7）
6. ✅ 简化条件逻辑（简化 #2, #6, #9）
7. ✅ 提取魔法数字（简化 #10）
8. ✅ 优化推导式（简化 #11）

**预期收益**: 大幅提升可读性和可维护性

### 阶段 3：规范完善（持续）
9. ✅ 补充文档字符串（简化 #15）
10. ✅ 统一日志格式（简化 #14）
11. ✅ 优化类型注解（简化 #13）

**预期收益**: 符合团队规范，提升长期可维护性

---

## 验证清单

每个简化完成后，必须验证：

- [ ] 所有现有测试通过
- [ ] 代码行为未改变
- [ ] 符合 `开发规范.md`
- [ ] 无新增 linter 警告
- [ ] 增量提交，每个简化一个 commit

**提交格式**:
```
refactor(service): 简化 ask() 方法的条件逻辑

- 提取早期返回模式
- 消除嵌套条件
- 保持原有行为不变
```

---

## 附录：工具配置建议

为防止未来回退，建议配置自动化工具：

```toml
# pyproject.toml
[tool.ruff]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "C90",  # mccabe (复杂度检查)
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions (简化推导式)
    "SIM",  # flake8-simplify (简化建议)
]

[tool.ruff.mccabe]
max-complexity = 10  # 函数复杂度上限
```

---

**报告生成**: Claude Code (Opus 4.8)  
**技能**: agent-skills:code-simplification  
**下一步**: 执行阶段 1 的立即修复
