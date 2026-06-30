from __future__ import annotations

import asyncio
import base64
import binascii
import ipaddress
import json
import os
import re
import socket
import urllib.request
from pathlib import Path
from time import time
from typing import Any
from urllib.parse import quote, urlparse
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from .artifact_validation import validate_artifacts
from .codex_bridge import CodexBridge
from .execution import ExecutionEngine
from .llm import AnthropicMessagesClient
from .run_model import create_run
from .storage import RunStore
from .supervisor import JobSupervisor
from .tooling import artifact_studio_bundle, deck_from_brief, generic_llm_result, list_skill_tools, writing_advice

MAX_RUN_INPUT_CHARS = 120_000
MAX_DOCUMENT_CONTEXT_CHARS = 16_000
DEFAULT_CORS_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:4173", "http://localhost:4173")
TERMINAL_RUN_STATUSES = {"complete", "failed", "cancelled", "degraded"}
TERMINAL_EVENT_TYPES = {"run.done", "run.failed", "run.cancelled", "run.degraded"}


class RunCreateRequest(BaseModel):
    input: str = Field(min_length=1)
    mode: str = "local"
    @field_validator("input")
    @classmethod
    def strip_input(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Input cannot be blank")
        return stripped


class ToolInvokeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=120_000)
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


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    conversationId: str | None = None
    documentIds: list[str] = Field(default_factory=list)
    mode: str = "local"
    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class DocumentCreateRequest(BaseModel):
    title: str = "Nanus document"
    content: str = Field(min_length=1)
    mimeType: str = "text/plain"
    source: str = "text"


class BrowserSnapshotRequest(BaseModel):
    url: str
    runId: str | None = None
    approved: bool = False


class ApprovalDecisionRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


def _cors_origins() -> list[str]:
    configured = [origin.strip() for origin in os.environ.get("NANUS_CORS_ORIGINS", "").split(",") if origin.strip()]
    return configured or list(DEFAULT_CORS_ORIGINS)


def _append_run_log(run: dict[str, Any], line: str) -> None:
    log = run.setdefault("log", [])
    if line not in log:
        log.append(line)


def _ensure_run_input_size(input_text: str) -> None:
    if len(input_text) > MAX_RUN_INPUT_CHARS:
        raise HTTPException(status_code=413, detail=f"Input is too large for direct chat/run payload ({len(input_text)} chars > {MAX_RUN_INPUT_CHARS}). Use document upload/RAG.")


def _conversation_title(input_text: str) -> str:
    first_line = " ".join(input_text.strip().split())
    return first_line if len(first_line) <= 72 else f"{first_line[:69]}..."


def _assistant_message_id(run: dict[str, Any]) -> str | None:
    runtime = run.get("runtime") if isinstance(run.get("runtime"), dict) else {}
    conversation = runtime.get("conversation") if isinstance(runtime.get("conversation"), dict) else {}
    message_id = conversation.get("assistantMessageId")
    return str(message_id) if message_id else None


