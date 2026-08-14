"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import AITimeline from "@/components/AITimeline";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import ChatWorkspaceShell from "@/components/ai/ChatWorkspaceShell";
import {
  fetchNvidiaAIHealth,
  streamNvidiaAIChat,
  type AITimelineEvent,
  type NvidiaAIChatMeta,
  type NvidiaAIChatResponse,
  type NvidiaAIHealthResponse,
} from "@/lib/api";

function getFriendlyNvidiaErrorMessage(
  errorString: string | null | undefined,
  isHealthDetail: boolean = false,
): string | null {
  if (!errorString)
    return isHealthDetail ? null : "NVIDIA AI 서비스가 현재 불안정합니다.";

  const s = errorString.toLowerCase();
  if (s.includes("provider_unreachable"))
    return "NVIDIA AI 제공자 서버에 연결할 수 없습니다.";
  if (s.includes("model_not_installed"))
    return "설정한 NVIDIA 모델을 사용할 수 없습니다.";
  if (s.includes("nvidia_request_failed"))
    return "NVIDIA AI 요청에 실패했습니다.";
  if (s.includes("canceled") || s.includes("aborted"))
    return "질문이 취소되었습니다.";

  return isHealthDetail ? errorString : "NVIDIA AI 서비스가 현재 불안정합니다.";
}

function upsertTimelineEvent(
  previousEvents: AITimelineEvent[],
  nextEvent: AITimelineEvent,
): AITimelineEvent[] {
  const nextEvents = [...previousEvents];
  const existingIndex = nextEvents.findIndex(
    (event) => event.seq === nextEvent.seq,
  );

  if (existingIndex === -1) {
    nextEvents.push(nextEvent);
  } else {
    nextEvents[existingIndex] = nextEvent;
  }

  return nextEvents.sort((left, right) => left.seq - right.seq);
}

