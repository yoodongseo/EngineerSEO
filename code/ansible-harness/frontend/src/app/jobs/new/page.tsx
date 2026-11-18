"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PageShell from "@/components/PageShell";
import Editor from "@monaco-editor/react";
import {
  createJob,
  fetchManagedInventoryV2,
  fetchManagedInventoriesV2,
  fetchProjects,
  fetchProjectPlaybooks,
  fetchProjectInventories,
  fetchJobTemplates,
  createJobTemplate,
  deleteJobTemplate,
  type JobTemplate,
  type JobTargetScope,
  type ManagedInventoryV2ListItem,
  type ManagedInventoryV2Detail,
  type InventoryItem,
} from "@/lib/api";

const UNASSIGNED_GROUP_NAME = "__ansibleharness_unassigned__";
const PREVIEW_GROUP_HIDDEN_VAR = "_preview_hidden";

interface ManagedInventoryTargetGroupOption {
  name: string;
  hosts: string[];
}

interface MergedTask {
  projectName: string;
  playbookPath: string;
  playbookName: string;
}

function sortByKoreanText(a: string, b: string): number {
  return a.localeCompare(b, "ko");
}

function isVisibleManagedInventoryGroup(
  group: ManagedInventoryV2Detail["groups"][number]
): boolean {
  return (
    group.name !== UNASSIGNED_GROUP_NAME &&
    group.group_vars?.[PREVIEW_GROUP_HIDDEN_VAR] !== "true"
  );
}

function buildManagedInventoryTargetGroups(
  detail: ManagedInventoryV2Detail
): ManagedInventoryTargetGroupOption[] {
  const hostNameByKey = new Map<string, string>();

  const registerHost = (
    host: ManagedInventoryV2Detail["hosts"][number] | ManagedInventoryV2Detail["groups"][number]["hosts"][number]
  ) => {
    const key = host.key ?? host.name;
    if (!hostNameByKey.has(key)) {
      hostNameByKey.set(key, host.name);
    }
  };

  detail.hosts.forEach(registerHost);
  detail.groups.forEach((group) => group.hosts.forEach(registerHost));

  const visibleGroups = detail.groups.filter(isVisibleManagedInventoryGroup);
  const hostsByGroupName = new Map<string, Set<string>>();

  visibleGroups.forEach((group) => {
    const groupHosts = new Set(group.hosts.map((host) => host.name));

    for (const hostKey of group.host_keys ?? []) {
      const hostName = hostNameByKey.get(hostKey);
      if (hostName) {
        groupHosts.add(hostName);
      }
    }

    hostsByGroupName.set(group.name, groupHosts);
  });

  detail.memberships.forEach((membership) => {
    const groupHosts = hostsByGroupName.get(membership.group_name);
    const hostName = hostNameByKey.get(membership.host_key);

    if (groupHosts && hostName) {
      groupHosts.add(hostName);
    }
  });

  return visibleGroups
    .map((group) => ({
      name: group.name,
      hosts: Array.from(hostsByGroupName.get(group.name) ?? []).sort(sortByKoreanText),
    }))
    .sort((left, right) => sortByKoreanText(left.name, right.name));
}

