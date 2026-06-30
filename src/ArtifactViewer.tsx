import { Download, ExternalLink, FileText, GitBranch, Presentation, ShieldCheck } from "lucide-react";
import { getArtifactDownloadLabel, getArtifactDownloadMeta, getArtifactDownloadUrl, formatArtifactSize, sortArtifactsForDisplay } from "./artifactActions";
import type { ActiveRun, Artifact, ArtifactContent } from "./types";
import "./artifact-viewer.css";

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

function asSize(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function getSlides(content?: ArtifactContent): SlidePreview[] {
  const slides = Array.isArray(content?.slides) ? content.slides : [];
  return slides.filter(isRecord).map((slide, index) => {
    const bullets = Array.isArray(slide.bullets) ? slide.bullets.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
    return {
      number: asSize(slide.number) ?? index + 1,
      title: asText(slide.title, `Slide ${index + 1}`),
      message: asText(slide.message ?? slide.body, "슬라이드 메시지가 준비되었습니다."),
      bullets,
    };
  });
}

function ArtifactDownloadAction({ run, artifact }: { run: ActiveRun; artifact: Artifact }) {
  const url = getArtifactDownloadUrl(run, artifact);
  const meta = getArtifactDownloadMeta(artifact);
  const label = getArtifactDownloadLabel(artifact);
  if (!url) {
    return (
      <button className="artifact-download" type="button" onClick={() => void import("./artifactActions").then(({ downloadArtifact }) => downloadArtifact(run, artifact))}>
        <Download />
        {label}
        {meta.sizeBytes ? <span>{formatArtifactSize(meta.sizeBytes)}</span> : null}
      </button>
    );
  }
  return (
    <a className="artifact-download" href={url} target="_blank" rel="noreferrer" download={meta.filename}>
      <Download />
      {label}
      {meta.sizeBytes ? <span>{formatArtifactSize(meta.sizeBytes)}</span> : null}
    </a>
  );
}

function ArtifactOpenAction({ run, artifact }: { run: ActiveRun; artifact: Artifact }) {
  return (
    <button className="artifact-open" type="button" onClick={() => void import("./artifactActions").then(({ openArtifactOnline }) => openArtifactOnline(run, artifact))}>
      <ExternalLink />
      온라인 열기
    </button>
  );
}

function ArtifactActions({ run, artifact }: { run: ActiveRun; artifact: Artifact }) {
  return (
    <div className="artifact-card-actions">
      <ArtifactOpenAction run={run} artifact={artifact} />
      <ArtifactDownloadAction run={run} artifact={artifact} />
    </div>
  );
}

function renderSlides(slides: SlidePreview[]) {
  if (!slides.length) {
    return (
      <div className="artifact-empty">
        <strong>PPTX 프리뷰</strong>
        <span>백엔드 실행 후 슬라이드 구조와 다운로드 파일이 연결됩니다.</span>
      </div>
    );
  }
  return (
    <ol className="slide-preview-list">
      {slides.slice(0, 4).map((slide) => (
        <li key={`${slide.number}-${slide.title}`}>
          <span>{slide.number}</span>
          <div>
            <strong>{slide.title}</strong>
            <small>{slide.message}</small>
            {slide.bullets.length ? <em>{slide.bullets.slice(0, 2).join(" · ")}</em> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

function renderOutline(artifact: Artifact) {
  const slides = getSlides(artifact.content);
  const qualityChecklist = artifact.content?.qualityChecklist;
  const checklist = Array.isArray(qualityChecklist) ? qualityChecklist.filter((item): item is string => typeof item === "string") : [];
  return (
    <>
      {renderSlides(slides)}
      {checklist.length ? (
        <div className="artifact-checklist">
          {checklist.slice(0, 3).map((item) => (
            <span key={item}>
              <ShieldCheck />
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </>
  );
}

function renderGraph(artifact: Artifact) {
  const source = asText(artifact.content?.mermaidSrc, "요청 --> 계획 --> 도구 실행 --> 산출물 검증");
  const nodes = source
    .split(/-->|→|\n/)
    .map((item) => item.replace(/[;{}[\]()]/g, "").trim())
    .filter(Boolean)
    .slice(0, 5);
  const displayNodes = nodes.length ? nodes : ["요청", "계획", "도구 실행", "검증"];
  return (
    <div className="artifact-graph" aria-label="Mermaid-ready agent graph">
      {displayNodes.map((node, index) => (
        <span key={`${node}-${index}`}>
          {node}
          {index < displayNodes.length - 1 ? <em>→</em> : null}
        </span>
      ))}
    </div>
  );
}

function renderResearch(artifact: Artifact) {
  const text = asText(artifact.content?.summary ?? artifact.content?.text ?? artifact.content?.notes, "출처 검증과 요약 본문이 준비됩니다.");
  const artifactCitations = artifact.content?.citations;
  const citations = Array.isArray(artifactCitations) ? artifactCitations.filter(isRecord) : [];
  return (
    <>
      <p className="artifact-copy">{text}</p>
      {citations.length ? (
        <div className="citation-row">
          {citations.slice(0, 3).map((citation, index) => (
            <span key={`${asText(citation.title, "source")}-${index}`}>[{index + 1}] {asText(citation.title ?? citation.url, "출처")}</span>
          ))}
        </div>
      ) : null}
    </>
  );
}

function renderGeneric(artifact: Artifact) {
  const content = artifact.content;
  const text = asText(content?.text ?? content?.summary ?? content?.notes, "");
  if (text) return <p className="artifact-copy">{text}</p>;
  return (
    <div className="artifact-empty">
      <strong>{artifact.type}</strong>
      <span>{artifact.title}</span>
    </div>
  );
}

function ArtifactCard({ run, artifact }: { run: ActiveRun; artifact: Artifact }) {
  const meta = getArtifactDownloadMeta(artifact);
  const slides = getSlides(artifact.content);
  const isPptx = artifact.type === "pptx";
  const isOutline = artifact.type === "outline";
  const isGraph = artifact.type === "graph";
  const isResearch = artifact.type === "research-brief" || artifact.type === "citations";
  const Icon = isPptx ? Presentation : isGraph ? GitBranch : FileText;

  return (
    <article className={`artifact-card-preview ${artifact.type}`}>
      <header>
        <span className="artifact-type-icon">
          <Icon />
        </span>
        <div>
          <strong>{artifact.title}</strong>
          <small>
            {artifact.type}
            {meta.mimeType ? ` · ${meta.mimeType.split("/").pop()}` : ""}
            {meta.sizeBytes ? ` · ${formatArtifactSize(meta.sizeBytes)}` : ""}
          </small>
        </div>
        <ArtifactActions run={run} artifact={artifact} />
      </header>
      {isPptx ? renderSlides(slides) : isOutline ? renderOutline(artifact) : isGraph ? renderGraph(artifact) : isResearch ? renderResearch(artifact) : renderGeneric(artifact)}
    </article>
  );
}

export function ArtifactViewer({ run }: { run: ActiveRun }) {
  const artifacts = sortArtifactsForDisplay(run.artifacts ?? []);
  const pptxArtifact = artifacts.find((artifact) => artifact.type === "pptx");
  return (
    <section className="artifact-preview artifact-viewer" aria-label="Artifact preview">
      <div className="artifact-viewer-header">
        <div>
          <span className="eyebrow">Artifact Viewer</span>
          <strong>{artifacts.length ? `${artifacts.length}개 산출물` : "산출물 대기"}</strong>
        </div>
        {pptxArtifact ? <ArtifactActions run={run} artifact={pptxArtifact} /> : null}
      </div>
      {artifacts.length ? (
        <div className="artifact-card-list">
          {artifacts.slice(0, 3).map((artifact) => (
            <ArtifactCard key={artifact.id} run={run} artifact={artifact} />
          ))}
        </div>
      ) : (
        <div className="artifact-empty">
          <strong>아직 생성된 산출물이 없습니다</strong>
          <span>{run.status === "complete" ? "실행 로그를 확인하세요." : "실행이 진행되면 여기에 프리뷰가 표시됩니다."}</span>
        </div>
      )}
      <div className="preview-lines">
        {run.log.slice(-4).map((line) => (
          <span key={line}>{line}</span>
        ))}
      </div>
    </section>
  );
}
