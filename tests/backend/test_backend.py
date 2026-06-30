from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from nanus_backend.api import create_app  # noqa: E402


def make_client(tmp_path: Path) -> TestClient:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("NANUS_CORS_ORIGINS", None)
    os.environ["NANUS_CODEX_ENABLED"] = "false"
    app = create_app(db_path=tmp_path / "nanus-test.sqlite3")
    return TestClient(app)


def make_client_with_unset_codex(tmp_path: Path) -> TestClient:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("NANUS_CORS_ORIGINS", None)
    os.environ.pop("NANUS_CODEX_ENABLED", None)
    app = create_app(db_path=tmp_path / "nanus-unset-codex.sqlite3")
    return TestClient(app)


def test_run_creation_websocket_stream_and_persistence(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    created = client.post("/api/runs", json={"input": "/deck-from-brief 교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘", "mode": "local"})
    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "queued"
    assert run["progress"] == 0
    assert run["command"] == "/deck-from-brief"
    assert run["runtime"]["source"] == "backend"
    assert run["runtime"]["jobId"].startswith("job-")

    stream_events = []
    with client.websocket_connect(f"/ws/run/{run['id']}") as websocket:
        while True:
            event = websocket.receive_json()
            stream_events.append(event)
            if event["type"] == "run.done":
                break

    final_run = stream_events[-1]["payload"]["run"]
    assert final_run["status"] == "complete"
    assert final_run["progress"] == 100
    assert "백그라운드 작업자가 실행을 시작했습니다." in final_run["log"]
    assert any("Python skill /deck-from-brief" in line for line in final_run["log"])
    assert any(event["type"] == "artifact.created" for event in stream_events)

    persisted = client.get(f"/api/runs/{run['id']}").json()
    assert persisted["status"] == "complete"
    artifacts = client.get(f"/api/runs/{run['id']}/artifacts").json()["artifacts"]
    assert [artifact["type"] for artifact in artifacts] == ["outline", "pptx"]
    assert [artifact["type"] for artifact in final_run["artifacts"]] == ["outline", "pptx"]
    pptx_artifact = next(artifact for artifact in artifacts if artifact["type"] == "pptx")
    assert pptx_artifact["title"].endswith(".pptx")
    assert pptx_artifact["mimeType"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert pptx_artifact["sizeBytes"] == pptx_artifact["content"]["download"]["size"]

    download = client.get(f"/api/runs/{run['id']}/artifacts/{pptx_artifact['id']}/download")
    assert download.status_code == 200
    assert download.content[:2] == b"PK"
    assert len(download.content) == pptx_artifact["sizeBytes"]
    assert download.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.presentationml.presentation")
    assert "filename*=" in download.headers["content-disposition"]
    assert ".pptx" in download.headers["content-disposition"]

    missing_artifact = client.get(f"/api/runs/{run['id']}/artifacts/not-found/download")
    assert missing_artifact.status_code == 404
    missing_run = client.get("/api/runs/not-found/artifacts/not-found/download")
    assert missing_run.status_code == 404
    events = client.get(f"/api/runs/{run['id']}/events").json()["events"]
    assert {event["type"] for event in events} >= {"run.created", "run.queued", "run.started", "run.done"}
    later_events = client.get(f"/api/runs/{run['id']}/events?after={events[0]['id']}").json()["events"]
    assert later_events
    assert all(event["id"] > events[0]["id"] for event in later_events)


def test_run_completes_without_websocket_subscriber(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    created = client.post("/api/runs", json={"input": "/deck-from-brief 독립 백그라운드 실행", "mode": "local"})
    assert created.status_code == 200
    run_id = created.json()["id"]

    final_run = None
    for _ in range(30):
        candidate = client.get(f"/api/runs/{run_id}").json()
        if candidate["status"] == "complete":
            final_run = candidate
            break
        time.sleep(0.05)

    assert final_run is not None
    assert final_run["progress"] == 100
    events = client.get(f"/api/runs/{run_id}/events").json()["events"]
    assert events[-1]["type"] == "run.done"
    assert [artifact["type"] for artifact in client.get(f"/api/runs/{run_id}/artifacts").json()["artifacts"]] == ["outline", "pptx"]


def test_run_pause_resume_and_cancel_endpoints(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    first = client.post("/api/runs", json={"input": "일시정지 대상", "mode": "local"}).json()
    paused = client.post(f"/api/runs/{first['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["run"]["status"] == "paused"
    resumed = client.post(f"/api/runs/{first['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["run"]["status"] == "running"

    second = client.post("/api/runs", json={"input": "취소 대상", "mode": "local"}).json()
    cancelled = client.post(f"/api/runs/{second['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["run"]["status"] == "cancelled"
    events = client.get(f"/api/runs/{second['id']}/events").json()["events"]
    assert any(event["type"] == "run.cancelled" for event in events)


def test_tools_expose_codex_and_codex_fallback_is_invokable(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    tools = client.get("/api/tools").json()["tools"]
    tool_ids = {tool["id"] for tool in tools}
    assert {"deck-from-brief", "artifact-studio", "codex-cli", "anthropic-messages"}.issubset(tool_ids)
    codex_tool = next(tool for tool in tools if tool["id"] == "codex-cli")
    assert "codex exec" in codex_tool["connection"]["invocation"]

    invoked = client.post("/api/tools/codex-cli/invoke", json={"prompt": "코드베이스를 분석해줘"})
    assert invoked.status_code == 200
    artifact = invoked.json()["artifacts"][0]
    assert artifact["type"] == "codex-summary"
    assert artifact["content"]["live"] is False
    assert "NANUS_CODEX_ENABLED" in artifact["content"]["error"]


def test_codex_bridge_requires_explicit_truthy_opt_in(tmp_path: Path) -> None:
    client = make_client_with_unset_codex(tmp_path)
    codex_status = client.get("/health").json()["codex"]
    assert codex_status["enabled"] is False

    invoked = client.post("/api/tools/codex-cli/invoke", json={"prompt": "코드베이스를 분석해줘"})
    assert invoked.status_code == 200
    artifact = invoked.json()["artifacts"][0]
    assert artifact["content"]["live"] is False
    assert "NANUS_CODEX_ENABLED" in artifact["content"]["error"]


def test_prompt_payloads_are_trimmed_and_bounded(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/api/runs", json={"input": "   /deck-from-brief 교육지원 발표자료   "})
    assert created.status_code == 200
    assert created.json()["prompt"] == "교육지원 발표자료"

    blank = client.post("/api/runs", json={"input": "   "})
    assert blank.status_code == 422

    too_large = client.post("/api/tools/deck-from-brief/invoke", json={"prompt": "x" * 10_001})
    assert too_large.status_code == 422


def test_mcp_tool_list_and_call_router(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    listed = client.post("/mcp", json={"jsonrpc": "2.0", "id": "tools", "method": "tools/list"})
    assert listed.status_code == 200
    tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "deck-from-brief" in tool_names
    assert "artifact-studio" in tool_names

    called = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "call",
            "method": "tools/call",
            "params": {"name": "deck-from-brief", "arguments": {"prompt": "교육지원 성과 발표자료"}},
        },
    )
    assert called.status_code == 200
    assert [artifact["type"] for artifact in called.json()["result"]["artifacts"]] == ["outline", "pptx"]

    artifact_studio = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "artifact",
            "method": "tools/call",
            "params": {"name": "artifact-studio", "arguments": {"prompt": "HWPX 계획서를 PPTX로 변환"}},
        },
    )
    assert artifact_studio.status_code == 200
    assert artifact_studio.json()["result"]["artifacts"][1]["content"]["download"]["mimeType"].endswith("presentation")


def test_database_foreign_keys_and_configurable_cors(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    with client.app.state.store._connect() as conn:  # persistence invariant probe
        assert conn.execute("pragma foreign_keys").fetchone()[0] == 1

    custom_origin = "https://nanus.example"
    os.environ["NANUS_CORS_ORIGINS"] = custom_origin
    custom_client = TestClient(create_app(db_path=tmp_path / "custom-cors.sqlite3"))
    response = custom_client.options(
        "/api/runs",
        headers={"origin": custom_origin, "access-control-request-method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == custom_origin


def test_code_or_app_run_uses_codex_bridge_fallback(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    run = client.post("/api/runs", json={"input": "/codex-refactor App.tsx 구조를 분석해줘"}).json()
    with client.websocket_connect(f"/ws/run/{run['id']}") as websocket:
        while True:
            event = websocket.receive_json()
            if event["type"] == "run.done":
                final_run = event["payload"]["run"]
                break

    assert final_run["status"] == "complete"
    assert any("Codex Bridge: deterministic fallback" in line for line in final_run["log"])
    artifacts = client.get(f"/api/runs/{run['id']}/artifacts").json()["artifacts"]
    assert any(artifact["type"] == "codex-summary" for artifact in artifacts)
