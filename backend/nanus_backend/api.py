from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from .codex_bridge import CodexBridge
from .execution import ExecutionEngine
from .llm import AnthropicMessagesClient
from .run_model import create_run
from .tooling import deck_from_brief, generic_llm_result, list_skill_tools
from .storage import RunStore


class RunCreateRequest(BaseModel):
    input: str = Field(min_length=1, max_length=10_000)
    mode: str = "local"

    @field_validator("input")
    @classmethod
    def strip_input(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Input cannot be blank")
        return stripped


class ToolInvokeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Prompt cannot be blank")
        return stripped


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)


def _cors_origins() -> list[str]:
    configured = [origin.strip() for origin in os.environ.get("NANUS_CORS_ORIGINS", "").split(",") if origin.strip()]
    return configured or list(DEFAULT_CORS_ORIGINS)


def create_app(*, db_path: str | Path | None = None) -> FastAPI:
    store = RunStore(db_path)
    llm = AnthropicMessagesClient()
    codex = CodexBridge()
    engine = ExecutionEngine(store, llm=llm, codex=codex)

    app = FastAPI(title="Nanus Execution Backend", version="0.1.0")
    app.state.store = store
    app.state.llm = llm
    app.state.codex = codex
    app.state.engine = engine

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "database": str(store.db_path), "anthropic": llm.status(), "codex": codex.status()}

    @app.get("/api/tools")
    def tools() -> dict[str, Any]:
        return {"tools": list_skill_tools(anthropic_status=llm.status(), codex_status=codex.status())}

    @app.get("/api/mcp/tools")
    def mcp_tools() -> dict[str, Any]:
        tools_payload = list_skill_tools(anthropic_status=llm.status(), codex_status=codex.status())
        return {
            "tools": [
                {
                    "name": tool["id"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                    "metadata": {
                        "command": tool["command"],
                        "runtime": tool["runtime"],
                        "permissions": tool["permissions"],
                        "connection": tool["connection"],
                    },
                }
                for tool in tools_payload
            ]
        }

    async def invoke_tool_by_id(tool_id: str, prompt: str) -> dict[str, Any]:
        if tool_id in {"deck-from-brief", "deck_from_brief", "artifact-studio", "artifact_studio"}:
            return await deck_from_brief(prompt, llm)
        if tool_id in {"codex-cli", "codex_cli"}:
            result = await codex.run(prompt)
            return {
                "logs": ["Codex CLI bridge invoked"],
                "artifacts": [
                    {
                        "id": f"codex-{uuid4().hex[:8]}",
                        "title": "Codex CLI 결과",
                        "type": "codex-summary",
                        "content": result.__dict__,
                    }
                ],
            }
        if tool_id in {"anthropic-messages", "anthropic_messages"}:
            return await generic_llm_result(prompt, llm)
        raise HTTPException(status_code=404, detail="Unknown tool")

    @app.post("/api/tools/{tool_id}/invoke")
    async def invoke_tool(tool_id: str, payload: ToolInvokeRequest) -> dict[str, Any]:
        return await invoke_tool_by_id(tool_id, payload.prompt)

    @app.post("/mcp")
    async def mcp(request: JsonRpcRequest) -> dict[str, Any]:
        if request.method in {"tools/list", "list_tools"}:
            result = mcp_tools()
        elif request.method in {"tools/call", "call_tool"}:
            params = request.params
            tool_name = str(params.get("name") or params.get("tool") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else params
            prompt = str(arguments.get("prompt") or arguments.get("brief") or "")
            if not tool_name:
                return {"jsonrpc": request.jsonrpc, "id": request.id, "error": {"code": -32602, "message": "Missing tool name"}}
            try:
                result = await invoke_tool_by_id(tool_name, prompt)
            except HTTPException as exc:
                return {"jsonrpc": request.jsonrpc, "id": request.id, "error": {"code": -32602, "message": str(exc.detail)}}
        else:
            return {"jsonrpc": request.jsonrpc, "id": request.id, "error": {"code": -32601, "message": "Method not found"}}
        return {"jsonrpc": request.jsonrpc, "id": request.id, "result": result}

    @app.post("/api/runs")
    def create_backend_run(payload: RunCreateRequest) -> dict[str, Any]:
        run = create_run(payload.input, mode=payload.mode)
        store.save_run(run)
        store.add_event(run["id"], "run.created", {"run": run})
        return run

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        return {"runs": store.list_runs()}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.get("/api/runs/{run_id}/artifacts")
    def get_artifacts(run_id: str) -> dict[str, Any]:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        return {"artifacts": store.list_artifacts(run_id)}

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}/download")
    def download_artifact(run_id: str, artifact_id: str) -> Response:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        artifact = store.get_artifact(run_id, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        content = artifact.get("content") if isinstance(artifact.get("content"), dict) else {}
        download = content.get("download") if isinstance(content, dict) else None
        if isinstance(download, dict) and isinstance(download.get("base64"), str):
            try:
                data = base64.b64decode(download["base64"], validate=True)
            except (ValueError, binascii.Error) as exc:
                raise HTTPException(status_code=500, detail="Artifact download payload is invalid") from exc
            filename = str(download.get("filename") or artifact.get("fileName") or artifact["title"])
            media_type = str(download.get("mimeType") or artifact.get("mimeType") or "application/octet-stream")
        else:
            filename = str(artifact.get("fileName") or artifact["title"])
            if not filename.endswith(".json"):
                filename = f"{filename}.json"
            media_type = "application/json"
            data = json.dumps(artifact, ensure_ascii=False, indent=2).encode("utf-8")

        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        return Response(content=data, media_type=media_type, headers=headers)

    @app.get("/api/runs/{run_id}/events")
    def get_events(run_id: str) -> dict[str, Any]:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        return {"events": store.list_events(run_id)}

    @app.websocket("/ws/run/{run_id}")
    async def run_stream(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        if not store.get_run(run_id):
            await websocket.send_json({"type": "error", "payload": {"message": "Run not found"}})
            await websocket.close(code=4404)
            return
        try:
            async for event in engine.stream_run(run_id):
                await websocket.send_json(event)
        except WebSocketDisconnect:
            return

    return app


app = create_app()
