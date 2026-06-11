from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_should_create_agent_plan_with_memory_and_audit():
    response = client.post(
        "/api/v1/agent/plans",
        json={
            "session_id": "interview-demo",
            "question": "IF1接收时延异常怎么处理",
            "analysis_result": {
                "keywords": ["IF1接收时延", "网络"],
                "normalized_metric": "IF1接收时延",
                "confidence": 0.42,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    plan = data["plan"]
    assert plan["plan_id"].startswith("plan_")
    assert plan["goal"] == "定位 IF1接收时延 相关异常并生成安全的诊断路径 (已通过 ReAct 推理验证)"
    assert len(plan["steps"]) >= 5
    assert any(step["tool_name"] == "llm_fallback" for step in plan["steps"])
    assert plan["recommended_actions"]
    assert data["memory"]["session_id"] == "interview-demo"
    assert any("IF1接收时延" in fact for fact in data["memory"]["facts"])

    plan_response = client.get(f"/api/v1/agent/plans/{plan['plan_id']}")
    assert plan_response.status_code == 200
    assert plan_response.json()["plan_id"] == plan["plan_id"]

    memory_response = client.get("/api/v1/agent/memory/interview-demo")
    assert memory_response.status_code == 200
    assert memory_response.json()["last_question"] == "IF1接收时延异常怎么处理"

    audit_response = client.get("/api/v1/agent/audit")
    assert audit_response.status_code == 200
    assert any(event["event_type"] == "plan_created" for event in audit_response.json())


def test_should_append_conversation_memory():
    response = client.post(
        "/api/v1/agent/memory",
        json={
            "session_id": "manual-memory",
            "facts": ["用户正在排查浙江 IF1 链路", "用户正在排查浙江 IF1 链路"],
            "question": "继续看这个链路",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["facts"].count("用户正在排查浙江 IF1 链路") == 1
    assert data["last_question"] == "继续看这个链路"


def test_should_evaluate_agent_cases():
    response = client.post(
        "/api/v1/agent/evaluate",
        json={
            "cases": [
                {
                    "case_id": "metric-delay",
                    "question": "IF1接收时延异常怎么处理",
                    "expected_keywords": ["IF1接收时延"],
                },
                {
                    "case_id": "network",
                    "question": "网络不通需要先看什么",
                    "expected_keywords": ["网络"],
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] == 2
    assert data["average_score"] > 0
    assert all(result["plan_id"].startswith("plan_") for result in data["results"])


def test_should_reject_action_id_mismatch():
    action_response = client.post(
        "/api/v1/agent/actions/generate",
        json={
            "question": "查看系统负载",
            "analysis_result": {"keywords": ["系统"], "normalized_metric": ""},
        },
    )
    action = action_response.json()["actions"][0]

    response = client.post(
        "/api/v1/agent/actions/wrong_id/execute",
        json={
            "action_id": "wrong_id",
            "parameters": {"action": action},
            "user_confirmation": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Action ID mismatch"
