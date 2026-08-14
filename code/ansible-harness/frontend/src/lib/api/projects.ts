import { apiFetch } from "./client";
import type {
  InventoryItem,
  ManagedInventoryCreateRequest,
  ManagedInventoryDetail,
  ManagedInventoryListItem,
  ManagedInventoryUpdateRequest,
} from "./inventories";

export interface ProjectItem {
  name: string;
  playbook_count: number;
  inventory_count: number;
}

export interface PlaybookItem {
  name: string;
  path: string;
  size: number;
}

export interface ProjectFileNode {
  name: string;
  path: string;
  is_dir: boolean;
  children?: ProjectFileNode[];
}

export interface ProjectFileContent {
  content: string;
}

export async function fetchProjects(): Promise<ProjectItem[]> {
  return apiFetch<ProjectItem[]>("/api/projects");
}

export async function fetchProjectPlaybooks(
  project: string
): Promise<PlaybookItem[]> {
  return apiFetch<PlaybookItem[]>(
    `/api/projects/${encodeURIComponent(project)}/playbooks`
  );
}

export async function fetchProjectFiles(
  project: string
): Promise<ProjectFileNode[]> {
  return apiFetch<ProjectFileNode[]>(
    `/api/projects/${encodeURIComponent(project)}/files`
  );
}

export async function fetchProjectFileContent(
  project: string,
  filePath: string
): Promise<ProjectFileContent> {
  return apiFetch<ProjectFileContent>(
    `/api/projects/${encodeURIComponent(project)}/files/${encodeURIComponent(filePath)}`
  );
}

export async function updateProjectFileContent(
  project: string,
  filePath: string,
  content: string
): Promise<ProjectFileNode> {
  return apiFetch<ProjectFileNode>(
    `/api/projects/${encodeURIComponent(project)}/files/${encodeURIComponent(filePath)}`,
    {
      method: "PUT",
      body: JSON.stringify({ content }),
    }
  );
}

export async function fetchProjectInventories(
  project: string
): Promise<InventoryItem[]> {
  return apiFetch<InventoryItem[]>(
    `/api/projects/${encodeURIComponent(project)}/inventories`
  );
}

export async function fetchProjectManagedInventories(
  project: string
): Promise<ManagedInventoryListItem[]> {
  return apiFetch<ManagedInventoryListItem[]>(
    `/api/projects/${encodeURIComponent(project)}/managed-inventories`
  );
}

export async function createProjectManagedInventory(
  project: string,
  data: ManagedInventoryCreateRequest
): Promise<ManagedInventoryDetail> {
  return apiFetch<ManagedInventoryDetail>(
    `/api/projects/${encodeURIComponent(project)}/managed-inventories`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function fetchProjectManagedInventory(
  project: string,
  filename: string
): Promise<ManagedInventoryDetail> {
  return apiFetch<ManagedInventoryDetail>(
    `/api/projects/${encodeURIComponent(project)}/managed-inventories/${encodeURIComponent(filename)}`
  );
}

export async function updateProjectManagedInventory(
  project: string,
  filename: string,
  data: ManagedInventoryUpdateRequest
): Promise<ManagedInventoryDetail> {
  return apiFetch<ManagedInventoryDetail>(
    `/api/projects/${encodeURIComponent(project)}/managed-inventories/${encodeURIComponent(filename)}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    }
  );
}

export async function renameProjectManagedInventory(
  project: string,
  filename: string,
  data: ManagedInventoryUpdateRequest
): Promise<ManagedInventoryDetail> {
  return updateProjectManagedInventory(project, filename, data);
}

export async function deleteProjectManagedInventory(
  project: string,
  filename: string
): Promise<void> {
  return apiFetch<void>(
    `/api/projects/${encodeURIComponent(project)}/managed-inventories/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
    }
  );
}

export async function uploadProject(project: string, file: File): Promise<{ message: string; project_name: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const { buildApiUrl } = await import("./client");
  const res = await fetch(buildApiUrl(`/api/projects/${encodeURIComponent(project)}/upload`), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detailMsg = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
    throw new Error(detailMsg || `Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function createProjectFile(
  project: string,
  path: string,
  is_dir: boolean = false,
  content: string = ""
): Promise<ProjectFileNode> {
  return apiFetch<ProjectFileNode>(`/api/projects/${encodeURIComponent(project)}/files`, {
    method: "POST",
    body: JSON.stringify({ path, is_dir, content }),
  });
}
