export { buildApiUrl } from "./api/client";

export type {
  Job,
  JobCreateRequest,
  JobListResponse,
  JobLogResponse,
  JobTargetScope,
  DashboardStatTrendItem,
  DashboardStatTopPlaybook,
  DashboardStatFailureReason,
  DashboardStatsResponse,
} from "./api/jobs";

export {
  createJob,
  deleteJob,
  fetchJob,
  fetchJobLogs,
  fetchJobs,
  fetchDashboardStats,
  healthCheck,
} from "./api/jobs";

export type { 
  PlaybookItem, 
  ProjectItem,
  ProjectFileNode,
  ProjectFileContent,
} from "./api/projects";

export {
  createProjectFile,
  createProjectManagedInventory,
  deleteProjectManagedInventory,
  fetchProjectInventories,
  fetchProjectManagedInventories,
  fetchProjectManagedInventory,
  fetchProjectPlaybooks,
  fetchProjects,
  renameProjectManagedInventory,
  updateProjectManagedInventory,
  fetchProjectFiles,
  fetchProjectFileContent,
  updateProjectFileContent,
  uploadProject,
} from "./api/projects";

export type {
  InventoryConnectionStatus,
  InventoryConnectionSummary,
  InventoryConnectionType,
  InventoryGroup,
  InventoryGroupPayload,
  InventoryGroupV2,
  InventoryGroupV2Payload,
  InventoryHost,
  InventoryHostAssetV2,
  InventoryHostAssetV2Payload,
  InventoryHostConnectionStatusV2,
  InventoryHostPayload,
  InventoryHostV2,
  InventoryHostV2Payload,
  InventoryItem,
  InventoryMembershipV2,
  InventoryMembershipV2Payload,
  InventoryProtocolMix,
  ManagedInventoryCreateRequest,
  ManagedInventoryDetail,
  ManagedInventoryListItem,
  ManagedInventoryUpdateRequest,
  ManagedInventoryV2BulkConnectionCheckResult,
  ManagedInventoryV2BulkConnectionCheckSummary,
  ManagedInventoryV2BulkConnectionCheckTarget,
  ManagedInventoryV2CreateRequest,
  ManagedInventoryV2Detail,
  ManagedInventoryV2HostAssetDetail,
  ManagedInventoryV2HostAssetMembership,
  ManagedInventoryV2HostAssetUpdateRequest,
  ManagedInventoryV2HostAttachRequest,
  ManagedInventoryV2HostConnectionCheckResult,
  ManagedInventoryV2ListItem,
  ManagedInventoryV2UpdateRequest,
} from "./api/inventories";

export {
  attachManagedInventoryHostAssetV2,
  checkInventoryConnectionV2,
  checkInventoryGroupConnectionV2,
  checkInventoryHostConnectionV2,
  createManagedInventoryV2,
  deleteManagedInventoryHostAssetV2,
  deleteManagedInventoryHostV2,
  deleteManagedInventoryV2,
  fetchManagedInventoryHostAssetsV2,
  fetchManagedInventoryV2,
  fetchManagedInventoriesV2,
  updateManagedInventoryHostAssetV2,
  updateManagedInventoryV2,
} from "./api/inventories";

export type {
  CredentialCreateRequest,
  CredentialDetail,
  CredentialSummary,
  CredentialUpdateRequest,
  InventoryCredentialV2CreateRequest,
  InventoryCredentialV2Detail,
  InventoryCredentialV2Summary,
  InventoryCredentialV2UpdateRequest,
} from "./api/credentials";

export {
  createCredential,
  createGlobalCredential,
  createInventoryCredentialV2,
  deleteCredential,
  deleteGlobalCredential,
  deleteInventoryCredentialV2,
  fetchCredential,
  fetchCredentials,
  fetchGlobalCredential,
  fetchGlobalCredentials,
  fetchInventoryCredentialV2,
  fetchInventoryCredentialsV2,
  updateCredential,
  updateGlobalCredential,
  updateInventoryCredentialV2,
} from "./api/credentials";

export type {
  AIChatRequest,
  AIChatResponse,
  AIHealthResponse,
  AIIndexRebuildResponse,
  AIIndexState,
  AISourceItem,
  AISourcesData,
  AITimelineCounts,
  AITimelineEvent,
  NvidiaAICapabilities,
  NvidiaAIChatMeta,
  NvidiaAIChatRequest,
  NvidiaAIChatResponse,
  NvidiaAIChunk,
  NvidiaAIHealthResponse,
} from "./api/ai";

export {
  fetchAIHealth,
  fetchNvidiaAIHealth,
  rebuildAIIndex,
  streamAIChat,
  streamNvidiaAIChat,
  submitAIChat,
} from "./api/ai";

export async function deleteProjectFile(project: string, path: string): Promise<any> {
  const res = await fetch(`/api/projects/${project}/files/${path}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "  ");
  }
  return res.json();
}


export interface JobTemplate {
  id: string;
  name: string;
  description?: string;
  project: string;
  playbook: string;
  inventory_id?: string;
  extra_vars?: any;
  target_scope: string;
  target_group_name?: string;
  target_host_name?: string;
  cron_expression?: string;
  is_active: boolean;
}

export async function fetchJobTemplates(): Promise<JobTemplate[]> {
  const res = await fetch("/api/job_templates/");
  if (!res.ok) throw new Error("Failed to fetch job templates");
  return res.json();
}

export async function createJobTemplate(data: Partial<JobTemplate>): Promise<JobTemplate> {
  const res = await fetch("/api/job_templates/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create job template");
  return res.json();
}

export async function deleteJobTemplate(id: string): Promise<any> {
  const res = await fetch(`/api/job_templates/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete job template");
  return res.json();
}
