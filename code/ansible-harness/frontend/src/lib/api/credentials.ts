import { apiFetch } from "./client";

export interface CredentialSummary {
  ref: string;
  name: string;
  credential_type: string;
  username: string;
  has_secret: boolean;
  last_rotated_at: string | null;
}

export type CredentialDetail = CredentialSummary;

export interface CredentialCreateRequest {
  name: string;
  credential_type: string;
  username: string;
  secret: string;
}

export interface CredentialUpdateRequest {
  name: string;
  username: string;
  secret?: string;
}

export interface InventoryCredentialV2Summary {
  id?: string;
  ref?: string;
  name: string;
  credential_type: string;
  username: string;
  has_secret: boolean;
  has_become_secret: boolean;
  become_username?: string | null;
  last_rotated_at: string | null;
}

export type InventoryCredentialV2Detail = InventoryCredentialV2Summary;

export interface InventoryCredentialV2CreateRequest {
  name: string;
  credential_type: string;
  username?: string;
  secret: string;
  become_username?: string;
  become_secret?: string;
}

export interface InventoryCredentialV2UpdateRequest {
  name: string;
  username?: string;
  become_username?: string | null;
  secret?: string;
  become_secret?: string;
  clear_become_secret?: boolean;
}

export async function fetchInventoryCredentialsV2(
  inventoryId: string
): Promise<InventoryCredentialV2Summary[]> {
  return apiFetch<InventoryCredentialV2Summary[]>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/credentials`
  );
}

export async function fetchInventoryCredentialV2(
  inventoryId: string,
  credentialId: string
): Promise<InventoryCredentialV2Detail> {
  return apiFetch<InventoryCredentialV2Detail>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/credentials/${encodeURIComponent(credentialId)}`
  );
}

export async function createInventoryCredentialV2(
  inventoryId: string,
  data: InventoryCredentialV2CreateRequest
): Promise<InventoryCredentialV2Summary> {
  return apiFetch<InventoryCredentialV2Summary>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/credentials`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function updateInventoryCredentialV2(
  inventoryId: string,
  credentialId: string,
  data: InventoryCredentialV2UpdateRequest
): Promise<InventoryCredentialV2Summary> {
  return apiFetch<InventoryCredentialV2Summary>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/credentials/${encodeURIComponent(credentialId)}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteInventoryCredentialV2(
  inventoryId: string,
  credentialId: string
): Promise<void> {
  return apiFetch<void>(
    `/api/inventories/${encodeURIComponent(inventoryId)}/credentials/${encodeURIComponent(credentialId)}`,
    {
      method: "DELETE",
    }
  );
}

export async function fetchGlobalCredentials(): Promise<
  InventoryCredentialV2Summary[]
> {
  return apiFetch<InventoryCredentialV2Summary[]>("/api/credentials");
}

export async function fetchGlobalCredential(
  credentialId: string
): Promise<InventoryCredentialV2Detail> {
  return apiFetch<InventoryCredentialV2Detail>(
    `/api/credentials/${encodeURIComponent(credentialId)}`
  );
}

export async function createGlobalCredential(
  data: InventoryCredentialV2CreateRequest
): Promise<InventoryCredentialV2Summary> {
  return apiFetch<InventoryCredentialV2Summary>("/api/credentials", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateGlobalCredential(
  credentialId: string,
  data: InventoryCredentialV2UpdateRequest
): Promise<InventoryCredentialV2Summary> {
  return apiFetch<InventoryCredentialV2Summary>(
    `/api/credentials/${encodeURIComponent(credentialId)}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteGlobalCredential(
  credentialId: string
): Promise<void> {
  return apiFetch<void>(`/api/credentials/${encodeURIComponent(credentialId)}`, {
    method: "DELETE",
  });
}

export async function fetchCredentials(
  project: string
): Promise<CredentialSummary[]> {
  return apiFetch<CredentialSummary[]>(
    `/api/projects/${encodeURIComponent(project)}/credentials`
  );
}

export async function fetchCredential(
  project: string,
  id: string
): Promise<CredentialDetail> {
  return apiFetch<CredentialDetail>(
    `/api/projects/${encodeURIComponent(project)}/credentials/${encodeURIComponent(id)}`
  );
}

export async function createCredential(
  project: string,
  data: CredentialCreateRequest
): Promise<CredentialSummary> {
  return apiFetch<CredentialSummary>(
    `/api/projects/${encodeURIComponent(project)}/credentials`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function updateCredential(
  project: string,
  id: string,
  data: CredentialUpdateRequest
): Promise<CredentialSummary> {
  return apiFetch<CredentialSummary>(
    `/api/projects/${encodeURIComponent(project)}/credentials/${encodeURIComponent(id)}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteCredential(
  project: string,
  id: string
): Promise<void> {
  return apiFetch<void>(
    `/api/projects/${encodeURIComponent(project)}/credentials/${encodeURIComponent(id)}`,
    {
      method: "DELETE",
    }
  );
}
