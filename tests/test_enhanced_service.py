"""测试增强版 Service - 向量检索和 RAG"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.enhanced_service import EnhancedOpsAssistantService
from app.core.ai.vector_retriever import VectorRetriever
from app.core.ai.rag_assistant import RAGAssistant
from app.core.models.base import KnowledgeItem


@pytest.fixture
def mock_repository():
    """Mock 数据仓库"""
    repo = Mock(spec=InMemoryRepository)

    # Mock 知识库数据
    repo.list_knowledge.return_value = [
        KnowledgeItem(
            id=1,
            question="CPU 占用率过高",
            reason="进程占用过多资源",
            method="检查进程列表；重启异常进程",
            sort="性能问题",
            province="全部"
        ),
        KnowledgeItem(
            id=2,
            question="磁盘空间不足",
            reason="日志文件过大",
            method="清理日志文件；扩容磁盘",
            sort="存储问题",
            province="全部"
        ),
    ]

    # Mock 指标数据
    repo.list_metrics.return_value = []

    # Mock 标签数据
    repo.list_public_tags.return_value = []

    return repo


@pytest.fixture
def mock_vector_retriever():
    """Mock 向量检索器"""
    retriever = Mock(spec=VectorRetriever)
    retriever.load_existing.return_value = False
    retriever.initialize_from_knowledge = Mock()
    retriever.search.return_value = [
        {
            "id": 1,
            "question": "CPU 占用率过高",
            "reason": "进程占用过多资源",
            "method": "检查进程列表；重启异常进程",
            "sort": "性能问题",
            "province": "全部",
            "score": 0.85
        }
    ]
    return retriever


@pytest.fixture
def mock_rag_assistant():
    """Mock RAG 助手"""
    assistant = Mock(spec=RAGAssistant)
    assistant.enabled = True
    assistant.ask_with_context = AsyncMock(return_value={
        "enabled": True,
        "response": "**可能原因：**\n- 进程占用过多\n\n**排查步骤：**\n1. 检查进程\n2. 重启服务\n\n**后续动作：**\n- 监控资源",
        "parsed": {
            "possible_reason": ["进程占用过多"],
            "suggested_steps": ["检查进程", "重启服务"],
            "next_actions": ["监控资源"],
            "confidence": "high"
        }
    })
    return assistant


def test_service_initialization_with_vector_search(mock_repository, mock_vector_retriever):
    """测试启用向量搜索的服务初始化"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        vector_retriever=mock_vector_retriever,
        use_vector_search=True,
        action_generator=None
    )

    assert service.use_vector_search is True
    assert service.vector_retriever is mock_vector_retriever
    mock_vector_retriever.load_existing.assert_called_once()


def test_service_initialization_without_vector_search(mock_repository):
    """测试禁用向量搜索的服务初始化"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        use_vector_search=False,
        action_generator=None
    )

    assert service.use_vector_search is False
    assert service.vector_retriever is None


def test_ask_with_vector_search(mock_repository, mock_vector_retriever):
    """测试使用向量搜索的查询"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        vector_retriever=mock_vector_retriever,
        use_vector_search=True,
        action_generator=None
    )

    result = service.ask("CPU 占用率过高怎么办？", top_k=3)

    assert result["question"] == "CPU 占用率过高怎么办？"
    assert result["retrieval_method"] == "vector"
    assert len(result["matched_knowledge"]) > 0
    assert result["matched_knowledge"][0]["score"] == 0.85

    # 验证向量搜索被调用
    mock_vector_retriever.search.assert_called_once()


def test_ask_with_string_search(mock_repository):
    """测试使用字符串匹配的查询"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        use_vector_search=False,
        action_generator=None
    )

    result = service.ask("CPU 占用率过高怎么办？", top_k=3)

    assert result["question"] == "CPU 占用率过高怎么办？"
    assert result["retrieval_method"] == "string"


@pytest.mark.asyncio
async def test_ask_with_ai_enhancement(
    mock_repository,
    mock_vector_retriever,
    mock_rag_assistant
):
    """测试 RAG AI 增强查询"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        vector_retriever=mock_vector_retriever,
        rag_assistant=mock_rag_assistant,
        use_vector_search=True,
        action_generator=None
    )

    # Mock 低置信度场景
    mock_vector_retriever.search.return_value = [
        {
            "id": 1,
            "question": "相关问题",
            "reason": "某个原因",
            "method": "某个方法",
            "sort": "分类",
            "province": "全部",
            "score": 0.3  # 低置信度
        }
    ]

    result = await service.ask_with_ai("一个不常见的问题", top_k=3)

    # 验证触发了 AI 增强
    assert result["ai_fallback"]["used"] is True
    assert result["ai_fallback"]["with_context"] is True

    # 验证 RAG 助手被调用，并传入了上下文
    mock_rag_assistant.ask_with_context.assert_called_once()
    call_args = mock_rag_assistant.ask_with_context.call_args
    assert call_args[1]["question"] == "一个不常见的问题"
    assert len(call_args[1]["context"]) > 0


@pytest.mark.asyncio
async def test_ask_without_ai_when_confidence_high(
    mock_repository,
    mock_vector_retriever,
    mock_rag_assistant
):
    """测试高置信度时不触发 AI"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        vector_retriever=mock_vector_retriever,
        rag_assistant=mock_rag_assistant,
        use_vector_search=True,
        action_generator=None
    )

    # Mock 高置信度场景
    mock_vector_retriever.search.return_value = [
        {
            "id": 1,
            "question": "CPU 占用率过高",
            "reason": "进程占用过多",
            "method": "检查进程",
            "sort": "性能",
            "province": "全部",
            "score": 0.95  # 高置信度
        }
    ]

    result = await service.ask_with_ai("CPU 占用率过高", top_k=3)

    # 验证没有触发 AI 增强
    ai_fallback = result.get("ai_fallback")
    assert ai_fallback is None or not ai_fallback.get("used")

    # 验证 RAG 助手未被调用
    mock_rag_assistant.ask_with_context.assert_not_called()


def test_extract_keywords(mock_repository):
    """测试关键词提取"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        use_vector_search=False,
        action_generator=None
    )

    keywords = service.extract_keywords("cpu占用率过高怎么办？")

    # 关键词提取后应该包含主要词汇
    assert len(keywords) > 0
    # 检查是否包含关键词（不区分大小写）
    keywords_lower = [k.lower() for k in keywords]
    assert "cpu" in keywords_lower or any("占用" in k for k in keywords) or any("过高" in k for k in keywords)
    assert "怎么办" not in keywords  # 停用词应被过滤


def test_build_confidence(mock_repository):
    """测试置信度计算"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        use_vector_search=False,
        action_generator=None
    )

    knowledge_matches = [{"score": 0.8}]
    metric_matches = [{"score": 0.6}]

    confidence = service.build_confidence(knowledge_matches, metric_matches)

    assert confidence == 0.7  # (0.8 + 0.6) / 2


def test_build_confidence_empty(mock_repository):
    """测试空结果的置信度"""
    service = EnhancedOpsAssistantService(
        repository=mock_repository,
        use_vector_search=False,
        action_generator=None
    )

    confidence = service.build_confidence([], [])

    assert confidence == 0.0