export default function NvidiaAIPage() {
  const [health, setHealth] = useState<NvidiaAIHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatMeta, setChatMeta] = useState<NvidiaAIChatMeta | null>(null);
  const [chatResponse, setChatResponse] = useState<NvidiaAIChatResponse | null>(
    null,
  );
  const [timelineEvents, setTimelineEvents] = useState<AITimelineEvent[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (chatLoading) {
      setElapsedSeconds(0);
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(interval);
  }, [chatLoading]);

  useEffect(() => {
    async function loadHealth() {
      try {
        const data = await fetchNvidiaAIHealth();
        setHealth(data);
      } catch (err: unknown) {
        setHealthError(
          err instanceof Error
            ? err.message
            : "Failed to fetch NVIDIA AI health",
        );
      } finally {
        setHealthLoading(false);
      }
    }

    loadHealth();
  }, []);

  const canChat = Boolean(
    health?.provider_reachable && health?.chat_model_installed,
  );
  const effectiveHealthStatus = useMemo(() => {
    if (healthLoading) return "loading";
    if (health?.status === "ok") return "ok";
    return "degraded";
  }, [health, healthLoading]);

  const healthLabel =
    effectiveHealthStatus === "loading"
      ? "Checking..."
      : effectiveHealthStatus === "ok"
        ? "NVIDIA AI Ready"
        : "NVIDIA AI Degraded";

  const handleCancelChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleChatSubmit = async () => {
    if (!question.trim()) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setChatLoading(true);
    setChatError(null);
    setChatMeta(null);
    setChatResponse(null);
    setTimelineEvents([]);

    try {
      await streamNvidiaAIChat(
        { question },
        (meta) => {
          setChatMeta(meta);
        },
        (chunk) => {
          setChatResponse((prev: NvidiaAIChatResponse | null) => ({
            answer: prev?.answer_so_far ?? "",
            answer_so_far: chunk.answer_so_far,
            grounded: false,
            model: chunk.model,
            provider: chunk.provider,
          }));
        },
        (timelineEvent) => {
          setTimelineEvents((prev) => upsertTimelineEvent(prev, timelineEvent));
        },
        controller.signal,
      );
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        setChatError("canceled");
      } else {
        setChatError(
          err instanceof Error
            ? err.message
            : "Failed to get NVIDIA AI response",
        );
      }
    } finally {
      setChatLoading(false);
      abortControllerRef.current = null;
    }
  };

  const latestTimelineEvent = timelineEvents[timelineEvents.length - 1] ?? null;
  const hasTimeline = timelineEvents.length > 0;
  const hasTrailingPanels = chatLoading || hasTimeline;
  const showErrorBanner = Boolean(
    healthError ||
    chatError ||
    (health && (!health.provider_reachable || !health.chat_model_installed)),
  );
  const waitHeadline =
    latestTimelineEvent?.label ??
    (chatResponse?.answer_so_far
      ? "응답 생성 중..."
      : "NVIDIA 응답 대기 중...");
  const waitDetail = latestTimelineEvent?.detail ?? null;

  const errorBanner = showErrorBanner ? (
    <div
      className="card mb-lg"
      style={{
        padding: "var(--spacing-lg)",
        borderColor: "var(--color-error)",
        backgroundColor: "var(--color-error-bg)",
      }}
      data-testid="nvidia-ai-error-banner"
    >
      <p className="text-error" style={{ fontWeight: 600 }}>
        ⚠️ NVIDIA AI 서비스 연결 오류
      </p>
      <p
        className="text-sm"
        style={{ marginTop: 8, color: "var(--color-text-primary)" }}
      >
        {getFriendlyNvidiaErrorMessage(
          chatError ||
            healthError ||
            (health && !health.provider_reachable
              ? "provider_unreachable"
              : health && !health.chat_model_installed
                ? "model_not_installed"
                : health?.detail),
          false,
        )}
      </p>
    </div>
  ) : null;

  const statusCard = (
    <div className="card mb-lg">
      <div className="card-header">
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>시스템 상태</h2>
        {healthLoading ? (
          <div
            data-testid="nvidia-ai-health-status"
            className="badge"
            style={{ backgroundColor: "var(--color-bg-secondary)" }}
          >
            <span
              className="spinner"
              style={{ width: 12, height: 12, marginRight: 6, borderWidth: 2 }}
            ></span>
            {healthLabel}
          </div>
        ) : health && health.status === "ok" ? (
          <div
            data-testid="nvidia-ai-health-status"
            className="badge badge-successful"
          >
            <span className="badge-dot"></span>
            {healthLabel}
          </div>
        ) : (
          <div
            data-testid="nvidia-ai-health-status"
            className="badge badge-failed"
          >
            <span className="badge-dot"></span>
            {healthLabel}
          </div>
        )}
      </div>
      {health && (
        <div
          className="card-body"
          style={{ paddingTop: 0, paddingBottom: "var(--spacing-md)" }}
        >
          <div
            style={{
              display: "flex",
              gap: "var(--spacing-lg)",
              fontSize: 13,
              color: "var(--color-text-secondary)",
            }}
          >
            <div>
              Provider:{" "}
              <span style={{ color: "var(--color-text-primary)" }}>
                {health.provider}
              </span>
            </div>
            <div>
              Model:{" "}
              <span style={{ color: "var(--color-text-primary)" }}>
                {health.chat_model}
              </span>
            </div>
            <div>
              Streaming:{" "}
              <span style={{ color: "var(--color-text-primary)" }}>
                {health.capabilities.streaming ? "enabled" : "disabled"}
              </span>
            </div>
          </div>
          {health.detail && (
            <p
              style={{
                marginTop: 10,
                fontSize: 12,
                color: "var(--color-text-muted)",
              }}
            >
              {getFriendlyNvidiaErrorMessage(health.detail, true)}
            </p>
          )}
        </div>
      )}
    </div>
  );

  const promptCard = (
    <div className="card mb-lg">
      <div className="card-body">
        <div className="form-group">
          <label className="form-label" htmlFor="nvidia-ai-question-input">
            무엇을 도와드릴까요?
          </label>
          <p
            style={{
              marginBottom: "var(--spacing-md)",
              fontSize: 13,
              color: "var(--color-text-secondary)",
              lineHeight: 1.5,
            }}
          >
            NVIDIA 호환 호스팅 모델로 직접 채팅합니다. 현재 단계에서는
            지식베이스 검색과 인덱스 재구성 없이 채팅만 지원합니다.
          </p>
          <textarea
            id="nvidia-ai-question-input"
            className="form-textarea"
            placeholder="예: Ansible 롤 구조를 간단히 설명해줘"
            data-testid="nvidia-ai-question-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleChatSubmit();
              }
            }}
            disabled={chatLoading}
          ></textarea>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "var(--spacing-md)",
          }}
        >
          {chatLoading && (
            <button
              className="btn btn-secondary"
              data-testid="nvidia-ai-cancel-button"
              type="button"
              onClick={handleCancelChat}
            >
              🚫 취소
            </button>
          )}
          <button
            className="btn btn-primary"
            data-testid="nvidia-ai-submit-button"
            type="button"
            onClick={handleChatSubmit}
            disabled={!question.trim() || chatLoading || !canChat}
          >
            {chatLoading ? (
              <>
                <span
                  className="spinner"
                  style={{
                    width: 14,
                    height: 14,
                    marginRight: 8,
                    borderWidth: 2,
                  }}
                ></span>
                답변 생성 중...
              </>
            ) : (
              "✨ NVIDIA에게 질문하기"
            )}
          </button>
        </div>
      </div>
    </div>
  );

  const answerBody = (
    <>
      {chatLoading && (
        <div
          data-testid="nvidia-ai-wait-indicator"
          style={{
            marginBottom: "var(--spacing-lg)",
            padding: "var(--spacing-md)",
            backgroundColor: "var(--color-bg-secondary)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 8,
              fontSize: 13,
              color: "var(--color-text-secondary)",
            }}
          >
            <span style={{ fontWeight: 500 }}>{waitHeadline}</span>
            <span className="ai-wait-meta">
              응답 생성 경과 시간: {elapsedSeconds}초
            </span>
          </div>
          <div className="ai-wait-progress-track">
            <div
              className="ai-wait-progress-bar"
              style={{
                height: "100%",
                backgroundColor: "var(--color-primary)",
                width: `${Math.min((elapsedSeconds / 120) * 100, 100)}%`,
                transition: "width 1s linear",
                borderRadius: 3,
              }}
            />
          </div>
          {waitDetail && <p className="ai-wait-detail">{waitDetail}</p>}
        </div>
      )}

      {chatLoading && !chatResponse ? (
        <div
          style={{
            padding: "var(--spacing-xl)",
            textAlign: "center",
            color: "var(--color-text-muted)",
          }}
        >
          <div
            className="spinner"
            style={{
              width: 32,
              height: 32,
              margin: "0 auto 16px",
              borderWidth: 3,
            }}
          ></div>
          <p>
            {latestTimelineEvent?.detail ??
              "NVIDIA 응답을 준비하고 있습니다..."}
          </p>
        </div>
      ) : chatResponse ? (
        <div>
          {chatMeta && (
            <p
              style={{
                marginBottom: "var(--spacing-md)",
                fontSize: 12,
                color: "var(--color-text-muted)",
              }}
            >
              Provider: {chatMeta.provider} · Model: {chatMeta.model}
            </p>
          )}
          <div className="ai-answer-stream">
            {chatResponse.answer_so_far ? (
              <MarkdownRenderer
                content={chatResponse.answer_so_far}
                streaming={chatLoading}
                className="ai-answer-markdown"
              />
            ) : chatLoading ? (
              <span className="text-muted">답변을 작성하고 있습니다...</span>
            ) : null}
            {chatLoading && (
              <span className="ai-answer-cursor" aria-hidden="true">
                █
              </span>
            )}
          </div>
        </div>
      ) : (
        <div
          style={{
            padding: "var(--spacing-2xl)",
            textAlign: "center",
            color: "var(--color-text-muted)",
          }}
        >
          <p style={{ fontSize: 32, marginBottom: 16 }}>🟢</p>
          <p>NVIDIA 모델에 질문하면 여기에 답변이 표시됩니다.</p>
        </div>
      )}
    </>
  );

  const lowerPanels =
    chatLoading || hasTimeline ? (
      <div className="ai-panel-row">
        <AITimeline events={timelineEvents} loading={chatLoading} />
      </div>
    ) : null;

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        <Header
          title="AI 어시스턴트"
          subtitle="NVIDIA 호환 호스팅 모델과 직접 채팅합니다"
        />
        <ChatWorkspaceShell
          errorBanner={errorBanner}
          statusCard={statusCard}
          promptCard={promptCard}
          answerBody={answerBody}
          hasTrailingPanels={hasTrailingPanels}
          lowerPanels={lowerPanels}
        />
      </main>
    </div>
  );
}
