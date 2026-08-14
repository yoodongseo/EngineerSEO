"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { buildApiUrl, fetchJobLogs } from "@/lib/api";

interface LogViewerProps {
  jobId: string;
  status: string;
}

type ConnectionState = "connecting" | "connected" | "disconnected" | "polling";

function splitLogChunk(stdout: string | null | undefined): string[] {
  if (!stdout) return [];

  const normalized = stdout.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");

  if (lines[lines.length - 1] === "") {
    lines.pop();
  }

  return lines;
}

export default function LogViewer({ jobId, status }: LogViewerProps) {
  const [logs, setLogs] = useState("");
  const [connectionState, setConnectionState] =
    useState<ConnectionState>(() =>
      status === "running" || status === "pending" ? "connecting" : "disconnected"
    );
  const [autoScroll, setAutoScroll] = useState(true);
  const [lastOutputAt, setLastOutputAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const bodyRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingOffsetRef = useRef(0);
  const terminalRetryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const appendLines = useCallback((incomingLines: string[]) => {
    if (incomingLines.length === 0) return;

    setLogs((prev) => prev + incomingLines.map((line) => `${line}\n`).join(""));
    pollingOffsetRef.current += incomingLines.length;
    setLastOutputAt(Date.now());
  }, []);

  const syncLogsFromOffset = useCallback(async () => {
    const data = await fetchJobLogs(jobId, pollingOffsetRef.current);
    const incomingLines = splitLogChunk(data.stdout);

    if (incomingLines.length > 0) {
      appendLines(incomingLines);
    }

    pollingOffsetRef.current = data.offset;
    return { data, incomingLines };
  }, [appendLines, jobId]);

  // Polling 폴백
  const startPolling = useCallback(() => {
    if (pollingRef.current) return;
    setConnectionState("polling");

    const poll = async () => {
      try {
        const { data } = await syncLogsFromOffset();
        if (!data.has_more) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setConnectionState("disconnected");
        }
      } catch {
        // silently fail
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 1000);
  }, [syncLogsFromOffset]);

  useEffect(() => {
    if (status !== "running" && status !== "pending") {
      return;
    }

    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [status]);

  // SSE 연결
  useEffect(() => {
    // 완료된 Job은 DB에서 로그 조회
    if (status !== "running" && status !== "pending") {
      const loadFinalLogs = async (attempt = 0) => {
        try {
          const { incomingLines } = await syncLogsFromOffset();

          if (
            attempt < 5 &&
            pollingOffsetRef.current === 0 &&
            incomingLines.length === 0
          ) {
            terminalRetryRef.current = setTimeout(() => {
              void loadFinalLogs(attempt + 1);
            }, 500);
            return;
          }

          setConnectionState("disconnected");
        } catch {
          if (attempt < 5) {
            terminalRetryRef.current = setTimeout(() => {
              void loadFinalLogs(attempt + 1);
            }, 500);
            return;
          }

          setConnectionState("disconnected");
        }
      };

      void loadFinalLogs();

      return;
    }

    // 실행 중인 Job은 SSE 연결
    const es = new EventSource(buildApiUrl(`/api/jobs/${jobId}/stream`));
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionState("connected");
    };

    es.onmessage = (event) => {
      setConnectionState("connected");
      appendLines([event.data.replace(/\r/g, "")]);
    };

    const handleHeartbeat = (event: Event) => {
      setConnectionState("connected");

      try {
        const data = JSON.parse((event as MessageEvent).data) as {
          offset?: number;
        };
        if (typeof data.offset === "number") {
          pollingOffsetRef.current = Math.max(pollingOffsetRef.current, data.offset);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.addEventListener("heartbeat", handleHeartbeat);

    es.addEventListener("done", (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data);
        setLogs(
          (prev) =>
            prev + `\n--- Job ${data.status} (rc=${data.rc ?? "?"}) ---\n`
        );
      } catch {
        // ignore parse errors
      }
      es.close();
      setConnectionState("disconnected");
      void syncLogsFromOffset();
    });

    es.onerror = () => {
      es.close();
      // SSE 실패 시 polling으로 폴백
      startPolling();
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      if (terminalRetryRef.current) {
        clearTimeout(terminalRetryRef.current);
        terminalRetryRef.current = null;
      }
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [appendLines, jobId, startPolling, status, syncLogsFromOffset]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!bodyRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = bodyRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
  };

  const formatLine = (line: string, index: number) => {
    let className = "";
    if (
      line.includes("FAILED") ||
      line.includes("ERROR") ||
      line.includes("fatal")
    ) {
      className = "log-line-error";
    } else if (line.includes("ok:") || line.includes("SUCCESS")) {
      className = "log-line-ok";
    } else if (line.includes("changed:")) {
      className = "log-line-changed";
    } else if (line.includes("TASK [") || line.includes("PLAY [")) {
      className = "log-line-task";
    } else if (line.startsWith("[HARNESS]")) {
      className = "log-line-task";
    }

    return (
      <div key={index} className="log-line">
        <span className="log-line-number">{index + 1}</span>
        <span className={`log-line-content ${className}`}>{line}</span>
      </div>
    );
  };

  const lines = logs.split("\n").filter((l) => l !== "");
  const secondsSinceLastOutput =
    lastOutputAt !== null ? Math.max(0, Math.floor((now - lastOutputAt) / 1000)) : null;

  const secondaryStatusText =
    status === "pending"
      ? "작업 시작 대기 중"
      : connectionState === "connecting"
      ? "실시간 로그 연결 중"
      : connectionState === "polling"
      ? secondsSinceLastOutput !== null
        ? `Polling 수집 중 · 새 출력 대기 ${secondsSinceLastOutput}초`
        : "Polling 수집 중"
      : connectionState === "connected"
      ? secondsSinceLastOutput !== null
        ? `실행 중 · 새 출력 대기 ${secondsSinceLastOutput}초`
        : "실행 중 · 로그 수신 대기"
      : status === "success" || status === "failed" || status === "error"
      ? "실행 완료 로그"
      : "로그 대기 중";

  const connectionIndicator = {
    connecting: { icon: "🟡", text: "연결 중..." },
    connected: { icon: "🟢", text: "Live" },
    disconnected: { icon: "⚫", text: "완료" },
    polling: { icon: "🔵", text: "Polling" },
  };

  const indicator = connectionIndicator[connectionState];

  return (
    <div className="log-viewer">
      <div className="log-viewer-header">
        <span className="log-viewer-title">
          📋 실행 로그
          <span
            style={{
              marginLeft: 12,
              fontSize: 12,
              color:
                connectionState === "connected"
                  ? "var(--color-success)"
                  : connectionState === "polling"
                  ? "var(--color-primary)"
                  : "var(--color-text-muted)",
            }}
          >
            {indicator.icon} {indicator.text}
          </span>
          <span
            style={{
              marginLeft: 8,
              fontSize: 12,
              color: "var(--color-text-muted)",
            }}
          >
            {secondaryStatusText}
          </span>
        </span>
        <div className="flex-center gap-sm">
          <span
            className="text-sm text-muted"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {lines.length} lines
          </span>
          <button
            className="btn btn-secondary"
            style={{ padding: "4px 10px", fontSize: "12px" }}
            onClick={() => {
              setAutoScroll(true);
              if (bodyRef.current) {
                bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
              }
            }}
          >
            ↓ 맨 아래로
          </button>
        </div>
      </div>
      <div ref={bodyRef} className="log-viewer-body" onScroll={handleScroll}>
        {lines.length > 0 ? (
          lines.map((line, i) => formatLine(line, i))
        ) : (
          <span style={{ color: "var(--color-text-muted)" }}>
            {status === "pending"
              ? "⏳ 실행 대기 중..."
              : connectionState === "connecting"
              ? "⏳ SSE 연결 중..."
              : "로그가 없습니다."}
          </span>
        )}
      </div>
    </div>
  );
}
