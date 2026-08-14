"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import PageErrorState from "@/components/PageErrorState";
import PageLoadingState from "@/components/PageLoadingState";
import PageShell from "@/components/PageShell";
import StatusBadge from "@/components/StatusBadge";
import LogViewer from "@/components/LogViewer";
import { fetchJob, deleteJob, type Job } from "@/lib/api";
import {
  formatJobDetailDateTime,
  formatJobDetailDuration,
} from "@/lib/format";

function formatJobTarget(job: Job): string | null {
  if (job.target_scope === "host") {
    const path = [job.target_group_name, job.target_host_name].filter(
      (value): value is string => Boolean(value)
    );
    return path.length > 0 ? `개별 호스트 · ${path.join(" / ")}` : "개별 호스트";
  }

  if (job.target_scope === "group") {
    return job.target_group_name
      ? `그룹 · ${job.target_group_name}`
      : "그룹";
  }

  if (job.target_scope === "inventory") {
    return "전체 인벤토리";
  }

  if (job.managed_inventory_id) {
    return "전체 인벤토리";
  }

  return null;
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const jobStatusRef = useRef<Job["status"] | null>(null);

  const loadJob = useCallback(async () => {
    try {
      const data = await fetchJob(jobId);
      setJob(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Job을 불러올 수 없습니다");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    jobStatusRef.current = job?.status ?? null;
  }, [job?.status]);

  useEffect(() => {
    loadJob();
    // Job이 실행 중이거나 대기 중일 때만 1초마다 갱신
    const interval = setInterval(() => {
      if (
        jobStatusRef.current === "running" ||
        jobStatusRef.current === "pending" ||
        jobStatusRef.current === null
      ) {
        loadJob();
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [loadJob]);

  const handleDelete = async () => {
    if (!confirm("이 Job을 삭제하시겠습니까?")) return;
    try {
      await deleteJob(jobId);
      router.push("/");
    } catch (err) {
      alert(err instanceof Error ? err.message : "삭제 실패");
    }
  };

  const targetSummary = job ? formatJobTarget(job) : null;

  if (loading) {
    return (
      <PageShell title="Job 상세" contentClassName="app-content flex-center">
        <PageLoadingState minHeight={400} />
      </PageShell>
    );
  }

  if (error || !job) {
    return (
      <PageShell title="Job 상세" contentClassName="app-content">
        <PageErrorState
          message={`⚠️ ${error || "Job을 찾을 수 없습니다"}`}
          messageStyle={{ fontSize: 18 }}
          className="card card-body"
          style={{ textAlign: "center" }}
          action={
            <Link href="/" className="btn btn-primary">
              ← 대시보드로
            </Link>
          }
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      title={`Job: ${job.project} / ${job.playbook}`}
      subtitle={`ID: ${job.id}`}
      actions={
        <div className="flex-center gap-sm">
          <Link href="/" className="btn btn-secondary">
            ← 목록
          </Link>
          {job.status !== "pending" && job.status !== "running" && (
            <button className="btn btn-danger" onClick={handleDelete}>
              🗑 삭제
            </button>
          )}
        </div>
      }
      contentClassName="app-content fade-in"
    >
          {/* Job Meta Info */}
          <div className="job-meta mb-lg">
            <div className="job-meta-item">
              <div className="job-meta-label">상태</div>
              <div className="job-meta-value">
                <StatusBadge status={job.status} />
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">프로젝트</div>
              <div className="job-meta-value">
                <span
                  style={{
                    background: "var(--color-surface-elevated)",
                    padding: "2px 8px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: 13,
                    color: "var(--color-primary)",
                    fontWeight: 500,
                  }}
                >
                  {job.project}
                </span>
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">플레이북</div>
              <div className="job-meta-value">{job.playbook}</div>
            </div>

            {targetSummary && (
              <div className="job-meta-item">
                <div className="job-meta-label">실행 대상</div>
                <div className="job-meta-value" style={{ fontSize: 14 }}>
                  {targetSummary}
                </div>
              </div>
            )}

            <div className="job-meta-item">
              <div className="job-meta-label">소요 시간</div>
              <div className="job-meta-value">
                {formatJobDetailDuration(job.started_at, job.finished_at)}
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">반환 코드</div>
              <div
                className="job-meta-value"
                style={{
                  color:
                    job.rc === 0
                      ? "var(--color-success)"
                      : job.rc !== null
                      ? "var(--color-error)"
                      : "inherit",
                }}
              >
                {job.rc !== null ? job.rc : "-"}
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">생성 시간</div>
              <div className="job-meta-value" style={{ fontSize: 14 }}>
                {formatJobDetailDateTime(job.created_at)}
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">시작 시간</div>
              <div className="job-meta-value" style={{ fontSize: 14 }}>
                {formatJobDetailDateTime(job.started_at)}
              </div>
            </div>

            <div className="job-meta-item">
              <div className="job-meta-label">종료 시간</div>
              <div className="job-meta-value" style={{ fontSize: 14 }}>
                {formatJobDetailDateTime(job.finished_at)}
              </div>
            </div>

            {job.inventory_file && (
              <div className="job-meta-item">
                <div className="job-meta-label">인벤토리 파일</div>
                <div className="job-meta-value" style={{ fontSize: 14 }}>
                  {job.inventory_file}
                </div>
              </div>
            )}
          </div>

          {/* Extra Vars */}
          {job.extra_vars && Object.keys(job.extra_vars).length > 0 && (
            <div className="card mb-lg">
              <div className="card-header">
                <h3 style={{ fontSize: 14, fontWeight: 600 }}>
                  🔧 Extra Variables
                </h3>
              </div>
              <div className="card-body">
                <pre
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 13,
                    color: "var(--color-text-secondary)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {JSON.stringify(job.extra_vars, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Error Message */}
          {job.error_message && (
            <div
              className="card mb-lg"
              style={{ borderColor: "rgba(248, 81, 73, 0.3)" }}
            >
              <div className="card-header">
                <h3
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--color-error)",
                  }}
                >
                  ⚠️ 에러 메시지
                </h3>
              </div>
              <div className="card-body">
                <pre
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 13,
                    color: "var(--color-error)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {job.error_message}
                </pre>
              </div>
            </div>
          )}

          {/* Log Viewer */}
          <LogViewer jobId={jobId} status={job.status} />
    </PageShell>
  );
}
