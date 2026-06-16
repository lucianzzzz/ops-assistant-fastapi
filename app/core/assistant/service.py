import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Optional

from app.core.models.base import KnowledgeItem, MetricItem, PublicTagItem
from app.core.assistant.repository import InMemoryRepository
from app.core.ai.ai_assistant import AIAssistant
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


class OpsAssistantService:
    stop_words = {
        "怎么处理",
        "怎么办",
        "怎么排查",
        "如何处理",
        "如何排查",
        "异常",
        "指标",
        "告警",
        "为什么",
        "怎么",
        "如何",
    }

    def __init__(
        self,
        repository: InMemoryRepository,
        ai_assistant: Optional[AIAssistant] = None,
        action_generator=None
    ):
        self.repository = repository
        self.ai_assistant = ai_assistant or AIAssistant()

        if action_generator is None:
            from app.core.agent.action_generator import ActionGenerator
            action_generator = ActionGenerator(self.ai_assistant)

        self.action_generator = action_generator

        # 性能优化：预处理和缓存
        self._normalized_knowledge_cache = {}
        self._normalized_metrics_cache = {}
        self._preprocess_data()

    def _preprocess_data(self):
        """预处理数据以加速查询"""
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

    def ask(self, question: str, province: str = "", top_k: int = 3) -> dict[str, Any]:
        normalized_question = self.normalize(question)
        keywords = self.extract_keywords(normalized_question)
        knowledge_matches = self.match_knowledge(normalized_question, province, top_k)
        metric_matches = self.match_metrics(normalized_question, keywords, top_k)

        # 判断是否需要 AI 后备查询
        confidence = self.build_confidence(knowledge_matches, metric_matches)
        use_ai_fallback = confidence < 0.5 and self.ai_assistant.enabled

        possible_reason = self.build_possible_reasons(knowledge_matches, metric_matches)
        suggested_steps = self.build_suggested_steps(knowledge_matches, metric_matches)
        related_objects = self.build_related_objects(metric_matches, keywords)

        result = {
            "question": question,
            "normalized_question": normalized_question,
            "normalized_metric": metric_matches[0]["name"] if metric_matches else "",
            "keywords": keywords,
            "matched_knowledge": knowledge_matches,
            "possible_reason": possible_reason,
            "suggested_steps": suggested_steps,
            "related_objects": related_objects,
            "confidence": confidence,
            "next_actions": self.build_next_actions(metric_matches),
            "fallback_questions": [],
            "ai_fallback": None,  # AI 后备查询结果
            "executable_actions": [],  # 可执行动作列表
        }

        # 生成可执行动作
        try:
            if keywords or metric_matches:
                metric_name = metric_matches[0]["name"] if metric_matches else ""
                actions = self.action_generator.generate_from_keywords(keywords, metric_name)
                result["executable_actions"] = [action.model_dump() for action in actions]
        except (KeyError, AttributeError, ValueError) as e:
            # 动作生成失败不影响主流程
            logger.warning(
                "Failed to generate actions",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "keywords": keywords[:3] if keywords else [],
                    "has_metric_matches": bool(metric_matches)
                }
            )
            result["executable_actions"] = []

        # 添加推理步骤（仅当使用AI时才生成）
        if use_ai_fallback:
            result["reasoning_steps"] = [
                {
                    "iteration": 1,
                    "thought": f"分析问题：{normalized_question}，识别关键词：{', '.join(keywords[:3])}",
                    "thought_type": "analyze",
                    "action": "查询知识库",
                    "action_type": "query_knowledge",
                    "observation": f"找到 {len(knowledge_matches)} 条相关知识，匹配度 {confidence:.2%}"
                },
                {
                    "iteration": 2,
                    "thought": "本地知识库匹配度不足，调用DeepSeek AI增强",
                    "thought_type": "decide",
                    "action": "AI增强查询",
                    "action_type": "ai_fallback",
                    "observation": "DeepSeek API调用中..."
                }
            ]
        else:
            result["reasoning_steps"] = []

        if not result["matched_knowledge"] and not result["related_objects"]["metrics"]:
            result["fallback_questions"] = self.build_fallback_questions(question, top_k)

        # 如果置信度低且启用了 AI，添加 AI 查询标记
        if use_ai_fallback:
            result["ai_fallback"] = {
                "enabled": True,
                "confidence_too_low": True,
                "message": "本地知识库匹配度较低，正在使用 AI 增强查询..."
            }

        return result

    def _build_empty_result(self, question: str, error_message: str = "查询出错，请稍后重试") -> dict[str, Any]:
        """构建空结果（DRY）"""
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

    async def ask_with_ai(self, question: str, province: str = "", top_k: int = 3) -> dict[str, Any]:
        """带 AI 后备查询的异步版本"""
        try:
            result = self.ask(question, province, top_k)
        except Exception as e:
            logger.error(f"Error in ask(): {e}")
            import traceback
            traceback.print_exc()
            return self._build_empty_result(question)

        if not result:
            return self._build_empty_result(question)

        # 如果需要 AI 后备查询
        ai_fallback = result.get("ai_fallback") or {}
        if ai_fallback.get("enabled"):
            ai_result = await self.ai_assistant.ask(question)

            # 合并 AI 结果
            if ai_result.get("parsed"):
                parsed = ai_result["parsed"]
                # 将 AI 的结果追加到现有结果中
                result["possible_reason"].extend(parsed.get("possible_reason", []))
                result["suggested_steps"].extend(parsed.get("suggested_steps", []))
                result["next_actions"].extend(parsed.get("next_actions", []))

                # 注意：不修改原始置信度，保持本地知识库的真实匹配度
                # 用户可以通过 ai_fallback.used 判断是否使用了AI增强

            result["ai_fallback"] = {
                "enabled": True,
                "used": True,
                "raw_response": ai_result.get("response"),
                "error": ai_result.get("error")
            }

        return result

    def normalize(self, question: str) -> str:
        return re.sub(r"\s+", "", question).strip().lower()

    def extract_keywords(self, question: str) -> list[str]:
        tokens = re.split(r"[^0-9a-zA-Z一-鿿]+", question)
        keywords = []
        for token in tokens:
            token = token.strip()
            if len(token) < 2 or token in self.stop_words:
                continue
            keywords.append(token)
        return list(dict.fromkeys(keywords))

    def match_knowledge(self, question: str, province: str, top_k: int) -> list[dict[str, Any]]:
        queryset = self.repository.list_knowledge()
        if province:
            queryset = [item for item in queryset if item.province in {province, "", "全部"}]

        matches: list[KnowledgeMatch] = []
        for item in queryset[:500]:
            # 使用缓存的标准化文本
            target = self._normalized_knowledge_cache.get(item.id)
            if not target:
                target = self.normalize(item.question)
                self._normalized_knowledge_cache[item.id] = target

            score = self._similarity_cached(question, target)
            if question and question in target:
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

    def match_metrics(self, question: str, keywords: list[str], top_k: int) -> list[dict[str, Any]]:
        matches: list[MetricMatch] = []
        for item in self.repository.list_metrics()[:500]:
            # 使用缓存的标准化文本
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

            score = max(self._similarity_cached(question, candidate) for candidate in candidates if candidate)
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

    def build_possible_reasons(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> list[str]:
        reasons = [item["reason"] for item in knowledge_matches if item.get("reason")]
        if not reasons and metric_matches:
            metric = metric_matches[0]
            reasons.append(f"指标 {metric['name']} 出现异常，建议先确认 {metric['measurement']} 分区下 {metric['field_name']} 的采集与计算口径是否正确。")
            if metric.get("desc"):
                reasons.append(f"指标说明：{metric['desc']}")
        return reasons

    def build_suggested_steps(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> list[str]:
        steps: list[str] = []
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

    def build_related_objects(self, metric_matches: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
        public_tags = [
            item.model_dump()
            for item in self.repository.list_public_tags()
            if item.name in keywords[:10]
        ][:10]
        return {
            "metrics": metric_matches,
            "public_tags": public_tags,
        }

    def build_confidence(self, knowledge_matches: list[dict[str, Any]], metric_matches: list[dict[str, Any]]) -> float:
        scores = []
        if knowledge_matches:
            scores.append(knowledge_matches[0]["score"])
        if metric_matches:
            scores.append(metric_matches[0]["score"])
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    def build_next_actions(self, metric_matches: list[dict[str, Any]]) -> list[str]:
        if not metric_matches:
            return ["补充更具体的指标名、模块名或告警信息后重新提问。"]
        metric = metric_matches[0]
        return [
            f"查看指标 {metric['name']} 的最近趋势与关联告警。",
            f"人工核对 {metric['measurement']}.{metric['field_name']} 的采集来源和字段口径。",
            "如需进一步自动化排查，可在下一阶段接入 Agent 执行能力。",
        ]

    def build_fallback_questions(self, question: str, top_k: int) -> list[dict[str, Any]]:
        normalized_question = self.normalize(question)
        fallback_items = []
        for item in self.repository.list_knowledge():
            haystack = self.normalize(f"{item.question}{item.reason}{item.method}")
            if normalized_question and normalized_question in haystack:
                fallback_items.append({"id": item.id, "question": item.question})
        return fallback_items[:top_k]

    @lru_cache(maxsize=1024)
    def _similarity_cached(self, source: str, target: str) -> float:
        """缓存相似度计算结果"""
        return SequenceMatcher(None, source, target).ratio()
