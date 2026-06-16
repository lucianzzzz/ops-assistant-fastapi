from pathlib import Path

from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.service import OpsAssistantService


class TestOpsAssistantService:
    def setup_method(self):
        self.service = OpsAssistantService(repository=InMemoryRepository())

    def test_should_match_knowledge_and_metric(self):
        result = self.service.ask("IF1接收时延异常怎么处理", province="浙江", top_k=3)
        assert result["normalized_metric"] != ""
        assert result["normalized_metric"].startswith("IF1")
        assert result["matched_knowledge"] or result["related_objects"]["metrics"]
        assert result["suggested_steps"]
        assert result["confidence"] > 0

    def test_should_build_metric_based_answer_when_no_knowledge(self):
        result = self.service.ask("IF1接收时延波动", province="广东", top_k=3)
        assert result["normalized_metric"] != ""
        assert result["normalized_metric"].startswith("IF1")
        assert result["possible_reason"]
        assert result["next_actions"]

    def test_should_return_low_confidence_when_no_match(self):
        result = self.service.ask("完全不存在的异常问题", province="", top_k=3)
        assert result["confidence"] == 0.0
        assert not result["matched_knowledge"]

    def test_should_load_realistic_export_shapes(self, tmp_path: Path):
        (tmp_path / "knowledge.json").write_text(
            '[{"省份":"浙江","问题描述":"IF1接收时延异常怎么处理","问题分类":"指标异常","问题原因":"链路拥塞","解决办法描述":"检查链路；检查进程"}]',
            encoding="utf-8",
        )
        (tmp_path / "metrics.json").write_text(
            '[{"名称":"IF1接收时延","存储分区":"dpi","字段名":"if1_delay","单位":"ms","描述信息":"用于衡量 IF1 链路接收时延情况"}]',
            encoding="utf-8",
        )
        (tmp_path / "public_tags.json").write_text(
            '[{"name":"device_id","field_name":"device_id","desc":"设备标识"}]',
            encoding="utf-8",
        )
        service = OpsAssistantService(repository=InMemoryRepository(seed_dir=tmp_path))
        result = service.ask("IF1接收时延异常怎么处理", province="浙江", top_k=3)
        assert result["matched_knowledge"]
        assert result["normalized_metric"] == "IF1接收时延"
