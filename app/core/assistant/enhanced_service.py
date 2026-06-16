"""增强版 Service - 集成向量检索和真正的 RAG"""
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Optional, List, Dict

from app.core.models.base import KnowledgeItem
from app.core.assistant.repository import InMemoryRepository
from app.core.ai.vector_retriever import VectorRetriever
from app.core.ai.rag_assistant import RAGAssistant
from app.core.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeMatch:
    id: int
    question: str
    reason: str
    method: str
    sort: str
    province: str
    score: float


@dataclass
class MetricMatch:
    metric: str
    name: str
    measurement: str
    field_name: str
    desc: str
    unit: str
    score: float


class EnhancedOpsAssistantService:
    """增强版运维助手服务 - 支持向量检索和真正的 RAG"""

    stop_words = {
        "怎么处理", "怎么办", "怎么排查", "如何处理", "如何排查",
        "异常", "指标", "告警", "为什么", "怎么", "如何",
    }

    def __init__(
        self,
        repository: InMemoryRepository,
        rag_assistant: Optional[RAGAssistant] = None,
        vector_retriever: Optional[VectorRetriever] = None,
        action_generator=None,
        use_vector_search: bool = True
    ):
        """
        初始化增强版服务

        Args:
            repository: 数据仓库
            rag_assistant: RAG 助手
            vector_retriever: 向量检索器
            action_generator: 动作生成器
            use_vector_search: 是否使用向量搜索（False 则退回字符串匹配）
        """
        self.repository = repository
        self.rag_assistant = rag_assistant or RAGAssistant(use_structured_output=True)
        self.use_vector_search = use_vector_search

        # 初始化向量检索器
        if use_vector_search:
            self.vector_retriever = vector_retriever or VectorRetriever()

            # 尝试加载已存在的向量库，如果不存在则创建
            if not self.vector_retriever.load_existing():
                logger.info("Initializing vector store from knowledge base...")
                knowledge_items = self.repository.list_knowledge()
                self.vector_retriever.initialize_from_knowledge(knowledge_items)
        else:
            self.vector_retriever = None
            logger.info("Vector search disabled, using string similarity")

        # 动作生成器（可选）
        if action_generator is None:
            try:
                from app.core.agent.action_generator import ActionGenerator
                # 传统 AIAssistant（用于动作生成）
                from app.core.ai.ai_assistant import AIAssistant
                action_generator = ActionGenerator(AIAssistant())
            except ImportError:
                logger.warning("ActionGenerator not available")
                action_generator = None

        self.action_generator = action_generator

        # 性能优化缓存（仅用于字符串匹配模式）
        self._normalized_knowledge_cache = {}
        self._normalized_metrics_cache = {}
        if not use_vector_search:
            self._preprocess_data()

    def _preprocess_data(self):
        """预处理数据以加速查询（仅字符串匹配模式）"""
        for item in self.repository.list_knowledge():
            self._normalized_knowledge_cache[item.id] = self.normalize(item.question)

        for item in self.repository.list_metrics():
            key = item.metric or item.name
            self._normalized_metrics_cache[key] = {
                'name': self.normalize(item.name),
                'metric': self.normalize(item.metric or ""),
                'field': self.normalize(item.field_name),
                'desc': self.normalize(item.desc or "")
            }

    def ask(self, question: str, province: str = "", top_k: int = 3) -> Dict[str, Any]:
        """
        同步查询（不使用 AI 增强）

        Args:
            question: 用户问题
            province: 省份过滤
            top_k: 返回的最大结果数

        Returns:
            查询结果字典
        """
        normalized_question = self.normalize(question)
        keywords = self.extract_keywords(normalized_question)

        # 使用向量搜索或字符串匹配
        if self.use_vector_search and self.vector_retriever:
            knowledge_matches = self._vector_match_knowledge(question, province, top_k)
        else:
            knowledge_matches = self._string_match_knowledge(normalized_question, province, top_k)

        # 指标匹配（保留字符串方式，因为数据量小）
        metric_matches = self.match_metrics(normalized_question, keywords, top_k)

        # 构建结果
        confidence = self.build_confidence(knowledge_matches, metric_matches)
        use_ai_fallback = confidence < 0.5 and self.rag_assistant.enabled

        result = {
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
            "reasoning_steps": [],
            "retrieval_method": "vector" if self.use_vector_search else "string"
        }

        # 生成可执行动作
        if self.action_generator and (keywords or metric_matches):
            try:
                metric_name = metric_matches[0]["name"] if metric_matches else ""
                actions = self.action_generator.generate_from_keywords(keywords, metric_name)
                result["executable_actions"] = [action.model_dump() for action in actions]
            except Exception as e:
                logger.warning(f"Failed to generate actions: {e}")
                result["executable_actions"] = []

        # 添加推理步骤（仅当使用AI时）
        if use_ai_fallback:
            result["reasoning_steps"] = [
                {
                    "iteration": 1,
                    "thought": f"分析问题：{normalized_question}，识别关键词：{', '.join(keywords[:3])}",
                    "thought_type": "analyze",
                    "action": f"{'向量' if self.use_vector_search else '字符串'}检索知识库",
                    "action_type": "query_knowledge",
                    "observation": f"找到 {len(knowledge_matches)} 条相关知识，匹配度 {confidence:.2%}"
                },
                {
                    "iteration": 2,
                    "thought": "本地知识库匹配度不足，调用 RAG AI 增强",
                    "thought_type": "decide",
                    "action": "RAG 增强查询（基于检索上下文）",
                    "action_type": "rag_query",
                    "observation": "AI 调用中..."
                }
            ]

            result["ai_fallback"] = {
                "enabled": True,
                "confidence_too_low": True,
                "message": "本地知识库匹配度较低，正在使用 RAG AI 增强查询..."
            }

        if not result["matched_knowledge"] and not result["related_objects"]["metrics"]:
            result["fallback_questions"] = self.build_fallback_questions(question, top_k)

        return result

    def _vector_match_knowledge(
        self,
        question: str,
        province: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用向量搜索匹配知识库"""
        return self.vector_retriever.search(
            query=question,
            top_k=top_k,
            province_filter=province if province else None,
            score_threshold=0.3
        )

    def _string_match_knowledge(
        self,
        normalized_question: str,
        province: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用字符串相似度匹配知识库（兼容旧版）"""
        from difflib import SequenceMatcher

        queryset = self.repository.list_knowledge()
        if province:
            queryset = [item for item in queryset if item.province in {province, "", "全部"}]

        matches: List[KnowledgeMatch] = []
        for item in queryset[:500]:
            target = self._normalized_knowledge_cache.get(item.id) or self.normalize(item.question)
            score = SequenceMatcher(None, normalized_question, target).ratio()

            if normalized_question and normalized_question in target:
                score = max(score, 0.95)
            if score < 0.35:
                continue

            matches.append(
                KnowledgeMatch(
                    id=item.id,
                    question=item.question,
                    reason=item.reason,
                    method=item.method,
                    sort=item.sort,
                    province=item.province,
                    score=round(score, 4),
                )
            )

        matches.sort(key=lambda item: item.score, reverse=True)
        return [asdict(item) for item in matches[:top_k]]

    async def ask_with_ai(self, question: str, province: str = "", top_k: int = 3) -> Dict[str, Any]:
        """
        带 RAG AI 增强的异步查询

        Args:
            question: 用户问题
            province: 省份过滤
            top_k: 返回的最大结果数

        Returns:
            查询结果字典
        """
        try:
            result = self.ask(question, province, top_k)
        except Exception as e:
            logger.error(f"Error in ask(): {e}", exc_info=True)
            return self._build_empty_result(question)

        if not result:
            return self._build_empty_result(question)

        # 如果需要 RAG AI 增强
        ai_fallback = result.get("ai_fallback") or {}
        if ai_fallback.get("enabled"):
            # 关键改进：把检索结果作为上下文传给 LLM
            context = result["matched_knowledge"][:3]  # 取前 3 条

            ai_result = await self.rag_assistant.ask_with_context(
                question=question,
                context=context
            )

            # 合并 AI 结果
            if ai_result.get("parsed"):
                parsed = ai_result["parsed"]
                # 将 AI 的结果追加到现有结果中
                result["possible_reason"].extend(parsed.get("possible_reason", []))
                result["suggested_steps"].extend(parsed.get("suggested_steps", []))
                result["next_actions"].extend(parsed.get("next_actions", []))

                # 如果有置信度评估，记录下来
                if "confidence" in parsed:
                    result["ai_confidence"] = parsed["confidence"]

            result["ai_fallback"] = {
                "enabled": True,
                "used": True,
                "raw_response": ai_result.get("response"),
                "error": ai_result.get("error"),
                "with_context": len(context) > 0
            }

        return result

    # === 以下方法与原 Service 相同 ===

    def normalize(self, question: str) -> str:
        return re.sub(r"\s+", "", question).strip().lower()

    def extract_keywords(self, question: str) -> List[str]:
        tokens = re.split(r"[^0-9a-zA-Z一-鿿]+", question)
        keywords = []
        for token in tokens:
            token = token.strip()
            if len(token) < 2 or token in self.stop_words:
                continue
            keywords.append(token)
        return list(dict.fromkeys(keywords))

    def match_metrics(self, question: str, keywords: List[str], top_k: int) -> List[Dict[str, Any]]:
        from difflib import SequenceMatcher

        matches: List[MetricMatch] = []
        for item in self.repository.list_metrics()[:500]:
            key = item.metric or item.name
            cached = self._normalized_metrics_cache.get(key)
            if cached:
                candidates = [cached['name'], cached['metric'], cached['field'], cached['desc']]
            else:
                candidates = [
                    self.normalize(item.name),
                    self.normalize(item.metric or ""),
                    self.normalize(item.field_name),
                    self.normalize(item.desc or ""),
                ]

            score = max(SequenceMatcher(None, question, candidate).ratio() for candidate in candidates if candidate)
            keyword_hits = sum(1 for keyword in keywords if any(keyword in candidate for candidate in candidates if candidate))
            if keyword_hits:
                score = max(score, min(0.9, 0.45 + keyword_hits * 0.15))
            if score < 0.3:
                continue

            matches.append(
                MetricMatch(
                    metric=item.metric,
                    name=item.name,
                    measurement=item.measurement,
                    field_name=item.field_name,
                    desc=item.desc or "",
                    unit=item.unit or "",
                    score=round(score, 4),
                )
            )

        matches.sort(key=lambda item: item.score, reverse=True)
        return [asdict(item) for item in matches[:top_k]]

    def build_possible_reasons(self, knowledge_matches: List[Dict[str, Any]], metric_matches: List[Dict[str, Any]]) -> List[str]:
        reasons = [item["reason"] for item in knowledge_matches if item.get("reason")]
        if not reasons and metric_matches:
            metric = metric_matches[0]
            reasons.append(f"指标 {metric['name']} 出现异常，建议先确认 {metric['measurement']} 分区下 {metric['field_name']} 的采集与计算口径是否正确。")
            if metric.get("desc"):
                reasons.append(f"指标说明：{metric['desc']}")
        return reasons

    def build_suggested_steps(self, knowledge_matches: List[Dict[str, Any]], metric_matches: List[Dict[str, Any]]) -> List[str]:
        steps: List[str] = []
        for item in knowledge_matches:
            method = item.get("method", "")
            if not method:
                continue
            parts = re.split(r"[\n；;。]", method)
            steps.extend([part.strip() for part in parts if part.strip()])
        if not steps and metric_matches:
            metric = metric_matches[0]
            steps = [
                f"确认指标 {metric['name']} 的采集周期、计算表达式和展示口径是否一致。",
                f"检查 measurement={metric['measurement']}、field={metric['field_name']} 的原始数据是否连续。",
                "结合最近告警、巡检结果和设备运行状态进行交叉排查。",
            ]
        return steps[:6]

    def build_related_objects(self, metric_matches: List[Dict[str, Any]], keywords: List[str]) -> Dict[str, Any]:
        public_tags = [
            item.model_dump()
            for item in self.repository.list_public_tags()
            if item.name in keywords[:10]
        ][:10]
        return {
            "metrics": metric_matches,
            "public_tags": public_tags,
        }

    def build_confidence(self, knowledge_matches: List[Dict[str, Any]], metric_matches: List[Dict[str, Any]]) -> float:
        scores = []
        if knowledge_matches:
            scores.append(knowledge_matches[0]["score"])
        if metric_matches:
            scores.append(metric_matches[0]["score"])
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    def build_next_actions(self, metric_matches: List[Dict[str, Any]]) -> List[str]:
        if not metric_matches:
            return ["补充更具体的指标名、模块名或告警信息后重新提问。"]
        metric = metric_matches[0]
        return [
            f"查看指标 {metric['name']} 的最近趋势与关联告警。",
            f"人工核对 {metric['measurement']}.{metric['field_name']} 的采集来源和字段口径。",
            "如需进一步自动化排查，可在下一阶段接入 Agent 执行能力。",
        ]

    def build_fallback_questions(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        normalized_question = self.normalize(question)
        fallback_items = []
        for item in self.repository.list_knowledge():
            haystack = self.normalize(f"{item.question}{item.reason}{item.method}")
            if normalized_question and normalized_question in haystack:
                fallback_items.append({"id": item.id, "question": item.question})
        return fallback_items[:top_k]

    def _build_empty_result(self, question: str, error_message: str = "查询出错，请稍后重试") -> Dict[str, Any]:
        """构建空结果"""
        return {
            "question": question,
            "normalized_question": question,
            "normalized_metric": "",
            "keywords": [],
            "matched_knowledge": [],
            "possible_reason": [error_message],
            "suggested_steps": [],
            "related_objects": {"metrics": [], "public_tags": []},
            "confidence": 0.0,
            "next_actions": [],
            "fallback_questions": [],
            "ai_fallback": None,
            "executable_actions": [],
        }
