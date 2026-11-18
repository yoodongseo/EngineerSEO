import { apiFetch } from "./client";

export interface InventoryItem {
  name: string;
  path: string;
}

export interface ManagedInventoryListItem extends InventoryItem {
  status_summary: string;
}

export interface InventoryHost {
  name: string;
  address: string;
  connection_type?: string;
  port?: number;
  remote_user?: string;
  become_enabled?: boolean;
  become_user?: string;
  ansibleharness_login_credential_ref?: string;
  ansibleharness_become_credential_ref?: string;
  host_vars?: Record<string, string>;
}

export interface InventoryGroup {
  name: string;
  hosts: InventoryHost[];
}

export interface ManagedInventoryDetail extends ManagedInventoryListItem {
  rendered_content: string;
  groups: InventoryGroup[];
}

export interface InventoryHostPayload {
  name: string;
  address: string;
  connection_type?: string;
  port?: number;
  remote_user?: string;
  become_enabled?: boolean;
  become_user?: string;
  ansibleharness_login_credential_ref?: string;
  ansibleharness_become_credential_ref?: string;
  host_vars?: Record<string, string>;
}

export interface InventoryGroupPayload {
  name: string;
  hosts: InventoryHostPayload[];
}

export interface ManagedInventoryCreateRequest {
  filename: string;
  groups: InventoryGroupPayload[];
}

export interface ManagedInventoryUpdateRequest {
  filename: string;
  groups: InventoryGroupPayload[];
}

export type InventoryConnectionType = "ssh" | "winrm" | "local" | string;

export type InventoryConnectionStatus =
  | "success"
  | "failed"
  | "unknown"
  | "stale"
  | string;

export interface InventoryHostConnectionStatusV2 {
  status?: InventoryConnectionStatus | null;
  checked_at?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
}

export interface InventoryHostV2 {
  key?: string | null;
  name: string;
  address: string;
  connection_type?: InventoryConnectionType;
  connection_status?:
    | InventoryConnectionStatus
    | InventoryHostConnectionStatusV2
    | null;
  port?: number | null;
  remote_user?: string | null;
  become_enabled?: boolean | null;
  become_user?: string | null;
  login_credential_ref?: string | null;
  become_credential_ref?: string | null;
  ansibleharness_login_credential_ref?: string | null;
  ansibleharness_become_credential_ref?: string | null;
  host_vars?: Record<string, string>;
}

export interface InventoryGroupV2 {
  name: string;
  tags?: string[];
  group_vars?: Record<string, string>;
  host_keys?: string[];
  hosts: InventoryHostV2[];
}

export interface InventoryHostAssetV2 extends InventoryHostV2 {
  key: string;
}

export interface InventoryMembershipV2 {
  group_name: string;
  host_key: string;
}

export interface InventoryProtocolMix {
  ssh?: number;
  winrm?: number;
  local?: number;
  [key: string]: number | undefined;
}

export interface InventoryConnectionSummary {
  success?: number;
  failed?: number;
  unknown?: number;
  stale?: number;
  [key: string]: number | undefined;
}

