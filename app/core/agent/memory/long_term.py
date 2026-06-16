"""长期记忆实现（简化版，用列表模拟向量库）"""
from typing import List, Optional
from app.core.agent.memory.base import Memory, MemoryStore, MemoryType


class SimpleLongTermMemory(MemoryStore):
    """长期记忆（简单实现，列表存储）"""

    def __init__(self):
        self.storage: List[Memory] = []

    async def add(self, memory: Memory) -> str:
        """添加记忆"""
        self.storage.append(memory)
        return memory.memory_id

    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        for memory in self.storage:
            if memory.memory_id == memory_id:
                memory.access_count += 1
                return memory
        return None

    async def search(self, query: str, top_k: int = 5) -> List[Memory]:
        """搜索相关记忆（简单实现：全文匹配 + 重要性排序）"""
        results = []
        for memory in self.storage:
            if query.lower() in memory.content.lower():
                results.append(memory)

        # 按重要性排序
        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:top_k]

    async def update_importance(self, memory_id: str, importance: float):
        """更新重要性"""
        memory = await self.get(memory_id)
        if memory:
            memory.importance = importance

    async def forget(self, memory_id: str):
        """遗忘（删除）"""
        self.storage = [m for m in self.storage if m.memory_id != memory_id]


# 真实 ChromaDB 实现（可选，需要 chromadb 库）
class VectorLongTermMemory(MemoryStore):
    """长期记忆（向量数据库实现）"""

    def __init__(self, collection_name: str = "agent_long_term_memory"):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("需要安装: pip install chromadb sentence-transformers")

        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def add(self, memory: Memory) -> str:
        """添加到向量库"""
        # 生成 embedding
        embedding = self.embedding_model.encode(memory.content)

        # 存储
        self.collection.add(
            embeddings=[embedding.tolist()],
            documents=[memory.content],
            ids=[memory.memory_id],
            metadatas=[{
                "type": memory.memory_type,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
                **memory.metadata
            }]
        )

        return memory.memory_id

    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        try:
            result = self.collection.get(ids=[memory_id])
            if result['ids']:
                metadata = result['metadatas'][0]
                return Memory(
                    memory_id=memory_id,
                    memory_type=MemoryType(metadata['type']),
                    content=result['documents'][0],
                    importance=metadata['importance'],
                    created_at=metadata['created_at'],
                    metadata=metadata
                )
        except Exception as e:
            logger.error(f"Failed to get memory by id {memory_id}: {e}")
        return None

    async def search(self, query: str, top_k: int = 5) -> List[Memory]:
        """语义检索"""
        query_embedding = self.embedding_model.encode(query)

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )

        memories = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            memory = Memory(
                memory_id=results['ids'][0][i],
                memory_type=MemoryType(metadata['type']),
                content=doc,
                importance=metadata['importance'],
                created_at=metadata['created_at'],
                metadata=metadata
            )
            memories.append(memory)

        return memories

    async def update_importance(self, memory_id: str, importance: float):
        """更新重要性"""
        # ChromaDB 不支持直接更新，需要先删除再添加
        pass

    async def forget(self, memory_id: str):
        """遗忘（删除）"""
        self.collection.delete(ids=[memory_id])
