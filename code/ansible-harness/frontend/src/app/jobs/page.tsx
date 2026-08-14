"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import PageErrorState from "@/components/PageErrorState";
import PageShell from "@/components/PageShell";
import StatusBadge from "@/components/StatusBadge";
import { fetchJobs, deleteJob, type Job, type JobListResponse } from "@/lib/api";
import { formatDashboardDateTime, formatDashboardDuration } from "@/lib/format";

const STATUS_FILTERS = [
  { value: "", label: "전체" },
  { value: "running", label: "실행 중" },
  { value: "success", label: "성공" },
  { value: "failed", label: "실패" },
  { value: "pending", label: "대기" },
];

export default function JobsPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchJobs(filter || undefined, page);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [filter, page]);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 10000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  const handleDelete = async (id: string) => {
    if (!confirm("이 Job을 삭제하시겠습니까?")) return;
    try {
      await deleteJob(id);
      loadJobs();
    } catch (err) {
      alert(err instanceof Error ? err.message : "삭제 실패");
    }
  };

  return (
    <PageShell
      title="작업 내역"
      subtitle="실행된 Ansible 작업들의 상세 목록입니다"
      actions={
        <Link href="/jobs/new" className="btn btn-primary btn-lg">
          🚀 새 작업실행
        </Link>
      }
      contentClassName="app-content dashboard-content fade-in"
    >
      {error && (
        <PageErrorState
          message={`⚠️ ${error}`}
          helper="백엔드 서버가 실행 중인지 확인해주세요."
          className="card"
          style={{
            padding: "var(--spacing-lg)",
            borderColor: "var(--color-error)",
            marginBottom: "var(--spacing-lg)",
          }}
        />
      )}

      {/* Filter Bar */}
      <div className="filter-bar">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            className={`filter-chip ${filter === f.value ? "active" : ""}`}
            onClick={() => {
              setFilter(f.value);
              setPage(1);
            }}
          >
            {f.label}
            {f.value === "" && data && (
              <span style={{ marginLeft: 4, opacity: 0.6 }}>
                ({data.total})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Jobs Table */}
      <div className="card dashboard-table-card">
        <div className="table-wrapper dashboard-table-wrapper">
          <table className="table dashboard-table">
            <thead>
              <tr>
                <th>상태</th>
                <th>프로젝트</th>
                <th>플레이북</th>
                <th>생성 시간</th>
                <th>소요 시간</th>
                <th className="dashboard-actions-cell">작업</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <tr>
                  <td colSpan={6} className="table-empty">
                    <div className="flex-center gap-md">
                      <div className="spinner" />
                      <span>로딩 중...</span>
                    </div>
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-empty">
                    <p style={{ fontSize: 32, marginBottom: 8 }}>📭</p>
                    <p>실행된 Job이 없습니다.</p>
                    <Link
                      href="/jobs/new"
                      className="btn btn-primary"
                      style={{ marginTop: 16 }}
                    >
                      🚀 첫 작업실행하기
                    </Link>
                  </td>
                </tr>
              ) : (
                data?.items.map((job: Job) => (
                  <tr key={job.id}>
                    <td>
                      <StatusBadge status={job.status} />
                    </td>
                    <td>
                      <span
                        style={{
                          background: "var(--color-surface-elevated)",
                          padding: "2px 8px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: 12,
                          color: "var(--color-primary)",
                          fontWeight: 500,
                        }}
                      >
                        {job.project}
                      </span>
                    </td>
                    <td>
                      <Link
                        href={`/jobs/${job.id}`}
                        style={{ color: "var(--color-text-primary)" }}
                      >
                        {job.playbook}
                      </Link>
                    </td>
                    <td>{formatDashboardDateTime(job.created_at)}</td>
                    <td>
                      {formatDashboardDuration(
                        job.started_at,
                        job.finished_at,
                      )}
                    </td>
                    <td className="dashboard-actions-cell">
                      <div className="dashboard-actions gap-sm">
                        <Link
                          href={`/jobs/${job.id}`}
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: 12 }}
                        >
                          상세
                        </Link>
                        {job.status !== "pending" &&
                          job.status !== "running" && (
                            <button
                              className="btn btn-danger"
                              style={{ padding: "4px 10px", fontSize: 12 }}
                              onClick={() => handleDelete(job.id)}
                            >
                              삭제
                            </button>
                          )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "var(--spacing-sm)",
              padding: "var(--spacing-md)",
              borderTop: "1px solid var(--color-border)",
            }}
          >
            <button
              className="btn btn-secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ← 이전
            </button>
            <span className="text-sm text-muted">
              {page} / {data.pages}
            </span>
            <button
              className="btn btn-secondary"
              disabled={page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              다음 →
            </button>
          </div>
        )}
      </div>
    </PageShell>
  );
}
