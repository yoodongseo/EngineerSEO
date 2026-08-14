import { apiFetch, buildApiUrl } from "./client";

export interface AIHealthResponse {
  status: "ok" | "degraded";
  provider: string;
  provider_reachable: boolean;
  base_url: string;
  chat_model: string;
  chat_model_installed: boolean;
  embedding_model: string;
  embedding_model_installed: boolean;
  timeout_seconds: number;
  index_state: AIIndexState;
}

export interface AIIndexState {
  status: "missing" | "ready" | "building" | "error";
  document_count: number;
  chunk_count: number;
  last_rebuilt_at: string | null;
  detail: string | null;
}

export interface AISourceItem {
  source: string;
  filename: string;
  doc_group: string;
  ext: string;
  chunk_id: string;
  excerpt: string;
}

export interface AIChatRequest {
  question: string;
  use_knowledge_base?: boolean;
}

export interface AIChatResponse {
  answer: string;
  grounded: boolean;
  sources: AISourceItem[];
  model: string;
  retrieval_count: number;
  index_state: AIIndexState;
}

export type AISourcesData = Omit<AIChatResponse, "answer">;

export type AITimelineCounts = Partial<Record<string, number>>;

export interface AITimelineEvent {
  seq: number;
  stage: string;
  status: string;
  label: string;
  detail: string | null;
  mode: string;
  counts?: AITimelineCounts;
  ts?: string | null;
}

export interface AIIndexRebuildResponse {
  status: string;
  message: string;
  document_count: number;
  chunk_count: number;
  index_path: string;
  index_state: AIIndexState;
}

export interface NvidiaAICapabilities {
  chat: boolean;
  streaming: boolean;
  knowledge_base: boolean;
  index_rebuild: boolean;
  sources: boolean;
  timeline: boolean;
}

export interface NvidiaAIHealthResponse {
  status: "ok" | "degraded";
  provider: "nvidia";
  provider_reachable: boolean;
  base_url: string;
  chat_model: string;
  chat_model_installed: boolean;
  timeout_seconds: number;
  capabilities: NvidiaAICapabilities;
  detail: string | null;
}

export interface NvidiaAIChatRequest {
  question: string;
}

export interface NvidiaAIChatMeta {
  provider: "nvidia";
  model: string;
  grounded: false;
  capabilities: NvidiaAICapabilities;
}

export interface NvidiaAIChunk {
  answer: string;
  answer_so_far: string;
  grounded: false;
  model: string;
  provider: "nvidia";
}

export interface NvidiaAIChatResponse {
  answer: string;
  answer_so_far: string;
  grounded: false;
  model: string;
  provider: "nvidia";
}

export async function fetchAIHealth(): Promise<AIHealthResponse> {
  return apiFetch<AIHealthResponse>("/api/ai/health");
}

export async function submitAIChat(
  data: AIChatRequest,
  signal?: AbortSignal
): Promise<AIChatResponse> {
  return apiFetch<AIChatResponse>("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify(data),
    signal,
  });
}

export async function rebuildAIIndex(): Promise<AIIndexRebuildResponse> {
  return apiFetch<AIIndexRebuildResponse>("/api/ai/index/rebuild", {
    method: "POST",
  });
}

export async function fetchNvidiaAIHealth(): Promise<NvidiaAIHealthResponse> {
  return apiFetch<NvidiaAIHealthResponse>("/api/nvidia-ai/health");
}

export async function streamAIChat(
  request: AIChatRequest,
  onSources: (sourcesData: AISourcesData) => void,
  onChunk: (chunk: string) => void,
  onTimeline?: (event: AITimelineEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = buildApiUrl("/api/ai/chat");
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    let errorDetail = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) errorDetail = errorData.detail;
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(errorDetail);
  }

  if (!response.body) {
    throw new Error("No response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const eventBlock = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = "";
      const eventDataLines: string[] = [];

      const lines = eventBlock.split("\n");
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.substring(7).trim();
        } else if (line.startsWith("data: ")) {
          eventDataLines.push(line.substring(6));
        }
      }

      const eventData = eventDataLines.join("\n");

      if (eventType === "sources" && eventData) {
        onSources(JSON.parse(eventData));
      } else if (eventType === "chunk" && eventData) {
        onChunk(JSON.parse(eventData));
      } else if (eventType === "timeline" && eventData) {
        try {
          const timelineEvent = JSON.parse(eventData) as AITimelineEvent;
          if (onTimeline) {
            onTimeline(timelineEvent);
          }
        } catch (e) {
          console.warn("Failed to parse timeline event:", eventData, e);
        }
      } else if (eventType === "error" && eventData) {
        throw new Error(JSON.parse(eventData));
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
}

export async function streamNvidiaAIChat(
  request: NvidiaAIChatRequest,
  onMeta: (meta: NvidiaAIChatMeta) => void,
  onChunk: (chunk: NvidiaAIChunk) => void,
  onTimeline?: (event: AITimelineEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = buildApiUrl("/api/nvidia-ai/chat");
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    let errorDetail = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) errorDetail = errorData.detail;
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(errorDetail);
  }

  if (!response.body) {
    throw new Error("No response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const eventBlock = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = "";
      const eventDataLines: string[] = [];

      const lines = eventBlock.split("\n");
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.substring(7).trim();
        } else if (line.startsWith("data: ")) {
          eventDataLines.push(line.substring(6));
        }
      }

      const eventData = eventDataLines.join("\n");

      if (eventType === "meta" && eventData) {
        onMeta(JSON.parse(eventData));
      } else if (eventType === "chunk" && eventData) {
        onChunk(JSON.parse(eventData));
      } else if (eventType === "timeline" && eventData) {
        try {
          const timelineEvent = JSON.parse(eventData) as AITimelineEvent;
          if (onTimeline) {
            onTimeline(timelineEvent);
          }
        } catch (e) {
          console.warn("Failed to parse NVIDIA timeline event:", eventData, e);
        }
      } else if (eventType === "error" && eventData) {
        const parsed = JSON.parse(eventData) as { message?: string } | string;
        throw new Error(
          typeof parsed === "string"
            ? parsed
            : parsed.message || "NVIDIA AI request failed"
        );
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
}
