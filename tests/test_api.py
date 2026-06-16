from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.core.assistant.repository import InMemoryRepository

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask():
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "IF1接收时延异常怎么处理", "province": "浙江", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["normalized_metric"] != ""
    assert data["normalized_metric"].startswith("IF1")
    assert data["matched_knowledge"] or data["related_objects"]["metrics"]


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "智能运维问答" in response.text
    # 验证首页包含数据源状态（服务端渲染）
    assert "数据源状态" in response.text
    assert "已加载" in response.text


def test_data_source_status():
    response = client.get("/api/v1/data-source/status")
    assert response.status_code == 200
    data = response.json()
    assert "data_dir" in data
    assert "knowledge" in data
    assert "metrics" in data
    assert "public_tags" in data
    # 验证文件状态结构
    for key in ["knowledge", "metrics", "public_tags"]:
        assert "exists" in data[key]
        assert "file_path" in data[key]
        assert "loaded_count" in data[key]
        assert isinstance(data[key]["exists"], bool)
        assert isinstance(data[key]["loaded_count"], int)


def test_repository_can_read_export_style_json(tmp_path: Path):
    (tmp_path / "knowledge.json").write_text(
        '[{"省份":"浙江","问题描述":"IF1接收时延异常怎么处理","问题分类":"指标异常","问题原因":"链路拥塞","解决办法描述":"检查链路；检查进程"}]',
        encoding="utf-8",
    )
    (tmp_path / "metrics.json").write_text(
        '[{"名称":"IF1接收时延","存储分区":"dpi","字段名":"if1_delay","单位":"ms","描述信息":"用于衡量 IF1 链路接收时延情况"}]',
        encoding="utf-8",
    )
    (tmp_path / "public_tags.json").write_text(
        '[{"名称":"device_id","字段名":"device_id","描述":"设备标识"}]',
        encoding="utf-8",
    )
    repository = InMemoryRepository(seed_dir=tmp_path)
    assert repository.list_knowledge()[0].question == "IF1接收时延异常怎么处理"
    assert repository.list_metrics()[0].field_name == "if1_delay"
    assert repository.list_public_tags()[0].name == "device_id"
