"use client";

import { useEffect, useState, forwardRef, useImperativeHandle, useRef } from "react";
import PageShell from "@/components/PageShell";
import Editor from "@monaco-editor/react";
import {
  fetchProjects,
  fetchProjectFiles,
  fetchProjectFileContent,
  updateProjectFileContent,
  uploadProject,
  createProjectFile,
  deleteProjectFile,
  type ProjectItem,
  type ProjectFileNode,
} from "@/lib/api";

function FileTreeItem({ node, onSelect, selectedPath, level = 0, onDelete }: { node: ProjectFileNode, onSelect: (path: string) => void, selectedPath: string, level?: number, onDelete: (path: string) => void }) {
  const [isOpen, setIsOpen] = useState(false);

  const isSelected = selectedPath === node.path;
  const paddingLeft = level * 16 + 8;

  const handleClick = () => {
    if (node.is_dir) {
      setIsOpen(!isOpen);
    } else {
      onSelect(node.path);
    }
  };

  return (
    <div>
      <div 
        onClick={handleClick}
        style={{
          padding: `6px 8px 6px ${paddingLeft}px`,
          cursor: "pointer",
          backgroundColor: isSelected ? "rgba(99, 102, 241, 0.1)" : "transparent",
          color: isSelected ? "var(--color-primary)" : "var(--color-text-primary)",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "13px",
          borderLeft: isSelected ? "2px solid var(--color-primary)" : "2px solid transparent",
        }}
      >
        <span>{node.is_dir ? (isOpen ? "📂" : "📁") : "📄"}</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
        <button onClick={(e) => { e.stopPropagation(); onDelete(node.path); }} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", padding: "0 4px", marginLeft: "auto", display: "inline-block" }} title="삭제">🗑️</button>
      </div>
      {node.is_dir && isOpen && node.children && (
        <div>
          {node.children.map((child, i) => (
            <FileTreeItem key={i} node={child} onSelect={onSelect} selectedPath={selectedPath} level={level + 1} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

const ProjectTreeItem = forwardRef(({ 
  project, 
  onSelectFile, 
  selectedProject, 
  selectedPath, 
  onNewFile,
  onNewDir,
  onDeleteFile
}: { 
  project: string, 
  onSelectFile: (project: string, path: string) => void, 
  selectedProject: string, 
  selectedPath: string,
  onNewFile: (project: string) => void,
  onNewDir: (project: string) => void,
  onDeleteFile: (project: string, path: string) => void
}, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [fileTree, setFileTree] = useState<ProjectFileNode[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTree = async () => {
    setLoading(true);
    try {
      const data = await fetchProjectFiles(project);
      setFileTree(data);
    } catch (err) {
      console.error("Failed to load project files", err);
    } finally {
      setLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({
    reloadTree: () => {
      if (isOpen) loadTree();
    }
  }));

  useEffect(() => {
    if (isOpen) {
      loadTree();
    }
  }, [isOpen]);

  return (
    <div style={{ marginBottom: "1px" }}>
      <div 
        style={{
          padding: `10px 12px`,
          cursor: "pointer",
          backgroundColor: "var(--color-surface-elevated)",
          color: "var(--color-text-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--color-border)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, fontWeight: 600, fontSize: "14px" }} onClick={() => setIsOpen(!isOpen)}>
          <span>{isOpen ? "📂" : "📁"}</span>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{project}</span>
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          <button title="새 파일" onClick={(e) => { e.stopPropagation(); onNewFile(project); }} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", padding: "4px" }}>📄+</button>
          <button title="새 폴더" onClick={(e) => { e.stopPropagation(); onNewDir(project); }} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", padding: "4px" }}>📁+</button>
          <button title="새로고침" onClick={(e) => { e.stopPropagation(); loadTree(); setIsOpen(true); }} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", padding: "4px" }}>🔄</button>
        </div>
      </div>
      {isOpen && (
        <div style={{ padding: "4px 0", background: "var(--color-bg-primary)" }}>
          {loading ? (
            <div style={{ padding: "8px 16px", fontSize: "12px", color: "var(--color-text-muted)" }}>로딩 중...</div>
          ) : fileTree.length === 0 ? (
            <div style={{ padding: "8px 16px", fontSize: "12px", color: "var(--color-text-muted)" }}>파일이 없습니다.</div>
          ) : (
            fileTree.map((node, i) => (
              <FileTreeItem 
                key={i} 
                node={node} 
                onSelect={(path) => onSelectFile(project, path)} 
                selectedPath={selectedProject === project ? selectedPath : ""} 
                level={0} 
                onDelete={(path) => onDeleteFile(project, path)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
});
ProjectTreeItem.displayName = "ProjectTreeItem";

export default function CodeManagementPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  
  const [selectedProject, setSelectedProject] = useState("");
  const [selectedFilePath, setSelectedFilePath] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use refs to call reloadTree on specific projects
  const projectRefs = useRef<Record<string, any>>({});

  const fetchProjectList = async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch (err) {
      setError("프로젝트를 불러오는데 실패했습니다.");
    }
  };

  useEffect(() => {
    fetchProjectList();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const projName = window.prompt("업로드할 프로젝트 이름을 입력하세요 (기존 이름 입력 시 전체 덮어쓰기):", selectedProject || "");
    if (!projName) {
      e.target.value = "";
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await uploadProject(projName, file);
      alert("프로젝트가 성공적으로 세팅되었습니다.");
      await fetchProjectList();
      if (projectRefs.current[projName]) {
        projectRefs.current[projName].reloadTree();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드 실패");
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const handleFileSelect = async (project: string, filePath: string) => {
    if (fileContent !== originalContent) {
      if (!confirm("저장하지 않은 변경사항이 있습니다. 무시하고 다른 파일을 여시겠습니까?")) {
        return;
      }
    }
    
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectFileContent(project, filePath);
      setSelectedProject(project);
      setSelectedFilePath(filePath);
      setFileContent(data.content);
      setOriginalContent(data.content);
    } catch (err) {
      setError("파일 내용을 불러오는데 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedProject || !selectedFilePath) return;
    if (!window.confirm("변경사항을 저장하시겠습니까?")) return;
    setSaving(true);
    setError(null);
    try {
      await updateProjectFileContent(selectedProject, selectedFilePath, fileContent);
      setOriginalContent(fileContent);
      alert("성공적으로 저장되었습니다.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "파일 저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFileOrDir = async (project: string, path: string) => {
    if (!window.confirm(`정말로 '${path}' 항목을 삭제하시겠습니까?`)) return;
    setLoading(true);
    try {
      await deleteProjectFile(project, path);
      if (projectRefs.current[project]) {
        projectRefs.current[project].reloadTree();
      }
      if (selectedProject === project && selectedFilePath === path) {
        setSelectedFilePath("");
        setFileContent("");
        setOriginalContent("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFileOrDir = async (project: string, isDir: boolean) => {
    const typeStr = isDir ? "폴더" : "파일";
    const path = window.prompt(`생성할 ${typeStr}의 경로 및 이름을 입력하세요\n(예: playbooks/new_playbook.yml):`);
    if (!path) return;

    setLoading(true);
    setError(null);
    try {
      await createProjectFile(project, path, isDir, "");
      if (projectRefs.current[project]) {
        projectRefs.current[project].reloadTree();
      }
      if (!isDir) {
        await handleFileSelect(project, path);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "생성 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell
      title="코드 관리 (IDE)"
      subtitle="모든 프로젝트의 코드 자산을 한 곳에서 바로 탐색하고 편집합니다."
      contentClassName="app-content fade-in"
    >
      <div style={{ display: "flex", gap: "20px", height: "calc(100vh - 200px)" }}>
        
        {/* Left Sidebar: Project Tree List */}
        <div className="card" style={{ width: "320px", display: "flex", flexDirection: "column", overflow: "hidden", padding: 0 }}>
          <div style={{ padding: "16px", borderBottom: "1px solid var(--color-border)", backgroundColor: "var(--color-bg-primary)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <span style={{ fontWeight: 600, fontSize: "15px" }}>프로젝트 목록</span>
            </div>
            <div style={{ position: "relative" }}>
              <input 
                type="file" 
                accept=".zip,.tar.gz,.tgz" 
                onChange={handleUpload} 
                style={{ position: "absolute", width: "100%", height: "100%", opacity: 0, cursor: "pointer" }} 
              />
              <button className="btn btn-secondary" style={{ width: "100%", justifyContent: "center", display: "flex", gap: "8px" }}>
                <span>⬆️</span> 전체 프로젝트 업로드 (.zip)
              </button>
            </div>
          </div>
          
          <div style={{ flex: 1, overflowY: "auto" }}>
            {projects.length === 0 && (
              <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--color-text-muted)" }}>
                등록된 프로젝트가 없습니다.<br/>위 버튼을 눌러 프로젝트를 업로드하세요.
              </div>
            )}
            {projects.map(p => (
              <ProjectTreeItem 
                key={p.name} 
                project={p.name}
                selectedProject={selectedProject}
                selectedPath={selectedFilePath}
                onSelectFile={handleFileSelect}
                onNewFile={(proj) => handleCreateFileOrDir(proj, false)}
                onNewDir={(proj) => handleCreateFileOrDir(proj, true)}
                onDeleteFile={handleDeleteFileOrDir}
                ref={(el) => { projectRefs.current[p.name] = el; }}
              />
            ))}
          </div>
        </div>

        {/* Right Area: Editor */}
        <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", padding: 0 }}>
          {error && (
            <div style={{ padding: "12px 16px", backgroundColor: "rgba(239, 68, 68, 0.1)", color: "var(--color-error)", borderBottom: "1px solid var(--color-error)" }}>
              ⚠️ {error}
            </div>
          )}
          
          {selectedFilePath ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-elevated)" }}>
                <div style={{ fontWeight: 600, color: "var(--color-text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", padding: "2px 6px", background: "var(--color-bg-primary)", borderRadius: "4px", border: "1px solid var(--color-border)" }}>{selectedProject}</span>
                  <span>📄</span> {selectedFilePath}
                  {fileContent !== originalContent && <span style={{ color: "var(--color-warning)", fontSize: "12px" }}>• 수정됨</span>}
                </div>
                <button 
                  className="btn btn-primary" 
                  onClick={handleSave} 
                  disabled={saving || fileContent === originalContent}
                  style={{ padding: "6px 16px" }}
                >
                  {saving ? "저장 중..." : "💾 저장"}
                </button>
              </div>
              <div style={{ flex: 1, position: "relative" }}>
                <Editor
                  height="100%"
                  language={selectedFilePath.endsWith(".json") ? "json" : selectedFilePath.endsWith(".md") ? "markdown" : selectedFilePath.endsWith(".sh") ? "shell" : "yaml"}
                  value={fileContent}
                  theme="vs-dark"
                  onChange={(val) => setFileContent(val || "")}
                  options={{
                    minimap: { enabled: true },
                    fontSize: 14,
                    wordWrap: "on",
                    scrollBeyondLastLine: false,
                    tabSize: 2,
                    formatOnPaste: true
                  }}
                />
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-muted)", flexDirection: "column", gap: "16px" }}>
              <span style={{ fontSize: "48px" }}>⌨️</span>
              <p>왼쪽 트리에서 편집할 파일을 선택하거나 새 파일을 생성하세요.</p>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  );
}