def _read_documents(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    docs: list[dict[str, Any]] = []
    for path in sorted(root.glob("doc-*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            docs.append({key: data.get(key) for key in ["id", "title", "mimeType", "source", "charCount", "chunkCount", "createdAt"]})
        except (OSError, json.JSONDecodeError):
            continue
    return docs


def _chunk_text(text: str) -> list[dict[str, Any]]:
    parts = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()] or [text.strip()]
    chunks: list[dict[str, Any]] = []
    buffer = ""
    for part in parts:
        if buffer and len(buffer) + len(part) > 1600:
            chunks.append({"id": f"chunk-{uuid4().hex[:10]}", "index": len(chunks), "text": buffer.strip()})
            buffer = ""
        buffer += ("\n\n" if buffer else "") + part
    if buffer.strip():
        chunks.append({"id": f"chunk-{uuid4().hex[:10]}", "index": len(chunks), "text": buffer.strip()})
    return chunks


def _save_document(root: Path, *, title: str, content: str, mime_type: str, source: str) -> dict[str, Any]:
    clean = content.strip()
    if not clean:
        raise HTTPException(status_code=422, detail="Document content cannot be blank")
    doc_id = f"doc-{uuid4().hex}"
    chunks = _chunk_text(clean)
    payload = {"id": doc_id, "title": title.strip() or "Nanus document", "mimeType": mime_type, "source": source, "charCount": len(clean), "chunkCount": len(chunks), "createdAt": time(), "content": clean, "chunks": chunks}
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{doc_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {key: payload.get(key) for key in ["id", "title", "mimeType", "source", "charCount", "chunkCount", "createdAt"]}


def _load_document(root: Path, document_id: str) -> dict[str, Any] | None:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", document_id)
    path = root / f"{safe}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _search_documents(root: Path, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    terms = [term.lower() for term in re.findall(r"[\w가-힣]{2,}", query)]
    results: list[dict[str, Any]] = []
    for doc in _read_documents(root):
        full = _load_document(root, str(doc.get("id")))
        if not full:
            continue
        for chunk in full.get("chunks", []):
            text = str(chunk.get("text", ""))
            score = sum(1 for term in terms if term in text.lower()) if terms else 1
            if score:
                results.append({"documentId": doc["id"], "title": doc["title"], "chunkId": chunk.get("id"), "index": chunk.get("index"), "score": score, "text": text[:900]})
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]


def _document_context(root: Path, message: str, document_ids: list[str]) -> tuple[str, list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    if document_ids:
        for document_id in document_ids:
            full = _load_document(root, document_id)
            if full:
                for chunk in full.get("chunks", [])[:10]:
                    selected.append({"documentId": full["id"], "title": full["title"], "chunkId": chunk.get("id"), "index": chunk.get("index"), "score": 999, "text": str(chunk.get("text", ""))[:900]})
    else:
        selected = _search_documents(root, message, limit=8)
    if not selected:
        return "", []
    parts: list[str] = []
    used = 0
    for item in selected:
        snippet = f"[D:{item['documentId']}#{item['index']} {item['title']}]\n{item['text']}"
        if used + len(snippet) > MAX_DOCUMENT_CONTEXT_CHARS:
            break
        parts.append(snippet)
        used += len(snippet)
    return "\n\n".join(parts), selected[: len(parts)]


def _assemble_run_input(root: Path, message: str, document_ids: list[str]) -> tuple[str, list[dict[str, Any]]]:
    context, matches = _document_context(root, message, document_ids)
    if not context:
        return message, []
    return f"{message}\n\n[Nanus Retrieved Document Context]\n{context}\n[/Nanus Retrieved Document Context]", matches


def _blocked_ip(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="Browser target host cannot be resolved")
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    return False


def _browser_snapshot(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Only http(s) URLs can be browsed")
    host = parsed.hostname or ""
    if _blocked_ip(host):
        raise HTTPException(status_code=403, detail="Local/private browser targets are blocked")
    request = urllib.request.Request(url, headers={"user-agent": "NanusBrowser/0.1"})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(1_000_000).decode("utf-8", errors="replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else url
    cleaned = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", cleaned)
    text = re.sub(r"\s+", " ", text).strip()[:6000]
    return {"url": url, "title": title, "text": text, "engine": "urllib-browser-snapshot", "charCount": len(text), "trace": {"allowedHost": host, "bytesReadLimit": 1_000_000}}


def _approval(run: dict[str, Any]) -> dict[str, Any] | None:
    runtime = run.get("runtime") if isinstance(run.get("runtime"), dict) else {}
    approval = runtime.get("approval") if isinstance(runtime.get("approval"), dict) else None
    return approval


def create_app(*, db_path: str | Path | None = None) -> FastAPI:
    store = RunStore(db_path)
    document_root = store.db_path.parent / "documents"
    llm = AnthropicMessagesClient()
    codex = CodexBridge()
    engine = ExecutionEngine(store, llm=llm, codex=codex)
    supervisor = JobSupervisor(store, engine)
    app = FastAPI(title="Nanus Execution Backend", version="0.2.0")
    app.state.store = store
    app.state.documents_root = document_root
    app.state.llm = llm
    app.state.codex = codex
    app.state.engine = engine
    app.state.supervisor = supervisor
    app.add_middleware(CORSMiddleware, allow_origins=_cors_origins(), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.on_event("startup")
    async def recover_background_jobs() -> None:
        supervisor.recover_jobs()

    @app.on_event("shutdown")
    async def shutdown_background_jobs() -> None:
        await supervisor.shutdown()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "database": str(store.db_path), "documents": len(_read_documents(document_root)), "browser": {"available": True, "engine": "safe-urllib-snapshot", "privateNetworkBlocked": True}, "artifactValidation": True, "anthropic": llm.status(), "codex": codex.status(), "activeJobs": supervisor.active_job_ids()}

    @app.get("/api/tools")
    def tools() -> dict[str, Any]:
        return {"tools": list_skill_tools(anthropic_status=llm.status(), codex_status=codex.status())}

    @app.get("/api/mcp/tools")
    def mcp_tools() -> dict[str, Any]:
        payload = list_skill_tools(anthropic_status=llm.status(), codex_status=codex.status())
        return {"tools": [{"name": tool["id"], "description": tool["description"], "inputSchema": tool["inputSchema"], "metadata": {"command": tool["command"], "runtime": tool["runtime"], "permissions": tool["permissions"], "connection": tool["connection"]}} for tool in payload]}

    async def invoke_tool_by_id(tool_id: str, prompt: str) -> dict[str, Any]:
        if tool_id in {"artifact-studio", "artifact_studio"}:
            return await artifact_studio_bundle(prompt, llm)
        if tool_id in {"deck-from-brief", "deck_from_brief"}:
            return await deck_from_brief(prompt, llm)
        if tool_id in {"writing-advice", "writing_advice"}:
            return await writing_advice(prompt, llm)
        if tool_id in {"anthropic-messages", "anthropic_messages"}:
            return await generic_llm_result(prompt, llm)
        if tool_id in {"codex-cli", "codex_cli"}:
            result = await codex.run(prompt)
            return {"finalAnswer": result.text, "logs": ["Codex CLI bridge invoked"], "artifacts": [{"id": f"codex-{uuid4().hex[:8]}", "title": "Codex CLI 결과", "type": "codex-summary", "content": result.__dict__}]}
        raise HTTPException(status_code=404, detail="Unknown tool")

    def create_and_enqueue_run(input_text: str, mode: str, *, conversation_id: str | None = None, display_text: str | None = None, context_matches: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        _ensure_run_input_size(input_text)
        run = create_run(input_text, mode=mode)
        resolved_conversation_id = conversation_id or f"conv-{run['id'][:12]}"
        user_message_id = f"user-{run['id'][:12]}"
        assistant_message_id = f"msg-{run['id'][:12]}"
        run["runtime"]["conversation"] = {"id": resolved_conversation_id, "userMessageId": user_message_id, "assistantMessageId": assistant_message_id}
        if context_matches:
            run["runtime"]["retrieval"] = {"matches": context_matches, "count": len(context_matches)}
        store.save_run(run)
        store.save_conversation(resolved_conversation_id, title=_conversation_title(display_text or input_text))
        store.add_message(user_message_id, resolved_conversation_id, role="user", content=display_text or input_text, status="complete", run_id=run["id"])
        store.add_message(assistant_message_id, resolved_conversation_id, role="assistant", content="", status="queued", run_id=run["id"])
        job = supervisor.enqueue_run(run["id"])
        run["runtime"]["jobId"] = job["id"]
        store.save_run(run)
        store.add_event(run["id"], "run.created", {"run": run})
        store.add_event(run["id"], "run.queued", {"run": run, "job": job})
        if context_matches:
            store.add_event(run["id"], "retrieval.context.attached", {"runId": run["id"], "matches": context_matches})
        return run, job

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
    async def create_backend_run(payload: RunCreateRequest) -> dict[str, Any]:
        run, _job = create_and_enqueue_run(payload.input, payload.mode)
        return run

    @app.post("/api/chat")
    async def create_chat_message(payload: ChatMessageRequest) -> dict[str, Any]:
        run_input, matches = _assemble_run_input(document_root, payload.message, payload.documentIds)
        run, _job = create_and_enqueue_run(run_input, payload.mode, conversation_id=payload.conversationId, display_text=payload.message, context_matches=matches)
        conversation = run["runtime"]["conversation"]
        return {"conversationId": conversation["id"], "userMessageId": conversation["userMessageId"], "assistantMessageId": conversation["assistantMessageId"], "runId": run["id"], "status": run["status"], "run": run, "retrieval": {"matches": matches}}

    @app.post("/api/conversations/{conversation_id}/messages")
    async def append_conversation_message(conversation_id: str, payload: ChatMessageRequest) -> dict[str, Any]:
        run_input, matches = _assemble_run_input(document_root, payload.message, payload.documentIds)
        run, _job = create_and_enqueue_run(run_input, payload.mode, conversation_id=conversation_id, display_text=payload.message, context_matches=matches)
        conversation = run["runtime"]["conversation"]
        return {"conversationId": conversation["id"], "userMessageId": conversation["userMessageId"], "assistantMessageId": conversation["assistantMessageId"], "runId": run["id"], "status": run["status"], "run": run, "retrieval": {"matches": matches}}

    @app.get("/api/conversations")
    def list_conversations() -> dict[str, Any]:
        return {"conversations": store.list_conversations()}

    @app.get("/api/conversations/{conversation_id}/messages")
    def get_conversation_messages(conversation_id: str) -> dict[str, Any]:
        conversation = store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"conversation": conversation, "messages": store.list_messages(conversation_id)}

    @app.post("/api/documents")
    def create_document(payload: DocumentCreateRequest) -> dict[str, Any]:
        return {"document": _save_document(document_root, title=payload.title, content=payload.content, mime_type=payload.mimeType, source=payload.source)}

    @app.post("/api/documents/upload")
    async def upload_document(file: UploadFile = File(...), title: str | None = Form(default=None)) -> dict[str, Any]:
        data = await file.read()
        text = data.decode("utf-8", errors="replace")
        return {"document": _save_document(document_root, title=title or file.filename or "Nanus document", content=text, mime_type=file.content_type or "application/octet-stream", source="file")}

    @app.get("/api/documents")
    def list_documents() -> dict[str, Any]:
        return {"documents": _read_documents(document_root)}

    @app.get("/api/documents/search")
    def search_documents(q: str) -> dict[str, Any]:
        return {"results": _search_documents(document_root, q)}

    @app.get("/api/documents/{document_id}")
    def get_document(document_id: str) -> dict[str, Any]:
        document = _load_document(document_root, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"document": document}

    @app.post("/api/browser/snapshot")
    def browser_snapshot(payload: BrowserSnapshotRequest) -> dict[str, Any]:
        if payload.runId and not payload.approved:
            run = store.get_run(payload.runId)
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            approval = {"id": f"approval-{uuid4().hex[:10]}", "type": "browser.snapshot", "url": payload.url, "status": "waiting", "createdAt": time(), "scope": "read-only"}
            run.setdefault("runtime", {})["approval"] = approval
            run["status"] = "waiting"
            _append_run_log(run, f"브라우저 스냅샷 승인 대기: {payload.url}")
            store.save_run(run)
            event = store.add_event(run["id"], "approval.requested", {"run": run, "approval": approval})
            return {"status": "waiting", "approval": approval, "run": run, "event": event}
        snapshot = _browser_snapshot(payload.url)
        if payload.runId:
            artifact = {"id": f"browser-{uuid4().hex[:8]}", "title": snapshot["title"], "type": "browser-snapshot", "content": snapshot}
            stored = store.add_artifact(payload.runId, artifact)
            store.add_event(payload.runId, "browser.snapshot", {"artifact": stored, "snapshot": snapshot})
        return {"status": "complete", "snapshot": snapshot}

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        return {"runs": store.list_runs()}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.get("/api/runs/{run_id}/approvals")
    def list_run_approvals(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        approval = _approval(run)
        return {"approvals": [approval] if approval else []}

    @app.post("/api/runs/{run_id}/approvals/{approval_id}/confirm")
    def confirm_approval(run_id: str, approval_id: str, payload: ApprovalDecisionRequest | None = None) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        approval = _approval(run)
        if not approval or approval.get("id") != approval_id:
            raise HTTPException(status_code=404, detail="Approval not found")
        approval["status"] = "approved"
        approval["input"] = payload.input if payload else {}
        run.setdefault("runtime", {})["approval"] = approval
        if run["status"] == "waiting":
            run["status"] = "running"
        _append_run_log(run, f"승인 완료: {approval_id}")
        store.save_run(run)
        job = store.get_job_for_run(run_id)
        if job:
            supervisor.start_job(str(job["id"]))
        event = store.add_event(run_id, "approval.confirmed", {"run": run, "approval": approval})
        return {"run": run, "approval": approval, "event": event}

    @app.post("/api/runs/{run_id}/approvals/{approval_id}/reject")
    def reject_approval(run_id: str, approval_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        approval = _approval(run)
        if not approval or approval.get("id") != approval_id:
            raise HTTPException(status_code=404, detail="Approval not found")
        approval["status"] = "rejected"
        run.setdefault("runtime", {})["approval"] = approval
        run["status"] = "cancelled"
        _append_run_log(run, f"승인 거절: {approval_id}")
        store.save_run(run)
        event = store.add_event(run_id, "approval.rejected", {"run": run, "approval": approval})
        return {"run": run, "approval": approval, "event": event}

    @app.get("/api/runs/{run_id}/artifacts")
    def get_artifacts(run_id: str) -> dict[str, Any]:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        return {"artifacts": store.list_artifacts(run_id)}

    @app.get("/api/runs/{run_id}/artifacts/validate")
    def validate_run_artifacts(run_id: str) -> dict[str, Any]:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        artifacts = store.list_artifacts(run_id)
        return {"validation": validate_artifacts(artifacts), "artifacts": artifacts}

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
        return Response(content=data, media_type=media_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})

    @app.get("/api/runs/{run_id}/events")
    def get_events(run_id: str, after: int = 0) -> dict[str, Any]:
        if not store.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        return {"events": store.list_events(run_id, after=after)}

    @app.post("/api/runs/{run_id}/pause")
    def pause_run(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run["status"] in TERMINAL_RUN_STATUSES:
            raise HTTPException(status_code=409, detail=f"Run is already {run['status']}")
        run["status"] = "paused"
        _append_run_log(run, "사용자 요청으로 실행을 일시정지했습니다.")
        msg = _assistant_message_id(run)
        if msg:
            store.update_message(msg, status="paused")
        store.save_run(run)
        job = store.get_job_for_run(run_id)
        if job:
            store.update_job(str(job["id"]), "paused")
        event = store.add_event(run_id, "run.paused", {"run": run})
        return {"run": run, "event": event}

    @app.post("/api/runs/{run_id}/resume")
    def resume_run(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run["status"] in TERMINAL_RUN_STATUSES:
            raise HTTPException(status_code=409, detail=f"Run is already {run['status']}")
        run["status"] = "running"
        _append_run_log(run, "사용자 요청으로 실행을 재개했습니다.")
        msg = _assistant_message_id(run)
        if msg:
            store.update_message(msg, status="running")
        store.save_run(run)
        job = store.get_job_for_run(run_id)
        if job:
            store.update_job(str(job["id"]), "running")
            supervisor.start_job(str(job["id"]))
        event = store.add_event(run_id, "run.resumed", {"run": run})
        return {"run": run, "event": event}

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run["status"] in TERMINAL_RUN_STATUSES:
            raise HTTPException(status_code=409, detail=f"Run is already {run['status']}")
        run["status"] = "cancelled"
        _append_run_log(run, "사용자 요청으로 실행을 취소했습니다.")
        msg = _assistant_message_id(run)
        if msg:
            store.update_message(msg, status="cancelled", content="실행이 취소되었습니다.")
        store.save_run(run)
        job = store.get_job_for_run(run_id)
        if job:
            store.update_job(str(job["id"]), "cancelled")
        event = store.add_event(run_id, "run.cancelled", {"run": run})
        return {"run": run, "event": event}

    @app.websocket("/ws/run/{run_id}")
    async def run_stream(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        run = store.get_run(run_id)
        if not run:
            await websocket.send_json({"type": "error", "payload": {"message": "Run not found"}})
            await websocket.close(code=4404)
            return
        try:
            last_event_id = max(0, int(websocket.query_params.get("after", "0")))
        except ValueError:
            last_event_id = 0
        try:
            await websocket.send_json({"type": "run.snapshot", "payload": {"run": run}})
            while True:
                events = store.list_events(run_id, after=last_event_id)
                for event in events:
                    await websocket.send_json(event)
                    last_event_id = int(event["id"])
                    if event["type"] in TERMINAL_EVENT_TYPES:
                        return
                run = store.get_run(run_id)
                if run and run["status"] in TERMINAL_RUN_STATUSES:
                    event_type = "run.done" if run["status"] == "complete" else f"run.{run['status']}"
                    await websocket.send_json({"type": event_type, "payload": {"run": run}})
                    return
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            return

    return app


app = create_app()
