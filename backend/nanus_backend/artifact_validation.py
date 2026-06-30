from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from zipfile import BadZipFile, ZipFile
from io import BytesIO

PPTX_REQUIRED = {"[Content_Types].xml", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"}
XLSX_REQUIRED = {"[Content_Types].xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"}


def _decode_download(artifact: dict[str, Any]) -> tuple[bytes | None, str, str, list[str]]:
    content = artifact.get("content") if isinstance(artifact.get("content"), dict) else {}
    download = content.get("download") if isinstance(content, dict) else None
    if not isinstance(download, dict):
        return None, "", "", []
    errors: list[str] = []
    filename = str(download.get("filename") or artifact.get("fileName") or artifact.get("title") or "")
    mime = str(download.get("mimeType") or artifact.get("mimeType") or "")
    encoded = download.get("base64")
    if not isinstance(encoded, str):
        return None, filename, mime, [f"{artifact.get('id')}: missing base64 download payload"]
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        return None, filename, mime, [f"{artifact.get('id')}: invalid base64 payload: {exc}"]
    declared_size = download.get("size") or download.get("sizeBytes") or artifact.get("sizeBytes")
    if isinstance(declared_size, int) and declared_size != len(data):
        errors.append(f"{artifact.get('id')}: declared size {declared_size} != actual size {len(data)}")
    if not filename:
        errors.append(f"{artifact.get('id')}: missing filename")
    if not mime:
        errors.append(f"{artifact.get('id')}: missing mime type")
    return data, filename, mime, errors


def _zip_contains(data: bytes, required: set[str]) -> list[str]:
    try:
        with ZipFile(BytesIO(data)) as package:
            names = set(package.namelist())
    except BadZipFile as exc:
        return [f"invalid zip package: {exc}"]
    missing = sorted(required - names)
    return [f"missing package part: {name}" for name in missing]


def validate_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(artifact.get("type") or "")
    data, filename, mime, errors = _decode_download(artifact)
    warnings: list[str] = []
    checks: list[str] = []
    if data is None:
        if artifact_type in {"pptx", "spreadsheet", "visualization", "markdown"} and isinstance(artifact.get("content"), dict):
            content = artifact.get("content", {})
            if content.get("text") or content.get("spec") or content.get("slides"):
                checks.append("preview-content-present")
                return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks}
        return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks}
    if artifact_type == "pptx" or filename.endswith(".pptx"):
        errors.extend(_zip_contains(data, PPTX_REQUIRED))
        checks.append("pptx-package")
    elif artifact_type == "spreadsheet" or filename.endswith(".xlsx"):
        errors.extend(_zip_contains(data, XLSX_REQUIRED))
        checks.append("xlsx-package")
    elif artifact_type == "visualization" or filename.endswith(".html"):
        text = data.decode("utf-8", errors="replace").lower()
        if "<html" not in text or "</html" not in text:
            errors.append(f"{artifact.get('id')}: invalid html artifact")
        checks.append("html-document")
    elif artifact_type == "markdown" or filename.endswith(".md"):
        text = data.decode("utf-8", errors="replace")
        if len(text.strip()) < 40:
            errors.append(f"{artifact.get('id')}: markdown artifact too short")
        checks.append("markdown-document")
    elif artifact_type == "citations":
        try:
            json.loads(data.decode("utf-8"))
            checks.append("json-citations")
        except json.JSONDecodeError as exc:
            warnings.append(f"{artifact.get('id')}: citations download is not JSON: {exc}")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks}


def validate_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    for artifact in artifacts:
        result = validate_artifact(artifact)
        errors.extend(result["errors"])
        warnings.extend(result["warnings"])
        checks.extend(result["checks"])
    return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks}
