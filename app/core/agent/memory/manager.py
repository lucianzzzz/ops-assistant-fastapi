"""Memory Manager - 统一记忆管理接口"""
import uuid
from typing import List, Optional
from app.core.agent.memory.base import Memory, MemoryType
from app.core.agent.memory.short_term import ShortTermMemory
from app.core.agent.memory.long_term import SimpleLongTermMemory
from app.core.common.logging import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """记忆管理器"""

    def __init__(self, session_id: str, use_vector_db: bool = False):
        self.session_id = session_id
        self.short_term = ShortTermMemory(session_id)

        # 根据配置选择长期记忆实现
        if use_vector_db:
            try:
                from app.core.agent.memory.long_term import VectorLongTermMemory
                self.long_term = VectorLongTermMemory()
            except ImportError:
                logger.warning("ChromaDB not available, using simple implementation")
                self.long_term = SimpleLongTermMemory()
        else:
            self.long_term = SimpleLongTermMemory()

    async def remember(self, content: str, memory_type: MemoryType,
                      importance: float = 0.5, metadata: dict = None) -> str:
        """记住某事"""
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

    async def recall(self, query: str, top_k: int = 5,
                    search_long_term: bool = True) -> List[Memory]:
        """回忆相关内容"""
        results = []

        # 搜索短期记忆
        short_memories = await self.short_term.search(query, top_k)
        results.extend(short_memories)

        # 搜索长期记忆
        if search_long_term:
            long_memories = await self.long_term.search(query, top_k)
            results.extend(long_memories)

        # 按重要性和时间排序
        results.sort(
            key=lambda m: (m.importance, m.last_accessed),
            reverse=True
        )

        return results[:top_k]

    async def get_context(self, n: int = 5) -> str:
        """获取最近上下文（用于 Prompt）"""
        recent = await self.short_term.get_recent(n)

        context_lines = []
        for m in recent:
            context_lines.append(f"- {m.content}")

        return "\n".join(context_lines) if context_lines else "（无）"

    async def get_recent_memories(self, n: int = 10) -> List[Memory]:
        """获取最近的记忆"""
        return await self.short_term.get_recent(n)

    async def clear_session(self):
        """清空会话记忆"""
        if hasattr(self.short_term, 'clear'):
            self.short_term.clear()

    async def summarize_and_consolidate(self, llm_client=None) -> str:
        """总结会话并巩固到长期记忆"""
        recent = await self.short_term.get_recent(100)

        if not recent:
            return "无内容可总结"

        # 构建总结 Prompt
        content_list = [m.content for m in recent]
        summary_text = "\n".join(content_list[:20])  # 最多 20 条

        # 如果有 LLM，用 LLM 总结
        if llm_client:
            try:
                prompt = f"""请总结以下会话内容，提取关键信息（100字以内）：

{summary_text}

总结："""

                response = llm_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=200
                )

                summary = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Failed to generate memory summary: {e}")
                summary = f"会话包含 {len(recent)} 条记忆"
        else:
            # 简单总结
            summary = f"会话包含 {len(recent)} 条记忆，最近的是：{recent[0].content[:50]}"

        # 存入长期记忆
        await self.remember(
            content=summary,
            memory_type=MemoryType.LONG_TERM,
            importance=0.8,
            metadata={"session_id": self.session_id, "type": "summary"}
        )

        return summary