export interface ManagedInventoryV2ListItem {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  badges?: string[];
  revision: number;
  source_type?: string;
  filename?: string;
  host_count?: number;
  group_count?: number;
  protocol_mix?: InventoryProtocolMix;
  connection_summary?: InventoryConnectionSummary;
  groups?: InventoryGroupV2[];
  rendered_content?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ManagedInventoryV2Detail extends ManagedInventoryV2ListItem {
  rendered_content: string;
  groups: InventoryGroupV2[];
  hosts: InventoryHostAssetV2[];
  memberships: InventoryMembershipV2[];
}

export interface ManagedInventoryV2HostAssetMembership {
  inventory_id: string;
  inventory_name: string;
  group_name: string;
}

export interface ManagedInventoryV2HostAssetDetail extends InventoryHostAssetV2 {
  id: string;
  memberships: ManagedInventoryV2HostAssetMembership[];
}

export interface InventoryHostV2Payload {
  key?: string;
  name: string;
  address: string;
  connection_type?: InventoryConnectionType;
  port?: number;
  remote_user?: string;
  become_enabled?: boolean;
  become_user?: string;
  login_credential_ref?: string;
  become_credential_ref?: string;
  host_vars?: Record<string, string>;
}

export interface InventoryGroupV2Payload {
  name: string;
  tags: string[];
  group_vars?: Record<string, string>;
  host_keys?: string[];
  hosts: InventoryHostV2Payload[];
}

export interface InventoryHostAssetV2Payload extends InventoryHostV2Payload {
  key: string;
}

export type ManagedInventoryV2HostAssetUpdateRequest = Partial<
  Omit<InventoryHostV2Payload, "key">
>;

export interface ManagedInventoryV2HostAttachRequest {
  host_id: string;
  group_name: string;
}

export interface InventoryMembershipV2Payload {
  group_name: string;
  host_key: string;
}

export interface ManagedInventoryV2CreateRequest {
  name: string;
  description: string;
  tags: string[];
  groups: InventoryGroupV2Payload[];
  hosts?: InventoryHostAssetV2Payload[];
  memberships?: InventoryMembershipV2Payload[];
}

export interface ManagedInventoryV2UpdateRequest {
  name: string;
  description: string;
  tags: string[];
  groups: InventoryGroupV2Payload[];
  hosts?: InventoryHostAssetV2Payload[];
  memberships?: InventoryMembershipV2Payload[];
}

export interface ManagedInventoryV2HostConnectionCheckResult {
  host_name: string;
  group_name: string;
  status: InventoryConnectionStatus;
  checked_at: string | null;
  failure_code: string | null;
  failure_message: string | null;
}

export interface ManagedInventoryV2BulkConnectionCheckTarget {
  inventory_id: string;
  scope: "group" | "inventory";
  group_name?: string | null;
}

export interface ManagedInventoryV2BulkConnectionCheckSummary {
  total_hosts: number;
  success: number;
  failed: number;
  unknown: number;
  stale: number;
}

export interface ManagedInventoryV2BulkConnectionCheckResult {
  target: ManagedInventoryV2BulkConnectionCheckTarget;
  summary: ManagedInventoryV2BulkConnectionCheckSummary;
  results: ManagedInventoryV2HostConnectionCheckResult[];
}

export async function fetchManagedInventoriesV2(): Promise<
  ManagedInventoryV2ListItem[]
> {
  return apiFetch<ManagedInventoryV2ListItem[]>("/api/inventories");
}

export async function createManagedInventoryV2(
  data: ManagedInventoryV2CreateRequest
): Promise<ManagedInventoryV2Detail> {
  return apiFetch<ManagedInventoryV2Detail>("/api/inventories", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchManagedInventoryV2(
  id: string
): Promise<ManagedInventoryV2Detail> {
  return apiFetch<ManagedInventoryV2Detail>(
    `/api/inventories/${encodeURIComponent(id)}`
  );
}

export async function updateManagedInventoryV2(
  id: string,
  data: ManagedInventoryV2UpdateRequest
): Promise<ManagedInventoryV2Detail> {
  return apiFetch<ManagedInventoryV2Detail>(
    `/api/inventories/${encodeURIComponent(id)}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteManagedInventoryV2(id: string): Promise<void> {
  return apiFetch<void>(`/api/inventories/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function deleteManagedInventoryHostV2(
  inventoryId: string,
  hostKey: string
): Promise<void> {
  return apiFetch<void>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/hosts/${encodeURIComponent(hostKey)}`,
    { method: "DELETE" }
  );
}

export async function fetchManagedInventoryHostAssetsV2(): Promise<
  ManagedInventoryV2HostAssetDetail[]
> {
  return apiFetch<ManagedInventoryV2HostAssetDetail[]>("/api/hosts");
}

export async function deleteManagedInventoryHostAssetV2(
  hostId: string
): Promise<void> {
  return apiFetch<void>(`/api/hosts/${encodeURIComponent(hostId)}`, {
    method: "DELETE",
  });
}

export async function updateManagedInventoryHostAssetV2(
  hostId: string,
  data: ManagedInventoryV2HostAssetUpdateRequest
): Promise<ManagedInventoryV2HostAssetDetail> {
  return apiFetch<ManagedInventoryV2HostAssetDetail>(
    `/api/hosts/${encodeURIComponent(hostId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

export async function attachManagedInventoryHostAssetV2(
  inventoryId: string,
  data: ManagedInventoryV2HostAttachRequest
): Promise<ManagedInventoryV2Detail> {
  return apiFetch<ManagedInventoryV2Detail>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/hosts`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function checkInventoryHostConnectionV2(
  inventoryId: string,
  groupName: string,
  hostName: string
): Promise<ManagedInventoryV2HostConnectionCheckResult> {
  return apiFetch<ManagedInventoryV2HostConnectionCheckResult>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/groups/${encodeURIComponent(groupName)}/hosts/${encodeURIComponent(hostName)}/connection-check`,
    { method: "POST" }
  );
}

export async function checkInventoryGroupConnectionV2(
  inventoryId: string,
  groupName: string
): Promise<ManagedInventoryV2BulkConnectionCheckResult> {
  return apiFetch<ManagedInventoryV2BulkConnectionCheckResult>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/groups/${encodeURIComponent(groupName)}/connection-check`,
    { method: "POST" }
  );
}

export async function checkInventoryConnectionV2(
  inventoryId: string
): Promise<ManagedInventoryV2BulkConnectionCheckResult> {
  return apiFetch<ManagedInventoryV2BulkConnectionCheckResult>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/connection-check`,
    { method: "POST" }
  );
}
