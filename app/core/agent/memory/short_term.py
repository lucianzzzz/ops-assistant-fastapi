"""短期记忆实现（简化版，用字典模拟 Redis）"""
import time
from typing import Optional, List
from datetime import datetime, timedelta
from app.core.agent.memory.base import Memory, MemoryStore, MemoryType


class ShortTermMemory(MemoryStore):
    """短期记忆（内存实现，模拟 Redis）"""

    def __init__(self, session_id: str, ttl_seconds: int = 3600):
        self.session_id = session_id
        self.ttl_seconds = ttl_seconds
        self.storage: dict[str, tuple[Memory, float]] = {}  # {memory_id: (memory, expire_time)}

    def _cleanup_expired(self):
        """清理过期记忆"""
        current_time = time.time()
        expired = [
            mid for mid, (_, expire_time) in self.storage.items()
            if expire_time < current_time
        ]
        for mid in expired:
            del self.storage[mid]

    async def add(self, memory: Memory) -> str:
        """添加到内存"""
        self._cleanup_expired()

        expire_time = time.time() + self.ttl_seconds
        self.storage[memory.memory_id] = (memory, expire_time)

        return memory.memory_id

    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        self._cleanup_expired()

        if memory_id not in self.storage:
            return None

        memory, expire_time = self.storage[memory_id]

        # 更新访问记录
        memory.access_count += 1
        memory.last_accessed = datetime.now()

        # 更新存储
        self.storage[memory_id] = (memory, expire_time)

        return memory

    async def search(self, query: str, top_k: int = 5) -> List[Memory]:
        """搜索相关记忆（简单实现：全文匹配）"""
        self._cleanup_expired()

        results = []
        for memory, _ in self.storage.values():
            if query.lower() in memory.content.lower():
                results.append(memory)
                if len(results) >= top_k:
                    break

        # 按重要性和时间排序
        results.sort(key=lambda m: (m.importance, m.created_at), reverse=True)
        return results[:top_k]

    async def get_recent(self, n: int = 10) -> List[Memory]:
        """获取最近 N 条记忆"""
        self._cleanup_expired()

        memories = [memory for memory, _ in self.storage.values()]
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:n]

    async def update_importance(self, memory_id: str, importance: float):
        """更新重要性"""
        if memory_id in self.storage:
            memory, expire_time = self.storage[memory_id]
            memory.importance = importance
            self.storage[memory_id] = (memory, expire_time)

    async def forget(self, memory_id: str):
        """遗忘（删除）"""
        if memory_id in self.storage:
            del self.storage[memory_id]

    def clear(self):
        """清空所有记忆"""
        self.storage.clear()


# 真实 Redis 实现（可选，需要 redis 库）
class RedisShortTermMemory(MemoryStore):
    """短期记忆（Redis 实现）"""

    def __init__(self, session_id: str, redis_client=None):
        self.session_id = session_id
        self.key_prefix = f"memory:short:{session_id}"

        # 如果没有提供 redis_client，尝试创建
        if redis_client is None:
            try:
                import redis
                import os
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    decode_responses=True
                )
            except ImportError:
                raise ImportError("需要安装 redis: pip install redis")
        else:
            self.redis_client = redis_client

    async def add(self, memory: Memory) -> str:
        """添加到 Redis"""
        key = f"{self.key_prefix}:{memory.memory_id}"

        # 序列化
        data = memory.model_dump_json()

        # 存储，设置过期时间（1小时）
        self.redis_client.setex(key, 3600, data)

        # 添加到会话索引
        self.redis_client.zadd(
            f"{self.key_prefix}:index",
            {memory.memory_id: memory.created_at.timestamp()}
        )

        return memory.memory_id

    async def get(self, memory_id: str) -> Optional[Memory]:
        key = f"{self.key_prefix}:{memory_id}"
        data = self.redis_client.get(key)

        if not data:
            return None

        memory = Memory.model_validate_json(data)

        # 更新访问记录
        memory.access_count += 1
        memory.last_accessed = datetime.now()
        self.redis_client.setex(key, 3600, memory.model_dump_json())

        return memory

    async def search(self, query: str, top_k: int = 5) -> List[Memory]:
        """搜索相关记忆"""
        memory_ids = self.redis_client.zrevrange(
            f"{self.key_prefix}:index",
            0,
            -1
        )

        results = []
        for mid in memory_ids:
            memory = await self.get(mid)
            if memory and query.lower() in memory.content.lower():
                results.append(memory)
                if len(results) >= top_k:
                    break

        return results

    async def get_recent(self, n: int = 10) -> List[Memory]:
        """获取最近 N 条记忆"""
        memory_ids = self.redis_client.zrevrange(
            f"{self.key_prefix}:index",
            0,
            n - 1
        )

        memories = []
        for mid in memory_ids:
            memory = await self.get(mid)
            if memory:
                memories.append(memory)

        return memories

    async def update_importance(self, memory_id: str, importance: float):
        """更新重要性"""
        memory = await self.get(memory_id)
        if memory:
            memory.importance = importance
            key = f"{self.key_prefix}:{memory_id}"
            self.redis_client.setex(key, 3600, memory.model_dump_json())

    async def forget(self, memory_id: str):
        """遗忘（删除）"""
        key = f"{self.key_prefix}:{memory_id}"
        self.redis_client.delete(key)
        self.redis_client.zrem(f"{self.key_prefix}:index", memory_id)
