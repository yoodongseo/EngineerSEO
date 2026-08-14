"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  fetchManagedInventoriesV2,
  fetchManagedInventoryV2,
  updateManagedInventoryV2,
  createManagedInventoryV2,
  deleteManagedInventoryV2,
  type ManagedInventoryV2ListItem,
  type ManagedInventoryV2Detail,
  type InventoryGroupV2,
  type InventoryHostAssetV2,
} from "@/lib/api/inventories";
import PageShell from "@/components/PageShell";
import Editor from "@monaco-editor/react";

const DEFAULT_VAR_EXAMPLE = `{
  // "ansible_port": 22
}`;

export default function InventoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const inventoryId = params.id as string;

  const [inventoryList, setInventoryList] = useState<ManagedInventoryV2ListItem[]>([]);
  const [inventory, setInventory] = useState<ManagedInventoryV2Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [isCreateInvModalOpen, setCreateInvModalOpen] = useState(false);
  const [newInvName, setNewInvName] = useState("");
  const [newInvDesc, setNewInvDesc] = useState("");

  // UI State
  const [selectedGroupName, setSelectedGroupName] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"hosts" | "globalVars">("hosts");

  // Edit States for the currently selected group
  const [groupVarsEdit, setGroupVarsEdit] = useState(DEFAULT_VAR_EXAMPLE);
  const [isGroupVarsDirty, setIsGroupVarsDirty] = useState(false);

  const [isHostModalOpen, setHostModalOpen] = useState(false);
  const [editingHost, setEditingHost] = useState<InventoryHostAssetV2 | null>(null);
  const [hostForm, setHostForm] = useState({
    name: "",
    address: "",
    connection_type: "ssh",
    port: 22,
    remote_user: "",
    ansible_password: "",
    become_enabled: false,
    become_user: "",
    become_method: "sudo",
    ansible_become_password: "",
    ansible_winrm_transport: "basic",
    ansible_winrm_server_cert_validation: "ignore"
  });
  const [hostVarsEdit, setHostVarsEdit] = useState(DEFAULT_VAR_EXAMPLE);

  // Edit States for Group Modal
  const [isGroupModalOpen, setGroupModalOpen] = useState(false);
  const [groupForm, setGroupForm] = useState({
    name: "",
  });
  const [newGroupVarsEdit, setNewGroupVarsEdit] = useState(DEFAULT_VAR_EXAMPLE);

  const loadData = async () => {
    try {
      setLoading(true);
      const [listData, detailData] = await Promise.all([
        fetchManagedInventoriesV2(),
        fetchManagedInventoryV2(inventoryId)
      ]);
      setInventoryList(listData);
      setInventory(detailData);
      if (detailData.groups && detailData.groups.length > 0 && !selectedGroupName) {
        setSelectedGroupName(detailData.groups[0].name);
      }
    } catch (err: any) {
      setError(err.message || "인벤토리 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [inventoryId]);

  // Handle Group Vars selection change
  useEffect(() => {
    if (inventory && selectedGroupName) {
      const group = inventory.groups.find((g) => g.name === selectedGroupName);
      if (group) {
        setGroupVarsEdit(group.group_vars && Object.keys(group.group_vars).length > 0 ? JSON.stringify(group.group_vars, null, 2) : DEFAULT_VAR_EXAMPLE);
        setIsGroupVarsDirty(false);
      }
    }
  }, [selectedGroupName, inventory]);

  const handleSaveGroupVars = async () => {
    if (!inventory || !selectedGroupName) return;
    try {
      setSaving(true);
      const parsedVars = JSON.parse(groupVarsEdit);
      
      const payloadGroups = inventory.groups.map(g => ({
        name: g.name,
        tags: g.tags || [],
        group_vars: g.name === selectedGroupName ? parsedVars : g.group_vars,
        host_keys: [],
        hosts: []
      }));

      await updateManagedInventoryV2(inventoryId, {
        name: inventory.name,
        description: inventory.description || "",
        tags: inventory.tags || [],
        groups: payloadGroups,
        hosts: (inventory.hosts || []) as any,
        memberships: inventory.memberships || [],
      });

      await loadData();
      alert("그룹 변수가 저장되었습니다.");
    } catch (err: any) {
      alert("변수 저장 실패 (유효한 JSON 형식이 아닐 수 있습니다): " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleOpenHostModal = (host?: InventoryHostAssetV2) => {
    if (host) {
      setEditingHost(host);
      
      const vars = { ...(host.host_vars || {}) };
      const ansible_password = vars.ansible_password || "";
      const ansible_become_password = vars.ansible_become_password || vars.ansible_become_pass || "";
      const ansible_winrm_transport = vars.ansible_winrm_transport || "basic";
      const ansible_winrm_server_cert_validation = vars.ansible_winrm_server_cert_validation || "ignore";
      const become_method = vars.ansible_become_method || "sudo";
      const become_user = vars.ansible_become_user || host.become_user || "";
      
      delete vars.ansible_password;
      delete vars.ansible_become_password;
      delete vars.ansible_become_pass;
      delete vars.ansible_winrm_transport;
      delete vars.ansible_winrm_server_cert_validation;
      delete vars.ansible_become_method;
      delete vars.ansible_become_user;

      setHostForm({
        name: host.name,
        address: host.address,
        connection_type: host.connection_type || "ssh",
        port: host.port || 22,
        remote_user: host.remote_user || "",
        ansible_password,
        become_enabled: host.become_enabled || false,
        become_user,
        become_method,
        ansible_become_password,
        ansible_winrm_transport,
        ansible_winrm_server_cert_validation
      });
      setHostVarsEdit(Object.keys(vars).length > 0 ? JSON.stringify(vars, null, 2) : DEFAULT_VAR_EXAMPLE);
    } else {
      setEditingHost(null);
      setHostForm({
        name: "",
        address: "",
        connection_type: "ssh",
        port: 22,
        remote_user: "",
        ansible_password: "",
        become_enabled: false,
        become_user: "",
        become_method: "sudo",
        ansible_become_password: "",
        ansible_winrm_transport: "basic",
        ansible_winrm_server_cert_validation: "ignore"
      });
      setHostVarsEdit(DEFAULT_VAR_EXAMPLE);
    }
    setHostModalOpen(true);
  };

  const handleOpenGroupModal = () => {
    setGroupForm({ name: "" });
    setNewGroupVarsEdit(DEFAULT_VAR_EXAMPLE);
    setGroupModalOpen(true);
  };

  const handleSaveGroup = async () => {
    if (!inventory) return;
    if (!groupForm.name.trim()) {
      alert("그룹 이름을 입력해주세요.");
      return;
    }
    if (inventory.groups.some(g => g.name === groupForm.name)) {
      alert("이미 존재하는 그룹 이름입니다.");
      return;
    }
    
    try {
      setSaving(true);
      const parsedVars = JSON.parse(newGroupVarsEdit);
      
      const payloadGroups = [
        ...inventory.groups.map(g => ({
          name: g.name,
          tags: g.tags || [],
          group_vars: g.group_vars || {},
          host_keys: [],
          hosts: []
        })),
        {
          name: groupForm.name,
          tags: [],
          group_vars: parsedVars,
          host_keys: [],
          hosts: [],
        }
      ];

      await updateManagedInventoryV2(inventoryId, {
        name: inventory.name,
        description: inventory.description || "",
        tags: inventory.tags || [],
        groups: payloadGroups,
        hosts: (inventory.hosts || []) as any,
        memberships: inventory.memberships || [],
      });

      await loadData();
      setSelectedGroupName(groupForm.name);
      setGroupModalOpen(false);
      alert("새 그룹이 추가되었습니다.");
    } catch (err: any) {
      alert("저장 실패 (유효한 JSON 형식이 아닐 수 있습니다): " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveHost = async () => {
    if (!inventory || !selectedGroupName) return;
    try {
      setSaving(true);
      const parsedHostVars = JSON.parse(hostVarsEdit);
      
      if (hostForm.ansible_password) parsedHostVars.ansible_password = hostForm.ansible_password;
      
      if (hostForm.become_enabled) {
        parsedHostVars.ansible_become_method = hostForm.become_method;
        if (hostForm.become_user) {
          parsedHostVars.ansible_become_user = hostForm.become_user;
        }
        if (hostForm.ansible_become_password) {
          parsedHostVars.ansible_become_password = hostForm.ansible_become_password;
        }
      }
      
      if (hostForm.connection_type === 'winrm') {
        parsedHostVars.ansible_winrm_transport = hostForm.ansible_winrm_transport;
        parsedHostVars.ansible_winrm_server_cert_validation = hostForm.ansible_winrm_server_cert_validation;
      }
      
      const newHostKey = editingHost ? editingHost.key : `host-${Date.now()}`;
      
      const updatedHostPayload = {
        key: newHostKey,
        name: hostForm.name,
        address: hostForm.address,
        connection_type: hostForm.connection_type,
        port: hostForm.port,
        remote_user: hostForm.remote_user || undefined,
        become_enabled: hostForm.become_enabled,
        become_user: hostForm.become_user || undefined,
        host_vars: parsedHostVars
      };



      // 1. Update hosts array
      let newHosts = [...(inventory.hosts || [])];
      if (editingHost) {
        newHosts = newHosts.map(h => h.key === newHostKey ? { ...h, ...updatedHostPayload } as any : h);
      } else {
        newHosts.push(updatedHostPayload as any);
      }

      // Convert to payload format to satisfy TypeScript (remove nulls)
      const payloadHosts = newHosts.map(h => ({
        key: h.key || h.name,
        name: h.name,
        address: h.address,
        connection_type: h.connection_type || "ssh",
        port: h.port || undefined,
        remote_user: h.remote_user || undefined,
        become_enabled: h.become_enabled || false,
        become_user: h.become_user || undefined,
        login_credential_ref: h.login_credential_ref || undefined,
        become_credential_ref: h.become_credential_ref || undefined,
        host_vars: h.host_vars || {}
      }));

      // 2. Update memberships
      let newMemberships = [...(inventory.memberships || [])];
      if (!editingHost) {
        newMemberships.push({
          group_name: selectedGroupName,
          host_key: newHostKey
        });
      }

      // 3. Keep groups as is for Payload but clear host_keys so backend infers from memberships
      const payloadGroups = inventory.groups.map(g => ({
        name: g.name,
        tags: g.tags || [],
        group_vars: g.group_vars || {},
        host_keys: [],
        hosts: []
      }));

      await updateManagedInventoryV2(inventoryId, {
        name: inventory.name,
        description: inventory.description || "",
        tags: inventory.tags || [],
        groups: payloadGroups,
        hosts: payloadHosts,
        memberships: newMemberships
      });

      await loadData();
      setHostModalOpen(false);
      alert("호스트가 저장되었습니다.");
    } catch (err: any) {
      alert("저장 실패: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateInventory = async () => {
    if (!newInvName.trim()) return;
    try {
      const newInv = await createManagedInventoryV2({
        name: newInvName,
        description: newInvDesc,
        tags: [],
        groups: [],
      });
      setCreateInvModalOpen(false);
      setNewInvName("");
      setNewInvDesc("");
      router.push(`/inventories/${newInv.id}`);
    } catch (err: any) {
      alert("생성 실패: " + err.message);
    }
  };

  const handleDeleteInventory = async (id: string) => {
    if (!confirm("정말 이 인벤토리를 삭제하시겠습니까?")) return;
    try {
      await deleteManagedInventoryV2(id);
      router.push('/inventories');
    } catch (err: any) {
      alert("삭제 실패: " + err.message);
    }
  };

  if (loading) {
    return (
      <PageShell title="인벤토리 관리" contentClassName="app-content dashboard-content fade-in">
        <div style={{ display: "flex", justifyContent: "center", padding: "100px" }}>
          로딩 중...
        </div>
      </PageShell>
    );
  }

  if (!inventory) {
    return (
      <PageShell title="인벤토리 관리" contentClassName="app-content dashboard-content fade-in">
        <div className="managed-inventory-feedback managed-inventory-feedback-error">
          인벤토리를 찾을 수 없습니다.
        </div>
      </PageShell>
    );
  }

  const selectedGroup = inventory.groups.find((g) => g.name === selectedGroupName);
  const hostsInGroup = inventory.hosts.filter(host => 
    inventory.memberships?.some(m => m.group_name === selectedGroupName && m.host_key === host.key)
  );

  return (
    <PageShell
      title={inventory.name}
      subtitle={inventory.description || "인벤토리 상세 설정 및 변수 관리"}
      actions={
        <div style={{ display: "flex", gap: "10px" }}>
          <button 
            onClick={() => handleDeleteInventory(inventoryId)} 
            className="btn btn-danger"
          >
            삭제
          </button>
          <button className="btn btn-secondary">
            설정 변경
          </button>
        </div>
      }
      contentClassName="app-content dashboard-content fade-in"
    >
      <div style={{ display: "flex", gap: "var(--spacing-lg)", height: "calc(100vh - 180px)", alignItems: "stretch" }}>
        
        {/* Inventories Split View Left Sidebar */}
        <div className="card" style={{ width: "250px", flexShrink: 0, display: "flex", flexDirection: "column" }}>
          <div className="card-header" style={{ padding: "var(--spacing-md)", borderBottom: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 600 }}>인벤토리 목록</h3>
            <button onClick={() => setCreateInvModalOpen(true)} className="btn btn-secondary" style={{ padding: "2px 6px", fontSize: "12px" }}>+</button>
          </div>
          <div className="card-body" style={{ padding: 0, overflowY: "auto", flex: 1 }}>
            {inventoryList.map(inv => (
              <Link 
                key={inv.id} 
                href={`/inventories/${inv.id}`}
                style={{ 
                  display: "block", 
                  padding: "var(--spacing-md)", 
                  borderBottom: "1px solid var(--color-border)",
                  background: inv.id === inventoryId ? "var(--color-bg-tertiary)" : "transparent",
                  borderLeft: inv.id === inventoryId ? "3px solid var(--color-primary)" : "3px solid transparent",
                  textDecoration: "none",
                  color: "var(--color-text-primary)"
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "14px" }}>{inv.name}</div>
                <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginTop: "4px" }}>{inv.host_count || 0} Hosts</div>
              </Link>
            ))}
          </div>
        </div>

        {/* Right Detail Content */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflowY: "auto" }}>
          <div className="inv-tab-bar" style={{ marginBottom: "var(--spacing-lg)", borderBottom: "1px solid var(--color-border)", display: "flex", gap: "16px", flexShrink: 0 }}>
        <button
          onClick={() => setActiveTab("hosts")}
          style={{
            background: "none",
            border: "none",
            color: activeTab === "hosts" ? "var(--color-primary)" : "var(--color-text-secondary)",
            padding: "8px 16px",
            fontSize: "14px",
            fontWeight: activeTab === "hosts" ? 600 : 500,
            borderBottom: activeTab === "hosts" ? "2px solid var(--color-primary)" : "2px solid transparent",
            cursor: "pointer"
          }}
        >
          호스트 및 그룹 관리
        </button>
        <button
          onClick={() => setActiveTab("globalVars")}
          style={{
            background: "none",
            border: "none",
            color: activeTab === "globalVars" ? "var(--color-primary)" : "var(--color-text-secondary)",
            padding: "8px 16px",
            fontSize: "14px",
            fontWeight: activeTab === "globalVars" ? 600 : 500,
            borderBottom: activeTab === "globalVars" ? "2px solid var(--color-primary)" : "2px solid transparent",
            cursor: "pointer"
          }}
        >
          전역 변수 (Vars)
        </button>
      </div>

      {activeTab === "hosts" && (
        <div className="inventory-management-layout">
          {/* Left Column: Groups */}
          <div className="card inventory-management-sidebar-card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 className="inventory-management-card-title">그룹 목록</h3>
              <button 
                onClick={handleOpenGroupModal}
                className="btn btn-primary"
                style={{ padding: "4px 8px", fontSize: "12px" }}
              >
                + 추가
              </button>
            </div>
            <div className="card-body inventory-management-sidebar-body">
              <div className="inventory-management-list">
                {inventory.groups.map((group) => {
                  const hostCount = inventory.memberships?.filter(m => m.group_name === group.name).length || 0;
                  return (
                    <div
                      key={group.name}
                      onClick={() => setSelectedGroupName(group.name)}
                      className={`inventory-management-list-item ${selectedGroupName === group.name ? "active" : ""}`}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
                        <span className="inventory-management-list-name">{group.name}</span>
                        <span className="badge badge-info">{hostCount}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Group Vars Editor */}
              {selectedGroup && (
                <div style={{ marginTop: "var(--spacing-lg)", borderTop: "1px solid var(--color-border)", paddingTop: "var(--spacing-md)" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "8px" }}>
                    '{selectedGroup.name}' 그룹 변수 (JSON)
                  </h4>
                  <div style={{ height: "250px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                    <Editor
                      height="100%"
                      language="json"
                      theme="vs-dark"
                      value={groupVarsEdit}
                      onChange={(val) => {
                        setGroupVarsEdit(val || DEFAULT_VAR_EXAMPLE);
                        setIsGroupVarsDirty(true);
                      }}
                      options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                    />
                  </div>
                  <button
                    onClick={handleSaveGroupVars}
                    disabled={!isGroupVarsDirty || saving}
                    className="btn btn-primary"
                    style={{ marginTop: "10px", width: "100%", justifyContent: "center" }}
                  >
                    {saving ? "저장 중..." : "변경사항 저장"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Hosts */}
          <div className="card inventory-management-editor-card flex flex-col min-h-0">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 className="inventory-management-card-title">
                  호스트 목록 <span style={{ color: "var(--color-text-muted)", fontWeight: "normal" }}>({selectedGroupName})</span>
                </h3>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  placeholder="호스트 검색..."
                  className="form-input"
                  style={{ width: "200px" }}
                />
                <button 
                  onClick={() => handleOpenHostModal()}
                  className="btn btn-primary"
                >
                  + 호스트 추가
                </button>
              </div>
            </div>
            
            <div className="table-wrapper dashboard-table-wrapper" style={{ borderTop: "none" }}>
              <table className="table dashboard-table">
                <thead>
                  <tr>
                    <th>호스트명</th>
                    <th>주소 (IP/Domain)</th>
                    <th>연결 방식</th>
                    <th className="dashboard-actions-cell">관리</th>
                  </tr>
                </thead>
                <tbody>
                  {hostsInGroup.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="table-empty">
                        이 그룹에 등록된 호스트가 없습니다.
                      </td>
                    </tr>
                  ) : (
                    hostsInGroup.map(host => (
                      <tr key={host.key}>
                        <td>
                          <div style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>{host.name}</div>
                        </td>
                        <td>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px" }}>{host.address}</div>
                        </td>
                        <td>
                          <span className="badge badge-info">{host.connection_type || "ssh"}</span>
                        </td>
                        <td className="dashboard-actions-cell">
                          <button 
                            onClick={() => handleOpenHostModal(host)}
                            className="btn btn-secondary"
                            style={{ padding: "4px 10px", fontSize: "12px" }}
                          >
                            수정
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "globalVars" && (
        <div className="card">
          <div className="card-header">
            <h3 className="inventory-management-card-title">인벤토리 전역 변수 (all)</h3>
          </div>
          <div className="card-body">
            <p className="form-hint" style={{ marginBottom: "var(--spacing-md)", marginTop: 0 }}>모든 그룹과 호스트에 기본으로 적용될 변수입니다.</p>
            <textarea
              className="form-textarea"
              style={{ minHeight: "300px" }}
              placeholder="{&#10;  &quot;env&quot;: &quot;production&quot;&#10;}"
            />
            <div style={{ marginTop: "var(--spacing-md)", display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-primary">
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Host Modal */}
      {isHostModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ width: "100%", maxWidth: "700px", background: "var(--color-bg-secondary)" }}>
            <div className="card-header">
              <h3 className="inventory-management-card-title">
                {editingHost ? "호스트 수정" : "새 호스트 추가"}
              </h3>
            </div>
            
            <div className="card-body" style={{ maxHeight: "70vh", overflowY: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-md)", marginBottom: "var(--spacing-lg)" }}>
                <div className="form-group">
                  <label className="form-label">호스트명</label>
                  <input
                    type="text"
                    value={hostForm.name}
                    onChange={(e) => setHostForm({...hostForm, name: e.target.value})}
                    className="form-input"
                    placeholder="web-01"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">주소 (IP/Domain)</label>
                  <input
                    type="text"
                    value={hostForm.address}
                    onChange={(e) => setHostForm({...hostForm, address: e.target.value})}
                    className="form-input"
                    style={{ fontFamily: "var(--font-mono)" }}
                    placeholder="192.0.2.10"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">연결 방식</label>
                  <select
                    value={hostForm.connection_type}
                    onChange={(e) => setHostForm({...hostForm, connection_type: e.target.value})}
                    className="form-select"
                  >
                    <option value="ssh">SSH</option>
                    <option value="winrm">WinRM</option>
                    <option value="local">Local</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">포트</label>
                  <input
                    type="number"
                    value={hostForm.port}
                    onChange={(e) => setHostForm({...hostForm, port: parseInt(e.target.value) || 22})}
                    className="form-input"
                    style={{ fontFamily: "var(--font-mono)" }}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">접속 계정 (User)</label>
                  <input
                    type="text"
                    value={hostForm.remote_user}
                    onChange={(e) => setHostForm({...hostForm, remote_user: e.target.value})}
                    className="form-input"
                    placeholder="root"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">접속 비밀번호 (Password)</label>
                  <input
                    type="password"
                    value={hostForm.ansible_password}
                    onChange={(e) => setHostForm({...hostForm, ansible_password: e.target.value})}
                    className="form-input"
                    placeholder="비밀번호 (선택)"
                  />
                </div>
              </div>

              {hostForm.connection_type === 'winrm' && (
                <div style={{ padding: "var(--spacing-md)", background: "var(--color-bg-primary)", borderRadius: "var(--radius-md)", marginBottom: "var(--spacing-lg)", border: "1px solid var(--color-border)" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 600, marginBottom: "12px", color: "var(--color-text-primary)" }}>WinRM 상세 설정</h4>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-md)" }}>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label">WinRM 인증 방식 (Transport)</label>
                      <select
                        value={hostForm.ansible_winrm_transport}
                        onChange={(e) => setHostForm({...hostForm, ansible_winrm_transport: e.target.value})}
                        className="form-select"
                      >
                        <option value="basic">basic</option>
                        <option value="ntlm">ntlm</option>
                        <option value="credssp">credssp</option>
                        <option value="kerberos">kerberos</option>
                        <option value="certificate">certificate</option>
                      </select>
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label">서버 인증서 검증 (Cert Validation)</label>
                      <select
                        value={hostForm.ansible_winrm_server_cert_validation}
                        onChange={(e) => setHostForm({...hostForm, ansible_winrm_server_cert_validation: e.target.value})}
                        className="form-select"
                      >
                        <option value="ignore">ignore (무시)</option>
                        <option value="validate">validate (검증)</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {hostForm.connection_type !== 'winrm' && (
                <div style={{ padding: "var(--spacing-md)", background: "var(--color-bg-primary)", borderRadius: "var(--radius-md)", marginBottom: "var(--spacing-lg)", border: "1px solid var(--color-border)" }}>
                  <div style={{ display: "flex", alignItems: "center", marginBottom: hostForm.become_enabled ? "12px" : "0" }}>
                    <input
                      type="checkbox"
                      id="become_enabled"
                      checked={hostForm.become_enabled}
                      onChange={(e) => setHostForm({...hostForm, become_enabled: e.target.checked})}
                      style={{ marginRight: "8px" }}
                    />
                    <label htmlFor="become_enabled" style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", cursor: "pointer" }}>권한 상승 사용 (Become / Sudo)</label>
                  </div>
                  
                  {hostForm.become_enabled && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--spacing-md)", marginTop: "12px" }}>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label className="form-label">권한 상승 방식</label>
                        <select
                          value={hostForm.become_method}
                          onChange={(e) => setHostForm({...hostForm, become_method: e.target.value})}
                          className="form-select"
                        >
                          <option value="sudo">sudo</option>
                          <option value="su">su</option>
                          <option value="pbrun">pbrun</option>
                          <option value="doas">doas</option>
                        </select>
                      </div>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label className="form-label">상승 계정 (Become User)</label>
                        <input
                          type="text"
                          value={hostForm.become_user}
                          onChange={(e) => setHostForm({...hostForm, become_user: e.target.value})}
                          className="form-input"
                          placeholder="root"
                        />
                      </div>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label className="form-label">권한 상승 비밀번호</label>
                        <input
                          type="password"
                          value={hostForm.ansible_become_password}
                          onChange={(e) => setHostForm({...hostForm, ansible_become_password: e.target.value})}
                          className="form-input"
                          placeholder="필요 시 입력"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ color: "var(--color-primary)" }}>호스트 변수 (host_vars) - JSON</label>
                <div style={{ height: "200px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                  <Editor
                    height="100%"
                    language="json"
                    theme="vs-dark"
                    value={hostVarsEdit}
                    onChange={(val) => setHostVarsEdit(val || "")}
                    options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                  />
                </div>
              </div>
            </div>

            <div className="card-header" style={{ borderTop: "1px solid var(--color-border)", borderBottom: "none", justifyContent: "flex-end", gap: "10px" }}>
              <button
                onClick={() => setHostModalOpen(false)}
                className="btn btn-secondary"
              >
                취소
              </button>
              <button
                onClick={handleSaveHost}
                className="btn btn-primary"
                disabled={saving}
              >
                {saving ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Group Modal */}
      {isGroupModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ width: "100%", maxWidth: "500px", background: "var(--color-bg-secondary)" }}>
            <div className="card-header">
              <h3 className="inventory-management-card-title">새 그룹 추가</h3>
            </div>
            
            <div className="card-body" style={{ maxHeight: "70vh", overflowY: "auto" }}>
              <div className="form-group" style={{ marginBottom: "var(--spacing-md)" }}>
                <label className="form-label">그룹명</label>
                <input
                  type="text"
                  value={groupForm.name}
                  onChange={(e) => setGroupForm({ name: e.target.value })}
                  className="form-input"
                  placeholder="새로운_그룹명"
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ color: "var(--color-primary)" }}>그룹 변수 (group_vars) - JSON</label>
                <div style={{ height: "200px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                  <Editor
                    height="100%"
                    language="json"
                    theme="vs-dark"
                    value={newGroupVarsEdit}
                    onChange={(val) => setNewGroupVarsEdit(val || "")}
                    options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                  />
                </div>
              </div>
            </div>

            <div className="card-header" style={{ borderTop: "1px solid var(--color-border)", borderBottom: "none", justifyContent: "flex-end", gap: "10px" }}>
              <button
                onClick={() => setGroupModalOpen(false)}
                className="btn btn-secondary"
              >
                취소
              </button>
              <button
                onClick={handleSaveGroup}
                className="btn btn-primary"
                disabled={saving}
              >
                {saving ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}
      
        </div>
      </div>
    </PageShell>
  );
}
