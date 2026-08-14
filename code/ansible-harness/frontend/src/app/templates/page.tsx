"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PageShell from "@/components/PageShell";
import { fetchJobTemplates, deleteJobTemplate, type JobTemplate } from "@/lib/api";

export default function TemplatesPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<JobTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await fetchJobTemplates();
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "템플릿을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`'${name}' 템플릿을 정말 삭제하시겠습니까?`)) {
      return;
    }
    try {
      await deleteJobTemplate(id);
      alert("삭제되었습니다.");
      loadTemplates();
    } catch (err) {
      alert("삭제 실패: " + (err instanceof Error ? err.message : "알 수 없는 오류"));
    }
  };

  const handleEdit = (tmpl: JobTemplate) => {
    // Navigate to jobs/new with template selected
    router.push(`/jobs/new?templateId=${tmpl.id}`);
  };

  return (
    <PageShell
      title="작업 템플릿 관리"
      subtitle="저장된 작업 템플릿과 스케줄을 관리합니다."
      contentClassName="app-content fade-in"
    >
      <div className="card">
        {error && (
          <div style={{ padding: "12px", background: "rgba(239, 68, 68, 0.1)", color: "var(--color-error)", marginBottom: "16px", borderRadius: "8px" }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600 }}>저장된 템플릿 목록</h2>
          <Link href="/jobs/new" className="btn btn-primary">
            + 새 작업 생성
          </Link>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--color-text-muted)" }}>
            로딩 중...
          </div>
        ) : templates.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--color-text-muted)", background: "var(--color-bg-primary)", borderRadius: "8px" }}>
            저장된 템플릿이 없습니다. 작업 실행 메뉴에서 새로운 템플릿을 저장해보세요.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "12px" }}>템플릿 이름</th>
                  <th style={{ padding: "12px" }}>프로젝트</th>
                  <th style={{ padding: "12px" }}>플레이북</th>
                  <th style={{ padding: "12px" }}>스케줄 (Cron)</th>
                  <th style={{ padding: "12px", width: "200px" }}>관리</th>
                </tr>
              </thead>
              <tbody>
                {templates.map(tmpl => (
                  <tr key={tmpl.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "12px", fontWeight: 500 }}>{tmpl.name}</td>
                    <td style={{ padding: "12px", color: "var(--color-text-muted)" }}>{tmpl.project}</td>
                    <td style={{ padding: "12px", color: "var(--color-text-muted)" }}>{tmpl.playbook}</td>
                    <td style={{ padding: "12px" }}>
                      {tmpl.cron_expression ? (
                        <span style={{ background: "rgba(16, 185, 129, 0.1)", color: "var(--color-success)", padding: "4px 8px", borderRadius: "12px", fontSize: "12px" }}>
                          ⏰ {tmpl.cron_expression}
                        </span>
                      ) : (
                        <span style={{ color: "var(--color-text-muted)", fontSize: "14px" }}>없음</span>
                      )}
                    </td>
                    <td style={{ padding: "12px", display: "flex", gap: "8px" }}>
                      <button 
                        onClick={() => handleEdit(tmpl)}
                        className="btn btn-secondary"
                        style={{ padding: "6px 12px", fontSize: "13px" }}
                      >
                        수정 / 실행
                      </button>
                      <button 
                        onClick={() => handleDelete(tmpl.id, tmpl.name)}
                        className="btn btn-secondary"
                        style={{ padding: "6px 12px", fontSize: "13px", color: "var(--color-error)", borderColor: "var(--color-error)" }}
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PageShell>
  );
}
