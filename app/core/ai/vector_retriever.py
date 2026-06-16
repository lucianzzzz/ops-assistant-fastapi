"""向量检索模块 - 使用 ChromaDB + Embeddings 替代字符串相似度"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from app.core.models.base import KnowledgeItem
from app.core.common.logging import get_logger

logger = get_logger(__name__)


class VectorRetriever:
    """向量检索器 - 用于知识库的语义搜索"""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """
        初始化向量检索器

        Args:
            persist_directory: 向量数据库持久化目录，默认为 .chroma_db
            embedding_model: 嵌入模型名称，默认使用多语言小模型
        """
        self.persist_directory = persist_directory or str(
            Path(__file__).parent.parent.parent.parent / ".chroma_db"
        )

        # 初始化 Embedding 模型（支持中文）
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        self.vectorstore: Optional[Chroma] = None
        self._initialized = False

    def initialize_from_knowledge(self, knowledge_items: List[KnowledgeItem]) -> None:
        """
        从知识库条目初始化向量数据库

        Args:
            knowledge_items: 知识库条目列表
        """
        if not knowledge_items:
            logger.warning("No knowledge items provided, skipping vector initialization")
            return

        # 转换为 LangChain Document 格式
        documents = []
        for item in knowledge_items:
            # 组合文本：问题 + 原因 + 方法
            content_parts = [item.question]
            if item.reason:
                content_parts.append(f"原因: {item.reason}")
            if item.method:
                content_parts.append(f"方法: {item.method}")

            content = "\n".join(content_parts)

            # 元数据
            metadata = {
                "id": item.id,
                "question": item.question,
                "reason": item.reason or "",
                "method": item.method or "",
                "sort": item.sort,
                "province": item.province,
            }

            documents.append(Document(page_content=content, metadata=metadata))

        logger.info(f"Creating vector store with {len(documents)} documents")

        # 创建向量数据库
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
        )

        self._initialized = True
        logger.info(f"Vector store initialized and persisted to {self.persist_directory}")

    def load_existing(self) -> bool:
        """
        加载已存在的向量数据库

        Returns:
            是否成功加载
        """
        if not os.path.exists(self.persist_directory):
            logger.info("No existing vector store found")
            return False

        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
            )
            self._initialized = True
            logger.info(f"Loaded existing vector store from {self.persist_directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 3,
        province_filter: Optional[str] = None,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        语义搜索知识库

        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            province_filter: 省份过滤（可选）
            score_threshold: 相似度阈值（0-1，越高越严格）

        Returns:
            匹配的知识库条目列表，包含 score
        """
        if not self._initialized or self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []

        try:
            # 构建过滤器
            filter_dict = None
            if province_filter:
                # ChromaDB 的过滤语法
                filter_dict = {
                    "$or": [
                        {"province": {"$eq": province_filter}},
                        {"province": {"$eq": ""}},
                        {"province": {"$eq": "全部"}}
                    ]
                }

            # 执行相似度搜索
            results = self.vectorstore.similarity_search_with_relevance_scores(
                query=query,
                k=top_k * 2,  # 多取一些，过滤后可能不足
                filter=filter_dict
            )

            # 转换为统一格式，过滤低分结果
            matches = []
            for doc, score in results:
                # ChromaDB 的 score 是余弦相似度（越大越相似）
                # 需要根据阈值过滤
                if score < score_threshold:
                    continue

                matches.append({
                    "id": doc.metadata["id"],
                    "question": doc.metadata["question"],
                    "reason": doc.metadata["reason"],
                    "method": doc.metadata["method"],
                    "sort": doc.metadata["sort"],
                    "province": doc.metadata["province"],
                    "score": round(score, 4)
                })

            # 限制返回数量
            matches = matches[:top_k]

            logger.info(f"Found {len(matches)} matches for query: {query[:50]}")
            return matches

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def rebuild(self, knowledge_items: List[KnowledgeItem]) -> None:
        """
        重新构建向量数据库（清空后重建）

        Args:
            knowledge_items: 新的知识库条目列表
        """
        # 清空现有数据
        if self.vectorstore is not None:
            try:
                self.vectorstore.delete_collection()
                logger.info("Deleted existing collection")
            except Exception as e:
                logger.warning(f"Failed to delete collection: {e}")

        # 重新初始化
        self.initialize_from_knowledge(knowledge_items)
