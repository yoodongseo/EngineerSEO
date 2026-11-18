import { apiFetch } from "./client";

export type JobTargetScope = "inventory" | "group" | "host";

export interface Job {
  id: string;
  project: string;
  playbook: string;
  inventory: string | null;
  inventory_file: string | null;
  inventory_source_type: string | null;
  managed_inventory_id: string | null;
  managed_inventory_revision: number | null;
  target_scope?: JobTargetScope | null;
  target_group_name?: string | null;
  target_host_name?: string | null;
  extra_vars: Record<string, unknown> | null;
  status: "pending" | "running" | "success" | "failed" | "error";
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  rc: number | null;
  error_message: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface JobCreateRequest {
  project: string;
  playbook: string;
  inventory?: string;
  inventory_file?: string;
  managed_inventory_id?: string;
  target_scope?: JobTargetScope;
  target_group_names?: string[] | null;
  target_host_names?: string[] | null;
  extra_vars?: Record<string, unknown>;
  group_vars?: Record<string, Record<string, unknown>> | null;
  host_vars?: Record<string, Record<string, unknown>> | null;
}

export interface JobLogResponse {
  job_id: string;
  status: string;
  stdout: string | null;
  offset: number;
  has_more: boolean;
}

export interface DashboardStatTrendItem {
  date: string;
  success: number;
  failed: number;
}

export interface DashboardStatTopPlaybook {
  name: string;
  count: number;
}

export interface DashboardStatFailureReason {
  reason: string;
  count: number;
  most_frequent_task: string;
}

export interface DashboardStatsResponse {
  active_jobs: number;
  total_jobs_7d: number;
  success_rate_7d: number;
  success_rate_trend_7d: number;
  trends: DashboardStatTrendItem[];
  top_playbooks: DashboardStatTopPlaybook[];
  failure_reasons: DashboardStatFailureReason[];
}

export async function fetchDashboardStats(): Promise<DashboardStatsResponse> {
  return apiFetch("/api/stats/dashboard");
}

export async function fetchJobs(
  status?: string,
  page = 1,
  size = 20,
  project?: string
): Promise<JobListResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (project) params.set("project", project);
  params.set("page", String(page));
  params.set("size", String(size));
  return apiFetch<JobListResponse>(`/api/jobs?${params}`);
}

export async function fetchJob(id: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${encodeURIComponent(id)}`);
}

export async function createJob(data: JobCreateRequest): Promise<Job> {
  return apiFetch<Job>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteJob(id: string): Promise<void> {
  return apiFetch<void>(`/api/jobs/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function fetchJobLogs(
  id: string,
  offset = 0
): Promise<JobLogResponse> {
  return apiFetch<JobLogResponse>(
    `/api/jobs/${encodeURIComponent(id)}/logs?offset=${offset}`
  );
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/health");
}
