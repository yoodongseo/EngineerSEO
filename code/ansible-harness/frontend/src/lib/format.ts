export function formatDashboardDateTime(value: string | null): string {
  if (!value) return "-";

  return new Date(value).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatJobDetailDateTime(value: string | null): string {
  if (!value) return "-";

  return new Date(value).toLocaleString("ko-KR");
}

export function formatDashboardDuration(
  startedAt: string | null,
  finishedAt: string | null,
  nowMs: number = Date.now(),
): string {
  if (!startedAt) return "-";

  const seconds = getDurationSeconds(startedAt, finishedAt, nowMs);
  if (seconds < 60) return `${seconds}s`;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatJobDetailDuration(
  startedAt: string | null,
  finishedAt: string | null,
  nowMs: number = Date.now(),
): string {
  if (!startedAt) return "-";

  const seconds = getDurationSeconds(startedAt, finishedAt, nowMs);
  if (seconds < 60) return `${seconds}초`;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}분 ${remainingSeconds}초`;
}

function getDurationSeconds(
  startedAt: string,
  finishedAt: string | null,
  nowMs: number,
): number {
  const startMs = new Date(startedAt).getTime();
  const endMs = finishedAt ? new Date(finishedAt).getTime() : nowMs;
  return Math.round((endMs - startMs) / 1000);
}
