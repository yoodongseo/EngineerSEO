"use client";

import { useMemo } from "react";
import type { AITimelineEvent } from "@/lib/api";

interface AITimelineProps {
  events: AITimelineEvent[];
  loading: boolean;
}

const STATUS_COPY: Record<string, string> = {
  pending: "대기",
  queued: "대기",
  running: "진행 중",
  active: "진행 중",
  in_progress: "진행 중",
  completed: "완료",
  complete: "완료",
  done: "완료",
  success: "완료",
  succeeded: "완료",
  failed: "실패",
  error: "오류",
  cancelled: "취소",
  canceled: "취소",
  skipped: "건너뜀",
};

const MODE_COPY: Record<string, string> = {
  knowledge_base: "지식베이스",
  retrieval: "지식베이스",
  direct: "일반 질문",
  chat: "일반 질문",
  fallback: "폴백",
};

const COUNT_COPY: Record<string, string> = {
  document: "문서",
  documents: "문서",
  chunk: "청크",
  chunks: "청크",
  token: "토큰",
  tokens: "토큰",
  source: "출처",
  sources: "출처",
  match: "매치",
  matches: "매치",
};

function normalizeStatus(status: string): "pending" | "running" | "completed" | "failed" | "neutral" {
  const normalized = status.toLowerCase();

  if (["pending", "queued"].includes(normalized)) {
    return "pending";
  }

  if (["running", "active", "in_progress"].includes(normalized)) {
    return "running";
  }

  if (["completed", "complete", "done", "success", "succeeded"].includes(normalized)) {
    return "completed";
  }

  if (["failed", "error", "cancelled", "canceled"].includes(normalized)) {
    return "failed";
  }

  return "neutral";
}

function formatTimelineTime(ts?: string | null): string | null {
  if (!ts) {
    return null;
  }

  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatStage(stage: string): string {
  return stage
    .split(/[_-]+/)
    .filter(Boolean)
    .join(" ");
}

function formatMode(mode: string): string {
  const normalized = mode.toLowerCase();
  return MODE_COPY[normalized] ?? mode.replace(/[_-]+/g, " ");
}

function formatCountKey(key: string): string {
  const normalized = key.toLowerCase();
  return COUNT_COPY[normalized] ?? key.replace(/[_-]+/g, " ");
}

function isNumberCount(value: number | undefined): value is number {
  return typeof value === "number";
}

export default function AITimeline({ events, loading }: AITimelineProps) {
  const visibleEvents = useMemo(
    () => [...events].sort((left, right) => left.seq - right.seq),
    [events]
  );

  return (
    <div className="card mb-lg" data-testid="ai-timeline-panel">
      <div className="card-header">
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>처리 타임라인</h2>
      </div>
      <div className="card-body" style={{ paddingTop: 0 }}>
        <p className="ai-timeline-summary">
          {loading
            ? "백엔드에서 전달한 처리 이벤트를 순서대로 표시합니다. 답변 생성과 함께 계속 갱신됩니다."
            : "이번 응답 생성 중 기록된 처리 이벤트입니다."}
        </p>

        {visibleEvents.length === 0 ? (
          <div className="ai-timeline-empty">
            <span className="spinner ai-timeline-empty-spinner" aria-hidden="true"></span>
            <div>
              <strong>처리 이벤트 수신 대기 중</strong>
              <p>백엔드가 첫 번째 timeline 이벤트를 보내면 여기에 즉시 표시됩니다.</p>
            </div>
          </div>
        ) : (
          <ol className="ai-timeline-list">
            {visibleEvents.map((event, index) => {
              const statusKey = event.status.toLowerCase();
              const countEntries = Object.entries(event.counts ?? {}).reduce<Array<[string, number]>>(
                (entries, [key, value]) => {
                  if (isNumberCount(value)) {
                    entries.push([key, value]);
                  }

                  return entries;
                },
                []
              );
              const timeLabel = formatTimelineTime(event.ts);

              return (
                <li key={`${event.seq}-${event.stage}-${event.status}`} className="ai-timeline-item" data-status={normalizeStatus(event.status)}>
                  <div className="ai-timeline-rail" aria-hidden="true">
                    <span className="ai-timeline-dot"></span>
                    {index < visibleEvents.length - 1 ? <span className="ai-timeline-line"></span> : null}
                  </div>

                  <article className="ai-timeline-entry">
                    <div className="ai-timeline-entry-header">
                      <div className="ai-timeline-entry-title-wrap">
                        <span className="ai-timeline-seq">#{String(event.seq).padStart(2, "0")}</span>
                        <h3 className="ai-timeline-entry-title">{event.label}</h3>
                      </div>

                      <div className="ai-timeline-entry-meta">
                        <span className="ai-timeline-pill ai-timeline-pill-status">
                          {STATUS_COPY[statusKey] ?? event.status}
                        </span>
                        <span className="ai-timeline-pill">{formatMode(event.mode)}</span>
                        {timeLabel ? <time>{timeLabel}</time> : null}
                      </div>
                    </div>

                    <div className="ai-timeline-stage">stage · {formatStage(event.stage)}</div>

                    {event.detail ? <p className="ai-timeline-detail">{event.detail}</p> : null}

                    {countEntries.length > 0 ? (
                      <div className="ai-timeline-counts">
                        {countEntries.map(([key, value]) => (
                          <span key={key} className="ai-timeline-count-chip">
                            <strong>{value}</strong>
                            <span>{formatCountKey(key)}</span>
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
}