export default function NewJobPage() {
  const router = useRouter();

  const [templates, setTemplates] = useState<JobTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  
  // 1. Target State
  const [inventorySourceType, setInventorySourceType] = useState<"project" | "managed">("managed");
  
  const [projectInventories, setProjectInventories] = useState<InventoryItem[]>([]);
  const [projectInventoryName, setProjectInventoryName] = useState("");

  const [managedInventories, setManagedInventories] = useState<ManagedInventoryV2ListItem[]>([]);
  const [managedInventoryId, setManagedInventoryId] = useState("");
  const [managedInventoryDetail, setManagedInventoryDetail] = useState<ManagedInventoryV2Detail | null>(null);
  
  const [targetScope, setTargetScope] = useState<JobTargetScope>("inventory");
  const [targetGroupNames, setTargetGroupNames] = useState<string[]>([]);
  const [targetHostNames, setTargetHostNames] = useState<string[]>([]);

  // 2. Task State
  const [tasks, setTasks] = useState<MergedTask[]>([]);
  const [selectedTaskStr, setSelectedTaskStr] = useState("");

  // 3. Variables State
  const [extraVarsText, setExtraVarsText] = useState("{\n  // \"ansible_port\": 22\n}");
  const [inventoryVarsText, setInventoryVarsText] = useState("{\n  // \"ansible_port\": 22\n}");
  const [groupVarsTexts, setGroupVarsTexts] = useState<Record<string, string>>({});
  const [hostVarsTexts, setHostVarsTexts] = useState<Record<string, string>>({});
  
  const [varTab, setVarTab] = useState<"global" | "inventory" | "groups" | "hosts">("global");
  const [activeGroupVarTab, setActiveGroupVarTab] = useState<string>("");
  const [activeHostVarTab, setActiveHostVarTab] = useState<string>("");

  // App State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Template Modal State
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState("");
  const [newTemplateCronPreset, setNewTemplateCronPreset] = useState("none");
  const [cronMinute, setCronMinute] = useState("*");
  const [cronHour, setCronHour] = useState("*");
  const [cronDayOfMonth, setCronDayOfMonth] = useState("*");
  const [cronMonth, setCronMonth] = useState("*");
  const [cronDayOfWeek, setCronDayOfWeek] = useState("*");
  const [newTemplateCronCustom, setNewTemplateCronCustom] = useState("");

  useEffect(() => {
    const initData = async () => {
      try {
        const invs = await fetchManagedInventoriesV2();
        setManagedInventories(invs);

        const projs = await fetchProjects();
        const allTasks: MergedTask[] = [];
        await Promise.all(
          projs.map(async (p) => {
            const pbs = await fetchProjectPlaybooks(p.name);
            pbs.forEach((pb) => {
              allTasks.push({
                projectName: p.name,
                playbookPath: pb.path,
                playbookName: pb.name,
              });
            });
          })
        );
        allTasks.sort((a, b) => a.projectName.localeCompare(b.projectName));
        setTasks(allTasks);

        const tmpls = await fetchJobTemplates();
        setTemplates(tmpls);
      } catch (err) {
        console.error(err);
        setError("데이터를 불러오는데 실패했습니다.");
      }
    };
    initData();
  }, []);

  useEffect(() => {
    if (!selectedTaskStr) {
      setProjectInventories([]);
      return;
    }
    const task: MergedTask = JSON.parse(selectedTaskStr);
    let cancelled = false;
    fetchProjectInventories(task.projectName).then((invs) => {
      if (!cancelled) {
        setProjectInventories(invs);
      }
    }).catch(console.error);
    return () => { cancelled = true; };
  }, [selectedTaskStr]);

  useEffect(() => {
    if (!managedInventoryId || inventorySourceType !== "managed") {
      setManagedInventoryDetail(null);
      return;
    }
    let cancelled = false;
    fetchManagedInventoryV2(managedInventoryId).then((detail) => {
      if (!cancelled) setManagedInventoryDetail(detail);
    }).catch(console.error);
    return () => { cancelled = true; };
  }, [managedInventoryId, inventorySourceType]);

  const targetGroups = useMemo(() => {
    if (!managedInventoryDetail) return [];
    return buildManagedInventoryTargetGroups(managedInventoryDetail);
  }, [managedInventoryDetail]);

  const availableHosts = useMemo(() => {
    if (!managedInventoryDetail) return [];
    if (targetGroupNames.length === 0) return [];
    
    const hosts = new Set<string>();
    targetGroups.forEach(g => {
      if (targetGroupNames.includes(g.name)) {
        g.hosts.forEach(h => hosts.add(h));
      }
    });
    return Array.from(hosts).sort(sortByKoreanText);
  }, [targetGroupNames, targetGroups, managedInventoryDetail]);

  useEffect(() => {
    if (targetGroupNames.length > 0 && (!activeGroupVarTab || !targetGroupNames.includes(activeGroupVarTab))) {
      setActiveGroupVarTab(targetGroupNames[0]);
    } else if (targetGroupNames.length === 0) {
      setActiveGroupVarTab("");
      if (varTab === "groups") setVarTab("global");
    }
  }, [targetGroupNames, activeGroupVarTab, varTab]);

  useEffect(() => {
    if (targetHostNames.length > 0 && (!activeHostVarTab || !targetHostNames.includes(activeHostVarTab))) {
      setActiveHostVarTab(targetHostNames[0]);
    } else if (targetHostNames.length === 0) {
      setActiveHostVarTab("");
      if (varTab === "hosts") setVarTab("global");
    }
  }, [targetHostNames, activeHostVarTab, varTab]);

  const toggleGroup = (name: string) => {
    setTargetGroupNames(prev => 
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const toggleHost = (name: string) => {
    setTargetHostNames(prev => 
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const handleGroupVarChange = (group: string, val: string) => {
    setGroupVarsTexts(prev => ({ ...prev, [group]: val }));
  };

  const handleHostVarChange = (host: string, val: string) => {
    setHostVarsTexts(prev => ({ ...prev, [host]: val }));
  };

  const parseVars = async (text: string) => {
    if (!text.trim()) return null;
    try {
      return JSON.parse(text);
    } catch {
      try {
        const yaml = await import("yaml");
        const parsed = yaml.parse(text);
        if (typeof parsed !== "object" || parsed === null) return null;
        return parsed;
      } catch {
        return null;
      }
    }
  };

  const loadTemplate = (tmplId: string) => {
    setSelectedTemplate(tmplId);
    if (!tmplId) return;
    const tmpl = templates.find(t => t.id === tmplId);
    if (!tmpl) return;

    if (tmpl.inventory_id) {
      setInventorySourceType("managed");
      setManagedInventoryId(tmpl.inventory_id);
    } else {
      setInventorySourceType("project");
      // Project inventory matching would go here if we saved project inventory name
    }

    setTargetScope(tmpl.target_scope as any);
    if (tmpl.target_group_name) setTargetGroupNames([tmpl.target_group_name]);
    if (tmpl.target_host_name) setTargetHostNames([tmpl.target_host_name]);

    const taskMatch = tasks.find(t => t.projectName === tmpl.project && t.playbookPath === tmpl.playbook);
    if (taskMatch) {
      setSelectedTaskStr(JSON.stringify(taskMatch));
    }

    if (tmpl.extra_vars) {
      setExtraVarsText(JSON.stringify(tmpl.extra_vars, null, 2));
    }
  };

  const openTemplateModal = () => {
    if (!selectedTaskStr) {
      alert("플레이북을 먼저 선택해주세요.");
      return;
    }
    setNewTemplateName("");
    setNewTemplateCronPreset("none");
    setCronMinute("*");
    setCronHour("*");
    setCronDayOfMonth("*");
    setCronMonth("*");
    setCronDayOfWeek("*");
    setNewTemplateCronCustom("");
    setShowTemplateModal(true);
  };

  const confirmSaveTemplate = async () => {
    if (!newTemplateName.trim()) {
      alert("템플릿 이름을 입력하세요.");
      return;
    }

    if (!window.confirm("현재 설정된 작업을 템플릿으로 저장하시겠습니까?")) {
      return;
    }

    let cron: string | undefined = undefined;
    if (newTemplateCronPreset === "custom") {
      cron = newTemplateCronCustom;
    } else if (newTemplateCronPreset !== "none") {
      let min = cronMinute === "*" ? "0" : cronMinute;
      let hr = cronHour === "*" ? "0" : cronHour;
      let dom = cronDayOfMonth === "*" ? "1" : cronDayOfMonth;
      let mon = "*";
      let dow = cronDayOfWeek === "*" ? "1" : cronDayOfWeek;
      
      if (newTemplateCronPreset === "hourly") {
        hr = "*"; dom = "*"; mon = "*"; dow = "*";
      } else if (newTemplateCronPreset === "daily") {
        dom = "*"; mon = "*"; dow = "*";
      } else if (newTemplateCronPreset === "weekly") {
        dom = "*"; mon = "*";
      } else if (newTemplateCronPreset === "monthly") {
        dow = "*"; mon = "*";
      }
      cron = `${min} ${hr} ${dom} ${mon} ${dow}`;
    }

    const task: MergedTask = JSON.parse(selectedTaskStr);
    
    let parsedExtraVars = {};
    if (extraVarsText.trim()) {
      try {
        parsedExtraVars = JSON.parse(extraVarsText);
      } catch (err) {
        alert("전역 변수가 올바른 JSON 형식이 아닙니다.");
        return;
      }
    }

    const payload = {
      name: newTemplateName,
      project: task.projectName,
      playbook: task.playbookPath,
      inventory_id: inventorySourceType === "managed" && managedInventoryId ? managedInventoryId : undefined,
      extra_vars: parsedExtraVars,
      target_scope: targetScope,
      target_group_name: targetGroupNames.length > 0 ? targetGroupNames[0] : undefined,
      target_host_name: targetHostNames.length > 0 ? targetHostNames[0] : undefined,
      cron_expression: cron || undefined,
      is_active: true
    };

    setLoading(true);
    try {
      const newTmpl = await createJobTemplate(payload);
      setTemplates([...templates, newTmpl]);
      setSelectedTemplate(newTmpl.id);
      alert("템플릿이 성공적으로 저장되었습니다!");
      setShowTemplateModal(false);
    } catch (err) {
      alert("템플릿 저장 실패: " + err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateJob = async () => {
    setError(null);
    if (!selectedTaskStr) {
      alert("작업을 선택해주세요.");
      return;
    }
    
    if (inventorySourceType === "managed") {
      if (!managedInventoryId) {
        alert("통합 자산 인벤토리를 선택해주세요.");
        return;
      }
      if (targetScope === "group" && targetGroupNames.length === 0) {
        alert("그룹을 1개 이상 선택해주세요.");
        return;
      }
      if (targetScope === "host" && targetHostNames.length === 0) {
        alert("호스트를 1개 이상 선택해주세요.");
        return;
      }
    } else {
      if (!projectInventoryName) {
        alert("프로젝트 인벤토리를 선택해주세요.");
        return;
      }
    }

    const task: MergedTask = JSON.parse(selectedTaskStr);
    
    let parsedExtraVars: Record<string, unknown> | undefined;
    if (extraVarsText.trim()) {
      const parsed = await parseVars(extraVarsText);
      if (!parsed) { setError("전역 변수는 올바른 JSON/YAML이어야 합니다."); return; }
      parsedExtraVars = parsed;
    }

    let parsedInventoryVars: Record<string, unknown> | undefined;
    if (inventoryVarsText.trim()) {
      const parsed = await parseVars(inventoryVarsText);
      if (!parsed) { setError("인벤토리 변수는 올바른 JSON/YAML이어야 합니다."); return; }
      parsedInventoryVars = parsed;
    }

    const parsedGroupVars: Record<string, Record<string, unknown>> = {};
    if (inventorySourceType === "managed") {
      for (const group of targetGroupNames) {
        const text = groupVarsTexts[group];
        if (text && text.trim()) {
          const parsed = await parseVars(text);
          if (!parsed) { setError(`그룹 '${group}'의 변수가 올바른 JSON/YAML이 아닙니다.`); return; }
          parsedGroupVars[group] = parsed;
        }
      }
    }

    const parsedHostVars: Record<string, Record<string, unknown>> = {};
    if (inventorySourceType === "managed") {
      for (const host of targetHostNames) {
        const text = hostVarsTexts[host];
        if (text && text.trim()) {
          const parsed = await parseVars(text);
          if (!parsed) { setError(`호스트 '${host}'의 변수가 올바른 JSON/YAML이 아닙니다.`); return; }
          parsedHostVars[host] = parsed;
        }
      }
    }

    setLoading(true);
    try {
      const jobPayload: any = {
        project: task.projectName,
        playbook: task.playbookPath,
        extra_vars: parsedExtraVars,
        inventory_vars: parsedInventoryVars,
      };

      if (inventorySourceType === "managed") {
        jobPayload.managed_inventory_id = managedInventoryId;
        jobPayload.target_scope = targetScope;
        jobPayload.target_group_names = targetScope !== "inventory" ? targetGroupNames : null;
        jobPayload.target_host_names = targetScope === "host" ? targetHostNames : null;
        jobPayload.group_vars = Object.keys(parsedGroupVars).length > 0 ? parsedGroupVars : null;
        jobPayload.host_vars = Object.keys(parsedHostVars).length > 0 ? parsedHostVars : null;
      } else {
        jobPayload.inventory_file = projectInventoryName;
        jobPayload.target_scope = "inventory";
      }

      const job = await createJob(jobPayload);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "작업 실행 실패");
      setLoading(false);
    }
  };

  const parseTask = (str: string) => str ? JSON.parse(str) as MergedTask : null;
  const currentTask = parseTask(selectedTaskStr);

  return (
    <PageShell title="새 작업 실행" subtitle="Cascade 방식으로 작업 요소를 선택하세요">
      {error && (
        <div style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", color: "var(--color-error)", padding: "16px", borderRadius: "8px", marginBottom: "16px", border: "1px solid var(--color-error)" }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ padding: "0 24px", display: "flex", gap: "16px", alignItems: "center", marginBottom: "20px" }}>
        <div style={{ fontWeight: 600, fontSize: "14px" }}>작업 템플릿 로드:</div>
        <select 
          className="input-field" 
          style={{ width: "300px" }}
          value={selectedTemplate}
          onChange={(e) => loadTemplate(e.target.value)}
        >
          <option value="">-- 저장된 템플릿 선택 안함 --</option>
          {templates.map(t => (
            <option key={t.id} value={t.id}>
              {t.name} {t.cron_expression ? `(⏰ ${t.cron_expression})` : ""}
            </option>
          ))}
        </select>
        <button className="btn btn-secondary" onClick={openTemplateModal}>현재 설정을 템플릿으로 저장</button>
      </div>

      <div className="cascade-layout">
        
        {/* Column 1: Inventory Selection */}
        <div className="cascade-column">
          <div className="cascade-column-header">1. 인벤토리</div>
          <div className="cascade-column-body">
            <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
              <button 
                className={`btn ${inventorySourceType === "managed" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => { setInventorySourceType("managed"); setTargetScope("inventory"); }}
                style={{ flex: 1 }}
              >
                통합 자산
              </button>
              <button 
                className={`btn ${inventorySourceType === "project" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setInventorySourceType("project")}
                style={{ flex: 1 }}
              >
                프로젝트 자산
              </button>
            </div>

            {inventorySourceType === "managed" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {managedInventories.map(inv => (
                  <div 
                    key={inv.id} 
                    className={`cascade-list-item ${managedInventoryId === inv.id ? "selected" : ""}`}
                    onClick={() => setManagedInventoryId(inv.id)}
                  >
                    {inv.name}
                  </div>
                ))}
                {managedInventories.length === 0 && <div className="form-hint">자산 인벤토리가 없습니다.</div>}
              </div>
            ) : (
              <div>
                <label className="form-label" style={{ marginBottom: "8px", display: "block" }}>작업(Task)을 먼저 선택하면 사용 가능한 인벤토리가 표시됩니다.</label>
                {projectInventories.map(inv => (
                  <div 
                    key={inv.name} 
                    className={`cascade-list-item ${projectInventoryName === inv.name ? "selected" : ""}`}
                    onClick={() => setProjectInventoryName(inv.name)}
                  >
                    {inv.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Column 2: Target Selection (Managed Only) */}
        <div className="cascade-column">
          <div className="cascade-column-header">2. 대상 그룹/호스트</div>
          <div className="cascade-column-body">
            {inventorySourceType === "managed" && managedInventoryId ? (
              <>
                <div style={{ display: "flex", gap: "8px", marginBottom: "16px", backgroundColor: "var(--color-surface)", padding: "8px", borderRadius: "8px" }}>
                  <label style={{ flex: 1, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px" }}>
                    <input type="radio" checked={targetScope === "inventory"} onChange={() => setTargetScope("inventory")} /> 전체 대상
                  </label>
                  <label style={{ flex: 1, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px" }}>
                    <input type="radio" checked={targetScope === "group"} onChange={() => setTargetScope("group")} /> 특정 그룹
                  </label>
                  <label style={{ flex: 1, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px" }}>
                    <input type="radio" checked={targetScope === "host"} onChange={() => setTargetScope("host")} /> 특정 호스트
                  </label>
                </div>

                {targetScope !== "inventory" && (
                  <div style={{ marginBottom: "20px" }}>
                    <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "8px", color: "var(--color-text-secondary)" }}>그룹 선택</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      {targetGroups.map(g => (
                        <label key={g.name} className={`cascade-list-item ${targetGroupNames.includes(g.name) ? "selected" : ""}`} style={{ padding: "6px 12px", cursor: "pointer" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <input type="checkbox" checked={targetGroupNames.includes(g.name)} onChange={() => toggleGroup(g.name)} />
                            <span>{g.name}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {targetScope === "host" && (
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "8px", color: "var(--color-text-secondary)" }}>호스트 선택 (그룹 내)</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      {availableHosts.map(h => (
                        <label key={h} className={`cascade-list-item ${targetHostNames.includes(h) ? "selected" : ""}`} style={{ padding: "6px 12px", cursor: "pointer" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <input type="checkbox" checked={targetHostNames.includes(h)} onChange={() => toggleHost(h)} />
                            <span>{h}</span>
                          </div>
                        </label>
                      ))}
                      {availableHosts.length === 0 && <span style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>먼저 위에서 그룹을 선택하세요.</span>}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="form-hint">통합 자산 모드에서만 그룹/호스트를 선택할 수 있습니다.</div>
            )}
          </div>
        </div>

        {/* Column 3: Task & Variables */}
        <div className="cascade-column" style={{ flex: 1.5 }}>
          <div className="cascade-column-header">3. 작업 및 변수</div>
          <div className="cascade-column-body">
            <div style={{ marginBottom: "24px" }}>
              <label className="form-label" style={{ display: "block", marginBottom: "8px" }}>플레이북 선택</label>
              <select 
                className="form-select"
                value={selectedTaskStr}
                onChange={(e) => setSelectedTaskStr(e.target.value)}
                style={{ width: "100%", padding: "10px", borderRadius: "8px" }}
              >
                <option value="" disabled>플레이북 선택...</option>
                {Array.from(new Set(tasks.map(t => t.projectName))).map(projName => (
                  <optgroup key={projName} label={`📁 ${projName}`}>
                    {tasks.filter(t => t.projectName === projName).map((t, idx) => (
                      <option key={idx} value={JSON.stringify(t)}>
                        {t.playbookName}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <div>
              <label className="form-label" style={{ display: "block", marginBottom: "8px" }}>변수 오버라이드 (YAML/JSON)</label>
              <div className="cascade-var-tabs">
                <div className={`cascade-var-tab ${varTab === "global" ? "active" : ""}`} onClick={() => setVarTab("global")}>전역(Extra)</div>
                <div className={`cascade-var-tab ${varTab === "inventory" ? "active" : ""}`} onClick={() => setVarTab("inventory")}>인벤토리</div>
                {inventorySourceType === "managed" && targetGroupNames.length > 0 && (
                  <div className={`cascade-var-tab ${varTab === "groups" ? "active" : ""}`} onClick={() => setVarTab("groups")}>그룹별</div>
                )}
                {inventorySourceType === "managed" && targetHostNames.length > 0 && (
                  <div className={`cascade-var-tab ${varTab === "hosts" ? "active" : ""}`} onClick={() => setVarTab("hosts")}>호스트별</div>
                )}
              </div>

              {varTab === "global" && (
                <div style={{ height: "250px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                  <Editor
                    height="100%"
                    language="yaml"
                    theme="vs-dark"
                    value={extraVarsText}
                    onChange={(val) => setExtraVarsText(val || "")}
                    options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                  />
                </div>
              )}
              {varTab === "inventory" && (
                <div style={{ height: "250px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                  <Editor
                    height="100%"
                    language="yaml"
                    theme="vs-dark"
                    value={inventoryVarsText}
                    onChange={(val) => setInventoryVarsText(val || "{\n  // \"ansible_port\": 22\n}")}
                    options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                  />
                </div>
              )}
              {varTab === "groups" && (
                <div>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "12px", overflowX: "auto", paddingBottom: "4px" }}>
                    {targetGroupNames.map(g => (
                      <button
                        key={g} onClick={() => setActiveGroupVarTab(g)}
                        className={`badge ${activeGroupVarTab === g ? "badge-info" : ""}`}
                        style={{ padding: "6px 12px", cursor: "pointer", border: "1px solid var(--color-border)" }}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                  {activeGroupVarTab && (
                    <div style={{ height: "200px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                      <Editor
                        height="100%"
                        language="yaml"
                        theme="vs-dark"
                        value={groupVarsTexts[activeGroupVarTab] || ""}
                        onChange={(val) => handleGroupVarChange(activeGroupVarTab, val || "")}
                        options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                      />
                    </div>
                  )}
                </div>
              )}
              {varTab === "hosts" && (
                <div>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "12px", overflowX: "auto", paddingBottom: "4px" }}>
                    {targetHostNames.map(h => (
                      <button
                        key={h} onClick={() => setActiveHostVarTab(h)}
                        className={`badge ${activeHostVarTab === h ? "badge-info" : ""}`}
                        style={{ padding: "6px 12px", cursor: "pointer", border: "1px solid var(--color-border)" }}
                      >
                        {h}
                      </button>
                    ))}
                  </div>
                  {activeHostVarTab && (
                    <div style={{ height: "200px", border: "1px solid var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
                      <Editor
                        height="100%"
                        language="yaml"
                        theme="vs-dark"
                        value={hostVarsTexts[activeHostVarTab] || ""}
                        onChange={(val) => handleHostVarChange(activeHostVarTab, val || "")}
                        options={{ minimap: { enabled: false }, tabSize: 2, fontSize: 13 }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Column 4: Summary */}
        <div className="cascade-column cascade-column-fixed">
          <div className="cascade-column-header">4. 요약 및 실행</div>
          <div className="cascade-column-body" style={{ display: "flex", flexDirection: "column" }}>
            
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: "16px" }}>
                <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>선택된 인벤토리</div>
                <div style={{ fontWeight: 600, color: "var(--color-primary)" }}>
                  {inventorySourceType === "managed" ? 
                    (managedInventories.find(i => i.id === managedInventoryId)?.name || "없음") : 
                    (projectInventoryName || "없음")}
                </div>
              </div>

              {inventorySourceType === "managed" && targetScope !== "inventory" && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>대상 스코프 ({targetScope})</div>
                  <div style={{ fontSize: "13px", marginTop: "4px" }}>
                    <span style={{ color: "var(--color-info)" }}>{targetGroupNames.length}</span> 그룹, <span style={{ color: "var(--color-info)" }}>{targetHostNames.length}</span> 호스트 선택됨
                  </div>
                </div>
              )}

              <div style={{ marginBottom: "16px" }}>
                <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>선택된 작업</div>
                <div style={{ fontWeight: 600, fontSize: "13px", wordBreak: "break-all" }}>
                  {currentTask ? `${currentTask.projectName} / ${currentTask.playbookName}` : "선택 안 됨"}
                </div>
              </div>
            </div>

            <button 
              className="btn btn-primary" 
              style={{ width: "100%", padding: "16px", fontSize: "16px", marginTop: "auto" }} 
              onClick={handleCreateJob}
              disabled={loading}
            >
              {loading ? "시작 중..." : "🚀 작업 실행하기"}
            </button>
          </div>
        </div>
        
      </div>

      {showTemplateModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: "var(--color-bg-primary)", padding: "24px", borderRadius: "8px",
            width: "400px", border: "1px solid var(--color-border)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
          }}>
            <h3 style={{ margin: "0 0 16px 0" }}>템플릿으로 저장</h3>
            <div className="form-group">
              <label className="form-label">템플릿 이름</label>
              <input type="text" className="form-input" value={newTemplateName} onChange={(e) => setNewTemplateName(e.target.value)} placeholder="예: 데일리 헬스체크" />
            </div>
            <div className="form-group">
              <label className="form-label">스케줄링 주기</label>
              <select className="form-select" value={newTemplateCronPreset} onChange={(e) => setNewTemplateCronPreset(e.target.value)}>
                <option value="none">사용 안 함 (수동 실행)</option>
                <option value="hourly">매시간 (Hourly)</option>
                <option value="daily">매일 (Daily)</option>
                <option value="weekly">매주 (Weekly)</option>
                <option value="monthly">매월 (Monthly)</option>
                <option value="custom">사용자 지정 (Cron)</option>
              </select>
            </div>

            {newTemplateCronPreset !== "none" && newTemplateCronPreset !== "custom" && (
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
                {(newTemplateCronPreset === "weekly") && (
                  <div style={{ flex: "1 1 30%" }}>
                    <label className="form-label" style={{ fontSize: "12px" }}>요일 선택</label>
                    <select className="form-select" value={cronDayOfWeek === "*" ? "1" : cronDayOfWeek} onChange={(e) => setCronDayOfWeek(e.target.value)}>
                      <option value="0">일요일</option>
                      <option value="1">월요일</option>
                      <option value="2">화요일</option>
                      <option value="3">수요일</option>
                      <option value="4">목요일</option>
                      <option value="5">금요일</option>
                      <option value="6">토요일</option>
                    </select>
                  </div>
                )}
                {(newTemplateCronPreset === "monthly") && (
                  <div style={{ flex: "1 1 30%" }}>
                    <label className="form-label" style={{ fontSize: "12px" }}>일 선택</label>
                    <select className="form-select" value={cronDayOfMonth === "*" ? "1" : cronDayOfMonth} onChange={(e) => setCronDayOfMonth(e.target.value)}>
                      {Array.from({ length: 31 }, (_, i) => i + 1).map(d => (
                        <option key={d} value={d.toString()}>{d}일</option>
                      ))}
                    </select>
                  </div>
                )}
                {(newTemplateCronPreset === "daily" || newTemplateCronPreset === "weekly" || newTemplateCronPreset === "monthly") && (
                  <div style={{ flex: "1 1 30%" }}>
                    <label className="form-label" style={{ fontSize: "12px" }}>시 (Hour)</label>
                    <select className="form-select" value={cronHour === "*" ? "0" : cronHour} onChange={(e) => setCronHour(e.target.value)}>
                      {Array.from({ length: 24 }, (_, i) => i).map(h => (
                        <option key={h} value={h.toString()}>{h}시</option>
                      ))}
                    </select>
                  </div>
                )}
                <div style={{ flex: "1 1 30%" }}>
                  <label className="form-label" style={{ fontSize: "12px" }}>분 (Minute)</label>
                  <select className="form-select" value={cronMinute === "*" ? "0" : cronMinute} onChange={(e) => setCronMinute(e.target.value)}>
                    {Array.from({ length: 60 }, (_, i) => i).map(m => (
                      <option key={m} value={m.toString()}>{m}분</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {newTemplateCronPreset === "custom" && (
              <div className="form-group">
                <label className="form-label">Cron 표현식</label>
                <input type="text" className="form-input" value={newTemplateCronCustom} onChange={(e) => setNewTemplateCronCustom(e.target.value)} placeholder="* * * * *" />
              </div>
            )}
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "24px" }}>
              <button className="btn btn-secondary" onClick={() => setShowTemplateModal(false)}>취소</button>
              <button className="btn btn-primary" onClick={confirmSaveTemplate}>저장</button>
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
