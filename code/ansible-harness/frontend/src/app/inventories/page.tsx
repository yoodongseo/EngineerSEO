"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchManagedInventoriesV2,
  createManagedInventoryV2,
  deleteManagedInventoryV2,
  type ManagedInventoryV2ListItem,
} from "@/lib/api/inventories";
import PageShell from "@/components/PageShell";

import { useRouter } from "next/navigation";

export default function InventoryListPage() {
  const router = useRouter();
  const [inventories, setInventories] = useState<ManagedInventoryV2ListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // For creation modal
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const loadInventories = async () => {
    setLoading(true);
    try {
      const data = await fetchManagedInventoriesV2();
      if (data && data.length > 0) {
        // Redirect to the first inventory if any exists
        router.push(`/inventories/${data[0].id}`);
        return;
      }
      setInventories(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "인벤토리 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventories();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const newInv = await createManagedInventoryV2({
        name: newName,
        description: newDesc,
        tags: [],
        groups: [],
      });
      setCreateModalOpen(false);
      setNewName("");
      setNewDesc("");
      router.push(`/inventories/${newInv.id}`);
    } catch (err: any) {
      alert("생성 실패: " + err.message);
    }
  };

  if (loading) {
    return (
      <PageShell title="자산 관리" contentClassName="app-content dashboard-content fade-in">
        <div style={{ display: "flex", justifyContent: "center", padding: "100px" }}>로딩 중...</div>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="자산 (인벤토리) 관리"
      subtitle="Ansible 작업을 실행할 대상 인벤토리입니다."
      actions={
        <button
          onClick={() => setCreateModalOpen(true)}
          className="btn btn-primary"
        >
          + 새 인벤토리 만들기
        </button>
      }
      contentClassName="app-content dashboard-content fade-in"
    >
      {error && (
        <div className="managed-inventory-feedback managed-inventory-feedback-error mb-4">
          {error}
        </div>
      )}

      <div className="card dashboard-table-card" style={{ padding: "100px", textAlign: "center", background: "var(--color-bg-secondary)" }}>
        <h3 style={{ fontSize: "18px", marginBottom: "16px", color: "var(--color-text-primary)" }}>등록된 인벤토리가 없습니다.</h3>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "32px" }}>Ansible 호스트와 그룹을 관리할 첫 번째 인벤토리를 만들어주세요.</p>
        <button onClick={() => setCreateModalOpen(true)} className="btn btn-primary" style={{ padding: "12px 24px", fontSize: "16px" }}>
          + 새 인벤토리 만들기
        </button>
      </div>

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ width: "100%", maxWidth: "400px", background: "var(--color-bg-secondary)" }}>
            <div className="card-header">
              <h3 className="inventory-management-card-title">새 인벤토리 만들기</h3>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">이름</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="form-input"
                  placeholder="예: Production Servers"
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">설명</label>
                <input
                  type="text"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="form-input"
                  placeholder="인벤토리에 대한 간단한 설명"
                />
              </div>
            </div>
            <div className="card-header" style={{ borderTop: "1px solid var(--color-border)", borderBottom: "none", justifyContent: "flex-end", gap: "10px" }}>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="btn btn-secondary"
              >
                취소
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim()}
                className="btn btn-primary"
              >
                생성하기
              </button>
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
