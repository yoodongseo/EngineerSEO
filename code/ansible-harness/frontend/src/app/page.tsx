"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import PageErrorState from "@/components/PageErrorState";
import PageShell from "@/components/PageShell";
import StatusBadge from "@/components/StatusBadge";
import {
  fetchJobs,
  deleteJob,
  fetchDashboardStats,
  type Job,
  type JobListResponse,
  type DashboardStatsResponse,
} from "@/lib/api";
import {
  formatDashboardDateTime,
  formatDashboardDuration,
} from "@/lib/format";

const STATUS_FILTERS = [
  { value: "", label: "전체" },
  { value: "running", label: "실행 중" },
  { value: "success", label: "성공" },
  { value: "failed", label: "실패" },
  { value: "pending", label: "대기" },
];

export default function DashboardPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [result, statsResult] = await Promise.all([
        fetchJobs(filter || undefined, page),
        fetchDashboardStats(),
      ]);
      setData(result);
      setStats(statsResult);
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

  const getTrendColor = (val: number) => {
    if (val > 0) return "var(--color-success)";
    if (val < 0) return "var(--color-error)";
    return "var(--color-text-muted)";
  };

  return (
    <PageShell
      title="대시보드"
      subtitle="Ansible 작업실행 현황"
      actions={
        <Link href="/jobs/new" className="btn btn-primary btn-lg">
          🚀 새 작업실행
        </Link>
      }
      contentClassName="app-content dashboard-content fade-in"
    >
      {/* Error State */}
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

      {/* Stats Grid */}
      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-title">
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-info)" }}></div>
                활성 작업
              </div>
              <div className="stat-value">{stats.active_jobs}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-title">
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-success)" }}></div>
                7일 실행 수
              </div>
              <div className="stat-value">{stats.total_jobs_7d}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-title">
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-primary)" }}></div>
                7일 성공률
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
                <div className="stat-value" style={{ color: "var(--color-success)" }}>{stats.success_rate_7d}%</div>
                <div style={{ fontSize: "14px", fontWeight: 400, color: getTrendColor(stats.success_rate_trend_7d) }}>
                  {stats.success_rate_trend_7d > 0 ? "▲ " : ""}{stats.success_rate_trend_7d}%
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-title">
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-error)" }}></div>
                7일 실패
              </div>
              <div className="stat-value" style={{ color: "var(--color-error)" }}>
                {stats.trends.reduce((sum, item) => sum + item.failed, 0)}
              </div>
            </div>
          </div>

          <div className="dashboard-grid-2">
            {/* Chart */}
            <div className="panel" style={{ marginBottom: 0 }}>
              <div className="panel-header">
                <div className="panel-title">최근 14일 실행 추이</div>
              </div>
              <div style={{ display: "flex", gap: "16px", fontSize: "12px", marginBottom: "12px" }}>
                <span style={{ color: "var(--color-success)", fontWeight: 600 }}>― 성공 (Success)</span>
                <span style={{ color: "var(--color-error)", fontWeight: 600 }}>― 실패 (Failed)</span>
              </div>
              <div style={{ width: "100%", height: "250px", position: "relative" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="var(--color-text-muted)" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false}
                      tickFormatter={(val) => val.split("-").slice(1).join("/")} 
                    />
                    <YAxis 
                      stroke="var(--color-text-muted)" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: "var(--color-bg-secondary)", borderColor: "var(--color-border)", borderRadius: "8px", color: "var(--color-text-primary)" }}
                      itemStyle={{ color: "var(--color-text-primary)" }}
                    />
                    <Line type="monotone" dataKey="success" name="성공" stroke="var(--color-success)" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="failed" name="실패" stroke="var(--color-error)" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Top Playbooks */}
            <div className="panel" style={{ marginBottom: 0 }}>
              <div className="panel-header">
                <div className="panel-title">많이 실행된 작업 Top 5</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {stats.top_playbooks.map((playbook, i) => (
                  <div key={i}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "4px" }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginRight: "10px" }}>{playbook.name}</span>
                      <span style={{ fontWeight: 600, flexShrink: 0 }}>{playbook.count}건</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill" style={{ 
                        width: `${Math.min(100, (playbook.count / Math.max(1, stats.top_playbooks[0]?.count || 1)) * 100)}%` 
                      }}></div>
                    </div>
                  </div>
                ))}
                {stats.top_playbooks.length === 0 && (
                  <div style={{ color: "var(--color-text-muted)", fontSize: "13px", textAlign: "center", padding: "20px 0" }}>
                    데이터가 없습니다
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Failure Reasons */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">최근 실패 원인 Breakdown (Error Signatures)</div>
            </div>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>실패 원인 (Error Signature)</th>
                    <th style={{ width: "100px" }}>발생 횟수</th>
                    <th>주요 발생 작업</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.failure_reasons.map((reason, i) => (
                    <tr key={i}>
                      <td style={{ color: "var(--color-error)", fontFamily: "var(--font-mono)", fontSize: "13px", wordBreak: "break-all" }}>
                        {reason.reason}
                      </td>
                      <td>
                        <span style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", color: "var(--color-error)", padding: "4px 8px", borderRadius: "4px", fontWeight: 600, fontSize: "12px" }}>
                          {reason.count}회
                        </span>
                      </td>
                      <td style={{ fontSize: "13px", color: "var(--color-text-muted)" }}>
                        {reason.most_frequent_task}
                      </td>
                    </tr>
                  ))}
                  {stats.failure_reasons.length === 0 && (
                    <tr>
                      <td colSpan={3} className="table-empty">
                        <p>최근 실패한 작업이 없습니다. 🎉</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
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
