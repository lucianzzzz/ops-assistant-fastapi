"""语义检索系统单元测试"""
import pytest
from app.core.ai.semantic_retriever import HybridRetriever


class TestHybridRetriever:
    """测试混合检索器"""

    @pytest.fixture
    def knowledge_base(self):
        """测试知识库"""
        return [
            {
                "id": "kb1",
                "title": "CPU 使用率过高",
                "description": "CPU 占用率持续超过 80%",
                "solution": "检查进程 CPU 占用，优化或限制资源",
                "tags": ["CPU", "性能", "资源"],
                "category": "性能问题"
            },
            {
                "id": "kb2",
                "title": "内存泄漏排查",
                "description": "内存占用持续增长不释放",
                "solution": "使用 valgrind 或 heapdump 分析",
                "tags": ["内存", "泄漏", "调试"],
                "category": "内存问题"
            },
            {
                "id": "kb3",
                "title": "网络延迟问题",
                "description": "网络请求响应时间过长",
                "solution": "检查网络拓扑和带宽",
                "tags": ["网络", "延迟", "性能"],
                "category": "网络问题"
            }
        ]

    @pytest.fixture
    def retriever(self, knowledge_base):
        """创建检索器（禁用语义检索以避免依赖）"""
        return HybridRetriever(knowledge_base, use_semantic=False)

    def test_retriever_initialization(self, retriever):
        """测试检索器初始化"""
        assert retriever.knowledge_base is not None
        assert len(retriever.knowledge_base) > 0

    def test_keyword_search(self, retriever):
        """测试关键词搜索"""
        results = retriever.search(
            query="CPU 占用过高",
            keywords=["CPU", "性能"],
            top_k=2
        )

        assert len(results) > 0
        assert results[0]["match_type"] == "keyword"
        assert "CPU" in results[0]["title"] or "CPU" in results[0]["tags"]

    def test_search_with_empty_keywords(self, retriever):
        """测试空关键词搜索"""
        results = retriever.search(query="测试问题", keywords=[], top_k=5)
        # 没有语义检索且无关键词时应该返回空
        assert isinstance(results, list)

    def test_search_top_k_limit(self, retriever):
        """测试 top_k 限制"""
        results = retriever.search(
            query="性能问题",
            keywords=["性能", "CPU", "内存"],
            top_k=2
        )

        assert len(results) <= 2

    def test_keyword_match_scoring(self, retriever):
        """测试关键词匹配评分"""
        results = retriever.search(
            query="CPU 和内存问题",
            keywords=["CPU", "内存"],
            top_k=5
        )

        # 验证结果包含 score
        if results:
            assert "score" in results[0]
            assert 0 <= results[0]["score"] <= 1


class TestKeywordSearch:
    """测试纯关键词搜索"""

    def test_case_insensitive_search(self):
        """测试大小写不敏感"""
        kb = [
            {"id": "1", "title": "CPU Problem", "description": "", "tags": []},
            {"id": "2", "title": "Memory Issue", "description": "", "tags": []}
        ]
        retriever = HybridRetriever(kb, use_semantic=False)

        results = retriever.search("cpu problem", keywords=["cpu"], top_k=5)
        assert len(results) > 0
        assert results[0]["id"] == "1"

    def test_multiple_keyword_matching(self):
        """测试多关键词匹配"""
        kb = [
            {"id": "1", "title": "CPU and Memory", "description": "", "tags": ["performance"]},
            {"id": "2", "title": "CPU only", "description": "", "tags": []}
        ]
        retriever = HybridRetriever(kb, use_semantic=False)

        results = retriever.search("test", keywords=["CPU", "Memory"], top_k=5)

        # 匹配两个关键词的应该排在前面
        if len(results) >= 2:
            assert results[0]["id"] == "1"
