"use client";

import { Suspense, useEffect, useMemo, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import {
  fetchAIHealth,
  streamAIChat,
  rebuildAIIndex,
  type AIHealthResponse,
  type AIChatResponse,
  type AITimelineEvent,
} from "@/lib/api";
import AISourceList from "@/components/AISourceList";
import AITimeline from "@/components/AITimeline";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import ChatWorkspaceShell from "@/components/ai/ChatWorkspaceShell";

function getFriendlyErrorMessage(errorString: string | null | undefined, isHealthDetail: boolean = false): string | null {
  if (!errorString) return isHealthDetail ? null : "AI 서비스가 현재 불안정합니다.";
  
  const s = errorString.toLowerCase();
  if (s.includes("index_missing")) return "AI 인덱스를 찾을 수 없습니다.";
  if (s.includes("ollama_unreachable")) return "Ollama 서버에 연결할 수 없습니다.";
  if (s.includes("provider_unreachable")) return "AI 제공자 서버에 연결할 수 없습니다.";
  if (s.includes("model_not_installed")) return "요청한 AI 모델이 설치되어 있지 않습니다.";
  if (s.includes("ollama_request_failed")) return "Ollama 서버 요청에 실패했습니다.";
  if (s.includes("ai_index_rebuild_failed")) return "AI 인덱스 재구성에 실패했습니다.";
  
  if (s.includes("canceled") || s.includes("aborted")) return "질문이 취소되었습니다.";
  
  return isHealthDetail ? errorString : "AI 서비스가 현재 불안정합니다.";
}

function upsertTimelineEvent(
  previousEvents: AITimelineEvent[],
  nextEvent: AITimelineEvent
): AITimelineEvent[] {
  const nextEvents = [...previousEvents];
  const existingIndex = nextEvents.findIndex((event) => event.seq === nextEvent.seq);

  if (existingIndex === -1) {
    nextEvents.push(nextEvent);
  } else {
    nextEvents[existingIndex] = nextEvent;
  }

  return nextEvents.sort((left, right) => left.seq - right.seq);
}

function AIContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");
  const isErrorContract = mode === "error-contract";

  const [health, setHealth] = useState<AIHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [useKnowledgeBase, setUseKnowledgeBase] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [chatResponse, setChatResponse] = useState<AIChatResponse | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<AITimelineEvent[]>([]);

  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const [toast, setToast] = useState<{ title: string; message: string; type: "success" | "error"; id: number } | null>(null);
  const [isToastClosing, setIsToastClosing] = useState(false);
  const toastTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastCloseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, type: "success" | "error") => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    if (toastCloseTimeoutRef.current) clearTimeout(toastCloseTimeoutRef.current);

    setToast({
      title: type === "success" ? "갱신 완료" : "갱신 실패",
      message,
      type,
      id: Date.now(),
    });
    setIsToastClosing(false);

    toastTimeoutRef.current = setTimeout(() => {
      setIsToastClosing(true);
      toastCloseTimeoutRef.current = setTimeout(() => {
        setToast(null);
        setIsToastClosing(false);
      }, 250);
    }, 3200);
  };


  
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

  const effectiveHealthStatus = useMemo(() => {
    if (healthLoading) return "loading";
    if (!useKnowledgeBase && health?.provider_reachable && health?.chat_model_installed) {
      return "ok";
    }
    if (health?.status === "ok") return "ok";
    return "degraded";
  }, [health, healthLoading, useKnowledgeBase]);

  const healthLabel =
    effectiveHealthStatus === "loading"
      ? "Checking..."
      : effectiveHealthStatus === "ok"
      ? "AI Ready"
      : "AI Degraded";

  
  const closeToast = () => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    if (toastCloseTimeoutRef.current) clearTimeout(toastCloseTimeoutRef.current);
    setIsToastClosing(true);
    toastCloseTimeoutRef.current = setTimeout(() => {
      setToast(null);
      setIsToastClosing(false);
    }, 250);
  };

  const executeRebuild = async () => {
    try {
      setIsRebuilding(true);
      setShowConfirmModal(false);
      await rebuildAIIndex();
      showToast("최신 문서를 다시 읽고 인덱스를 안전하게 재구성했습니다.", "success");
      setHealthLoading(true);
      const data = await fetchAIHealth();
      setHealth(data);
      setHealthError(null);
    } catch (err: unknown) {
      showToast(
        `지식베이스를 다시 읽는 중 문제가 발생했습니다. ${err instanceof Error ? err.message : String(err)}`,
        "error"
      );
    } finally {
      setHealthLoading(false);
      setIsRebuilding(false);
    }
  };

  const handleRebuild = () => {
    if (isRebuilding) return;
    setShowConfirmModal(true);
  };

  useEffect(() => {
    async function loadHealth() {
      try {
        const data = await fetchAIHealth();
        setHealth(data);
      } catch (err: unknown) {
        setHealthError(err instanceof Error ? err.message : "Failed to fetch AI health");
      } finally {
        setHealthLoading(false);
      }
    }
    loadHealth();
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
      if (toastCloseTimeoutRef.current) clearTimeout(toastCloseTimeoutRef.current);
    };
  }, []);

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleChatSubmit = async () => {
    if (!question.trim()) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setChatLoading(true);
    setChatError(null);
    setChatResponse(null);
    setTimelineEvents([]);

    try {
            await streamAIChat(
              { question, use_knowledge_base: useKnowledgeBase },
              (sourcesData) => {
                setChatResponse((prev) => ({ ...sourcesData, answer: prev?.answer ?? "" }));
              },
              (chunk) => {
                setChatResponse((prev) => prev ? { ...prev, answer: prev.answer + chunk } : null);
              },
              (timelineEvent) => {
                setTimelineEvents((prev) => upsertTimelineEvent(prev, timelineEvent));
              },
              controller.signal
            );
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        setChatError("canceled");
      } else {
        setChatError(err instanceof Error ? err.message : "Failed to get AI response");
      }
    } finally {
      setChatLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancelChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const latestTimelineEvent = timelineEvents[timelineEvents.length - 1] ?? null;
  const hasTimeline = timelineEvents.length > 0;
  const hasSources = Boolean(chatResponse?.sources?.length);
  const hasAnswer = Boolean(chatResponse?.answer);
  const hasTrailingPanels = hasSources || chatLoading || hasTimeline;
  const isDirectMode = !useKnowledgeBase;
  const waitCapSeconds = useKnowledgeBase ? 180 : 120;
  const isStreamingAnswer = Boolean(chatLoading && chatResponse?.answer);
  const isDelayedWait = !isStreamingAnswer && elapsedSeconds > waitCapSeconds;
  const waitHeadline = latestTimelineEvent?.label ?? (
    chatResponse?.answer
      ? "답변 생성 중..."
      : chatResponse
        ? "답변 작성 중..."
        : useKnowledgeBase
          ? "지식베이스 검색 및 답변 대기 중..."
          : "일반 답변을 준비 중..."
  );
  const waitDetail = latestTimelineEvent?.detail ?? null;
  const canUseDirectChat = Boolean(health?.provider_reachable && health?.chat_model_installed);
  const shouldShowKbHealthIssue = Boolean(useKnowledgeBase && health && health.status === "degraded");
  const shouldShowDirectHealthIssue = Boolean(
    isDirectMode && health && (!health.provider_reachable || !health.chat_model_installed)
  );

  const showErrorBanner = isErrorContract || healthError || shouldShowKbHealthIssue || shouldShowDirectHealthIssue || chatError;

  const errorBanner = showErrorBanner ? (
    <div
      className="card mb-lg"
      style={{
        padding: "var(--spacing-lg)",
        borderColor: "var(--color-error)",
        backgroundColor: "var(--color-error-bg)",
      }}
      data-testid="ai-error-banner"
    >
      <p className="text-error" style={{ fontWeight: 600 }}>
        ⚠️ AI 서비스 연결 오류
      </p>
      <p className="text-sm" style={{ marginTop: 8, color: "var(--color-text-primary)" }}>
        {isErrorContract
          ? "현재 AI 서비스와 통신할 수 없습니다. 잠시 후 다시 시도해주세요."
          : getFriendlyErrorMessage(
              chatError ||
                healthError ||
                (shouldShowDirectHealthIssue
                  ? health?.provider_reachable
                    ? "model_not_installed"
                    : "provider_unreachable"
                  : shouldShowKbHealthIssue
                    ? health?.index_state.detail
                    : null),
              false
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
            data-testid="ai-health-status"
            className="badge"
            style={{ backgroundColor: "var(--color-bg-secondary)" }}
          >
            <span className="spinner" style={{ width: 12, height: 12, marginRight: 6, borderWidth: 2 }}></span>
            {healthLabel}
          </div>
        ) : health && health.status === "ok" ? (
          <div data-testid="ai-health-status" className="badge badge-successful">
            <span className="badge-dot"></span>
            {healthLabel}
          </div>
        ) : (
          <div data-testid="ai-health-status" className="badge badge-failed">
            <span className="badge-dot"></span>
            {healthLabel}
          </div>
        )}
      </div>
      {health && (
        <div className="card-body" style={{ paddingTop: 0, paddingBottom: "var(--spacing-md)" }}>
          <div style={{ display: "flex", gap: "var(--spacing-lg)", fontSize: 13, color: "var(--color-text-secondary)" }}>
            <div>Provider: <span style={{ color: "var(--color-text-primary)" }}>{health.provider}</span></div>
            <div>Model: <span style={{ color: "var(--color-text-primary)" }}>{health.chat_model}</span></div>
            <div>Index: <span style={{ color: "var(--color-text-primary)" }}>{health.index_state.status}</span></div>
          </div>
          {health.index_state.detail && (
            <p style={{ marginTop: 10, fontSize: 12, color: "var(--color-text-muted)" }}>
              {getFriendlyErrorMessage(health.index_state.detail, true)}
            </p>
          )}
          <div style={{ marginTop: "var(--spacing-md)", display: "grid", justifyItems: "end", gap: "var(--spacing-sm)" }}>
            <button
              type="button"
              onClick={handleRebuild}
              disabled={isRebuilding}
              className="btn btn-secondary"
              style={{ fontSize: 13, padding: "6px 12px", minWidth: 170 }}
            >
              {isRebuilding ? "⏳ 지식베이스 갱신 중..." : "🔄 지식베이스 갱신"}
            </button>
            {isRebuilding && (
              <div className="ai-rebuild-status" role="status" aria-live="polite">
                <span className="ai-rebuild-status-icon spinner" aria-hidden="true"></span>
                <div>
                  <strong>지식베이스를 갱신하고 있습니다.</strong>
                  <div className="ai-rebuild-status-text">최신 문서를 다시 읽고 인덱스를 재구성하는 중입니다.</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const promptCard = (
    <div className="card mb-lg">
      <div className="card-body">
        <div className="form-group">
          <label className="form-label" htmlFor="ai-question-input">무엇을 도와드릴까요?</label>
          <div data-testid="ai-kb-toggle" className="ai-kb-toggle">
            <button
              type="button"
              className={`btn ${useKnowledgeBase ? "btn-primary" : "btn-secondary"} ai-kb-toggle-button`.trim()}
              data-testid="ai-kb-toggle-on"
              aria-pressed={useKnowledgeBase}
              data-state={useKnowledgeBase ? "active" : "inactive"}
              onClick={() => setUseKnowledgeBase(true)}
              disabled={chatLoading}
            >
              <span aria-hidden="true">📚</span>
              지식베이스 사용
            </button>
            <button
              type="button"
              className={`btn ${!useKnowledgeBase ? "btn-primary" : "btn-secondary"} ai-kb-toggle-button`.trim()}
              data-testid="ai-kb-toggle-off"
              aria-pressed={!useKnowledgeBase}
              data-state={!useKnowledgeBase ? "active" : "inactive"}
              onClick={() => setUseKnowledgeBase(false)}
              disabled={chatLoading}
            >
              <span aria-hidden="true">💬</span>
              일반 질문
            </button>
          </div>
          <p
            style={{
              marginBottom: "var(--spacing-md)",
              fontSize: 13,
              color: "var(--color-text-secondary)",
              lineHeight: 1.5,
            }}
          >
            {useKnowledgeBase
              ? "지식베이스를 바탕으로 근거 문서를 먼저 찾고, 최대 180초 기준으로 답변을 이어서 생성합니다."
              : "지식베이스를 사용하지 않고 일반 질문에 바로 답변하며, 최대 120초 기준으로 응답을 기다립니다."}
          </p>
          <textarea
            id="ai-question-input"
            className="form-textarea"
            placeholder={useKnowledgeBase ? "예: Nginx 설치 플레이북을 작성해줘" : "예: HTTP와 HTTPS의 차이를 설명해줘"}
            data-testid="ai-question-input"
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
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--spacing-md)" }}>
          {chatLoading && (
            <button
              className="btn btn-secondary"
              data-testid="ai-cancel-button"
              type="button"
              onClick={handleCancelChat}
            >
              🚫 취소
            </button>
          )}
          <button
            className="btn btn-primary"
            data-testid="ai-submit-button"
            type="button"
            onClick={handleChatSubmit}
            disabled={!question.trim() || chatLoading || (isDirectMode && !canUseDirectChat)}
          >
            {chatLoading ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14, marginRight: 8, borderWidth: 2 }}></span>
                답변 생성 중...
              </>
            ) : (
              "✨ 질문하기"
            )}
          </button>
        </div>
      </div>
    </div>
  );

  const answerBody = (
    <>
      {chatLoading && (
        <div data-testid="ai-wait-indicator" style={{ marginBottom: "var(--spacing-lg)", padding: "var(--spacing-md)", backgroundColor: "var(--color-bg-secondary)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 13, color: "var(--color-text-secondary)" }}>
            <span style={{ fontWeight: 500 }}>{waitHeadline}</span>
            <span className="ai-wait-meta">
              {isStreamingAnswer
                ? `답변 생성 경과 시간: ${elapsedSeconds}초`
                : isDelayedWait
                  ? `답변이 지연되고 있습니다 (현재 ${elapsedSeconds}초)...`
                  : `예상 최대 대기시간: ${waitCapSeconds}초 (현재 ${elapsedSeconds}초)`}
            </span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={Math.min(elapsedSeconds, waitCapSeconds)}
            aria-valuemax={waitCapSeconds}
            className="ai-wait-progress-track"
          >
            <div
              data-state={isDelayedWait ? "indeterminate" : "determinate"}
              className="ai-wait-progress-bar"
              style={{
                height: "100%",
                backgroundColor: "var(--color-primary)",
                width: isDelayedWait ? "30%" : `${Math.min((elapsedSeconds / waitCapSeconds) * 100, 100)}%`,
                transition: isDelayedWait ? "none" : "width 1s linear",
                position: isDelayedWait ? "absolute" : "static",
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
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px", borderWidth: 3 }}></div>
          <p>
            {latestTimelineEvent?.detail ?? (useKnowledgeBase
              ? "지식베이스 문서를 검색하고 있습니다..."
              : "일반 질문에 대한 답변을 준비하고 있습니다...")}
          </p>
        </div>
      ) : chatResponse ? (
        <div>
          <div className="ai-answer-stream">
            {chatResponse.answer ? (
              <MarkdownRenderer
                content={chatResponse.answer}
                streaming={chatLoading}
                className="ai-answer-markdown"
              />
            ) : chatLoading ? (
              <span className="text-muted">
                {hasSources
                  ? "선택한 문서를 바탕으로 답변을 작성하고 있습니다..."
                  : "답변을 작성하고 있습니다..."}
              </span>
            ) : null}
            {chatLoading && (
              <span className="ai-answer-cursor" aria-hidden="true">
                █
              </span>
            )}
          </div>
          {!hasAnswer && chatLoading && hasSources && (
            <p
              style={{
                marginTop: "var(--spacing-md)",
                fontSize: 13,
                color: "var(--color-text-muted)",
              }}
            >
              문서를 먼저 읽고 있으며, 곧 답변 텍스트가 실시간으로 이어집니다.
            </p>
          )}
        </div>
      ) : (
        <div
          style={{
            padding: "var(--spacing-2xl)",
            textAlign: "center",
            color: "var(--color-text-muted)",
          }}
        >
          <p style={{ fontSize: 32, marginBottom: 16 }}>🤖</p>
          <p>질문을 입력하면 여기에 답변이 표시됩니다.</p>
        </div>
      )}
    </>
  );

  const lowerPanels = (hasSources && chatResponse) || chatLoading || hasTimeline ? (
    <div className="ai-panel-row">
      {hasSources && chatResponse && (
        <div className="card" data-testid="ai-source-panel">
          <div className="card-header">
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>
              {chatLoading ? "지금 참고 중인 문서" : "이번 답변에 반영된 문서"}
            </h2>
          </div>
          <div className="card-body" style={{ paddingTop: 0 }}>
            <p
              style={{
                marginBottom: "var(--spacing-md)",
                fontSize: 13,
                color: "var(--color-text-secondary)",
                lineHeight: 1.5,
              }}
            >
              {chatLoading
                ? "지식베이스에서 관련 문서를 먼저 찾았습니다. 아래 문서를 바탕으로 답변을 이어서 생성하고 있습니다."
                : "아래 문서를 근거로 이번 답변을 생성했습니다."}
            </p>
            <AISourceList sources={chatResponse.sources} />
          </div>
        </div>
      )}

      {(chatLoading || hasTimeline) && (
        <AITimeline events={timelineEvents} loading={chatLoading} />
      )}
    </div>
  ) : null;

  const modal = showConfirmModal ? (
    <div className="modal-overlay">
      <button
        type="button"
        className="modal-backdrop"
        aria-label="지식베이스 갱신 모달 닫기"
        onClick={() => setShowConfirmModal(false)}
      />
      <div className="modal-content">
        <div className="modal-title">지식베이스 갱신</div>
        <div className="modal-body">
          지식베이스를 갱신하시겠습니까?<br />
          파일 양에 따라 다소 시간이 걸릴 수 있습니다.
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={() => setShowConfirmModal(false)} disabled={isRebuilding}>
            취소
          </button>
          <button type="button" className="btn btn-primary" onClick={executeRebuild} disabled={isRebuilding}>
            {isRebuilding ? "갱신 중..." : "갱신 시작"}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  const toastNode = toast ? (
    <div className="toast-container">
      <div
        key={toast.id}
        className={`toast toast-${toast.type} ${isToastClosing ? "toast-closing" : ""}`.trim()}
        role="status"
        aria-live="polite"
      >
        <span className={`toast-icon toast-icon-${toast.type}`} aria-hidden="true">
          {toast.type === "success" ? "✅" : "⚠️"}
        </span>
        <div className="toast-copy" style={{ flex: 1 }}>
          <strong className="toast-title">{toast.title}</strong>
          <span className="toast-message">{toast.message}</span>
        </div>
        <button
          type="button"
          onClick={closeToast}
          className="toast-close"
          aria-label="알림 닫기"
        >
          ×
        </button>
      </div>
    </div>
  ) : null;

  return (
    <ChatWorkspaceShell
      errorBanner={errorBanner}
      statusCard={statusCard}
      promptCard={promptCard}
      answerBody={answerBody}
      hasTrailingPanels={hasTrailingPanels}
      lowerPanels={lowerPanels}
      modal={modal}
      toast={toastNode}
    />
  );
}

export default function AIPage() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        <Header
          title="AI 어시스턴트"
          subtitle="Ansible 관련 질문을 하거나 문제를 해결하세요"
        />
        <Suspense fallback={<div className="app-content"><div className="spinner" /></div>}>
          <AIContent />
        </Suspense>
      </main>
    </div>
  );
}
