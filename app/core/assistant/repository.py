import json
from pathlib import Path
from typing import Any

from app.core.common.config import DATA_DIR, KNOWLEDGE_FILE, METRICS_FILE, PUBLIC_TAGS_FILE
from app.core.models.base import DataSourceStatusResponse, KnowledgeItem, MetricItem, PublicTagItem


class InMemoryRepository:
    def __init__(self, seed_dir: Path | None = None):
        self.seed_dir = seed_dir or DATA_DIR
        self.knowledge_items = self._load_knowledge_items()
        self.metric_items = self._load_metric_items()
        self.public_tag_items = self._load_public_tag_items()

    def _load_json(self, filename: str) -> list[dict[str, Any]]:
        with (self.seed_dir / filename).open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, list):
            raise ValueError(f"{filename} 必须是 JSON 数组")
        return data

    def _load_knowledge_items(self) -> list[KnowledgeItem]:
        rows = self._load_json(KNOWLEDGE_FILE)
        items: list[KnowledgeItem] = []
        for index, item in enumerate(rows, start=1):
            normalized = {
                "id": item.get("id") or index,
                "province": item.get("province") or item.get("省份") or "",
                "question": item.get("question") or item.get("问题描述") or "",
                "sort": item.get("sort") or item.get("问题分类") or "",
                "reason": item.get("reason") or item.get("问题原因") or "",
                "method": item.get("method") or item.get("解决办法描述") or item.get("解决方法") or "",
            }
            if normalized["question"]:
                items.append(KnowledgeItem.model_validate(normalized))
        return items

    def _load_metric_items(self) -> list[MetricItem]:
        rows = self._load_json(METRICS_FILE)
        items: list[MetricItem] = []
        for item in rows:
            measurement = item.get("measurement") or item.get("存储分区") or ""
            field_name = item.get("field_name") or item.get("字段名") or ""
            normalized = {
                "metric": item.get("metric") or f"{measurement}.{field_name}".strip("."),
                "name": item.get("name") or item.get("名称") or "",
                "measurement": measurement,
                "field_name": field_name,
                "desc": item.get("desc") or item.get("描述信息") or "",
                "unit": item.get("unit") or item.get("单位") or "",
            }
            if normalized["name"] and normalized["measurement"] and normalized["field_name"]:
                items.append(MetricItem.model_validate(normalized))
        return items

    def _load_public_tag_items(self) -> list[PublicTagItem]:
        rows = self._load_json(PUBLIC_TAGS_FILE)
        items: list[PublicTagItem] = []
        for item in rows:
            normalized = {
                "name": item.get("name") or item.get("名称") or "",
                "field_name": item.get("field_name") or item.get("字段名") or "",
                "desc": item.get("desc") or item.get("描述") or item.get("描述信息") or "",
            }
            if normalized["name"] and normalized["field_name"]:
                items.append(PublicTagItem.model_validate(normalized))
        return items

    def get_data_source_status(self) -> DataSourceStatusResponse:
        knowledge_path = self.seed_dir / KNOWLEDGE_FILE
        metrics_path = self.seed_dir / METRICS_FILE
        public_tags_path = self.seed_dir / PUBLIC_TAGS_FILE
        return DataSourceStatusResponse(
            data_dir=str(self.seed_dir),
            knowledge={
                "file_name": KNOWLEDGE_FILE,
                "file_path": str(knowledge_path),
                "exists": knowledge_path.exists(),
                "loaded_count": len(self.knowledge_items),
            },
            metrics={
                "file_name": METRICS_FILE,
                "file_path": str(metrics_path),
                "exists": metrics_path.exists(),
                "loaded_count": len(self.metric_items),
            },
            public_tags={
                "file_name": PUBLIC_TAGS_FILE,
                "file_path": str(public_tags_path),
                "exists": public_tags_path.exists(),
                "loaded_count": len(self.public_tag_items),
            },
        )

    def list_knowledge(self) -> list[KnowledgeItem]:
        return self.knowledge_items

    def list_metrics(self) -> list[MetricItem]:
        return self.metric_items

    def list_public_tags(self) -> list[PublicTagItem]:
        return self.public_tag_items

    def list_public_tags(self) -> list[PublicTagItem]:
        return self.public_tag_items
