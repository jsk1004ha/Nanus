from __future__ import annotations

import io
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from nanus_backend.api import MAX_RUN_INPUT_CHARS, create_app  # noqa: E402


def make_client(tmp_path: Path) -> TestClient:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("NANUS_CORS_ORIGINS", None)
    os.environ["NANUS_CODEX_ENABLED"] = "false"
    return TestClient(create_app(db_path=tmp_path / "nanus-test.sqlite3"))


def make_client_with_unset_codex(tmp_path: Path) -> TestClient:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("NANUS_CORS_ORIGINS", None)
    os.environ.pop("NANUS_CODEX_ENABLED", None)
    return TestClient(create_app(db_path=tmp_path / "nanus-unset-codex.sqlite3"))


def wait_for_terminal_run(client: TestClient, run_id: str, *, attempts: int = 50) -> dict:
    for _ in range(attempts):
        candidate = client.get(f"/api/runs/{run_id}").json()
        if candidate["status"] in {"complete", "failed", "cancelled", "degraded"}:
            return candidate
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach a terminal state")


def assert_zip_parts(data: bytes, required: set[str]) -> None:
    assert data[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        names = set(package.namelist())
        assert required.issubset(names)
        for name in names:
            if name.endswith(".xml"):
                ET.fromstring(package.read(name))


def test_deck_run_streams_persists_and_validates_artifacts(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/api/runs", json={"input": "/deck-from-brief 교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘", "mode": "local"})
    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "queued"
    assert run["progress"] == 0
    assert run["runtime"]["jobId"].startswith("job-")

    stream_events = []
    with client.websocket_connect(f"/ws/run/{run['id']}") as websocket:
        while True:
            event = websocket.receive_json()
            stream_events.append(event)
            if event["type"] in {"run.done", "run.degraded"}:
                break

    final_run = stream_events[-1]["payload"]["run"]
    assert final_run["status"] == "degraded"
    assert final_run["progress"] == 100
    assert final_run["finalAnswer"]
    assert final_run["verification"]["finalAnswerPresent"] is True
    assert final_run["verification"]["artifactIntegrityOk"] is True
    assert any(event["type"] == "assistant.message.delta" for event in stream_events)
    assert any(event["type"] == "artifact.created" for event in stream_events)

    artifacts = client.get(f"/api/runs/{run['id']}/artifacts").json()["artifacts"]
    assert [artifact["type"] for artifact in artifacts] == ["outline", "pptx"]
    outline = next(artifact for artifact in artifacts if artifact["type"] == "outline")
    assert len(outline["content"]["slides"]) == 12
    pptx = next(artifact for artifact in artifacts if artifact["type"] == "pptx")
    download = client.get(f"/api/runs/{run['id']}/artifacts/{pptx['id']}/download")
    assert download.status_code == 200
    assert_zip_parts(download.content, {"[Content_Types].xml", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"})
    validation = client.get(f"/api/runs/{run['id']}/artifacts/validate").json()["validation"]
    assert validation["ok"] is True
    assert "pptx-package" in validation["checks"]


def test_document_upload_rag_context_and_chat_messages(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    doc = client.post("/api/documents", json={"title": "태양광 보고서", "content": "태양광 패널 오염과 빗물 세척 장치 실험 계획을 다룬 문서입니다. 세척 전후 전압 전류를 비교합니다."}).json()["document"]
    created = client.post("/api/chat", json={"message": "이 문서를 바탕으로 보고서 보강 방향 알려줘", "documentIds": [doc["id"]], "mode": "local"})
    assert created.status_code == 200
    payload = created.json()
    assert payload["retrieval"]["matches"]
    assert "Nanus Retrieved Document Context" in payload["run"]["prompt"]
    messages = client.get(f"/api/conversations/{payload['conversationId']}/messages").json()["messages"]
    assert messages[0]["content"] == "이 문서를 바탕으로 보고서 보강 방향 알려줘"
    final_run = wait_for_terminal_run(client, payload["runId"])
    assert final_run["runtime"]["retrieval"]["count"] >= 1


def test_artifact_studio_bundle_produces_real_xlsx_and_visualization(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/mcp", json={"jsonrpc": "2.0", "id": "artifact", "method": "tools/call", "params": {"name": "artifact-studio", "arguments": {"prompt": "HWPX 계획서를 문서 PPT 엑셀 시각화 묶음으로 변환"}}})
    assert response.status_code == 200
    artifacts = response.json()["result"]["artifacts"]
    types = {artifact["type"] for artifact in artifacts}
    assert {"markdown", "outline", "pptx", "spreadsheet", "visualization"}.issubset(types)
    sheet = next(artifact for artifact in artifacts if artifact["type"] == "spreadsheet")
    data = __import__("base64").b64decode(sheet["content"]["download"]["base64"])
    assert sheet["content"]["download"]["filename"].endswith(".xlsx")
    assert_zip_parts(data, {"[Content_Types].xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml"})


def test_browser_snapshot_requires_approval_and_blocks_private_targets(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    run = client.post("/api/runs", json={"input": "브라우저 스냅샷 테스트", "mode": "local"}).json()
    waiting = client.post("/api/browser/snapshot", json={"runId": run["id"], "url": "https://example.com"})
    assert waiting.status_code == 200
    approval = waiting.json()["approval"]
    assert waiting.json()["run"]["status"] == "waiting"
    rejected = client.post(f"/api/runs/{run['id']}/approvals/{approval['id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["run"]["status"] == "cancelled"
    blocked = client.post("/api/browser/snapshot", json={"url": "http://127.0.0.1:1234", "approved": True})
    assert blocked.status_code == 403


def test_general_run_uses_live_codex_when_bridge_is_enabled(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    class FakeCodex:
        enabled = True
        def should_handle(self, command: str, prompt: str, kind: str) -> bool:
            return False
        async def run(self, prompt: str):
            return SimpleNamespace(text="Codex CLI live 응답입니다. 일반 대화도 Codex Bridge를 통해 처리되었습니다.", live=True, command=["codex", "exec", "--json"], error=None)
    client.app.state.engine.codex = FakeCodex()
    created = client.post("/api/runs", json={"input": "안녕", "mode": "local"})
    assert created.status_code == 200
    final_run = wait_for_terminal_run(client, created.json()["id"])
    assert final_run["status"] == "complete"
    assert final_run["verification"]["status"] == "verified"
    assert "Codex CLI live 응답" in final_run["finalAnswer"]


def test_pause_resume_cancel_and_payload_bounds(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    first = client.post("/api/runs", json={"input": "일시정지 대상", "mode": "local"}).json()
    assert client.post(f"/api/runs/{first['id']}/pause").json()["run"]["status"] == "paused"
    assert client.post(f"/api/runs/{first['id']}/resume").json()["run"]["status"] == "running"
    second = client.post("/api/runs", json={"input": "취소 대상", "mode": "local"}).json()
    assert client.post(f"/api/runs/{second['id']}/cancel").json()["run"]["status"] == "cancelled"
    assert client.post("/api/runs", json={"input": "x" * (MAX_RUN_INPUT_CHARS + 1)}).status_code == 413
    assert client.post("/api/tools/deck-from-brief/invoke", json={"prompt": "x" * 120_001}).status_code == 422


def test_tools_and_codex_fallback(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    tools = client.get("/api/tools").json()["tools"]
    ids = {tool["id"] for tool in tools}
    assert {"deck-from-brief", "artifact-studio", "spreadsheet-studio", "visualization-studio", "writing-advice", "codex-cli"}.issubset(ids)
    invoked = client.post("/api/tools/codex-cli/invoke", json={"prompt": "코드베이스를 분석해줘"})
    assert invoked.status_code == 200
    artifact = invoked.json()["artifacts"][0]
    assert artifact["type"] == "codex-summary"
    assert artifact["content"]["live"] is False


def test_database_foreign_keys_and_configurable_cors(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    with client.app.state.store._connect() as conn:
        assert conn.execute("pragma foreign_keys").fetchone()[0] == 1
    os.environ["NANUS_CORS_ORIGINS"] = "https://nanus.example"
    custom_client = TestClient(create_app(db_path=tmp_path / "custom-cors.sqlite3"))
    response = custom_client.options("/api/runs", headers={"origin": "https://nanus.example", "access-control-request-method": "POST"})
    assert response.headers["access-control-allow-origin"] == "https://nanus.example"
