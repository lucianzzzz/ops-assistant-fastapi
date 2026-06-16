"""Memory 系统基础类"""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"   # 短期记忆（会话内）
    LONG_TERM = "long_term"     # 长期记忆（持久化）
    EPISODIC = "episodic"       # 情景记忆（历史案例）
    SEMANTIC = "semantic"       # 语义记忆（知识）


class Memory(BaseModel):
    """记忆条目"""
    memory_id: str
    memory_type: MemoryType
    content: str
    metadata: dict = {}
    importance: float = 0.5  # 重要性 0-1
    access_count: int = 0
    created_at: datetime = datetime.now()
    last_accessed: datetime = datetime.now()


class MemoryStore(ABC):
    """记忆存储抽象"""

    @abstractmethod
    async def add(self, memory: Memory) -> str:
        """添加记忆"""
        pass

    @abstractmethod
    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Memory]:
        """搜索相关记忆"""
        pass

    @abstractmethod
    async def update_importance(self, memory_id: str, importance: float):
        """更新重要性"""
        pass

    @abstractmethod
    async def forget(self, memory_id: str):
        """遗忘（删除）"""
        pass
