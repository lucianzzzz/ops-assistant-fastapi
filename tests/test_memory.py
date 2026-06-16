"""测试 Memory 系统"""
import pytest
import uuid
from app.core.agent.memory.base import Memory, MemoryType
from app.core.agent.memory.short_term import ShortTermMemory
from app.core.agent.memory.long_term import SimpleLongTermMemory
from app.core.agent.memory.manager import MemoryManager


class TestMemory:
    """测试记忆系统"""

    @pytest.mark.asyncio
    async def test_short_term_memory(self):
        """测试短期记忆"""
        memory_store = ShortTermMemory(session_id="test_session")

        # 添加记忆
        memory = Memory(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.SHORT_TERM,
            content="测试内容：IF1接收时延异常已解决",
            importance=0.7
        )

        memory_id = await memory_store.add(memory)
        assert memory_id == memory.memory_id

        # 获取记忆
        retrieved = await memory_store.get(memory_id)
        assert retrieved is not None
        assert retrieved.content == "测试内容：IF1接收时延异常已解决"
        assert retrieved.access_count == 1  # 访问次数增加

    @pytest.mark.asyncio
    async def test_short_term_search(self):
        """测试短期记忆搜索"""
        memory_store = ShortTermMemory(session_id="test_session")

        # 添加多条记忆
        contents = [
            "IF1接收时延异常怎么处理",
            "CPU使用率过高的排查方法",
            "IF1接收丢包问题解决"
        ]

        for content in contents:
            memory = Memory(
                memory_id=str(uuid.uuid4()),
                memory_type=MemoryType.SHORT_TERM,
                content=content
            )
            await memory_store.add(memory)

        # 搜索
        results = await memory_store.search(query="IF1", top_k=5)
        assert len(results) == 2  # 应该找到 2 条包含 IF1 的记忆

    @pytest.mark.asyncio
    async def test_short_term_get_recent(self):
        """测试获取最近记忆"""
        memory_store = ShortTermMemory(session_id="test_session")

        # 添加记忆
        for i in range(5):
            memory = Memory(
                memory_id=str(uuid.uuid4()),
                memory_type=MemoryType.SHORT_TERM,
                content=f"记忆 {i}"
            )
            await memory_store.add(memory)

        # 获取最近 3 条
        recent = await memory_store.get_recent(n=3)
        assert len(recent) == 3
        # 最近的记忆应该在前面（不验证具体顺序）

    @pytest.mark.asyncio
    async def test_long_term_memory(self):
        """测试长期记忆"""
        memory_store = SimpleLongTermMemory()

        # 添加记忆
        memory = Memory(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.LONG_TERM,
            content="长期知识：IF1接收时延通常由链路问题引起",
            importance=0.9
        )

        memory_id = await memory_store.add(memory)
        assert memory_id == memory.memory_id

        # 搜索
        results = await memory_store.search(query="IF1", top_k=5)
        assert len(results) == 1
        assert results[0].content == memory.content

    @pytest.mark.asyncio
    async def test_memory_manager(self):
        """测试记忆管理器"""
        manager = MemoryManager(session_id="test_session")

        # 记住短期内容
        memory_id = await manager.remember(
            content="用户问了 IF1 接收时延的问题",
            memory_type=MemoryType.SHORT_TERM,
            importance=0.6
        )
        assert memory_id is not None

        # 记住长期内容
        await manager.remember(
            content="IF1 接收时延的常见原因是链路质量问题",
            memory_type=MemoryType.LONG_TERM,
            importance=0.8
        )

        # 回忆
        results = await manager.recall(query="IF1", top_k=5)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_memory_context(self):
        """测试获取上下文"""
        manager = MemoryManager(session_id="test_session")

        # 添加几条记忆
        await manager.remember("第一条记忆", MemoryType.SHORT_TERM)
        await manager.remember("第二条记忆", MemoryType.SHORT_TERM)
        await manager.remember("第三条记忆", MemoryType.SHORT_TERM)

        # 获取上下文
        context = await manager.get_context(n=2)
        # 应该包含记忆（不验证具体顺序）
        assert "记忆" in context
        assert len(context) > 0

    @pytest.mark.asyncio
    async def test_memory_importance_ordering(self):
        """测试重要性排序"""
        manager = MemoryManager(session_id="test_session")

        # 添加不同重要性的记忆
        await manager.remember("低重要性", MemoryType.SHORT_TERM, importance=0.3)
        await manager.remember("高重要性", MemoryType.SHORT_TERM, importance=0.9)

        # 回忆（应该按重要性排序）
        results = await manager.recall(query="重要性", top_k=5)
        assert results[0].content == "高重要性"  # 重要性高的排前面

    @pytest.mark.asyncio
    async def test_memory_forget(self):
        """测试遗忘"""
        memory_store = ShortTermMemory(session_id="test_session")

        memory = Memory(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.SHORT_TERM,
            content="要被遗忘的内容"
        )
        memory_id = await memory_store.add(memory)

        # 确认存在
        retrieved = await memory_store.get(memory_id)
        assert retrieved is not None

        # 遗忘
        await memory_store.forget(memory_id)

        # 确认已删除
        retrieved = await memory_store.get(memory_id)
        assert retrieved is None
