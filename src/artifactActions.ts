import { backendApiUrl } from "./backendConfig";
import type { ActiveRun, Artifact, ArtifactContent } from "./types";

interface SlidePreview {
  number: number;
  title: string;
  message: string;
  bullets: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function asText(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getSlides(content?: ArtifactContent): SlidePreview[] {
  const slides = Array.isArray(content?.slides) ? content.slides : [];
  return slides.filter(isRecord).map((slide, index) => {
    const bullets = Array.isArray(slide.bullets) ? slide.bullets.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
    return {
      number: asNumber(slide.number) ?? index + 1,
      title: asText(slide.title, `Slide ${index + 1}`),
      message: asText(slide.message ?? slide.body, "슬라이드 메시지가 준비되었습니다."),
      bullets,
    };
  });
}

function getReadableText(artifact: Artifact) {
  return asText(artifact.content?.text ?? artifact.content?.summary ?? artifact.content?.notes, "");
}

export function getArtifactDownloadMeta(artifact: Artifact) {
  const download = artifact.content?.download;
  return {
    filename: artifact.fileName ?? download?.filename ?? download?.fileName ?? artifact.title,
    mimeType: artifact.mimeType ?? download?.mimeType ?? "",
    sizeBytes: artifact.sizeBytes ?? download?.sizeBytes ?? download?.size,
  };
}

export function getArtifactDownloadUrl(run: ActiveRun, artifact: Artifact) {
  if (artifact.downloadUrl) return backendApiUrl(artifact.downloadUrl);
  if (run.source !== "backend") return "";
  return backendApiUrl(`/api/runs/${encodeURIComponent(run.id)}/artifacts/${encodeURIComponent(artifact.id)}/download`);
}

export function formatArtifactSize(sizeBytes?: number) {
  if (!sizeBytes) return "";
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  return `${Math.round(sizeBytes / 102.4) / 10} KB`;
}

export function getArtifactDownloadLabel(artifact: Artifact) {
  const meta = getArtifactDownloadMeta(artifact);
  const filename = meta.filename.toLowerCase();
  const mimeType = meta.mimeType.toLowerCase();
  if (artifact.type === "pptx" || filename.endsWith(".pptx") || mimeType.includes("presentation")) return "PPT 다운로드";
  if (artifact.type === "markdown" || filename.endsWith(".md")) return "MD 다운로드";
  if (artifact.type === "pdf" || filename.endsWith(".pdf")) return "PDF 다운로드";
  if (artifact.type === "web" || mimeType.includes("html")) return "HTML 다운로드";
  return "JSON 다운로드";
}

export function sortArtifactsForDisplay(artifacts: Artifact[]) {
  const priority = (artifact: Artifact) => {
    if (artifact.type === "pptx") return 0;
    if (artifact.type === "markdown" || artifact.type === "pdf" || artifact.type === "web") return 1;
    if (artifact.type === "outline") return 2;
    return 3;
  };
  return [...artifacts].sort((left, right) => priority(left) - priority(right));
}

function saveBlob(filename: string, mimeType: string, data: BlobPart) {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

function base64ToBytes(base64: string) {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export function downloadArtifact(run: ActiveRun, artifact: Artifact) {
  const url = getArtifactDownloadUrl(run, artifact);
  const meta = getArtifactDownloadMeta(artifact);
  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.download = meta.filename;
    link.target = "_blank";
    link.rel = "noreferrer";
    document.body.append(link);
    link.click();
    link.remove();
    return;
  }

  const download = artifact.content?.download;
  if (download?.base64) {
    saveBlob(meta.filename, meta.mimeType || "application/octet-stream", base64ToBytes(download.base64));
    return;
  }

  const fallbackName = meta.filename.endsWith(".json") ? meta.filename : `${meta.filename}.json`;
  saveBlob(fallbackName, "application/json", JSON.stringify({ runId: run.id, artifact }, null, 2));
}

function renderSlides(slides: SlidePreview[]) {
  if (!slides.length) return "";
  return `<section class="slides">${slides
    .map(
      (slide) => `<article class="slide">
        <span>${slide.number}</span>
        <div>
          <h2>${escapeHtml(slide.title)}</h2>
          <p>${escapeHtml(slide.message)}</p>
          ${slide.bullets.length ? `<ul>${slide.bullets.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("")}</ul>` : ""}
        </div>
      </article>`,
    )
    .join("")}</section>`;
}

function renderArtifactBody(artifact: Artifact) {
  const slides = getSlides(artifact.content);
  if (slides.length) return renderSlides(slides);

  const text = getReadableText(artifact);
  if (text) {
    return `<section class="document">${text
      .split(/\n{2,}/)
      .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
      .join("")}</section>`;
  }

  if (artifact.content?.mermaidSrc) {
    return `<pre class="code">${escapeHtml(artifact.content.mermaidSrc)}</pre>`;
  }

  return `<pre class="code">${escapeHtml(JSON.stringify(artifact.content ?? artifact, null, 2))}</pre>`;
}

function buildArtifactPreviewHtml(run: ActiveRun, artifact: Artifact) {
  const meta = getArtifactDownloadMeta(artifact);
  const downloadUrl = getArtifactDownloadUrl(run, artifact);
  const downloadLabel = getArtifactDownloadLabel(artifact);
  const downloadAction = downloadUrl
    ? `<a class="primary" href="${escapeHtml(downloadUrl)}" download="${escapeHtml(meta.filename)}">${escapeHtml(downloadLabel)}</a>`
    : "";
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(artifact.title)} · Nanus Artifact</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #141414; color: #f5f5f5; }
    body { margin: 0; background: #141414; }
    .shell { min-height: 100vh; padding: 28px; box-sizing: border-box; }
    header { position: sticky; top: 0; z-index: 2; display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 14px 0 18px; background: #141414; border-bottom: 1px solid #303030; }
    h1 { margin: 0; max-width: 920px; font-size: clamp(22px, 3vw, 38px); line-height: 1.15; }
    small { display: block; margin-top: 8px; color: #9d9d9d; font-size: 13px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    a, button { min-height: 36px; padding: 0 13px; border: 1px solid #3a3a3a; border-radius: 10px; background: #232323; color: #f5f5f5; font-weight: 750; text-decoration: none; cursor: pointer; }
    .primary { border-color: #1e88ff; background: #1e88ff; color: white; }
    main { display: grid; gap: 14px; max-width: 980px; margin: 22px auto 0; }
    .slides { display: grid; gap: 12px; }
    .slide { display: grid; grid-template-columns: 42px minmax(0, 1fr); gap: 14px; padding: 18px; border: 1px solid #303030; border-radius: 14px; background: #1f1f1f; }
    .slide > span { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; background: rgba(30, 136, 255, .16); color: #58a6ff; font-weight: 850; }
    h2 { margin: 0; font-size: 20px; }
    p { color: #d2d2d2; line-height: 1.7; }
    ul { margin: 10px 0 0; padding-left: 18px; color: #cbd5e1; line-height: 1.65; }
    .document { padding: 20px; border: 1px solid #303030; border-radius: 14px; background: #1f1f1f; }
    .code { overflow: auto; padding: 18px; border: 1px solid #303030; border-radius: 14px; background: #101010; color: #d7d7d7; line-height: 1.55; }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>${escapeHtml(artifact.title)}</h1>
        <small>${escapeHtml(artifact.type)} · ${escapeHtml(meta.mimeType || "Nanus artifact")}${meta.sizeBytes ? ` · ${formatArtifactSize(meta.sizeBytes)}` : ""}</small>
      </div>
      <div class="actions">
        ${downloadAction}
        <button type="button" onclick="window.print()">PDF 저장</button>
      </div>
    </header>
    <main>${renderArtifactBody(artifact)}</main>
  </div>
</body>
</html>`;
}

export function openArtifactOnline(run: ActiveRun, artifact: Artifact) {
  const explicitUrl = asText(artifact.content?.url ?? artifact.content?.previewUrl ?? artifact.content?.webUrl, "");
  if (explicitUrl) {
    window.open(explicitUrl, "_blank", "noopener,noreferrer");
    return;
  }

  const blob = new Blob([buildArtifactPreviewHtml(run, artifact)], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const opened = window.open(url, "_blank", "noopener,noreferrer");
  if (!opened) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    document.body.append(link);
    link.click();
    link.remove();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
