"""语义检索系统 - 基于向量的知识检索"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


class SemanticRetriever:
    """语义检索器 - 使用 Sentence Transformers + ChromaDB"""

    def __init__(self, collection_name: str = "ops_knowledge", model_name: str = "all-MiniLM-L6-v2"):
        if not SEMANTIC_AVAILABLE:
            raise ImportError("请安装 sentence-transformers 和 chromadb: pip install sentence-transformers chromadb")

        self.model_name = model_name
        self.collection_name = collection_name
        self.model: Optional[SentenceTransformer] = None
        self.client: Optional[chromadb.Client] = None
        self.collection = None
        self._initialized = False

    def initialize(self, persist_directory: str = "./data/chroma_db"):
        """初始化模型和向量数据库"""
        if self._initialized:
            return

        # 初始化 Embedding 模型
        self.model = SentenceTransformer(self.model_name)

        # 初始化 ChromaDB
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "运维知识库"}
        )

        self._initialized = True

    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """添加文档到向量库"""
        if not self._initialized:
            self.initialize()

        if not documents:
            return 0

        # 提取文本和元数据
        texts = [doc.get("text", "") for doc in documents]
        ids = [doc.get("id", f"doc_{i}") for i, doc in enumerate(documents)]
        metadatas = [
            {
                "title": doc.get("title", ""),
                "category": doc.get("category", ""),
                "tags": ",".join(doc.get("tags", [])),
            }
            for doc in documents
        ]

        # 生成 embeddings
        embeddings = self.model.encode(texts).tolist()

        # 添加到 ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        return len(documents)

    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """语义搜索"""
        if not self._initialized:
            self.initialize()

        # 生成查询向量
        query_embedding = self.model.encode(query).tolist()

        # 查询向量库
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )

        # 格式化结果
        retrieved = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                retrieved.append({
                    "id": results["ids"][0][i],
                    "text": doc,
                    "distance": results["distances"][0][i] if "distances" in results else 0.0,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                })

        return retrieved

    def clear_collection(self):
        """清空集合"""
        if self._initialized and self.client:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "运维知识库"}
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._initialized:
            return {"initialized": False}

        count = self.collection.count() if self.collection else 0
        return {
            "initialized": True,
            "model": self.model_name,
            "collection": self.collection_name,
            "document_count": count
        }


class HybridRetriever:
    """混合检索器 - 结合关键词匹配和语义检索"""

    def __init__(self, knowledge_base: List[Dict[str, Any]], use_semantic: bool = True):
        self.knowledge_base = knowledge_base
        self.use_semantic = use_semantic and SEMANTIC_AVAILABLE
        self.semantic_retriever: Optional[SemanticRetriever] = None

        if self.use_semantic:
            self.semantic_retriever = SemanticRetriever()
            self._index_knowledge_base()

    def _index_knowledge_base(self):
        """索引知识库"""
        if not self.semantic_retriever:
            return

        try:
            self.semantic_retriever.initialize()
            documents = [
                {
                    "id": kb.get("id", f"kb_{i}"),
                    "text": f"{kb.get('title', '')} {kb.get('description', '')} {kb.get('solution', '')}",
                    "title": kb.get("title", ""),
                    "category": kb.get("category", ""),
                    "tags": kb.get("tags", [])
                }
                for i, kb in enumerate(self.knowledge_base)
            ]
            self.semantic_retriever.add_documents(documents)
        except Exception as e:
            print(f"语义检索初始化失败，回退到关键词匹配: {e}")
            self.use_semantic = False

    def search(self, query: str, keywords: List[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """混合搜索"""
        results = []

        # 语义检索
        if self.use_semantic and self.semantic_retriever:
            try:
                semantic_results = self.semantic_retriever.search(query, top_k=top_k)
                for result in semantic_results:
                    kb_id = result["id"]
                    matching_kb = next((kb for kb in self.knowledge_base if kb.get("id") == kb_id), None)
                    if matching_kb:
                        results.append({
                            **matching_kb,
                            "score": 1.0 - result["distance"],
                            "match_type": "semantic"
                        })
            except Exception as e:
                print(f"语义检索失败: {e}")

        # 关键词匹配（补充）
        if keywords and len(results) < top_k:
            keyword_results = self._keyword_search(keywords)
            for kb in keyword_results:
                if not any(r.get("id") == kb.get("id") for r in results):
                    results.append({**kb, "match_type": "keyword"})
                if len(results) >= top_k:
                    break

        return results[:top_k]

    def _keyword_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """关键词匹配搜索"""
        results = []
        for kb in self.knowledge_base:
            title = kb.get("title", "").lower()
            desc = kb.get("description", "").lower()
            tags = [t.lower() for t in kb.get("tags", [])]

            match_count = sum(1 for kw in keywords if kw.lower() in title or kw.lower() in desc or kw.lower() in " ".join(tags))

            if match_count > 0:
                results.append({
                    **kb,
                    "score": match_count / len(keywords),
                    "match_type": "keyword"
                })

        return sorted(results, key=lambda x: x["score"], reverse=True)
