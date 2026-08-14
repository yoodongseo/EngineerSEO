"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import {
  attachManagedInventoryHostAssetV2,
  createGlobalCredential,
  createManagedInventoryV2,
  deleteGlobalCredential,
  deleteManagedInventoryHostAssetV2,
  deleteManagedInventoryHostV2,
  deleteManagedInventoryV2,
  fetchGlobalCredentials,
  fetchManagedInventoryHostAssetsV2,
  fetchManagedInventoriesV2,
  fetchManagedInventoryV2,
  type InventoryCredentialV2Summary,
  updateGlobalCredential,
  updateManagedInventoryV2,
  type InventoryConnectionStatus,
  type InventoryHostV2,
  type ManagedInventoryV2HostAssetDetail,
  type ManagedInventoryV2HostAssetUpdateRequest,
  type ManagedInventoryV2CreateRequest,
  type ManagedInventoryV2Detail,
  updateManagedInventoryHostAssetV2,
} from "@/lib/api";

type HostStatus = "success" | "running" | "pending" | "failed";
type ConnectionType = "ssh" | "winrm" | "local";

interface PreviewGroup {
  id: string;
  name: string;
  note: string;
  tags: string[];
  varsSummary: string;
}

interface PreviewHost {
  id: string;
  name: string;
  address: string;
  platform: string;
  connection: ConnectionType;
  port: string;
  loginCredentialRef: string;
  becomeEnabled: boolean;
  legacyBecomeUser: string;
  legacyBecomeCredentialRef: string;
  status: HostStatus;
  groups: string[];
  note: string;
}

interface PreviewInventory {
  id: string;
  name: string;
  description: string;
  updatedAt: string;
  tags: string[];
  groups: PreviewGroup[];
  hosts: PreviewHost[];
}

type FocusScope =
  | { kind: "all" }
  | { kind: "inventory"; inventoryId: string }
  | { kind: "group"; inventoryId: string; groupId: string };

type InfoPanelState =
  | { kind: "inventory"; inventoryId: string }
  | { kind: "group"; inventoryId: string; groupId: string }
  | { kind: "host"; inventoryId: string; hostId: string }
  | { kind: "hostAsset"; hostAssetId: string }
  | { kind: "credentials"; inventoryId: string }
  | null;

type CredentialManagerSource = "workspace" | "host-select" | "host-create";

interface FeedbackState {
  tone: "info" | "success" | "error";
  message: string;
}

interface ConfirmDialogState {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  kicker: string;
  tone?: "danger" | "info";
  onConfirm: () => void | Promise<void>;
}

interface InventoryDraft {
  name: string;
  description: string;
  tagsText: string;
}

interface GroupDraft {
  name: string;
  note: string;
  tagsText: string;
  varsSummary: string;
}

interface HostDraft {
  name: string;
  address: string;
  platform: string;
  connection: ConnectionType;
  port: string;
  loginCredentialRef: string;
  becomeEnabled: boolean;
  legacyBecomeUser: string;
  legacyBecomeCredentialRef: string;
  status: HostStatus;
  note: string;
  groups: string[];
}

type InfoPanelDraft =
  | { kind: "inventory"; values: InventoryDraft }
  | { kind: "group"; values: GroupDraft }
  | { kind: "host"; values: HostDraft }
  | null;

interface HostDragData {
  kind: "host";
  inventoryId: string;
  hostId: string;
  hostAssetId?: string;
}

interface CredentialFormValues {
  name: string;
  credentialType: string;
  username: string;
  secret: string;
  becomeUsername: string;
  becomeSecret: string;
  clearBecomeSecret: boolean;
}

interface CredentialEditorState {
  mode: "create" | "edit";
  credentialId: string | null;
  values: CredentialFormValues;
  baseline: CredentialFormValues;
  hasBecomeSecret: boolean;
}

interface CredentialManagerOpenOptions {
  startCreate?: boolean;
}

interface CredentialOverlayState {
  inventoryId: string;
  hostId: string;
  source: Exclude<CredentialManagerSource, "workspace">;
}

interface GroupDropData {
  kind: "group";
  inventoryId: string;
  groupId: string;
}

interface GroupView {
  group: PreviewGroup;
  relatedHosts: PreviewHost[];
  displayHosts: PreviewHost[];
  visible: boolean;
  statusSummary: string;
  protocolSummary: string;
}

interface InventoryView {
  inventory: PreviewInventory;
  groups: GroupView[];
  groupLookup: Map<string, PreviewGroup>;
  matchingHostIds: Set<string>;
  displayHosts: PreviewHost[];
  visible: boolean;
  statusSummary: string;
  protocolSummary: string;
}

interface HostRowView {
  rowKey: string;
  inventory: PreviewInventory | null;
  inventoryLabel?: string;
  inventoryMeta?: string;
  host: PreviewHost;
  hostAssetId?: string;
  openAsHostAsset?: boolean;
  groupNames: string[];
  isOrphan?: boolean;
}

interface SelectedHostAssetSummary {
  id: string;
  name: string;
  memberships: ManagedInventoryV2HostAssetDetail["memberships"];
}

const STATUS_META: Record<HostStatus, { label: string; className: string }> = {
  success: { label: "정상", className: "badge-successful" },
  running: { label: "점검 중", className: "badge-running" },
  pending: { label: "대기", className: "badge-pending" },
  failed: { label: "주의", className: "badge-failed" },
};

const CONNECTION_LABELS: Record<ConnectionType, string> = {
  ssh: "SSH",
  winrm: "WinRM",
  local: "Local",
};

const STATUS_ORDER: HostStatus[] = ["success", "running", "pending", "failed"];
const CONNECTION_ORDER: ConnectionType[] = ["ssh", "winrm", "local"];

const PREVIEW_GROUP_ID_VAR = "_preview_id";
const PREVIEW_GROUP_NOTE_VAR = "_preview_note";
const PREVIEW_GROUP_ZONE_VAR = "_preview_zone";
const PREVIEW_GROUP_VARS_SUMMARY_VAR = "_preview_vars_summary";
const PREVIEW_GROUP_HIDDEN_VAR = "_preview_hidden";
const PREVIEW_HOST_PLATFORM_VAR = "_preview_platform";
const PREVIEW_HOST_NOTE_VAR = "_preview_note";
const PREVIEW_HOST_STATUS_VAR = "_preview_status";
const UNASSIGNED_GROUP_NAME = "__ansibleharness_unassigned__";
const HOST_BECOME_CREDENTIAL_REQUIRED_MESSAGE =
  "become을 사용하려면 become 계정 정보가 포함된 로그인 자격 증명을 선택하거나 새로 만드세요.";

function createSlug(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣_-]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return slug || "item";
}

function getStringVar(
  vars: Record<string, string> | undefined,
  key: string,
  fallback = ""
): string {
  const value = vars?.[key];
  return typeof value === "string" ? value : fallback;
}

function normalizeOptionalText(value: string | null | undefined): string {
  return typeof value === "string" ? value : "";
}

function isHiddenPreviewGroup(group: { name: string; group_vars?: Record<string, string> }): boolean {
  return group.name === UNASSIGNED_GROUP_NAME || group.group_vars?.[PREVIEW_GROUP_HIDDEN_VAR] === "true";
}

function normalizePreviewConnection(value: string | undefined): ConnectionType {
  if (value === "winrm" || value === "local") {
    return value;
  }

  return "ssh";
}

function normalizePreviewStatus(value: InventoryConnectionStatus | undefined): HostStatus {
  if (value === "success" || value === "failed") {
    return value;
  }

  return "pending";
}

function readLoginCredentialRef(host: InventoryHostV2): string {
  return normalizeOptionalText(
    host.login_credential_ref ?? host.ansibleharness_login_credential_ref
  );
}

function getInventoryCredentialRef(credential: InventoryCredentialV2Summary): string {
  return credential.ref ?? credential.id ?? "";
}

function truncateCredentialRef(value: string, maxLength = 36): string {
  const normalizedValue = value.trim();

  if (normalizedValue.length <= maxLength) {
    return normalizedValue;
  }

  return `${normalizedValue.slice(0, 20)}…${normalizedValue.slice(-10)}`;
}

function isMachineGeneratedCredentialName(value: string): boolean {
  const normalizedValue = value.trim().toLowerCase();

  if (!normalizedValue) {
    return false;
  }

  return [
    /^(?:gcred|cred)[_-]?[0-9a-f]{16,}$/,
    /^[0-9a-f]{24,}$/,
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/,
    /-[0-9a-f]{24,}$/,
    /^(?:embedded|legacy|generated|test)[a-z0-9-]*-[0-9a-f]{16,}$/,
  ].some((pattern) => pattern.test(normalizedValue));
}

function formatInventoryCredentialPrimaryLabel(
  credential: InventoryCredentialV2Summary
): string {
  const name = credential.name.trim();
  const credentialType = credential.credential_type.trim();
  const username = credential.username.trim();

  if (name && !isMachineGeneratedCredentialName(name)) {
    return name;
  }

  if (username && credentialType) {
    return `${username} · ${credentialType}`;
  }

  if (username) {
    return username;
  }

  if (credentialType) {
    return `${credentialType} 자격 증명`;
  }

  return "이름 없는 자격 증명";
}

function findInventoryCredentialByRef(
  credentials: InventoryCredentialV2Summary[],
  credentialRef: string
): InventoryCredentialV2Summary | null {
  const normalizedRef = credentialRef.trim();
  if (!normalizedRef) {
    return null;
  }

  return (
    credentials.find((credential) => getInventoryCredentialRef(credential) === normalizedRef) ?? null
  );
}

function readConnectionStatus(host: InventoryHostV2): HostStatus {
  const storedStatus = normalizePreviewStatus(host.host_vars?.[PREVIEW_HOST_STATUS_VAR]);
  if (storedStatus !== "pending") {
    return storedStatus;
  }

  const status = host.connection_status;
  if (typeof status === "string") {
    return normalizePreviewStatus(status);
  }

  return normalizePreviewStatus(status?.status ?? undefined);
}

function collectInventoryHosts(detail: ManagedInventoryV2Detail): InventoryHostV2[] {
  const hostsByKey = new Map<string, InventoryHostV2>();

  const addHost = (host: InventoryHostV2) => {
    const key = host.key || host.name;
    if (!hostsByKey.has(key)) {
      hostsByKey.set(key, host);
    }
  };

  detail.hosts.forEach(addHost);
  detail.groups.forEach((group) => group.hosts.forEach(addHost));

  return Array.from(hostsByKey.values());
}

function v2DetailToPreviewInventory(detail: ManagedInventoryV2Detail): PreviewInventory {
  const visibleGroups = detail.groups.filter((group) => !isHiddenPreviewGroup(group));
  const groups = visibleGroups.map<PreviewGroup>((group) => ({
    id: getStringVar(
      group.group_vars,
      PREVIEW_GROUP_ID_VAR,
      `group-${detail.id}-${createSlug(group.name)}`
    ),
    name: group.name,
    note: getStringVar(group.group_vars, PREVIEW_GROUP_NOTE_VAR, ""),
    tags:
      group.tags ??
      (() => {
        const legacyZone = getStringVar(group.group_vars, PREVIEW_GROUP_ZONE_VAR, "").trim();
        return legacyZone ? [legacyZone] : [];
      })(),
    varsSummary: getStringVar(group.group_vars, PREVIEW_GROUP_VARS_SUMMARY_VAR, ""),
  }));
  const groupIdByName = new Map(groups.map((group) => [group.name, group.id]));
  const hostGroupsByKey = new Map<string, Set<string>>();

  detail.memberships.forEach((membership) => {
    const groupId = groupIdByName.get(membership.group_name);
    if (!groupId) {
      return;
    }

    const current = hostGroupsByKey.get(membership.host_key) ?? new Set<string>();
    current.add(groupId);
    hostGroupsByKey.set(membership.host_key, current);
  });

  visibleGroups.forEach((group) => {
    const groupId = groupIdByName.get(group.name);
    if (!groupId) {
      return;
    }

    (group.host_keys ?? []).forEach((hostKey) => {
      const current = hostGroupsByKey.get(hostKey) ?? new Set<string>();
      current.add(groupId);
      hostGroupsByKey.set(hostKey, current);
    });
  });

  const hosts = collectInventoryHosts(detail).map<PreviewHost>((host, index) => {
    const hostId = host.key || host.name || `host-${detail.id}-${index + 1}`;

    return {
      id: hostId,
      name: host.name,
      address: host.address,
      platform: getStringVar(host.host_vars, PREVIEW_HOST_PLATFORM_VAR, "Linux"),
      connection: normalizePreviewConnection(host.connection_type),
      port: String(host.port ?? 22),
      loginCredentialRef: readLoginCredentialRef(host),
      becomeEnabled: Boolean(host.become_enabled),
      legacyBecomeUser: normalizeOptionalText(host.become_user),
      legacyBecomeCredentialRef: normalizeOptionalText(
        host.become_credential_ref ?? host.ansibleharness_become_credential_ref
      ),
      status: readConnectionStatus(host),
      groups: Array.from(hostGroupsByKey.get(hostId) ?? []),
      note: getStringVar(host.host_vars, PREVIEW_HOST_NOTE_VAR, ""),
    };
  });

  return {
    id: detail.id,
    name: detail.name,
    description: detail.description ?? "",
    updatedAt: "서버 동기화됨",
    tags: detail.tags ?? detail.badges ?? [],
    groups,
    hosts,
  };
}

function v2HostAssetToPreviewHost(host: ManagedInventoryV2HostAssetDetail): PreviewHost {
  const hostId = host.key || host.name;
  return {
    id: hostId,
    name: host.name,
    address: host.address,
    platform: getStringVar(host.host_vars, PREVIEW_HOST_PLATFORM_VAR, "Linux"),
    connection: normalizePreviewConnection(host.connection_type),
    port: String(host.port ?? 22),
    loginCredentialRef: readLoginCredentialRef(host),
    becomeEnabled: Boolean(host.become_enabled),
    legacyBecomeUser: normalizeOptionalText(host.become_user),
    legacyBecomeCredentialRef: normalizeOptionalText(
      host.become_credential_ref ?? host.ansibleharness_become_credential_ref
    ),
    status: readConnectionStatus(host),
    groups: [],
    note: getStringVar(host.host_vars, PREVIEW_HOST_NOTE_VAR, ""),
  };
}

function buildV2Payload(inventory: PreviewInventory): ManagedInventoryV2CreateRequest {
  const unassignedHostKeys = inventory.hosts
    .filter((host) => host.groups.length === 0)
    .map((host) => host.id);
  const memberships = inventory.hosts.flatMap((host) =>
    host.groups.flatMap((groupId) => {
      const group = inventory.groups.find((item) => item.id === groupId);
      return group ? [{ group_name: group.name, host_key: host.id }] : [];
    })
  );

  return {
    name: inventory.name.trim(),
    description: inventory.description.trim(),
    tags: inventory.tags,
    groups: [
      ...inventory.groups.map((group) => ({
        name: group.name.trim(),
        tags: group.tags,
        group_vars: {
          [PREVIEW_GROUP_ID_VAR]: group.id,
          [PREVIEW_GROUP_NOTE_VAR]: group.note,
          [PREVIEW_GROUP_VARS_SUMMARY_VAR]: group.varsSummary,
        },
        host_keys: inventory.hosts
          .filter((host) => host.groups.includes(group.id))
          .map((host) => host.id),
        hosts: [],
      })),
      ...(unassignedHostKeys.length > 0
        ? [
            {
              name: UNASSIGNED_GROUP_NAME,
              tags: [],
              group_vars: {
                [PREVIEW_GROUP_HIDDEN_VAR]: "true",
              },
              host_keys: unassignedHostKeys,
              hosts: [],
            },
          ]
        : []),
    ],
    hosts: inventory.hosts.map((host) => {
      const loginCredentialRef = host.loginCredentialRef.trim();
      const legacyBecomeUser = host.becomeEnabled ? host.legacyBecomeUser.trim() : "";
      const legacyBecomeCredentialRef = host.becomeEnabled
        ? host.legacyBecomeCredentialRef.trim()
        : "";

      return {
        key: host.id,
        name: host.name.trim(),
        address: host.address.trim(),
        connection_type: host.connection,
        port: Number.parseInt(host.port, 10) || (host.connection === "winrm" ? 5986 : 22),
        become_enabled: host.becomeEnabled,
        become_user: legacyBecomeUser || undefined,
        login_credential_ref: loginCredentialRef || undefined,
        become_credential_ref: legacyBecomeCredentialRef || undefined,
        host_vars: {
          [PREVIEW_HOST_PLATFORM_VAR]: host.platform,
          [PREVIEW_HOST_NOTE_VAR]: host.note,
          [PREVIEW_HOST_STATUS_VAR]: host.status,
        },
      };
    }),
    memberships,
  };
}

function buildHostAssetUpdatePayload(
  draft: HostDraft,
  hostAsset: ManagedInventoryV2HostAssetDetail
): ManagedInventoryV2HostAssetUpdateRequest {
  const loginCredentialRef = draft.loginCredentialRef.trim();
  const legacyBecomeUser = draft.becomeEnabled ? draft.legacyBecomeUser.trim() : "";
  const legacyBecomeCredentialRef = draft.becomeEnabled
    ? draft.legacyBecomeCredentialRef.trim()
    : "";

  return {
    name: draft.name.trim(),
    address: draft.address.trim(),
    connection_type: draft.connection,
    port: Number.parseInt(draft.port, 10) || (draft.connection === "winrm" ? 5986 : 22),
    become_enabled: draft.becomeEnabled,
    become_user: legacyBecomeUser || undefined,
    login_credential_ref: loginCredentialRef || undefined,
    become_credential_ref: legacyBecomeCredentialRef || undefined,
    host_vars: {
      ...(hostAsset.host_vars ?? {}),
      [PREVIEW_HOST_PLATFORM_VAR]: draft.platform.trim(),
      [PREVIEW_HOST_NOTE_VAR]: draft.note.trim(),
      [PREVIEW_HOST_STATUS_VAR]: draft.status,
    },
  };
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "알 수 없는 오류";
}

function getCredentialDeleteErrorMessage(error: unknown): string {
  const message = getErrorMessage(error);
  if (message.includes("still used by one or more hosts")) {
    return "이 계정은 하나 이상의 호스트에서 사용 중이라 삭제할 수 없습니다. 먼저 호스트의 접속 계정을 해제하거나 다른 계정으로 변경하세요.";
  }
  return message;
}

function createSearchText(parts: Array<string | undefined | null>): string {
  return parts
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part))
    .join(" ")
    .toLowerCase();
}

function buildInventorySearchText(inventory: PreviewInventory): string {
  return createSearchText([
    inventory.name,
    inventory.description,
    inventory.tags.join(" "),
  ]);
}

function buildGroupSearchText(group: PreviewGroup): string {
  return createSearchText([group.name, group.note, group.tags.join(" "), group.varsSummary]);
}

function buildHostSearchText(
  host: PreviewHost,
  inventory: PreviewInventory,
  groupLookup: Map<string, PreviewGroup>
): string {
  const groupText = host.groups
    .flatMap((groupId) => {
      const group = groupLookup.get(groupId);
      return group
        ? [group.name, group.note, group.tags.join(" "), group.varsSummary]
        : [groupId];
    })
    .join(" ");

  return createSearchText([
    host.name,
    host.address,
    host.platform,
    CONNECTION_LABELS[host.connection],
    STATUS_META[host.status].label,
    host.note,
    groupText,
    inventory.name,
    inventory.description,
    inventory.tags.join(" "),
  ]);
}

function formatGroupName(groupId: string, inventory: PreviewInventory): string {
  const group = inventory.groups.find((item) => item.id === groupId);
  return group?.name ?? groupId;
}

function summarizeProtocols(hosts: PreviewHost[]): string {
  const summary = CONNECTION_ORDER.map((connection) => {
    const count = hosts.filter((host) => host.connection === connection).length;
    return count > 0 ? `${CONNECTION_LABELS[connection]} ${count}` : null;
  }).filter((item): item is string => item !== null);

  return summary.join(" · ") || "프로토콜 없음";
}

function summarizeStatuses(hosts: PreviewHost[]): string {
  const summary = STATUS_ORDER.map((status) => {
    const count = hosts.filter((host) => host.status === status).length;
    return count > 0 ? `${STATUS_META[status].label} ${count}` : null;
  }).filter((item): item is string => item !== null);

  return summary.join(" · ") || "상태 정보 없음";
}

function isHostInScope(scope: FocusScope, inventoryId: string, host: PreviewHost): boolean {
  if (scope.kind === "all") {
    return true;
  }

  if (scope.kind === "inventory") {
    return scope.inventoryId === inventoryId;
  }

  return scope.inventoryId === inventoryId && host.groups.includes(scope.groupId);
}

function getScopeLabel(scope: FocusScope, inventories: PreviewInventory[]): string {
  if (scope.kind === "all") {
    return "전체 워크스페이스";
  }

  const inventory = inventories.find((item) => item.id === scope.inventoryId);
  if (!inventory) {
    return "전체 워크스페이스";
  }

  if (scope.kind === "inventory") {
    return inventory.name;
  }

  return `${inventory.name} / ${formatGroupName(scope.groupId, inventory)}`;
}

function getCountLabel(matchingCount: number, totalCount: number, query: string): string {
  return query ? `${matchingCount} / ${totalCount}` : `${totalCount}`;
}

function createEntityId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function touchInventory(inventory: PreviewInventory): PreviewInventory {
  return {
    ...inventory,
    updatedAt: "방금 전",
  };
}

function toTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

function createInventoryDraft(inventory: PreviewInventory): InventoryDraft {
  return {
    name: inventory.name,
    description: inventory.description,
    tagsText: inventory.tags.join(", "),
  };
}

function createGroupDraft(group: PreviewGroup): GroupDraft {
  return {
    name: group.name,
    note: group.note,
    tagsText: group.tags.join(", "),
    varsSummary: group.varsSummary,
  };
}

function createHostDraft(host: PreviewHost): HostDraft {
  return {
    name: host.name,
    address: host.address,
    platform: host.platform,
    connection: host.connection,
    port: host.port,
    loginCredentialRef: host.loginCredentialRef,
    becomeEnabled: host.becomeEnabled,
    legacyBecomeUser: host.legacyBecomeUser,
    legacyBecomeCredentialRef: host.legacyBecomeCredentialRef,
    status: host.status,
    note: host.note,
    groups: [...host.groups],
  };
}

function normalizeInventoryDraftValues(values: InventoryDraft): InventoryDraft {
  return {
    name: values.name.trim(),
    description: values.description.trim(),
    tagsText: toTags(values.tagsText).join(", "),
  };
}

function normalizeGroupDraftValues(values: GroupDraft): GroupDraft {
  return {
    name: values.name.trim(),
    note: values.note.trim(),
    tagsText: toTags(values.tagsText).join(", "),
    varsSummary: values.varsSummary.trim(),
  };
}

function normalizeHostDraftValues(values: HostDraft): HostDraft {
  return {
    name: values.name.trim(),
    address: values.address.trim(),
    platform: values.platform.trim(),
    connection: values.connection,
    port: values.port.trim(),
    loginCredentialRef: values.loginCredentialRef.trim(),
    becomeEnabled: values.becomeEnabled,
    legacyBecomeUser: values.legacyBecomeUser.trim(),
    legacyBecomeCredentialRef: values.legacyBecomeCredentialRef.trim(),
    status: values.status,
    note: values.note.trim(),
    groups: [...values.groups].sort(),
  };
}

function areStringArraysEqual(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function isInventoryDraftDirty(draft: InventoryDraft, inventory: PreviewInventory): boolean {
  const current = normalizeInventoryDraftValues(draft);
  const baseline = normalizeInventoryDraftValues(createInventoryDraft(inventory));
  return (
    current.name !== baseline.name ||
    current.description !== baseline.description ||
    current.tagsText !== baseline.tagsText
  );
}

function isGroupDraftDirty(draft: GroupDraft, group: PreviewGroup): boolean {
  const current = normalizeGroupDraftValues(draft);
  const baseline = normalizeGroupDraftValues(createGroupDraft(group));
  return (
    current.name !== baseline.name ||
    current.note !== baseline.note ||
    current.tagsText !== baseline.tagsText ||
    current.varsSummary !== baseline.varsSummary
  );
}

function isHostDraftDirty(draft: HostDraft, host: PreviewHost): boolean {
  const current = normalizeHostDraftValues(draft);
  const baseline = normalizeHostDraftValues(createHostDraft(host));
  return (
    current.name !== baseline.name ||
    current.address !== baseline.address ||
    current.platform !== baseline.platform ||
    current.connection !== baseline.connection ||
    current.port !== baseline.port ||
    current.loginCredentialRef !== baseline.loginCredentialRef ||
    current.becomeEnabled !== baseline.becomeEnabled ||
    current.legacyBecomeUser !== baseline.legacyBecomeUser ||
    current.legacyBecomeCredentialRef !== baseline.legacyBecomeCredentialRef ||
    current.status !== baseline.status ||
    current.note !== baseline.note ||
    !areStringArraysEqual(current.groups, baseline.groups)
  );
}

function createEmptyCredentialFormValues(): CredentialFormValues {
  return {
    name: "",
    credentialType: "ssh_password",
    username: "",
    secret: "",
    becomeUsername: "",
    becomeSecret: "",
    clearBecomeSecret: false,
  };
}

function createCredentialEditorState(
  mode: "create" | "edit",
  credential?: InventoryCredentialV2Summary
): CredentialEditorState {
  const values = credential
    ? {
        name: credential.name,
        credentialType: credential.credential_type,
        username: credential.username,
        secret: "",
        becomeUsername: normalizeOptionalText(credential.become_username),
        becomeSecret: "",
        clearBecomeSecret: false,
      }
    : createEmptyCredentialFormValues();

  return {
    mode,
    credentialId: credential ? getInventoryCredentialRef(credential) : null,
    values,
    baseline: { ...values },
    hasBecomeSecret: credential?.has_become_secret ?? false,
  };
}

function normalizeCredentialFormValues(values: CredentialFormValues): CredentialFormValues {
  return {
    name: values.name.trim(),
    credentialType: values.credentialType.trim(),
    username: values.username.trim(),
    secret: values.secret.trim(),
    becomeUsername: values.becomeUsername.trim(),
    becomeSecret: values.becomeSecret.trim(),
    clearBecomeSecret: values.clearBecomeSecret,
  };
}

function isCredentialEditorDirty(editor: CredentialEditorState): boolean {
  const current = normalizeCredentialFormValues(editor.values);
  const baseline = normalizeCredentialFormValues(editor.baseline);

  return (
    current.name !== baseline.name ||
    current.credentialType !== baseline.credentialType ||
    current.username !== baseline.username ||
    current.secret !== baseline.secret ||
    current.becomeUsername !== baseline.becomeUsername ||
    current.becomeSecret !== baseline.becomeSecret ||
    current.clearBecomeSecret !== baseline.clearBecomeSecret
  );
}

function credentialSupportsBecome(credential: InventoryCredentialV2Summary): boolean {
  return credential.has_become_secret || Boolean(normalizeOptionalText(credential.become_username));
}

function selectedCredentialSupportsBecome(
  credentials: InventoryCredentialV2Summary[],
  credentialRef: string
): boolean {
  const credential = findInventoryCredentialByRef(credentials, credentialRef);
  return credential ? credentialSupportsBecome(credential) : false;
}

function createInventoryPreviewDraft(nextIndex: number): PreviewInventory {
  const name = `새 인벤토리 ${nextIndex}`;
  const draftId = createEntityId("inventory");

  return {
    id: draftId,
    name,
    description: "",
    updatedAt: "저장 전 초안",
    tags: ["초안"],
    groups: [],
    hosts: [],
  };
}

function getGroupDraftKey(inventoryId: string, groupId: string): string {
  return `${inventoryId}::${groupId}`;
}

function getInventorySelectionKey(inventoryId: string): string {
  return inventoryId;
}

function getHostSelectionKey(
  hostAssetId: string | undefined,
  inventoryId: string | null,
  hostId: string
): string {
  return hostAssetId ? `asset::${hostAssetId}` : `${inventoryId ?? "orphan"}::${hostId}`;
}

function remapFocusScopeInventoryId(
  scope: FocusScope,
  previousInventoryId: string,
  nextInventoryId: string
): FocusScope {
  if (scope.kind === "all" || scope.inventoryId !== previousInventoryId) {
    return scope;
  }

  if (scope.kind === "inventory") {
    return { kind: "inventory", inventoryId: nextInventoryId };
  }

  return {
    kind: "group",
    inventoryId: nextInventoryId,
    groupId: scope.groupId,
  };
}

function isHostDragData(data: unknown): data is HostDragData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as Record<string, unknown>;
  return (
    candidate.kind === "host" &&
    typeof candidate.inventoryId === "string" &&
    typeof candidate.hostId === "string" &&
    (candidate.hostAssetId === undefined || typeof candidate.hostAssetId === "string")
  );
}

function isGroupDropData(data: unknown): data is GroupDropData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as Record<string, unknown>;
  return (
    candidate.kind === "group" &&
    typeof candidate.inventoryId === "string" &&
    typeof candidate.groupId === "string"
  );
}

function getInventoryContext(
  scope: FocusScope,
  inventories: PreviewInventory[]
): PreviewInventory | null {
  if (scope.kind === "all") {
    return null;
  }

  return inventories.find((inventory) => inventory.id === scope.inventoryId) ?? null;
}

function DraggableHostRow({
  inventory,
  inventoryLabel,
  inventoryMeta,
  host,
  hostAssetId,
  groupNames,
  isSelected,
  onToggleSelect,
  onOpen,
  isOrphan = false,
}: {
  inventory: PreviewInventory | null;
  inventoryLabel?: string;
  inventoryMeta?: string;
  host: PreviewHost;
  hostAssetId?: string;
  groupNames: string[];
  isSelected: boolean;
  onToggleSelect: () => void;
  onOpen?: () => void;
  isOrphan?: boolean;
}) {
  const interactionDisabled = !inventory && !hostAssetId;
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `host:${hostAssetId ?? inventory?.id ?? "orphan"}:${host.id}`,
    disabled: interactionDisabled,
    data: {
      kind: "host",
      inventoryId: inventory?.id ?? "",
      hostId: host.id,
      hostAssetId,
    } satisfies HostDragData,
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`host-row ${isDragging ? "dragging" : ""} ${isOrphan ? "orphan-host-row" : ""}`}
      onDoubleClick={onOpen}
    >
      <td className="host-primary-cell">
        <div className="host-name-cell">
          <label className="host-select-control" aria-label={`${host.name} 호스트 선택`}>
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              onClick={(event) => event.stopPropagation()}
              data-testid={`host-select-${hostAssetId ?? host.id}`}
            />
          </label>
          <button
            type="button"
            className={`drag-handle ${isDragging ? "dragging" : ""}`}
            aria-label={`${host.name} 드래그 핸들`}
            disabled={interactionDisabled}
            {...listeners}
            {...attributes}
          >
            ⋮⋮
          </button>
          <button
            type="button"
            className="host-identity-button"
            onClick={onOpen}
            aria-label={`${host.name} 정보 열기`}
            disabled={!onOpen}
          >
            <div className="host-identity">
              <strong className="host-identity-name">{host.name}</strong>
              <span className="host-identity-meta">
                {groupNames.length > 0 ? `배정 그룹 ${groupNames.length}개` : "배정 그룹 없음"}
              </span>
            </div>
          </button>
        </div>
      </td>
      <td>
        <div className="inventory-cell">
          <strong>{inventoryLabel ?? inventory?.name ?? "미소속"}</strong>
          <span>{inventoryMeta ?? "전체 보기에서만 표시"}</span>
        </div>
      </td>
      <td className="host-group-cell">
        <div className="host-group-tags">
          {groupNames.length > 0 ? (
            groupNames.map((groupName) => (
              <span key={`${host.id}-${groupName}`} className="host-group-tag">
                {groupName}
              </span>
            ))
          ) : (
            <span className="host-group-tag host-group-tag-empty">미할당</span>
          )}
        </div>
      </td>
      <td className="text-mono host-address">{host.address}</td>
      <td>
        <div className="platform-stack">
          <strong>{host.platform}</strong>
          <span>
            {CONNECTION_LABELS[host.connection]} · Port {host.port}
          </span>
        </div>
      </td>
      <td className="host-status-cell">
        <span className={`badge ${STATUS_META[host.status].className}`}>
          <span className="badge-dot" />
          {STATUS_META[host.status].label}
        </span>
      </td>
    </tr>
  );
}

function DroppableGroupTreeItem({
  inventoryId,
  groupView,
  isFocused,
  isSelected,
  onSelect,
  onOpen,
  onToggleSelect,
  countLabel,
}: {
  inventoryId: string;
  groupView: GroupView;
  isFocused: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onToggleSelect: () => void;
  countLabel: string;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `group:${inventoryId}:${groupView.group.id}`,
    data: {
      kind: "group",
      inventoryId,
      groupId: groupView.group.id,
    } satisfies GroupDropData,
  });

  return (
    <div
      ref={setNodeRef}
      className={`tree-group-branch ${isOver ? "over" : ""}`}
      role="treeitem"
      aria-selected={isFocused}
    >
      <div className="tree-node-row group-row">
        <label className="group-select-control" aria-label={`${groupView.group.name} 그룹 선택`}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggleSelect}
            onClick={(event) => event.stopPropagation()}
            data-testid={`group-select-${inventoryId}-${groupView.group.id}`}
          />
        </label>
        <button
          type="button"
          className={`tree-node group-node ${isFocused ? "active" : ""}`}
          onClick={onSelect}
          onDoubleClick={onOpen}
          aria-pressed={isFocused}
        >
          <span className="tree-node-main">
            <strong className="node-title">{groupView.group.name}</strong>
          </span>
          <span className="tree-node-meta">
            <span className="node-count">호스트 {countLabel}</span>
            <span className={`group-dropzone ${isOver ? "over" : ""}`}>
              {isOver ? "여기에 놓기" : "드롭"}
            </span>
          </span>
        </button>
        <button
          type="button"
          className="tree-info-button"
          onClick={onOpen}
          aria-label={`${groupView.group.name} 정보 열기`}
        >
          i
        </button>
      </div>
    </div>
  );
}

export default function InventoryPreviewPage() {
  const [inventories, setInventories] = useState<PreviewInventory[]>([]);
  const [allHostAssets, setAllHostAssets] = useState<ManagedInventoryV2HostAssetDetail[]>([]);
  const [sharedCredentials, setSharedCredentials] = useState<InventoryCredentialV2Summary[]>([]);
  const [sharedCredentialError, setSharedCredentialError] = useState("");
  const [isLoadingSharedCredentials, setIsLoadingSharedCredentials] = useState(false);
  const [hasLoadedSharedCredentials, setHasLoadedSharedCredentials] = useState(false);
  const isLoadingSharedCredentialsRef = useRef(false);
  const [isLoadingInventories, setIsLoadingInventories] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [treeSearchQuery, setTreeSearchQuery] = useState("");
  const [focusedScope, setFocusedScope] = useState<FocusScope>({ kind: "all" });
  const [expandedInventoryIds, setExpandedInventoryIds] = useState<Set<string>>(new Set());
  const [selectedInventoryKeys, setSelectedInventoryKeys] = useState<Set<string>>(new Set());
  const [selectedGroupKeys, setSelectedGroupKeys] = useState<Set<string>>(new Set());
  const [selectedHostKeys, setSelectedHostKeys] = useState<Set<string>>(new Set());
  const [bulkHostAssignmentTarget, setBulkHostAssignmentTarget] = useState("");
  const [hostAssetAssignmentTarget, setHostAssetAssignmentTarget] = useState("");
  const [pendingInventoryDraftIds, setPendingInventoryDraftIds] = useState<Set<string>>(new Set());
  const [pendingGroupDraftIds, setPendingGroupDraftIds] = useState<Set<string>>(new Set());
  const [pendingHostDraftIds, setPendingHostDraftIds] = useState<Set<string>>(new Set());
  const [infoPanel, setInfoPanel] = useState<InfoPanelState>(null);
  const [isHostAssignmentEditorOpen, setIsHostAssignmentEditorOpen] = useState(false);
  const [infoPanelDraft, setInfoPanelDraft] = useState<InfoPanelDraft>(null);
  const [credentialOverlay, setCredentialOverlay] = useState<CredentialOverlayState | null>(null);
  const [credentialSearchQuery, setCredentialSearchQuery] = useState("");
  const [credentialEditor, setCredentialEditor] = useState<CredentialEditorState | null>(null);
  const [credentialEditorError, setCredentialEditorError] = useState("");
  const [pendingCredentialCreateInventoryId, setPendingCredentialCreateInventoryId] = useState<string | null>(
    null
  );
  const [isSavingCredential, setIsSavingCredential] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  useEffect(() => {
    if (!feedback) {
      return;
    }

    const timer = window.setTimeout(() => {
      setFeedback(null);
    }, 5000);

    return () => window.clearTimeout(timer);
  }, [feedback]);

  useEffect(() => {
    let cancelled = false;

    const loadInventories = async () => {
      setIsLoadingInventories(true);

      try {
        const [inventoryList, hostAssets] = await Promise.all([
          fetchManagedInventoriesV2(),
          fetchManagedInventoryHostAssetsV2(),
        ]);
        const details = await Promise.all(
          inventoryList.map((inventory) => fetchManagedInventoryV2(inventory.id))
        );
        const nextInventories = details.map(v2DetailToPreviewInventory);

        if (cancelled) {
          return;
        }

        setInventories(nextInventories);
        setAllHostAssets(hostAssets);
        const firstInventory = nextInventories[0] ?? null;
        setFocusedScope(firstInventory ? { kind: "inventory", inventoryId: firstInventory.id } : { kind: "all" });
        setExpandedInventoryIds(new Set(firstInventory ? [firstInventory.id] : []));
        setFeedback(null);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setInventories([]);
        setAllHostAssets([]);
        setFocusedScope({ kind: "all" });
        setExpandedInventoryIds(new Set());
        setFeedback({
          tone: "error",
          message: `인벤토리 API를 불러오지 못했습니다: ${getErrorMessage(error)}`,
        });
      } finally {
        if (!cancelled) {
          setIsLoadingInventories(false);
        }
      }
    };

    void loadInventories();

    return () => {
      cancelled = true;
      isLoadingSharedCredentialsRef.current = false;
      setIsLoadingSharedCredentials(false);
    };
  }, []);

  const activeCredentialManager = useMemo(
    () =>
      credentialOverlay ??
      (infoPanel?.kind === "credentials"
        ? { inventoryId: infoPanel.inventoryId, source: "workspace" as const }
        : null),
    [credentialOverlay, infoPanel]
  );

  useEffect(() => {
    const inventoryId =
      credentialOverlay?.inventoryId ??
      (infoPanel && (infoPanel.kind === "host" || infoPanel.kind === "credentials")
        ? infoPanel.inventoryId
        : infoPanel?.kind === "hostAsset"
          ? "host-asset"
          : null);

    if (!inventoryId) {
      return;
    }

    if (
      (inventoryId !== "host-asset" && pendingInventoryDraftIds.has(inventoryId)) ||
      sharedCredentialError ||
      hasLoadedSharedCredentials ||
      isLoadingSharedCredentialsRef.current
    ) {
      return;
    }

    let cancelled = false;

    isLoadingSharedCredentialsRef.current = true;
    setIsLoadingSharedCredentials(true);

    void fetchGlobalCredentials()
      .then((credentials) => {
        if (cancelled) {
          return;
        }

        setSharedCredentials(credentials);
        setSharedCredentialError("");
        setHasLoadedSharedCredentials(true);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setSharedCredentialError(getErrorMessage(error));
      })
      .finally(() => {
        if (cancelled) {
          return;
        }

        isLoadingSharedCredentialsRef.current = false;
        setIsLoadingSharedCredentials(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    credentialOverlay,
    hasLoadedSharedCredentials,
    infoPanel,
    pendingInventoryDraftIds,
    sharedCredentialError,
  ]);

  useEffect(() => {
    if (!credentialOverlay) {
      return;
    }

    if (
      !infoPanel ||
      infoPanel.kind !== "host" ||
      infoPanel.inventoryId !== credentialOverlay.inventoryId ||
      infoPanel.hostId !== credentialOverlay.hostId
    ) {
      setCredentialOverlay(null);
      setPendingCredentialCreateInventoryId(null);
      resetCredentialEditor();
    }
  }, [credentialOverlay, infoPanel]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const normalizedTreeQuery = treeSearchQuery.trim().toLowerCase();
  const inventoryViews = useMemo<InventoryView[]>(() => {
    return inventories.map((inventory) => {
      const groupLookup = new Map(inventory.groups.map((group) => [group.id, group]));
      const inventoryMatchesHostQuery = normalizedQuery
        ? buildInventorySearchText(inventory).includes(normalizedQuery)
        : true;
      const inventoryMatchesTreeQuery = normalizedTreeQuery
        ? buildInventorySearchText(inventory).includes(normalizedTreeQuery)
        : true;

      const matchingHosts = inventory.hosts.filter((host) => {
        if (!normalizedQuery) {
          return true;
        }

        return buildHostSearchText(host, inventory, groupLookup).includes(normalizedQuery);
      });

      const matchingHostIds = new Set(matchingHosts.map((host) => host.id));

      const groups = inventory.groups.map<GroupView>((group) => {
        const relatedHosts = inventory.hosts.filter((host) => host.groups.includes(group.id));
        const displayHosts = normalizedQuery
          ? relatedHosts.filter((host) => matchingHostIds.has(host.id))
          : relatedHosts;

        const groupMatchesHostQuery = normalizedQuery
          ? buildGroupSearchText(group).includes(normalizedQuery)
          : true;
        const groupMatchesTreeQuery = normalizedTreeQuery
          ? buildGroupSearchText(group).includes(normalizedTreeQuery)
          : true;
        const visibleByHostQuery =
          !normalizedQuery ||
          inventoryMatchesHostQuery ||
          groupMatchesHostQuery ||
          displayHosts.length > 0;
        const visibleByTreeQuery =
          !normalizedTreeQuery || inventoryMatchesTreeQuery || groupMatchesTreeQuery;

        return {
          group,
          relatedHosts,
          displayHosts,
          visible: visibleByHostQuery && visibleByTreeQuery,
          statusSummary: summarizeStatuses(displayHosts),
          protocolSummary: summarizeProtocols(displayHosts),
        };
      });

      const displayHosts = normalizedQuery ? matchingHosts : inventory.hosts;

      return {
        inventory,
        groups,
        groupLookup,
        matchingHostIds,
        displayHosts,
        visible:
          (!normalizedQuery ||
            inventoryMatchesHostQuery ||
            displayHosts.length > 0 ||
            groups.some((group) => group.visible)) &&
          (!normalizedTreeQuery ||
            inventoryMatchesTreeQuery ||
            groups.some((group) => group.visible)),
        statusSummary: summarizeStatuses(displayHosts),
        protocolSummary: summarizeProtocols(displayHosts),
      };
    });
  }, [inventories, normalizedQuery, normalizedTreeQuery]);

  const filteredHostRows = useMemo<HostRowView[]>(() => {
    if (focusedScope.kind === "all") {
      return allHostAssets
        .map((hostAsset) => {
          const host = v2HostAssetToPreviewHost(hostAsset);
          const memberships = hostAsset.memberships;
          const uniqueInventoryIds = [...new Set(memberships.map((membership) => membership.inventory_id))];
          const inventory =
            uniqueInventoryIds.length === 1
              ? inventories.find((item) => item.id === uniqueInventoryIds[0]) ?? null
              : null;
          const inventoryLabel =
            memberships.length === 0
              ? "미소속"
              : uniqueInventoryIds.length === 1
                ? memberships[0]?.inventory_name || inventory?.name || "연결된 인벤토리"
                : `${memberships[0]?.inventory_name || "연결된 인벤토리"} 외 ${uniqueInventoryIds.length - 1}개`;
          const inventoryMeta =
            memberships.length === 0
              ? "전체 보기에서만 표시"
              : uniqueInventoryIds.length === 1
                ? "연결됨"
                : "중복 연결";
          const groupNames =
            memberships.length === 0
              ? []
              : memberships.map((membership) =>
                  uniqueInventoryIds.length > 1
                    ? `${membership.inventory_name} / ${membership.group_name}`
                    : membership.group_name
                );
          return {
            rowKey: `asset-${hostAsset.id}`,
            inventory,
            inventoryLabel,
            inventoryMeta,
            host,
            hostAssetId: hostAsset.id,
            openAsHostAsset: true,
            groupNames,
            isOrphan: memberships.length === 0,
          };
        })
        .filter(
          ({ host, inventoryLabel, inventoryMeta, groupNames }) =>
            !normalizedQuery ||
            createSearchText([
              host.name,
              host.address,
              host.platform,
              CONNECTION_LABELS[host.connection],
              inventoryLabel,
              inventoryMeta,
              ...groupNames,
            ]).includes(normalizedQuery)
        );
    }

    const inventoryRows = inventoryViews.flatMap((view) =>
      view.inventory.hosts
        .filter((host) => isHostInScope(focusedScope, view.inventory.id, host))
        .filter((host) => !normalizedQuery || view.matchingHostIds.has(host.id))
        .map((host) => ({
          rowKey: `${view.inventory.id}-${host.id}`,
          inventory: view.inventory,
          hostAssetId:
            allHostAssets.find(
              (hostAsset) =>
                hostAsset.key === host.id &&
                hostAsset.memberships.some(
                  (membership) => membership.inventory_id === view.inventory.id
                )
            )?.id,
          host,
          groupNames: host.groups.map((groupId) => formatGroupName(groupId, view.inventory)),
        }))
    );

    return inventoryRows;
  }, [allHostAssets, focusedScope, inventories, inventoryViews, normalizedQuery]);

  const scopeTotalHostCount = useMemo(() => {
    const scopedInventoryHosts = inventories.flatMap((inventory) =>
      inventory.hosts.filter((host) => isHostInScope(focusedScope, inventory.id, host))
    ).length;

    if (focusedScope.kind !== "all") {
      return scopedInventoryHosts;
    }

    return allHostAssets.length;
  }, [allHostAssets, focusedScope, inventories]);

  const visibleInventoryCount = inventoryViews.filter((inventory) => inventory.visible).length;
  const visibleGroupCount = inventoryViews.reduce(
    (total, inventory) => total + inventory.groups.filter((group) => group.visible).length,
    0
  );

  const infoPanelInventory =
    infoPanel &&
    (infoPanel.kind === "inventory" ||
      infoPanel.kind === "group" ||
      infoPanel.kind === "host" ||
      infoPanel.kind === "credentials")
      ? inventories.find((inventory) => inventory.id === infoPanel.inventoryId) ?? null
      : null;

  const infoPanelHostAsset =
    infoPanel?.kind === "hostAsset"
      ? allHostAssets.find((host) => host.id === infoPanel.hostAssetId) ?? null
      : null;

  const infoPanelHostAssetPreview = infoPanelHostAsset
    ? v2HostAssetToPreviewHost(infoPanelHostAsset)
    : null;

  const infoPanelHostAssetGroupNames = infoPanelHostAsset
    ? infoPanelHostAsset.memberships.map(
        (membership) => `${membership.inventory_name} / ${membership.group_name}`
      )
    : [];

  const infoPanelGroup =
    infoPanel?.kind === "group" && infoPanelInventory
      ? infoPanelInventory.groups.find((group) => group.id === infoPanel.groupId) ?? null
      : null;

  const infoPanelHost =
    infoPanel?.kind === "host" && infoPanelInventory
      ? infoPanelInventory.hosts.find((host) => host.id === infoPanel.hostId) ?? null
      : null;

  const infoPanelHostLinkedAsset =
    infoPanel?.kind === "host" && infoPanelHost
      ? allHostAssets.find(
          (hostAsset) =>
            hostAsset.key === infoPanelHost.id ||
            hostAsset.id === infoPanelHost.id ||
            (hostAsset.name === infoPanelHost.name && hostAsset.address === infoPanelHost.address)
        ) ?? null
      : null;

  const activeInfoPanelHostAsset = infoPanelHostAsset ?? infoPanelHostLinkedAsset;

  const infoPanelGroupHosts =
    infoPanelInventory && infoPanelGroup
      ? infoPanelInventory.hosts.filter((host) => host.groups.includes(infoPanelGroup.id))
      : [];

  const infoPanelHostGroupNames =
    infoPanelInventory && infoPanelHost
      ? infoPanelHost.groups.map((groupId) => formatGroupName(groupId, infoPanelInventory))
      : [];

  const infoPanelHostDraftGroupNames =
    infoPanelInventory && infoPanelDraft?.kind === "host"
      ? infoPanelDraft.values.groups.map((groupId) => formatGroupName(groupId, infoPanelInventory))
      : infoPanelHostGroupNames;

  const infoPanelInventoryCredentials =
    infoPanel &&
    (infoPanel.kind === "host" ||
      infoPanel.kind === "credentials" ||
      infoPanel.kind === "hostAsset")
      ? sharedCredentials
      : [];

  const missingHostLoginCredentialRef =
    infoPanelDraft?.kind === "host" &&
    infoPanelDraft.values.loginCredentialRef.trim() &&
    !findInventoryCredentialByRef(
      infoPanelInventoryCredentials,
      infoPanelDraft.values.loginCredentialRef
    )
      ? infoPanelDraft.values.loginCredentialRef.trim()
      : "";

  const selectedHostLoginCredential =
    infoPanelDraft?.kind === "host"
      ? findInventoryCredentialByRef(
          infoPanelInventoryCredentials,
          infoPanelDraft.values.loginCredentialRef
        )
      : null;

  const hostCredentialPickerDisabled =
    infoPanel?.kind === "host" && pendingInventoryDraftIds.has(infoPanel.inventoryId);

  const canSelectedHostCredentialBecome = selectedHostLoginCredential
    ? credentialSupportsBecome(selectedHostLoginCredential)
    : false;

  const selectedHostCredentialPrimaryText = selectedHostLoginCredential
    ? formatInventoryCredentialPrimaryLabel(selectedHostLoginCredential)
    : missingHostLoginCredentialRef
      ? "현재 연결된 계정을 찾을 수 없음"
      : "계정 없이 접속";

  const selectedHostCredentialMetaText = selectedHostLoginCredential
    ? `${selectedHostLoginCredential.credential_type} · ${selectedHostLoginCredential.username || "사용자명 없음"}`
    : missingHostLoginCredentialRef
      ? `참조 ${truncateCredentialRef(missingHostLoginCredentialRef)}`
      : "필요하면 오른쪽 버튼에서 선택하거나 관리하세요.";

  const isHostInfoPanelDraft =
    infoPanelDraft?.kind === "host" && (infoPanel?.kind === "host" || infoPanel?.kind === "hostAsset");

  const hostPanelStatusMeta = isHostInfoPanelDraft
    ? STATUS_META[infoPanelDraft.values.status]
    : null;

  const hostPanelConnectionLabel = isHostInfoPanelDraft
    ? CONNECTION_LABELS[infoPanelDraft.values.connection]
    : "";

  const hostPanelGroupNames =
    infoPanel?.kind === "hostAsset"
      ? infoPanelHostAssetGroupNames
      : isHostInfoPanelDraft
        ? infoPanelHostDraftGroupNames
        : [];

  const hostPanelGroupMetricValue =
    infoPanel?.kind === "hostAsset"
      ? hostPanelGroupNames.length > 0
        ? `${hostPanelGroupNames.length}개 연결`
        : "미소속"
      : hostPanelGroupNames.length > 0
        ? `${hostPanelGroupNames.length}개 그룹`
        : "없음";

  const hostPanelGroupMetricDetail =
    hostPanelGroupNames.length > 0
      ? `${hostPanelGroupNames.slice(0, 2).join(", ")}${
          hostPanelGroupNames.length > 2 ? ` 외 ${hostPanelGroupNames.length - 2}개` : ""
        }`
      : infoPanel?.kind === "hostAsset"
        ? "연결된 그룹이 없습니다."
        : "이 호스트가 포함된 그룹이 없습니다.";

  const infoPanelTargetName =
    infoPanel?.kind === "inventory"
      ? infoPanelInventory?.name ?? "선택 항목"
      : infoPanel?.kind === "group"
        ? infoPanelGroup?.name ?? "선택 항목"
        : infoPanel?.kind === "host"
          ? infoPanelHost?.name ?? "선택 항목"
          : infoPanel?.kind === "hostAsset"
            ? infoPanelHostAsset?.name ?? "선택 항목"
            : infoPanelInventory?.name ?? "선택 항목";

  const refreshHostAssets = async () => {
    const hostAssets = await fetchManagedInventoryHostAssetsV2();
    setAllHostAssets(hostAssets);
    return hostAssets;
  };

  const refreshInventoriesByIds = async (inventoryIds: string[]) => {
    const uniqueInventoryIds = [...new Set(inventoryIds)].filter(Boolean);

    if (uniqueInventoryIds.length === 0) {
      return;
    }

    const details = await Promise.all(
      uniqueInventoryIds.map((inventoryId) => fetchManagedInventoryV2(inventoryId))
    );
    const nextInventories = details.map(v2DetailToPreviewInventory);

    setInventories((current) =>
      current.map((inventory) =>
        nextInventories.find((nextInventory) => nextInventory.id === inventory.id) ?? inventory
      )
    );
  };

  const scopeLabel = getScopeLabel(focusedScope, inventories);
  const allInventoriesExpanded =
    inventories.length > 0 && inventories.every((inventory) => expandedInventoryIds.has(inventory.id));

  const updateInventoryLocally = (nextInventory: PreviewInventory) => {
    setInventories((current) =>
      current.map((item) => (item.id === nextInventory.id ? nextInventory : item))
    );
  };

  const ensureInventoryExpanded = (inventoryId: string) => {
    setExpandedInventoryIds((current) => {
      if (current.has(inventoryId)) {
        return current;
      }

      const next = new Set(current);
      next.add(inventoryId);
      return next;
    });
  };

  const toggleGroupSelection = (inventoryId: string, groupId: string) => {
    const groupKey = getGroupDraftKey(inventoryId, groupId);

    setSelectedGroupKeys((current) => {
      const next = new Set(current);

      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }

      return next;
    });
  };

  const clearGroupSelection = () => {
    setSelectedGroupKeys(new Set());
  };

  const toggleInventorySelection = (inventoryId: string) => {
    const selectionKey = getInventorySelectionKey(inventoryId);
    setSelectedInventoryKeys((current) => {
      const next = new Set(current);
      if (next.has(selectionKey)) {
        next.delete(selectionKey);
      } else {
        next.add(selectionKey);
      }
      return next;
    });
  };

  const clearInventorySelection = () => {
    setSelectedInventoryKeys(new Set());
  };

  const toggleHostSelection = (hostAssetId: string | undefined, inventoryId: string | null, hostId: string) => {
    const selectionKey = getHostSelectionKey(hostAssetId, inventoryId, hostId);
    setSelectedHostKeys((current) => {
      const next = new Set(current);
      if (next.has(selectionKey)) {
        next.delete(selectionKey);
      } else {
        next.add(selectionKey);
      }
      return next;
    });
  };

  const clearHostSelection = () => {
    setSelectedHostKeys(new Set());
  };

  const clearAllSelections = () => {
    clearInventorySelection();
    clearGroupSelection();
    clearHostSelection();
  };

  const getSelectedHostAssets = useCallback((): SelectedHostAssetSummary[] => {
    const selectedAssetIds = new Set<string>();

    filteredHostRows.forEach((row) => {
      const selectionKey = getHostSelectionKey(row.hostAssetId, row.inventory?.id ?? null, row.host.id);
      if (selectedHostKeys.has(selectionKey) && row.hostAssetId) {
        selectedAssetIds.add(row.hostAssetId);
      }
    });

    return allHostAssets
      .filter((hostAsset) => selectedAssetIds.has(hostAsset.id))
      .map((hostAsset) => ({
        id: hostAsset.id,
        name: hostAsset.name,
        memberships: hostAsset.memberships,
      }));
  }, [allHostAssets, filteredHostRows, selectedHostKeys]);

  const selectedHostAssetsForToolbar = useMemo(
    () => getSelectedHostAssets(),
    [getSelectedHostAssets]
  );

  const hostAssignmentTargetOptions = useMemo(
    () =>
      inventories.flatMap((inventory) =>
        inventory.groups.map((group) => ({
          value: `${inventory.id}::${group.id}`,
          inventoryId: inventory.id,
          inventoryName: inventory.name,
          groupId: group.id,
          groupName: group.name,
          label: `${inventory.name} / ${group.name}`,
        }))
      ),
    [inventories]
  );

  const selectedHostAssignmentTargetOption = useMemo(
    () => hostAssignmentTargetOptions.find((option) => option.value === hostAssetAssignmentTarget) ?? null,
    [hostAssignmentTargetOptions, hostAssetAssignmentTarget]
  );

  const assignHostAssetsToGroup = async (
    hosts: SelectedHostAssetSummary[],
    targetValue: string,
    options?: { clearSelection?: boolean; sourceHostName?: string }
  ) => {
    const target = hostAssignmentTargetOptions.find((option) => option.value === targetValue);

    if (!target) {
      setFeedback({ tone: "info", message: "호스트를 넣을 인벤토리/그룹을 선택하세요." });
      return false;
    }

    if (hosts.length === 0) {
      setFeedback({ tone: "info", message: "배정할 호스트를 먼저 선택하세요." });
      return false;
    }

    if (pendingInventoryDraftIds.has(target.inventoryId)) {
      setFeedback({
        tone: "info",
        message: `인벤토리 '${target.inventoryName}'를 먼저 저장하면 호스트를 그룹에 추가할 수 있습니다.`,
      });
      return false;
    }

    const assignableHosts = hosts.filter(
      (host) =>
        !host.memberships.some(
          (membership) =>
            membership.inventory_id === target.inventoryId &&
            membership.group_name === target.groupName
        )
    );
    const skippedCount = hosts.length - assignableHosts.length;

    if (assignableHosts.length === 0) {
      setFeedback({
        tone: "info",
        message:
          hosts.length > 1
            ? `선택한 호스트가 모두 이미 '${target.label}' 그룹에 배정되어 있습니다.`
            : `'${hosts[0]?.name ?? options?.sourceHostName ?? "호스트"}' 호스트는 이미 '${target.label}' 그룹에 배정되어 있습니다.`,
      });
      return false;
    }

    try {
      let updatedInventory: PreviewInventory | null = null;

      for (const host of assignableHosts) {
        updatedInventory = v2DetailToPreviewInventory(
          await attachManagedInventoryHostAssetV2(target.inventoryId, {
            host_id: host.id,
            group_name: target.groupName,
          })
        );
      }

      if (updatedInventory) {
        updateInventoryLocally(updatedInventory);
      }
      await refreshHostAssets();
      ensureInventoryExpanded(target.inventoryId);
      setFocusedScope({ kind: "all" });
      if (options?.clearSelection) {
        clearHostSelection();
      }
      setFeedback({
        tone: "success",
        message:
          assignableHosts.length > 1
            ? `선택 호스트 ${assignableHosts.length}개를 '${target.label}' 그룹에 추가했습니다.${
                skippedCount > 0 ? ` 이미 연결된 ${skippedCount}개는 건너뛰었습니다.` : ""
              }`
            : `'${assignableHosts[0]?.name ?? options?.sourceHostName ?? "호스트"}' 호스트를 '${target.label}' 그룹에 추가했습니다.${
                skippedCount > 0 ? ` 이미 연결된 ${skippedCount}개는 건너뛰었습니다.` : ""
              }`,
      });
      return true;
    } catch (error) {
      setFeedback({
        tone: "error",
        message: `호스트를 그룹에 추가하지 못했습니다: ${getErrorMessage(error)}`,
      });
      return false;
    }
  };

  const handleBulkAssignSelectedHosts = async () => {
    await assignHostAssetsToGroup(selectedHostAssetsForToolbar, bulkHostAssignmentTarget, {
      clearSelection: true,
    });
  };

  const handleAssignOpenHostAsset = async () => {
    if (!infoPanelHostAsset) {
      setFeedback({ tone: "error", message: "호스트 자산을 찾을 수 없습니다." });
      return;
    }

    await assignHostAssetsToGroup(
      [
        {
          id: infoPanelHostAsset.id,
          name: infoPanelHostAsset.name,
          memberships: infoPanelHostAsset.memberships,
        },
      ],
      hostAssetAssignmentTarget,
      { sourceHostName: infoPanelHostAsset.name }
    );
  };

  const handleAssignOpenHostToSelectedTarget = async () => {
    if (!activeInfoPanelHostAsset) {
      setFeedback({
        tone: "error",
        message: "이 호스트의 자산 ID를 찾을 수 없어 다른 인벤토리 그룹에 추가할 수 없습니다.",
      });
      return;
    }

    await assignHostAssetsToGroup(
      [
        {
          id: activeInfoPanelHostAsset.id,
          name: activeInfoPanelHostAsset.name,
          memberships: activeInfoPanelHostAsset.memberships,
        },
      ],
      hostAssetAssignmentTarget,
      { sourceHostName: activeInfoPanelHostAsset.name }
    );
  };

  const handleBulkDeleteSelectedInventories = () => {
    const selectedInventories = inventories.filter((inventory) =>
      selectedInventoryKeys.has(getInventorySelectionKey(inventory.id))
    );

    if (selectedInventories.length === 0) {
      setFeedback({ tone: "info", message: "삭제할 인벤토리를 먼저 선택하세요." });
      return;
    }

    const groupCount = selectedInventories.reduce((total, inventory) => total + inventory.groups.length, 0);
    const hostCount = selectedInventories.reduce((total, inventory) => total + inventory.hosts.length, 0);

    setConfirmDialog({
      title: "인벤토리 일괄 삭제",
      message: `인벤토리 ${selectedInventories.length}개와 그룹 ${groupCount}개를 삭제합니다. 호스트 ${hostCount}개는 삭제되지 않고 자산으로 보존됩니다.`,
      confirmLabel: "삭제하기",
      cancelLabel: "계속 편집",
      kicker: "삭제 확인",
      tone: "danger",
      onConfirm: async () => {
        const deletedIds: string[] = [];
        const failed: string[] = [];

        for (const inventory of selectedInventories) {
          try {
            await deleteManagedInventoryV2(inventory.id);
            deletedIds.push(inventory.id);
          } catch (error) {
            failed.push(`${inventory.name}: ${getErrorMessage(error)}`);
          }
        }

        if (deletedIds.length === 0) {
          setFeedback({
            tone: "error",
            message: `인벤토리를 삭제하지 못했습니다: ${failed.join(" / ")}`,
          });
          return;
        }

        try {
          await refreshHostAssets();
        } catch {
          setAllHostAssets((current) =>
            current.map((host) => ({
              ...host,
              memberships: host.memberships.filter(
                (membership) => !deletedIds.includes(membership.inventory_id)
              ),
            }))
          );
        }

        const nextInventories = inventories.filter((inventory) => !deletedIds.includes(inventory.id));
        const fallbackInventory = nextInventories[0] ?? null;
        setInventories(nextInventories);
        setExpandedInventoryIds((current) => {
          const next = new Set([...current].filter((inventoryId) => !deletedIds.includes(inventoryId)));
          if (next.size === 0 && fallbackInventory) {
            next.add(fallbackInventory.id);
          }
          return next;
        });
        setSelectedInventoryKeys((current) =>
          new Set([...current].filter((inventoryId) => !deletedIds.includes(inventoryId)))
        );
        setSelectedGroupKeys((current) =>
          new Set(
            [...current].filter(
              (selectionKey) =>
                !deletedIds.some((inventoryId) => selectionKey.startsWith(`${inventoryId}::`))
            )
          )
        );

        if (focusedScope.kind !== "all" && deletedIds.includes(focusedScope.inventoryId)) {
          setFocusedScope(
            fallbackInventory ? { kind: "inventory", inventoryId: fallbackInventory.id } : { kind: "all" }
          );
        }

        if (infoPanel && infoPanel.kind !== "hostAsset" && deletedIds.includes(infoPanel.inventoryId)) {
          dismissInfoPanel();
        }

        setFeedback({
          tone: failed.length > 0 ? "info" : "success",
          message:
            failed.length > 0
              ? `인벤토리 ${deletedIds.length}개를 삭제했습니다. 호스트 자산은 보존됩니다. 실패: ${failed.join(" / ")}`
              : `인벤토리 ${deletedIds.length}개를 삭제했습니다. 호스트 자산은 보존됩니다.`,
        });
      },
    });
  };

  const handleBulkDeleteSelectedHosts = () => {
    const selectedHosts = getSelectedHostAssets();

    if (selectedHosts.length === 0) {
      setFeedback({ tone: "info", message: "삭제할 호스트를 먼저 선택하세요." });
      return;
    }

    setConfirmDialog({
      title: "호스트 일괄 삭제",
      message: `호스트 자산 ${selectedHosts.length}개를 삭제합니다. 연결된 인벤토리/그룹 membership도 함께 제거됩니다.`,
      confirmLabel: "삭제하기",
      cancelLabel: "계속 편집",
      kicker: "삭제 확인",
      tone: "danger",
      onConfirm: async () => {
        const deletedIds: string[] = [];
        const failed: string[] = [];
        const affectedInventoryIds = new Set<string>();

        for (const host of selectedHosts) {
          host.memberships.forEach((membership) => affectedInventoryIds.add(membership.inventory_id));
          try {
            await deleteManagedInventoryHostAssetV2(host.id);
            deletedIds.push(host.id);
          } catch (error) {
            failed.push(`${host.name}: ${getErrorMessage(error)}`);
          }
        }

        if (deletedIds.length === 0) {
          setFeedback({ tone: "error", message: `호스트를 삭제하지 못했습니다: ${failed.join(" / ")}` });
          return;
        }

        await refreshHostAssets();
        await refreshInventoriesByIds([...affectedInventoryIds]);
        setSelectedHostKeys((current) =>
          new Set(
            [...current].filter(
              (selectionKey) => !deletedIds.some((hostId) => selectionKey === `asset::${hostId}`)
            )
          )
        );

        if (infoPanel?.kind === "hostAsset" && deletedIds.includes(infoPanel.hostAssetId)) {
          dismissInfoPanel();
        }

        setFeedback({
          tone: failed.length > 0 ? "info" : "success",
          message:
            failed.length > 0
              ? `호스트 ${deletedIds.length}개를 삭제했습니다. 실패: ${failed.join(" / ")}`
              : `호스트 ${deletedIds.length}개를 삭제했습니다.`,
        });
      },
    });
  };

  const handleBulkDeleteSelectedGroups = () => {
    const selectedGroupsByInventory = inventories
      .map((inventory) => ({
        inventory,
        groups: inventory.groups.filter((group) =>
          selectedGroupKeys.has(getGroupDraftKey(inventory.id, group.id))
        ),
      }))
      .filter((entry) => entry.groups.length > 0);

    if (selectedGroupsByInventory.length === 0) {
      setFeedback({ tone: "info", message: "삭제할 그룹을 먼저 선택하세요." });
      return;
    }

    if (selectedGroupsByInventory.length > 1) {
      setFeedback({
        tone: "info",
        message: "한 번에 하나의 인벤토리 안에서만 그룹을 삭제할 수 있습니다.",
      });
      return;
    }

    const [{ inventory, groups }] = selectedGroupsByInventory;
    const selectedGroupIds = new Set(groups.map((group) => group.id));
    const selectedGroupNames = new Set(groups.map((group) => group.name));
    const affectedHostCount = inventory.hosts.filter((host) =>
      host.groups.some((groupId) => selectedGroupIds.has(groupId))
    ).length;

    setConfirmDialog({
      title: "그룹 일괄 삭제",
      message: `그룹 ${groups.length}개를 삭제합니다. 호스트 ${affectedHostCount}개는 삭제되지 않고, 그룹 연결만 제거됩니다.`,
      confirmLabel: "삭제하기",
      cancelLabel: "계속 편집",
      kicker: "삭제 확인",
      tone: "danger",
      onConfirm: async () => {
        const nextInventory = touchInventory({
          ...inventory,
          groups: inventory.groups.filter((group) => !selectedGroupIds.has(group.id)),
          hosts: inventory.hosts.map((host) =>
            host.groups.some((groupId) => selectedGroupIds.has(groupId))
              ? {
                  ...host,
                  groups: host.groups.filter((groupId) => !selectedGroupIds.has(groupId)),
                }
              : host
          ),
        });

        const savedInventory = await persistInventory(
          nextInventory,
          `그룹 ${groups.length}개를 삭제했습니다. 호스트 자산은 보존됩니다.`
        );

        if (!savedInventory) {
          return;
        }

        setSelectedGroupKeys((current) => {
          const next = new Set(current);
          groups.forEach((group) => next.delete(getGroupDraftKey(inventory.id, group.id)));
          return next;
        });

        setPendingGroupDraftIds((current) => {
          const next = new Set(current);
          groups.forEach((group) => next.delete(getGroupDraftKey(inventory.id, group.id)));
          return next;
        });

        if (
          focusedScope.kind === "group" &&
          focusedScope.inventoryId === inventory.id &&
          selectedGroupIds.has(focusedScope.groupId)
        ) {
          setFocusedScope({ kind: "inventory", inventoryId: inventory.id });
        }

        if (
          infoPanel?.kind === "group" &&
          infoPanel.inventoryId === inventory.id &&
          selectedGroupIds.has(infoPanel.groupId)
        ) {
          setInfoPanel({ kind: "inventory", inventoryId: savedInventory.id });
          setInfoPanelDraft({ kind: "inventory", values: createInventoryDraft(savedInventory) });
        }

        try {
          await refreshHostAssets();
        } catch {
          setAllHostAssets((current) =>
            current.map((host) => ({
              ...host,
              memberships: host.memberships.filter(
                (membership) =>
                  membership.inventory_id !== inventory.id || !selectedGroupNames.has(membership.group_name)
              ),
            }))
          );
        }
      },
    });
  };

  const clearPendingInventoryDraft = (inventoryId: string) => {
    setPendingInventoryDraftIds((current) => {
      if (!current.has(inventoryId)) {
        return current;
      }

      const next = new Set(current);
      next.delete(inventoryId);
      return next;
    });
  };

  const clearPendingGroupDraft = (inventoryId: string, groupId: string) => {
    const groupDraftKey = getGroupDraftKey(inventoryId, groupId);

    setPendingGroupDraftIds((current) => {
      if (!current.has(groupDraftKey)) {
        return current;
      }

      const next = new Set(current);
      next.delete(groupDraftKey);
      return next;
    });
  };

  const removePendingInventoryDraft = (inventoryId: string) => {
    const draftInventory = inventories.find((item) => item.id === inventoryId);

    if (!draftInventory) {
      return;
    }

    const nextInventories = inventories.filter((item) => item.id !== inventoryId);
    const fallbackInventory = nextInventories[0] ?? null;
    const draftHostIds = new Set(draftInventory.hosts.map((host) => host.id));

    setInventories(nextInventories);
    clearPendingInventoryDraft(inventoryId);
    setPendingGroupDraftIds((current) =>
      new Set(
        [...current].filter((draftKey) => !draftKey.startsWith(`${inventoryId}::`))
      )
    );
    setPendingHostDraftIds((current) =>
      new Set([...current].filter((hostId) => !draftHostIds.has(hostId)))
    );
    setExpandedInventoryIds((current) => {
      const next = new Set(
        [...current].filter((currentInventoryId) => currentInventoryId !== inventoryId)
      );

      if (next.size === 0 && fallbackInventory) {
        next.add(fallbackInventory.id);
      }

      return next;
    });

    if (focusedScope.kind !== "all" && focusedScope.inventoryId === inventoryId) {
      setFocusedScope(
        fallbackInventory
          ? { kind: "inventory", inventoryId: fallbackInventory.id }
          : { kind: "all" }
      );
    }
  };

  const removePendingHostDraft = (inventoryId: string, hostId: string) => {
    setInventories((current) =>
      current.map((inventory) =>
        inventory.id === inventoryId
          ? touchInventory({
              ...inventory,
              hosts: inventory.hosts.filter((host) => host.id !== hostId),
            })
          : inventory
      )
    );
    setPendingHostDraftIds((current) => {
      if (!current.has(hostId)) {
        return current;
      }

      const next = new Set(current);
      next.delete(hostId);
      return next;
    });
  };

  const removePendingGroupDraft = (inventoryId: string, groupId: string) => {
    const inventory = inventories.find((item) => item.id === inventoryId);

    if (!inventory) {
      return;
    }

    updateInventoryLocally(
      touchInventory({
        ...inventory,
        groups: inventory.groups.filter((group) => group.id !== groupId),
        hosts: inventory.hosts.map((host) =>
          host.groups.includes(groupId)
            ? {
                ...host,
                groups: host.groups.filter((currentGroupId) => currentGroupId !== groupId),
              }
            : host
        ),
      })
    );
    clearPendingGroupDraft(inventoryId, groupId);

    if (
      focusedScope.kind === "group" &&
      focusedScope.inventoryId === inventoryId &&
      focusedScope.groupId === groupId
    ) {
      setFocusedScope({ kind: "inventory", inventoryId });
    }
  };

  const resetCredentialEditor = () => {
    setCredentialEditor(null);
    setCredentialEditorError("");
  };

  const dismissInfoPanel = () => {
    setInfoPanel(null);
    setInfoPanelDraft(null);
    resetCredentialEditor();
  };

  const dismissCredentialOverlay = () => {
    setCredentialOverlay(null);
    setCredentialSearchQuery("");
    setPendingCredentialCreateInventoryId(null);
    resetCredentialEditor();
  };

  const confirmDiscardCredentialEditor = (nextAction: () => void) => {
    setConfirmDialog({
      title: "자격 증명 변경 폐기",
      message:
        "저장하지 않은 자격 증명 변경이 있습니다. 지금 닫으면 입력한 자격 증명 수정이 반영되지 않습니다.",
      confirmLabel: "변경 버리기",
      cancelLabel: "계속 편집",
      kicker: "미저장 변경",
      tone: "danger",
      onConfirm: nextAction,
    });
  };

  const hasOpenInfoPanelUnsavedChanges = () => {
    if (!infoPanel) {
      return false;
    }

    if (infoPanel.kind === "credentials") {
      return credentialEditor ? isCredentialEditorDirty(credentialEditor) : false;
    }

    if (
      infoPanel.kind === "hostAsset" &&
      infoPanelDraft?.kind === "host" &&
      infoPanelHostAssetPreview
    ) {
      return isHostDraftDirty(infoPanelDraft.values, infoPanelHostAssetPreview);
    }

    if (!infoPanelDraft || !infoPanelInventory) {
      return false;
    }

    if (infoPanel.kind === "inventory" && infoPanelDraft.kind === "inventory") {
      return isInventoryDraftDirty(infoPanelDraft.values, infoPanelInventory);
    }

    if (
      infoPanel.kind === "group" &&
      infoPanelDraft.kind === "group" &&
      infoPanelGroup
    ) {
      return isGroupDraftDirty(infoPanelDraft.values, infoPanelGroup);
    }

    if (
      infoPanel.kind === "host" &&
      infoPanelDraft.kind === "host" &&
      infoPanelHost
    ) {
      return isHostDraftDirty(infoPanelDraft.values, infoPanelHost);
    }

    return false;
  };

  const maybeDiscardOpenPendingDraft = (nextAction?: () => void) => {
    if (!infoPanel) {
      return true;
    }

    const queueDiscardConfirm = (title: string, message: string, discardDraft: () => void) => {
      setConfirmDialog({
        title,
        message,
        confirmLabel: "초안 버리기",
        cancelLabel: "계속 편집",
        kicker: "미저장 변경",
        tone: "danger",
        onConfirm: () => {
          discardDraft();
          nextAction?.();
        },
      });
      return false;
    };

    if (infoPanel.kind === "inventory" && pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
      return queueDiscardConfirm(
        "인벤토리 초안 폐기",
        "저장하지 않은 인벤토리 초안이 있습니다. 지금 버리면 트리와 편집 패널에서 즉시 사라집니다.",
        () => removePendingInventoryDraft(infoPanel.inventoryId)
      );
    }

    if (
      infoPanel.kind === "group" &&
      pendingGroupDraftIds.has(getGroupDraftKey(infoPanel.inventoryId, infoPanel.groupId))
    ) {
      return queueDiscardConfirm(
        "그룹 초안 폐기",
        "저장하지 않은 그룹 초안이 있습니다. 지금 버리면 연결된 임시 배정도 함께 정리됩니다.",
        () => removePendingGroupDraft(infoPanel.inventoryId, infoPanel.groupId)
      );
    }

    if (infoPanel.kind !== "host" || !pendingHostDraftIds.has(infoPanel.hostId)) {
      if (!hasOpenInfoPanelUnsavedChanges()) {
        return true;
      }

      const dialogCopy =
        infoPanel.kind === "inventory"
          ? {
              title: "인벤토리 변경 폐기",
              message:
                "저장하지 않은 인벤토리 변경이 있습니다. 지금 닫으면 수정한 내용이 서버에 반영되지 않은 채 사라집니다.",
            }
          : infoPanel.kind === "group"
            ? {
                title: "그룹 변경 폐기",
                message:
                  "저장하지 않은 그룹 변경이 있습니다. 지금 닫으면 이름·태그·설명 수정이 저장되지 않습니다.",
              }
            : infoPanel.kind === "host"
              ? {
                  title: "호스트 변경 폐기",
                  message:
                    "저장하지 않은 호스트 변경이 있습니다. 지금 닫으면 접속 정보와 그룹 배정 수정이 저장되지 않습니다.",
                }
              : {
                  title: "자격 증명 변경 폐기",
                  message:
                    "저장하지 않은 자격 증명 변경이 있습니다. 지금 닫으면 입력한 자격 증명 수정이 반영되지 않습니다.",
                };

      setConfirmDialog({
        ...dialogCopy,
        confirmLabel: "변경 버리기",
        cancelLabel: "계속 편집",
        kicker: "미저장 변경",
        tone: "danger",
        onConfirm: () => {
          dismissInfoPanel();
          nextAction?.();
        },
      });

      return false;
    }

    return queueDiscardConfirm(
      "호스트 초안 폐기",
      "저장하지 않은 호스트 초안이 있습니다. 주소와 그룹 배정 변경이 서버에 반영되지 않은 채 사라집니다.",
      () => removePendingHostDraft(infoPanel.inventoryId, infoPanel.hostId)
    );
  };

  const handleCancelConfirmDialog = () => {
    setConfirmDialog(null);
  };

  const handleConfirmDialog = () => {
    if (!confirmDialog) {
      return;
    }

    const { onConfirm } = confirmDialog;
    setConfirmDialog(null);
    void onConfirm();
  };

  const closeInfoPanel = () => {
    if (!maybeDiscardOpenPendingDraft(dismissInfoPanel)) {
      return;
    }

    dismissInfoPanel();
  };

  const closeCredentialOverlay = () => {
    if (credentialEditor && isCredentialEditorDirty(credentialEditor)) {
      confirmDiscardCredentialEditor(dismissCredentialOverlay);
      return;
    }

    dismissCredentialOverlay();
  };

  const openInventoryPanel = (inventoryId: string) => {
    const proceed = () => {
      const inventory = inventories.find((item) => item.id === inventoryId);

      if (!inventory) {
        return;
      }

      setInfoPanel({ kind: "inventory", inventoryId });
      setInfoPanelDraft({ kind: "inventory", values: createInventoryDraft(inventory) });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const openGroupPanel = (inventoryId: string, groupId: string) => {
    const proceed = () => {
      const inventory = inventories.find((item) => item.id === inventoryId);
      const group = inventory?.groups.find((item) => item.id === groupId);

      if (!inventory || !group) {
        return;
      }

      ensureInventoryExpanded(inventoryId);
      setInfoPanel({ kind: "group", inventoryId, groupId });
      setInfoPanelDraft({ kind: "group", values: createGroupDraft(group) });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const openHostPanel = (inventoryId: string, hostId: string) => {
    const proceed = () => {
      const inventory = inventories.find((item) => item.id === inventoryId);
      const host = inventory?.hosts.find((item) => item.id === hostId);

      if (!inventory || !host) {
        return;
      }

      setInfoPanel({ kind: "host", inventoryId, hostId });
      setHostAssetAssignmentTarget("");
      setIsHostAssignmentEditorOpen(false);
      setInfoPanelDraft({ kind: "host", values: createHostDraft(host) });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const openHostAssetPanel = (hostAssetId: string) => {
    const proceed = () => {
      const hostAsset = allHostAssets.find((host) => host.id === hostAssetId);

      if (!hostAsset) {
        setFeedback({ tone: "error", message: "호스트 자산을 찾을 수 없습니다." });
        return;
      }

      setInfoPanel({ kind: "hostAsset", hostAssetId });
      setHostAssetAssignmentTarget("");
      setIsHostAssignmentEditorOpen(false);
      setInfoPanelDraft({
        kind: "host",
        values: createHostDraft(v2HostAssetToPreviewHost(hostAsset)),
      });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const openCredentialManager = (
    inventoryId: string,
    options?: CredentialManagerOpenOptions
  ) => {
    const proceed = () => {
      const inventory = inventories.find((item) => item.id === inventoryId);

      if (!inventory) {
        return;
      }

      if (pendingInventoryDraftIds.has(inventoryId)) {
        setFeedback({
          tone: "info",
          message: `인벤토리 '${inventory.name}'를 먼저 저장하면 공용 자격 증명을 연결할 수 있습니다.`,
        });
        return;
      }

      ensureInventoryExpanded(inventoryId);
      setFocusedScope({ kind: "inventory", inventoryId });
      setInfoPanel({ kind: "credentials", inventoryId });
      setInfoPanelDraft(null);
      resetCredentialEditor();
      setPendingCredentialCreateInventoryId(
        options?.startCreate ? inventoryId : null
      );
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const openCredentialOverlayFromHost = (
    inventoryId: string,
    hostId: string,
    options?: CredentialManagerOpenOptions
  ) => {
    const inventory = inventories.find((item) => item.id === inventoryId);

    if (!inventory) {
      return;
    }

    if (pendingInventoryDraftIds.has(inventoryId)) {
      setFeedback({
        tone: "info",
        message: `인벤토리 '${inventory.name}'를 먼저 저장하면 공용 자격 증명을 연결할 수 있습니다.`,
      });
      return;
    }

    ensureInventoryExpanded(inventoryId);
    resetCredentialEditor();
    setCredentialOverlay({
      inventoryId,
      hostId,
      source: options?.startCreate ? "host-create" : "host-select",
    });
    setCredentialSearchQuery("");
    setPendingCredentialCreateInventoryId(options?.startCreate ? inventoryId : null);
  };

  const handleOpenCredentialManagerFromSelection = () => {
    const inventory = getInventoryContext(focusedScope, inventories);

    if (!inventory) {
      setFeedback({
        tone: "info",
        message: "자격 증명을 관리하려면 먼저 인벤토리 또는 그룹 범위를 선택하세요.",
      });
      return;
    }

    openCredentialManager(inventory.id);
  };

  const refreshCredentials = async (): Promise<InventoryCredentialV2Summary[] | null> => {
    try {
      setIsLoadingSharedCredentials(true);
      const credentials = await fetchGlobalCredentials();
      setSharedCredentials(credentials);
      setSharedCredentialError("");
      setHasLoadedSharedCredentials(true);
      return credentials;
    } catch (error) {
      setSharedCredentialError(getErrorMessage(error));
      return null;
    } finally {
      setIsLoadingSharedCredentials(false);
    }
  };

  const handleStartCredentialCreate = useCallback(() => {
    if (!activeCredentialManager) return;
    setCredentialEditor(createCredentialEditorState("create"));
    setCredentialEditorError("");
  }, [activeCredentialManager]);

  useEffect(() => {
    if (!pendingCredentialCreateInventoryId) {
      return;
    }

    if (
      !activeCredentialManager ||
      activeCredentialManager.inventoryId !== pendingCredentialCreateInventoryId
    ) {
      return;
    }

    handleStartCredentialCreate();
    setPendingCredentialCreateInventoryId(null);
  }, [activeCredentialManager, handleStartCredentialCreate, pendingCredentialCreateInventoryId]);

  const handleStartCredentialEdit = (credential: InventoryCredentialV2Summary) => {
    setCredentialEditor(createCredentialEditorState("edit", credential));
    setCredentialEditorError("");
  };

  const handleCancelCredentialEditor = () => {
    resetCredentialEditor();
  };

  const applyHostLoginCredentialChange = (
    loginCredentialRef: string,
    credentials: InventoryCredentialV2Summary[]
  ) => {
    const shouldDisableBecome =
      infoPanelDraft?.kind === "host" &&
      infoPanelDraft.values.becomeEnabled &&
      !selectedCredentialSupportsBecome(credentials, loginCredentialRef);
    const shouldClearLegacyBecome =
      infoPanelDraft?.kind === "host" &&
      infoPanelDraft.values.loginCredentialRef.trim() !== loginCredentialRef.trim();

    setInfoPanelDraft((current) =>
      current?.kind === "host"
        ? {
            kind: "host",
            values: {
              ...current.values,
              loginCredentialRef,
              becomeEnabled: shouldDisableBecome ? false : current.values.becomeEnabled,
              legacyBecomeUser: shouldClearLegacyBecome ? "" : current.values.legacyBecomeUser,
              legacyBecomeCredentialRef: shouldClearLegacyBecome
                ? ""
                : current.values.legacyBecomeCredentialRef,
            },
          }
        : current
    );

    if (shouldDisableBecome) {
      setFeedback({ tone: "info", message: HOST_BECOME_CREDENTIAL_REQUIRED_MESSAGE });
    }
  };

  const handleCredentialEditorFieldChange = <K extends keyof CredentialFormValues>(
    field: K,
    value: CredentialFormValues[K]
  ) => {
    setCredentialEditor((current) => {
      if (!current) return current;
      return { ...current, values: { ...current.values, [field]: value } };
    });
  };

  const handleSaveCredential = async () => {
    if (!activeCredentialManager || !credentialEditor) return;

    const { values, mode, credentialId } = credentialEditor;
    const name = values.name.trim();

    if (!name) {
      setCredentialEditorError("자격 증명 이름을 입력하세요.");
      return;
    }

    if (!values.credentialType.trim()) {
      setCredentialEditorError("자격 증명 유형을 선택하세요.");
      return;
    }

    if (mode === "create" && !values.secret) {
      setCredentialEditorError("비밀번호/키를 입력하세요.");
      return;
    }

    setIsSavingCredential(true);
    setCredentialEditorError("");

    try {
      let createdCredential: InventoryCredentialV2Summary | null = null;

      if (mode === "create") {
        createdCredential = await createGlobalCredential({
          name,
          credential_type: values.credentialType.trim(),
          username: values.username || undefined,
          secret: values.secret,
          become_username: values.becomeUsername || undefined,
          become_secret: values.becomeSecret || undefined,
        });
      } else if (credentialId) {
        const updatePayload: Parameters<typeof updateGlobalCredential>[1] = {
          name,
          username: values.username || undefined,
          become_username: values.becomeUsername || undefined,
          ...(values.secret ? { secret: values.secret } : {}),
          ...(values.becomeSecret ? { become_secret: values.becomeSecret } : {}),
          ...(values.clearBecomeSecret ? { clear_become_secret: true } : {}),
        };
        await updateGlobalCredential(credentialId, updatePayload);
      }

      const refreshedCredentials = await refreshCredentials();

      if (mode === "create" && createdCredential && !refreshedCredentials) {
        setSharedCredentials((current) => {
          const createdRef = getInventoryCredentialRef(createdCredential);

          if (current.some((credential) => getInventoryCredentialRef(credential) === createdRef)) {
            return current;
          }

          return [...current, createdCredential];
        });
      }

      const feedbackCredentialLabel = isMachineGeneratedCredentialName(name)
        ? values.username && values.credentialType
          ? `${values.username} · ${values.credentialType}`
          : values.username || `${values.credentialType} 자격 증명`
        : name;

      resetCredentialEditor();
      setFeedback({
        tone: "success",
        message: `자격 증명 '${feedbackCredentialLabel}'을(를) ${mode === "create" ? "생성" : "수정"}했습니다.`,
      });

      if (
        mode === "create" &&
        credentialOverlay?.source === "host-create" &&
        infoPanel?.kind === "host" &&
        infoPanel.hostId === credentialOverlay.hostId
      ) {
        const createdRef = createdCredential ? getInventoryCredentialRef(createdCredential) : "";

        if (createdRef) {
          applyHostLoginCredentialChange(
            createdRef,
            refreshedCredentials ??
              (createdCredential ? [...sharedCredentials, createdCredential] : sharedCredentials)
          );
        }

        setCredentialOverlay(null);
        setPendingCredentialCreateInventoryId(null);
      }
    } catch (error) {
      setCredentialEditorError(`저장하지 못했습니다: ${getErrorMessage(error)}`);
    } finally {
      setIsSavingCredential(false);
    }
  };

  const handleDeleteCredential = async (credential: InventoryCredentialV2Summary) => {
    if (!activeCredentialManager) return;

    const credentialRef = getInventoryCredentialRef(credential);
    if (!credentialRef) return;

    const executeDelete = async () => {
      try {
        await deleteGlobalCredential(credentialRef);
        await refreshCredentials();
      setFeedback({
        tone: "success",
        message: `자격 증명 '${formatInventoryCredentialPrimaryLabel(credential)}'을(를) 삭제했습니다.`,
      });
      } catch (error) {
        setFeedback({ tone: "error", message: `삭제하지 못했습니다: ${getCredentialDeleteErrorMessage(error)}` });
      }
    };

    setConfirmDialog({
      title: "자격 증명 삭제",
        message: `'${formatInventoryCredentialPrimaryLabel(credential)}' 자격 증명을 삭제하시겠습니까?`,
      confirmLabel: "삭제하기",
      cancelLabel: "취소",
      kicker: "삭제 확인",
      tone: "danger",
      onConfirm: () => executeDelete(),
    });
  };

  const handleInventoryToggle = (inventoryId: string) => {
    const isExpanded = expandedInventoryIds.has(inventoryId);

    setExpandedInventoryIds((current) => {
      const next = new Set(current);

      if (next.has(inventoryId)) {
        next.delete(inventoryId);
      } else {
        next.add(inventoryId);
      }

      return next;
    });

    if (isExpanded && focusedScope.kind === "group" && focusedScope.inventoryId === inventoryId) {
      setFocusedScope({ kind: "inventory", inventoryId });
    }
  };

  const handleToggleAllInventories = () => {
    if (allInventoriesExpanded) {
      setExpandedInventoryIds(new Set());

      if (focusedScope.kind === "group") {
        setFocusedScope({ kind: "inventory", inventoryId: focusedScope.inventoryId });
      }

      return;
    }

    setExpandedInventoryIds(new Set(inventories.map((inventory) => inventory.id)));
  };

  const persistInventory = async (
    nextInventory: PreviewInventory,
    successMessage: string
  ): Promise<PreviewInventory | null> => {
    try {
      const savedInventory = v2DetailToPreviewInventory(
        await updateManagedInventoryV2(nextInventory.id, buildV2Payload(nextInventory))
      );
      setInventories((current) =>
        current.map((item) => (item.id === savedInventory.id ? savedInventory : item))
      );
      setFeedback({ tone: "success", message: successMessage });
      return savedInventory;
    } catch (error) {
      setFeedback({
        tone: "error",
        message: `저장하지 못했습니다: ${getErrorMessage(error)}`,
      });
      return null;
    }
  };

  const handleAddInventory = () => {
    const proceed = () => {
      const newInventory = createInventoryPreviewDraft(inventories.length + 1);

      setInventories((current) => [...current, newInventory]);
      setPendingInventoryDraftIds((current) => new Set([...current, newInventory.id]));
      setFocusedScope({ kind: "inventory", inventoryId: newInventory.id });
      setExpandedInventoryIds((current) => new Set([...current, newInventory.id]));
      setInfoPanel({ kind: "inventory", inventoryId: newInventory.id });
      setInfoPanelDraft({ kind: "inventory", values: createInventoryDraft(newInventory) });
      setFeedback({
        tone: "info",
        message: "새 인벤토리 초안을 만들었습니다. 저장을 눌러 서버에 반영하세요.",
      });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const handleAddGroup = () => {
    const proceed = () => {
      const inventory = getInventoryContext(focusedScope, inventories);

      if (!inventory) {
        setFeedback({
          tone: "info",
          message: "그룹을 추가하려면 먼저 인벤토리를 선택하세요.",
        });
        return;
      }

      const groupId = createEntityId("group");
      const newGroup: PreviewGroup = {
        id: groupId,
        name: `new_group_${inventory.groups.length + 1}`,
        note: "",
        tags: [],
        varsSummary: "",
      };

      const nextInventory = touchInventory({
        ...inventory,
        groups: [...inventory.groups, newGroup],
      });
      updateInventoryLocally(nextInventory);
      setPendingGroupDraftIds((current) =>
        new Set([...current, getGroupDraftKey(inventory.id, groupId)])
      );
      setFeedback({
        tone: "info",
        message: `인벤토리 '${inventory.name}'에 새 그룹 초안을 만들었습니다. 저장을 눌러 반영하세요.`,
      });
      ensureInventoryExpanded(inventory.id);
      setFocusedScope({ kind: "group", inventoryId: inventory.id, groupId });
      setInfoPanel({ kind: "group", inventoryId: inventory.id, groupId });
      setInfoPanelDraft({ kind: "group", values: createGroupDraft(newGroup) });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const handleAddHost = () => {
    const proceed = () => {
      const inventory = getInventoryContext(focusedScope, inventories);

      if (!inventory) {
        setFeedback({
          tone: "info",
          message: "호스트를 추가하려면 먼저 인벤토리를 선택하세요.",
        });
        return;
      }

      if (inventory.groups.length === 0) {
        setFeedback({
          tone: "info",
          message: `호스트를 추가하려면 '${inventory.name}' 인벤토리에 그룹을 하나 이상 먼저 만드세요.`,
        });
        return;
      }

      const hostId = createEntityId("host");
      const newHost: PreviewHost = {
        id: hostId,
        name: `new-host-${inventory.hosts.length + 1}`,
        address: `10.0.0.${inventory.hosts.length + 1}`,
        platform: "Ubuntu 22.04",
        connection: "ssh",
        port: "22",
        loginCredentialRef: "",
        becomeEnabled: false,
        legacyBecomeUser: "",
        legacyBecomeCredentialRef: "",
        status: "pending",
        groups: focusedScope.kind === "group" ? [focusedScope.groupId] : [],
        note: "",
      };

      const nextInventory = touchInventory({
        ...inventory,
        hosts: [...inventory.hosts, newHost],
      });

      setInventories((current) =>
        current.map((item) => (item.id === inventory.id ? nextInventory : item))
      );
      setPendingHostDraftIds((current) => new Set([...current, hostId]));
      setFeedback({
        tone: "info",
        message:
          focusedScope.kind === "group"
            ? "새 호스트 초안을 만들었습니다. 정보를 입력한 뒤 저장하면 선택한 그룹에 반영됩니다."
            : `인벤토리 '${inventory.name}'에 새 호스트 초안을 만들었습니다. 저장을 눌러 반영하세요.`,
      });

      ensureInventoryExpanded(inventory.id);
      setFocusedScope(
        focusedScope.kind === "group"
          ? { kind: "group", inventoryId: inventory.id, groupId: focusedScope.groupId }
          : { kind: "inventory", inventoryId: inventory.id }
      );
      setInfoPanel({ kind: "host", inventoryId: inventory.id, hostId });
      setIsHostAssignmentEditorOpen(false);
      setInfoPanelDraft({ kind: "host", values: createHostDraft(newHost) });
    };

    if (!maybeDiscardOpenPendingDraft(proceed)) {
      return;
    }

    proceed();
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const activeData = event.active.data.current;
    const overData = event.over?.data.current;

    if (!isHostDragData(activeData) || !isGroupDropData(overData)) {
      return;
    }

    if (activeData.hostAssetId) {
      const hostAsset = allHostAssets.find((host) => host.id === activeData.hostAssetId);

      if (!hostAsset) {
        return;
      }

      const activeSelectionKey = getHostSelectionKey(activeData.hostAssetId, null, activeData.hostId);
      const hostsToAssign = selectedHostKeys.has(activeSelectionKey)
        ? getSelectedHostAssets()
        : [
            {
              id: hostAsset.id,
              name: hostAsset.name,
              memberships: hostAsset.memberships,
            },
          ];

      await assignHostAssetsToGroup(hostsToAssign, `${overData.inventoryId}::${overData.groupId}`, {
        sourceHostName: hostAsset.name,
      });
      return;
    }

    if (activeData.inventoryId !== overData.inventoryId) {
      setFeedback({
        tone: "error",
        message: "호스트는 같은 인벤토리 안의 그룹으로만 이동할 수 있습니다.",
      });
      return;
    }

    const inventory = inventories.find((item) => item.id === activeData.inventoryId);
    const group = inventory?.groups.find((item) => item.id === overData.groupId);
    const host = inventory?.hosts.find((item) => item.id === activeData.hostId);

    if (!inventory || !group || !host) {
      return;
    }

    if (host.groups.includes(group.id)) {
      setFeedback({
        tone: "info",
        message: `'${host.name}' 호스트는 이미 '${group.name}' 그룹에 배정되어 있습니다.`,
      });
      return;
    }

    const nextInventory = touchInventory({
      ...inventory,
      hosts: inventory.hosts.map((hostItem) =>
        hostItem.id === host.id ? { ...hostItem, groups: [...hostItem.groups, group.id] } : hostItem
      ),
    });

    if (pendingInventoryDraftIds.has(inventory.id)) {
      updateInventoryLocally(nextInventory);
      setFeedback({
        tone: "success",
        message: `'${host.name}' 호스트 배정 초안을 저장했습니다. 인벤토리를 저장하면 서버에 반영됩니다.`,
      });
      return;
    }

    await persistInventory(
      nextInventory,
      `'${host.name}' 호스트를 '${group.name}' 그룹에 배정하고 저장했습니다.`
    );
  };

  const handleHostDraftGroupToggle = (groupId: string) => {
    setInfoPanelDraft((current) => {
      if (current?.kind !== "host") {
        return current;
      }

      const nextGroups = current.values.groups.includes(groupId)
        ? current.values.groups.filter((currentGroupId) => currentGroupId !== groupId)
        : [...current.values.groups, groupId];

      return {
        kind: "host",
        values: {
          ...current.values,
          groups: nextGroups,
        },
      };
    });
  };

  const handleHostLoginCredentialSelectFromOverlay = (loginCredentialRef: string) => {
    applyHostLoginCredentialChange(loginCredentialRef, sharedCredentials);
    dismissCredentialOverlay();
  };

  const handleHostBecomeEnabledChange = (becomeEnabled: boolean) => {
    if (becomeEnabled) {
      const loginCredentialRef =
        infoPanelDraft?.kind === "host" ? infoPanelDraft.values.loginCredentialRef : "";

      if (!selectedCredentialSupportsBecome(sharedCredentials, loginCredentialRef)) {
        setInfoPanelDraft((current) =>
          current?.kind === "host"
            ? {
                kind: "host",
                values: {
                  ...current.values,
                  becomeEnabled: false,
                },
              }
            : current
        );
        setFeedback({ tone: "info", message: HOST_BECOME_CREDENTIAL_REQUIRED_MESSAGE });
        return;
      }
    }

    setInfoPanelDraft((current) =>
      current?.kind === "host"
        ? {
            kind: "host",
            values: {
              ...current.values,
              becomeEnabled,
            },
          }
        : current
    );
  };

  const handleSaveInfoPanel = async () => {
    if (!infoPanel || !infoPanelDraft) {
      return;
    }

    if (
      infoPanel.kind === "hostAsset" &&
      infoPanelDraft.kind === "host" &&
      infoPanelHostAsset
    ) {
      const name = infoPanelDraft.values.name.trim();
      const address = infoPanelDraft.values.address.trim();

      if (!name || !address) {
        setFeedback({ tone: "error", message: "호스트 이름과 주소를 입력하세요." });
        return;
      }

      try {
        const updatedHostAsset = await updateManagedInventoryHostAssetV2(
          infoPanel.hostAssetId,
          buildHostAssetUpdatePayload(infoPanelDraft.values, infoPanelHostAsset)
        );

        setAllHostAssets((current) =>
          current.map((host) => (host.id === updatedHostAsset.id ? updatedHostAsset : host))
        );
        await refreshInventoriesByIds(
          updatedHostAsset.memberships.map((membership) => membership.inventory_id)
        );
        dismissInfoPanel();
        setFeedback({ tone: "success", message: `호스트 '${name}' 정보를 저장했습니다.` });
      } catch (error) {
        setFeedback({
          tone: "error",
          message: `호스트를 저장하지 못했습니다: ${getErrorMessage(error)}`,
        });
      }
      return;
    }

    if (!infoPanelInventory) {
      return;
    }

    if (infoPanel.kind === "inventory" && infoPanelDraft.kind === "inventory") {
      const name = infoPanelDraft.values.name.trim();

      if (!name) {
        setFeedback({
          tone: "error",
          message: "인벤토리 이름을 입력하세요.",
        });
        return;
      }

      const nextInventory: PreviewInventory = touchInventory({
        ...infoPanelInventory,
        name,
        description: infoPanelDraft.values.description.trim(),
        tags: toTags(infoPanelDraft.values.tagsText),
      });

      if (pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
        try {
          const previousInventoryId = infoPanel.inventoryId;
          const savedInventory = v2DetailToPreviewInventory(
            await createManagedInventoryV2(buildV2Payload(nextInventory))
          );

          setInventories((current) =>
            current.map((item) =>
              item.id === previousInventoryId ? savedInventory : item
            )
          );
          clearPendingInventoryDraft(previousInventoryId);
          setPendingGroupDraftIds((current) =>
            new Set(
              [...current].map((draftKey) =>
                draftKey.startsWith(`${previousInventoryId}::`)
                  ? `${savedInventory.id}::${draftKey.split("::")[1] ?? ""}`
                  : draftKey
              )
            )
          );
          setFocusedScope((current) =>
            remapFocusScopeInventoryId(current, previousInventoryId, savedInventory.id)
          );
          setExpandedInventoryIds((current) => {
            const next = new Set(current);

            if (next.delete(previousInventoryId)) {
              next.add(savedInventory.id);
            }

            return next;
          });
          dismissInfoPanel();
          setFeedback({
            tone: "success",
            message: `인벤토리 '${savedInventory.name}' 정보를 저장했습니다.`,
          });
        } catch (error) {
          setFeedback({
            tone: "error",
            message: `저장하지 못했습니다: ${getErrorMessage(error)}`,
          });
        }
        return;
      }

      const savedInventory = await persistInventory(
        nextInventory,
        `인벤토리 '${name}' 정보를 저장했습니다.`
      );
      if (savedInventory) {
        dismissInfoPanel();
      }
      return;
    }

    if (infoPanel.kind === "group" && infoPanelDraft.kind === "group" && infoPanelGroup) {
      const name = infoPanelDraft.values.name.trim();

      if (!name) {
        setFeedback({ tone: "error", message: "그룹 이름을 입력하세요." });
        return;
      }

      const nextGroup: PreviewGroup = {
        ...infoPanelGroup,
        name,
        note: infoPanelDraft.values.note.trim(),
        tags: toTags(infoPanelDraft.values.tagsText),
        varsSummary: infoPanelDraft.values.varsSummary.trim(),
      };

      const nextInventory = touchInventory({
        ...infoPanelInventory,
        groups: infoPanelInventory.groups.map((group) =>
          group.id === nextGroup.id ? nextGroup : group
        ),
      });

      if (pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
        updateInventoryLocally(nextInventory);
        clearPendingGroupDraft(infoPanel.inventoryId, nextGroup.id);
        dismissInfoPanel();
        setFeedback({
          tone: "success",
          message: `그룹 '${name}' 초안을 저장했습니다. 인벤토리를 저장하면 서버에 반영됩니다.`,
        });
        return;
      }

      const savedInventory = await persistInventory(
        nextInventory,
        `그룹 '${name}' 정보를 저장했습니다.`
      );
      if (savedInventory) {
        clearPendingGroupDraft(infoPanel.inventoryId, nextGroup.id);
        dismissInfoPanel();
      }
      return;
    }

    if (infoPanel.kind === "host" && infoPanelDraft.kind === "host" && infoPanelHost) {
      const name = infoPanelDraft.values.name.trim();
      const address = infoPanelDraft.values.address.trim();

      if (!name || !address) {
        setFeedback({ tone: "error", message: "호스트 이름과 주소를 입력하세요." });
        return;
      }

      const nextHost: PreviewHost = {
        ...infoPanelHost,
        name,
        address,
        platform: infoPanelDraft.values.platform.trim(),
        connection: infoPanelDraft.values.connection,
        port: infoPanelDraft.values.port.trim(),
        loginCredentialRef: infoPanelDraft.values.loginCredentialRef.trim(),
        becomeEnabled: infoPanelDraft.values.becomeEnabled,
        legacyBecomeUser: infoPanelDraft.values.legacyBecomeUser.trim(),
        legacyBecomeCredentialRef: infoPanelDraft.values.legacyBecomeCredentialRef.trim(),
        status: infoPanelDraft.values.status,
        note: infoPanelDraft.values.note.trim(),
        groups: infoPanelDraft.values.groups.filter((groupId) =>
          infoPanelInventory.groups.some((group) => group.id === groupId)
        ),
      };

      const nextInventory = touchInventory({
        ...infoPanelInventory,
        hosts: infoPanelInventory.hosts.map((host) =>
          host.id === nextHost.id ? nextHost : host
        ),
      });

      if (pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
        updateInventoryLocally(nextInventory);
        setPendingHostDraftIds((current) => {
          if (!current.has(nextHost.id)) {
            return current;
          }

          const next = new Set(current);
          next.delete(nextHost.id);
          return next;
        });
        dismissInfoPanel();
        setFeedback({
          tone: "success",
          message: `호스트 '${name}' 초안을 저장했습니다. 인벤토리를 저장하면 서버에 반영됩니다.`,
        });
        return;
      }

      const savedInventory = await persistInventory(
        nextInventory,
        `호스트 '${name}' 정보를 저장했습니다.`
      );
      if (savedInventory) {
        setPendingHostDraftIds((current) => {
          if (!current.has(nextHost.id)) {
            return current;
          }

          const next = new Set(current);
          next.delete(nextHost.id);
          return next;
        });
        dismissInfoPanel();
      }
    }
  };

  const handleDeleteInfoPanel = async () => {
    if (!infoPanel || !infoPanelInventory) {
      return;
    }

    const executeDelete = async () => {
      if (infoPanel.kind === "hostAsset") {
        setFeedback({ tone: "info", message: "호스트 자산 삭제는 개별 삭제 화면에서 처리합니다." });
        return;
      }

      if (infoPanel.kind === "inventory") {
        if (pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
          removePendingInventoryDraft(infoPanel.inventoryId);
          setInfoPanel(null);
          setInfoPanelDraft(null);
          setFeedback({
            tone: "success",
            message: `인벤토리 '${infoPanelTargetName}' 초안을 삭제했습니다.`,
          });
          return;
        }

        try {
          await deleteManagedInventoryV2(infoPanel.inventoryId);
        } catch (error) {
          setFeedback({
            tone: "error",
            message: `인벤토리를 삭제하지 못했습니다: ${getErrorMessage(error)}`,
          });
          return;
        }

        try {
          const refreshedHostAssets = await fetchManagedInventoryHostAssetsV2();
          setAllHostAssets(refreshedHostAssets);
        } catch {
          setAllHostAssets((current) =>
            current.map((host) => ({
              ...host,
              memberships: host.memberships.filter(
                (membership) => membership.inventory_id !== infoPanel.inventoryId
              ),
            }))
          );
        }

        const nextInventories = inventories.filter((item) => item.id !== infoPanel.inventoryId);
        const fallbackInventory = nextInventories[0] ?? null;

        setInventories(nextInventories);
        setExpandedInventoryIds((current) => {
          const next = new Set(
            [...current].filter((inventoryId) => nextInventories.some((item) => item.id === inventoryId))
          );

          if (next.size === 0 && fallbackInventory) {
            next.add(fallbackInventory.id);
          }

          return next;
        });

        if (focusedScope.kind !== "all" && focusedScope.inventoryId === infoPanel.inventoryId) {
          setFocusedScope(
            fallbackInventory
              ? { kind: "inventory", inventoryId: fallbackInventory.id }
              : { kind: "all" }
          );
        }

        dismissInfoPanel();
        setFeedback({
          tone: "success",
          message: `인벤토리 '${infoPanelTargetName}'를 삭제했습니다. 그룹과 연결은 제거되고 호스트 자산은 보존됩니다.`,
        });
        return;
      }

      if (infoPanel.kind === "group" && infoPanelGroup) {
        if (
          pendingInventoryDraftIds.has(infoPanel.inventoryId) ||
          pendingGroupDraftIds.has(getGroupDraftKey(infoPanel.inventoryId, infoPanel.groupId))
        ) {
          const nextInventory = touchInventory({
            ...infoPanelInventory,
            groups: infoPanelInventory.groups.filter((group) => group.id !== infoPanel.groupId),
            hosts: infoPanelInventory.hosts.map((host) =>
              host.groups.includes(infoPanel.groupId)
                ? {
                    ...host,
                    groups: host.groups.filter((groupId) => groupId !== infoPanel.groupId),
                  }
                : host
            ),
          });

          removePendingGroupDraft(infoPanel.inventoryId, infoPanel.groupId);
          setInfoPanel({ kind: "inventory", inventoryId: infoPanel.inventoryId });
          setInfoPanelDraft({ kind: "inventory", values: createInventoryDraft(nextInventory) });
          setFeedback({
            tone: "success",
            message: `그룹 '${infoPanelGroup.name}' 초안을 삭제했습니다.`,
          });
          return;
        }

        const nextInventory = touchInventory({
          ...infoPanelInventory,
          groups: infoPanelInventory.groups.filter((group) => group.id !== infoPanel.groupId),
          hosts: infoPanelInventory.hosts.map((host) =>
            host.groups.includes(infoPanel.groupId)
              ? {
                  ...host,
                  groups: host.groups.filter((groupId) => groupId !== infoPanel.groupId),
                }
              : host
          ),
        });
        const savedInventory = await persistInventory(
          nextInventory,
          `그룹 '${infoPanelGroup.name}'을 삭제했습니다.`
        );

        if (!savedInventory) {
          return;
        }

        if (
          focusedScope.kind === "group" &&
          focusedScope.inventoryId === infoPanel.inventoryId &&
          focusedScope.groupId === infoPanel.groupId
        ) {
          setFocusedScope({ kind: "inventory", inventoryId: infoPanel.inventoryId });
        }

        setInfoPanel({ kind: "inventory", inventoryId: savedInventory.id });
        setInfoPanelDraft({ kind: "inventory", values: createInventoryDraft(savedInventory) });
        return;
      }

      if (infoPanel.kind === "host" && infoPanelHost) {
        if (pendingInventoryDraftIds.has(infoPanel.inventoryId)) {
          const nextInventory = touchInventory({
            ...infoPanelInventory,
            hosts: infoPanelInventory.hosts.filter((host) => host.id !== infoPanel.hostId),
          });
          updateInventoryLocally(nextInventory);
          setPendingHostDraftIds((current) => {
            if (!current.has(infoPanel.hostId)) {
              return current;
            }

            const next = new Set(current);
            next.delete(infoPanel.hostId);
            return next;
          });
          setInfoPanel(null);
          setInfoPanelDraft(null);
          setFeedback({
            tone: "success",
            message: `호스트 '${infoPanelHost.name}' 초안을 삭제했습니다.`,
          });
          return;
        }

        if (pendingHostDraftIds.has(infoPanel.hostId)) {
          removePendingHostDraft(infoPanel.inventoryId, infoPanel.hostId);
          setInfoPanel(null);
          setInfoPanelDraft(null);
          setFeedback({ tone: "success", message: `호스트 '${infoPanelHost.name}' 초안을 삭제했습니다.` });
          return;
        }

        try {
          await deleteManagedInventoryHostV2(infoPanel.inventoryId, infoPanel.hostId);
        } catch (error) {
          setFeedback({
            tone: "error",
            message: `호스트를 삭제하지 못했습니다: ${getErrorMessage(error)}`,
          });
          return;
        }

        const nextInventory = touchInventory({
          ...infoPanelInventory,
          hosts: infoPanelInventory.hosts.filter((host) => host.id !== infoPanel.hostId),
        });
        updateInventoryLocally(nextInventory);
        setFeedback({ tone: "success", message: `호스트 '${infoPanelHost.name}'를 삭제했습니다.` });
        dismissInfoPanel();
      }
    };

    setConfirmDialog({
      title:
        infoPanel.kind === "inventory"
          ? "인벤토리 삭제"
          : infoPanel.kind === "group"
            ? "그룹 삭제"
            : "호스트 삭제",
      message:
        infoPanel.kind === "inventory"
          ? `'${infoPanelTargetName}' 인벤토리를 삭제하시겠습니까? 그룹과 연결은 함께 삭제되지만 호스트 자산은 보존됩니다.`
          : `'${infoPanelTargetName}' 항목을 삭제하시겠습니까?`,
      confirmLabel: "삭제하기",
      cancelLabel: "계속 편집",
      kicker: "삭제 확인",
      tone: "danger",
      onConfirm: () => executeDelete(),
    });
  };

  const isHostCredentialOverlay = Boolean(
    credentialOverlay && infoPanel?.kind === "host" && infoPanelDraft?.kind === "host"
  );
  const overlaySelectedLoginCredentialRef =
    isHostCredentialOverlay && infoPanelDraft?.kind === "host"
      ? infoPanelDraft.values.loginCredentialRef.trim()
      : "";
  const normalizedCredentialSearchQuery = credentialSearchQuery.trim().toLowerCase();
  const filteredSharedCredentials = normalizedCredentialSearchQuery
    ? sharedCredentials.filter((credential) => {
        const searchableText = [
          getInventoryCredentialRef(credential),
          formatInventoryCredentialPrimaryLabel(credential),
          credential.name,
          credential.username,
          credential.credential_type,
          credential.has_secret ? "secret 비밀번호 키 있음" : "secret 없음",
          credentialSupportsBecome(credential) ? "become 권한상승 가능" : "become 없음",
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchableText.includes(normalizedCredentialSearchQuery);
      })
    : sharedCredentials;

  const credentialManagerContent = (
    <div className="info-section">
      <div className="credential-manager-header">
        <h3>{isHostCredentialOverlay ? "선택 / 추가 / 관리" : "자격 증명 목록"}</h3>
        {!credentialEditor && (
          <button
            type="button"
            className="btn btn-primary compact-action-button"
            onClick={handleStartCredentialCreate}
            data-testid="credential-add-button"
          >
            + 추가
          </button>
        )}
      </div>
      {!credentialEditor && (
        <div className="credential-search-bar" role="search">
          <label className="credential-search-label" htmlFor="credential-search-input">
            자격 증명 검색
          </label>
          <div className="credential-search-control">
            <input
              id="credential-search-input"
              className="form-input"
              value={credentialSearchQuery}
              onChange={(event) => setCredentialSearchQuery(event.target.value)}
              placeholder="이름, 사용자명, 유형, become, secret 검색"
              data-testid="credential-search-input"
            />
            {credentialSearchQuery.trim() ? (
              <button
                type="button"
                className="btn btn-secondary compact-action-button"
                onClick={() => setCredentialSearchQuery("")}
                data-testid="credential-search-clear"
              >
                지우기
              </button>
            ) : null}
          </div>
          <span className="credential-search-summary">
            {normalizedCredentialSearchQuery
              ? `${filteredSharedCredentials.length} / ${sharedCredentials.length}개 표시`
              : `전체 ${sharedCredentials.length}개`}
          </span>
        </div>
      )}
      {isHostCredentialOverlay && !credentialEditor && (
        <button
          type="button"
          className={`credential-card credential-card-selectable ${
            !overlaySelectedLoginCredentialRef ? "selected" : ""
          }`}
          onClick={() => handleHostLoginCredentialSelectFromOverlay("")}
          aria-pressed={!overlaySelectedLoginCredentialRef}
          data-testid="credential-select-none"
        >
          <div className="credential-card-header">
            <strong>선택 안 함 / 기본 접속</strong>
            <span className="credential-select-state">
              {!overlaySelectedLoginCredentialRef ? "현재 선택" : "선택"}
            </span>
          </div>
          <div className="credential-card-details">
            <span className="credential-detail-text">호스트 변수/환경 기본값 사용</span>
          </div>
        </button>
      )}
      {credentialEditor && (
        <div className="credential-editor-form">
          <div className="info-form-grid">
            <label className="info-form-field">
              <span>이름</span>
              <input
                className="form-input"
                value={credentialEditor.values.name}
                onChange={(e) => handleCredentialEditorFieldChange("name", e.target.value)}
                placeholder="자격 증명 이름"
              />
            </label>
            <label className="info-form-field">
              <span>유형</span>
              <select
                className="form-select"
                value={credentialEditor.values.credentialType}
                onChange={(e) => handleCredentialEditorFieldChange("credentialType", e.target.value)}
              >
                <option value="ssh_password">SSH Password</option>
                <option value="ssh_key">SSH Key</option>
                <option value="winrm">WinRM</option>
              </select>
            </label>
            <label className="info-form-field">
              <span>사용자명</span>
              <input
                className="form-input"
                value={credentialEditor.values.username}
                onChange={(e) => handleCredentialEditorFieldChange("username", e.target.value)}
                placeholder="사용자명"
              />
            </label>
            <label className="info-form-field">
              <span>
                비밀번호 / 키
                {credentialEditor.mode === "edit" && "(변경 시만 입력)"}
              </span>
              <input
                className="form-input"
                type="password"
                value={credentialEditor.values.secret}
                onChange={(e) => handleCredentialEditorFieldChange("secret", e.target.value)}
                placeholder={
                  credentialEditor.mode === "create"
                    ? "비밀번호 또는 키"
                    : "변경하지 않으면 비움"
                }
              />
            </label>
            <label className="info-form-field">
              <span>become 사용자명</span>
              <input
                className="form-input"
                value={credentialEditor.values.becomeUsername}
                onChange={(e) =>
                  handleCredentialEditorFieldChange("becomeUsername", e.target.value)
                }
                placeholder="예: root"
              />
            </label>
            <label className="info-form-field">
              <span>
                become 비밀번호
                {credentialEditor.mode === "edit" && "(변경 시만 입력)"}
              </span>
              <input
                className="form-input"
                type="password"
                value={credentialEditor.values.becomeSecret}
                onChange={(e) =>
                  handleCredentialEditorFieldChange("becomeSecret", e.target.value)
                }
                placeholder={
                  credentialEditor.mode === "create"
                    ? "become 비밀번호"
                    : "변경하지 않으면 비움"
                }
              />
            </label>
          </div>
          {credentialEditor.hasBecomeSecret && credentialEditor.mode === "edit" && (
            <label className="inv-checkbox-label" style={{ marginTop: "var(--spacing-sm)" }}>
              <input
                type="checkbox"
                checked={credentialEditor.values.clearBecomeSecret}
                onChange={(e) =>
                  handleCredentialEditorFieldChange("clearBecomeSecret", e.target.checked)
                }
              />
              <span>become secret 제거</span>
            </label>
          )}
          {credentialEditorError && (
            <p className="info-inline-message error">{credentialEditorError}</p>
          )}
          <div className="credential-editor-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSaveCredential}
              disabled={isSavingCredential}
            >
              {isSavingCredential ? "저장 중..." : "저장"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCancelCredentialEditor}
            >
              취소
            </button>
          </div>
        </div>
      )}
      {isLoadingSharedCredentials ? (
        <div className="credential-loading">
          <span className="text-muted">자격 증명 목록을 불러오는 중입니다...</span>
        </div>
      ) : sharedCredentialError ? (
        <div className="credential-error">
          <span className="text-error">
            자격 증명을 불러오지 못했습니다: {sharedCredentialError}
          </span>
        </div>
      ) : sharedCredentials.length === 0 ? (
        <div className="credential-empty">
          <span className="text-muted">
            등록된 자격 증명이 없습니다. + 추가를 눌러 첫 자격 증명을 만드세요.
          </span>
        </div>
      ) : filteredSharedCredentials.length === 0 ? (
        <div className="credential-empty">
          <span className="text-muted">
            {`'${credentialSearchQuery.trim()}'에 맞는 자격 증명이 없습니다.`}
          </span>
        </div>
      ) : (
        <div className="credential-list">
          {filteredSharedCredentials.map((credential) => {
            const ref = getInventoryCredentialRef(credential);
            const isSelectedForHost = isHostCredentialOverlay && ref === overlaySelectedLoginCredentialRef;
            return (
              <div
                key={ref}
                className={`credential-card ${isSelectedForHost ? "selected" : ""}`}
                data-testid={`credential-card-${ref}`}
              >
                <div className="credential-card-header">
                  <strong>{formatInventoryCredentialPrimaryLabel(credential)}</strong>
                  <div className="credential-card-actions">
                    {isHostCredentialOverlay && (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleHostLoginCredentialSelectFromOverlay(ref)}
                        disabled={isSelectedForHost || !ref}
                        data-testid={`credential-select-${ref}`}
                      >
                        {isSelectedForHost ? "현재 선택" : "선택"}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => handleStartCredentialEdit(credential)}
                      data-testid={`credential-edit-${ref}`}
                    >
                      편집
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => handleDeleteCredential(credential)}
                      data-testid={`credential-delete-${ref}`}
                    >
                      삭제
                    </button>
                  </div>
                </div>
                <div className="credential-card-details">
                  <span className="credential-detail-badge">{credential.credential_type}</span>
                  <span className="credential-detail-text">{credential.username}</span>
                  {credential.has_secret && (
                    <span className="credential-detail-badge">secret ●●●</span>
                  )}
                  {credentialSupportsBecome(credential) && (
                    <span className="credential-detail-badge">become 가능</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  const infoPanelContent =
    infoPanel &&
    (infoPanelInventory || infoPanel.kind === "hostAsset") &&
    (infoPanelDraft || infoPanel.kind === "credentials")
      ? (() => {
          const activeInfoPanel = infoPanel;

          return (
      <div
        className="info-panel-shell"
        aria-modal="true"
        role="dialog"
        data-testid="inventory-info-panel"
      >
        <div className="info-panel-backdrop" aria-hidden="true" />
        <aside className="info-panel">
          <div className="info-panel-header">
            <div>
              <span className="pane-kicker">
                {activeInfoPanel.kind === "inventory"
                  ? "인벤토리 편집"
                  : activeInfoPanel.kind === "group"
                    ? "그룹 편집"
                    : activeInfoPanel.kind === "host" || activeInfoPanel.kind === "hostAsset"
                      ? "호스트 편집"
                      : "자격 증명 관리"}
              </span>
              {activeInfoPanel.kind === "credentials" ? (
                <>
                  <h2 className="info-panel-title">
                    공용 자격 증명
                  </h2>
                  <p className="panel-subtitle">
                    {`${infoPanelInventory?.name ?? ""} · 모든 인벤토리에서 함께 쓰는 공용 자격 증명`}
                  </p>
                </>
              ) : null}
            </div>
          </div>

          <div className="info-panel-body">
            {activeInfoPanel.kind === "inventory" &&
            infoPanelDraft?.kind === "inventory" &&
            infoPanelInventory ? (
              <>
                <div className="info-metric-grid">
                  <article className="info-metric-card">
                    <span>그룹</span>
                    <strong>{infoPanelInventory?.groups.length ?? 0}개</strong>
                  </article>
                  <article className="info-metric-card">
                    <span>호스트</span>
                    <strong>{infoPanelInventory?.hosts.length ?? 0}대</strong>
                  </article>
                  <article className="info-metric-card">
                    <span>프로토콜</span>
                    <strong>{summarizeProtocols(infoPanelInventory?.hosts ?? [])}</strong>
                  </article>
                </div>
                <div className="info-section">
                  <h3>기본 정보</h3>
                  <div className="info-form-grid">
                    <label className="info-form-field">
                      <span>이름</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.name}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "inventory"
                              ? {
                                  kind: "inventory",
                                  values: { ...current.values, name: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                    <label className="info-form-field">
                      <span>태그</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.tagsText}
                        placeholder="쉼표로 구분"
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "inventory"
                              ? {
                                  kind: "inventory",
                                  values: { ...current.values, tagsText: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                  </div>
                </div>
                <div className="info-section">
                  <h3>설명</h3>
                  <textarea
                    className="form-textarea"
                    value={infoPanelDraft.values.description}
                    onChange={(event) =>
                      setInfoPanelDraft((current) =>
                        current?.kind === "inventory"
                          ? {
                              kind: "inventory",
                              values: { ...current.values, description: event.target.value },
                            }
                          : current
                      )
                    }
                  />
                </div>
                <div className="info-section">
                  <h3>호스트 상태 집계</h3>
                  <p>{summarizeStatuses(infoPanelInventory?.hosts ?? [])}</p>
                </div>
              </>
            ) : activeInfoPanel.kind === "group" &&
              infoPanelDraft?.kind === "group" &&
              infoPanelGroup &&
              infoPanelInventory ? (
              <>
                <div className="info-metric-grid">
                  <article className="info-metric-card">
                    <span>호스트</span>
                    <strong>{infoPanelGroupHosts.length}대</strong>
                  </article>
                  <article className="info-metric-card">
                    <span>프로토콜</span>
                    <strong>{summarizeProtocols(infoPanelGroupHosts)}</strong>
                  </article>
                  <article className="info-metric-card">
                    <span>호스트 상태 집계</span>
                    <strong>{summarizeStatuses(infoPanelGroupHosts)}</strong>
                  </article>
                </div>
                <div className="info-section">
                  <h3>기본 정보</h3>
                  <div className="info-form-grid">
                    <label className="info-form-field">
                      <span>그룹 이름</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.name}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "group"
                              ? {
                                  kind: "group",
                                  values: { ...current.values, name: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                    <label className="info-form-field">
                      <span>태그</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.tagsText}
                        placeholder="쉼표로 구분"
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "group"
                              ? {
                                  kind: "group",
                                  values: { ...current.values, tagsText: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                  </div>
                </div>
                <div className="info-section">
                  <h3>설명</h3>
                  <textarea
                    className="form-textarea"
                    value={infoPanelDraft.values.note}
                    onChange={(event) =>
                      setInfoPanelDraft((current) =>
                        current?.kind === "group"
                          ? {
                              kind: "group",
                              values: { ...current.values, note: event.target.value },
                            }
                          : current
                      )
                    }
                  />
                </div>
                <div className="info-section">
                  <h3>연관 호스트</h3>
                  {infoPanelGroupHosts.length > 0 ? (
                    <div className="related-host-list">
                      {infoPanelGroupHosts.map((host) => (
                        <span key={host.id} className="host-group-tag">
                          {host.name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="info-inline-message">이 그룹에 포함된 호스트가 없습니다.</p>
                  )}
                </div>
              </>
            ) : infoPanelDraft?.kind === "host" &&
              ((activeInfoPanel.kind === "host" && infoPanelHost) ||
                (activeInfoPanel.kind === "hostAsset" && infoPanelHostAssetPreview)) ? (
              <>
                <div className="info-metric-grid">
                  <article className="info-metric-card">
                    <span>연결 상태</span>
                    <strong>{hostPanelStatusMeta?.label ?? "-"}</strong>
                    <small className="info-metric-detail">현재 저장된 상태 요약</small>
                  </article>
                  <article className="info-metric-card">
                    <span>연결 방식</span>
                    <strong>{hostPanelConnectionLabel || "-"}</strong>
                    <small className="info-metric-detail">
                      포트 {infoPanelDraft.values.port.trim() || "미설정"}
                    </small>
                  </article>
                  <article className="info-metric-card">
                    <span>소속 그룹</span>
                    <strong>{hostPanelGroupMetricValue}</strong>
                    <small className="info-metric-detail">{hostPanelGroupMetricDetail}</small>
                  </article>
                </div>
                <div className="info-section">
                  <h3>기본 정보</h3>
                  <div className="info-form-grid">
                    <label className="info-form-field">
                      <span>호스트 이름</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.name}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "host"
                              ? {
                                  kind: "host",
                                  values: { ...current.values, name: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                    <label className="info-form-field">
                      <span>주소</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.address}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "host"
                              ? {
                                  kind: "host",
                                  values: { ...current.values, address: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                    <label className="info-form-field">
                      <span>연결 방식</span>
                      <select
                        className="form-select"
                        value={infoPanelDraft.values.connection}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "host"
                              ? {
                                  kind: "host",
                                  values: {
                                    ...current.values,
                                    connection: event.target.value as ConnectionType,
                                  },
                                }
                              : current
                          )
                        }
                      >
                        {CONNECTION_ORDER.map((connection) => (
                          <option key={connection} value={connection}>
                            {CONNECTION_LABELS[connection]}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="info-form-field">
                      <span>포트</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.port}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "host"
                              ? {
                                  kind: "host",
                                  values: { ...current.values, port: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                    <label className="info-form-field">
                      <span>플랫폼</span>
                      <input
                        className="form-input"
                        value={infoPanelDraft.values.platform}
                        onChange={(event) =>
                          setInfoPanelDraft((current) =>
                            current?.kind === "host"
                              ? {
                                  kind: "host",
                                  values: { ...current.values, platform: event.target.value },
                                }
                              : current
                          )
                        }
                      />
                    </label>
                  </div>
                </div>
                {activeInfoPanel.kind === "hostAsset" ? (
                  <div className="info-section host-asset-assignment-section">
                    <div className="assignment-section-header">
                      <div>
                        <h3>인벤토리 / 그룹 배정</h3>
                        <p className="info-inline-message">
                          인벤토리 하위 그룹을 경로 카드로 보고 선택하세요. 같은 그룹명도 어느 인벤토리인지 함께 표시됩니다.
                        </p>
                      </div>
                      <span className="assignment-count-badge">
                        {infoPanelHostAsset?.memberships.length ?? 0}개 연결됨
                      </span>
                    </div>

                    <div className="assignment-target-summary" aria-live="polite">
                      <span className="assignment-target-label">선택한 위치</span>
                      <strong>
                        {selectedHostAssignmentTargetOption
                          ? selectedHostAssignmentTargetOption.label
                          : "아직 선택하지 않음"}
                      </strong>
                    </div>

                    {hostAssignmentTargetOptions.length === 0 ? (
                      <div className="assignment-empty-state">
                        <strong>선택 가능한 그룹이 없습니다.</strong>
                        <span>왼쪽 인벤토리에서 그룹을 먼저 만든 뒤 호스트를 배정할 수 있습니다.</span>
                      </div>
                    ) : (
                      <div className="assignment-tree-map" aria-label="호스트를 넣을 인벤토리와 그룹 선택">
                        {inventories.map((inventory) => (
                          <section key={inventory.id} className="assignment-tree-inventory">
                            <div className="assignment-tree-inventory-title">
                              <span className="assignment-tree-caret" aria-hidden="true">▾</span>
                              <div className="assignment-tree-title-copy">
                                <strong>{inventory.name}</strong>
                                <span>{inventory.groups.length}개 그룹 · {inventory.hosts.length}개 호스트</span>
                              </div>
                            </div>
                            {inventory.groups.length > 0 ? (
                              <div className="assignment-tree-groups">
                                {inventory.groups.map((group) => {
                                  const targetValue = `${inventory.id}::${group.id}`;
                                  const isSelected = hostAssetAssignmentTarget === targetValue;
                                  const isAlreadyAssigned =
                                    infoPanelHostAsset?.memberships.some(
                                      (membership) =>
                                        membership.inventory_id === inventory.id &&
                                        membership.group_name === group.name
                                    ) ?? false;

                                  return (
                                    <button
                                      key={group.id}
                                      type="button"
                                      className={`assignment-tree-group-card ${isSelected ? "selected" : ""} ${
                                        isAlreadyAssigned ? "assigned" : ""
                                      }`}
                                      onClick={() => setHostAssetAssignmentTarget(targetValue)}
                                      aria-pressed={isSelected}
                                    >
                                      <span className="assignment-tree-group-name">{group.name}</span>
                                      <span className="assignment-tree-group-path">
                                        경로: {inventory.name} / {group.name}
                                      </span>
                                      <span className="assignment-tree-state-badge">
                                        {isSelected ? "선택" : isAlreadyAssigned ? "이미 연결됨" : "추가 가능"}
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>
                            ) : (
                              <span className="assignment-card-empty">이 인벤토리에는 그룹이 없습니다.</span>
                            )}
                          </section>
                        ))}
                      </div>
                    )}

                    <div className="host-asset-assignment-actions">
                      <button
                        type="button"
                        className="btn btn-secondary host-section-inline-button"
                        onClick={handleAssignOpenHostAsset}
                        disabled={!hostAssetAssignmentTarget}
                      >
                        선택한 그룹에 넣기
                      </button>
                      <span className="assignment-action-helper">
                        드래그앤드랍도 계속 지원됩니다.
                      </span>
                    </div>
                  </div>
                ) : null}
                {activeInfoPanel.kind === "host" ? (
                  <div className="info-section host-group-assignment-section">
                    <div className="assignment-section-header">
                      <h3>소속 그룹</h3>
                      <button
                        type="button"
                        className="btn btn-secondary section-action-button host-edit-toggle-button"
                        onClick={() => setIsHostAssignmentEditorOpen((current) => !current)}
                        aria-expanded={isHostAssignmentEditorOpen}
                      >
                        {isHostAssignmentEditorOpen ? "그룹 변경 닫기" : "그룹 변경"}
                      </button>
                    </div>
                    <div className="host-edit-collapsed-summary" aria-live="polite">
                      <div className="info-form-field host-readonly-field">
                        <div className="host-summary-heading">
                          <span>현재 그룹</span>
                          {infoPanelHostDraftGroupNames.length > 0 ? (
                            <span className="assignment-count-badge">
                              {`${infoPanelHostDraftGroupNames.length}개 그룹`}
                            </span>
                          ) : null}
                        </div>
                        {infoPanelHostDraftGroupNames.length > 0 ? (
                          <div className="host-readonly-card-stack host-group-summary-list">
                            {infoPanelHostDraftGroupNames.map((groupName) => (
                              <div
                                key={groupName}
                                className="host-readonly-card host-readonly-chip-card"
                              >
                                {`${infoPanelInventory?.name ?? "현재 인벤토리"} / ${groupName}`}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="host-readonly-card host-readonly-empty-card">
                            이 호스트가 포함된 그룹이 없습니다.
                          </div>
                        )}
                      </div>
                    </div>
                    {inventories.some((inventory) => inventory.groups.length > 0) ? (
                      isHostAssignmentEditorOpen ? (
                       <>
                         <div className="assignment-target-summary" aria-live="polite">
                           <span className="assignment-target-label">다른 인벤토리 추가 위치</span>
                          <strong>
                            {selectedHostAssignmentTargetOption
                              ? selectedHostAssignmentTargetOption.label
                              : "아직 선택하지 않음"}
                          </strong>
                        </div>
                        <div className="assignment-tree-map host-group-editor-tree">
                          {inventories.map((inventory) => {
                            const isCurrentInventory = inventory.id === infoPanelInventory?.id;

                            return (
                              <section className="assignment-tree-inventory" key={inventory.id}>
                                <div className="assignment-tree-inventory-title">
                                  <span className="assignment-tree-caret" aria-hidden="true">▾</span>
                                  <div className="assignment-tree-title-copy">
                                    <strong>{inventory.name}</strong>
                                    <span>
                                      {inventory.groups.length}개 그룹 · {inventory.hosts.length}개 호스트
                                      {isCurrentInventory ? " · 현재 편집 중" : ""}
                                    </span>
                                  </div>
                                </div>
                                {inventory.groups.length > 0 ? (
                                  <div className="assignment-tree-groups">
                                    {inventory.groups.map((group) => {
                                      const targetValue = `${inventory.id}::${group.id}`;
                                      const isCurrentGroupSelected =
                                        isCurrentInventory && infoPanelDraft.values.groups.includes(group.id);
                                      const isAlreadyAssigned =
                                        isCurrentGroupSelected ||
                                        (!isCurrentInventory &&
                                          (activeInfoPanelHostAsset?.memberships.some(
                                            (membership) =>
                                              membership.inventory_id === inventory.id &&
                                              membership.group_name === group.name
                                          ) ?? false));
                                      const isTargetSelected =
                                        !isCurrentInventory && hostAssetAssignmentTarget === targetValue;
                                      const isSelected = isCurrentGroupSelected || isTargetSelected;

                                      return (
                                        <button
                                          key={group.id}
                                          type="button"
                                          className={`assignment-tree-group-card ${isSelected ? "selected" : ""} ${
                                            isAlreadyAssigned && !isCurrentGroupSelected ? "assigned" : ""
                                          }`}
                                          onClick={() => {
                                            if (isCurrentInventory) {
                                              handleHostDraftGroupToggle(group.id);
                                              return;
                                            }

                                            if (isAlreadyAssigned) {
                                              return;
                                            }

                                            setHostAssetAssignmentTarget(targetValue);
                                          }}
                                          aria-pressed={isSelected}
                                          disabled={!isCurrentInventory && !activeInfoPanelHostAsset}
                                        >
                                          <span className="assignment-tree-group-name">{group.name}</span>
                                          <span className="assignment-tree-group-path">
                                            경로: {inventory.name} / {group.name}
                                          </span>
                                          <span className="assignment-tree-state-badge">
                                            {isSelected ? "선택" : isAlreadyAssigned ? "이미 연결됨" : "추가 가능"}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <span className="assignment-card-empty">이 인벤토리에는 그룹이 없습니다.</span>
                                )}
                              </section>
                            );
                          })}
                        </div>
                        <div className="host-asset-assignment-actions">
                          <button
                            type="button"
                            className="btn btn-secondary host-section-inline-button"
                            onClick={handleAssignOpenHostToSelectedTarget}
                            disabled={!hostAssetAssignmentTarget || !activeInfoPanelHostAsset}
                          >
                            선택한 다른 인벤토리 그룹에 추가
                          </button>
                          <span className="assignment-action-helper">
                            현재 인벤토리의 선택/해제는 아래 저장 버튼으로 반영됩니다.
                          </span>
                        </div>
                      </>
                      ) : null
                    ) : (
                      <div className="assignment-empty-state">
                        <strong>그룹 없음</strong>
                        <span>인벤토리에 그룹을 먼저 추가하면 호스트를 배정할 수 있습니다.</span>
                      </div>
                    )}
                  </div>
                ) : null}
                <div className="info-section host-credential-section">
                  <div className="credential-section-header">
                    <div>
                      <h3>접속 계정</h3>
                    </div>
                    <div className="credential-header-controls">
                      <span className="assignment-count-badge">
                        {selectedHostLoginCredential
                          ? "1개 선택됨"
                          : infoPanelDraft.values.loginCredentialRef.trim()
                            ? "참조 누락"
                            : "선택 안 함"}
                      </span>
                      {activeInfoPanel.kind === "host" ? (
                        <button
                          type="button"
                          className="btn btn-secondary section-action-button host-credential-unified-button"
                          onClick={() =>
                            openCredentialOverlayFromHost(
                              activeInfoPanel.inventoryId,
                              activeInfoPanel.hostId
                            )
                          }
                          disabled={hostCredentialPickerDisabled}
                          data-testid="host-edit-open-credential-picker"
                        >
                          계정 선택/관리
                        </button>
                      ) : null}
                    </div>
                  </div>

                  <div className="selected-credential-summary">
                    <div className="info-form-field host-readonly-field">
                      <span>현재 계정</span>
                      <div className="host-readonly-card-stack">
                        <div className="host-readonly-card host-summary-primary-card">
                          <strong>{selectedHostCredentialPrimaryText}</strong>
                        </div>
                        <div className="host-readonly-card host-readonly-meta-card">
                          <div className="selected-credential-meta">{selectedHostCredentialMetaText}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="host-become-control">
                    <h3>권한 상승</h3>
                    <div className="info-form-field host-readonly-field host-become-toggle-field">
                      <span>사용 여부</span>
                      <div className="host-readonly-card host-readonly-control-card host-become-toggle">
                        <label className="host-become-switch">
                          <input
                            type="checkbox"
                            checked={infoPanelDraft.values.becomeEnabled && canSelectedHostCredentialBecome}
                            onChange={(event) => handleHostBecomeEnabledChange(event.target.checked)}
                          />
                          <span>사용</span>
                        </label>
                      </div>
                    </div>
                  </div>

                </div>
                <div className="info-section host-note-section">
                  <h3>설명</h3>
                  <textarea
                    className="form-textarea"
                    value={infoPanelDraft.values.note}
                    onChange={(event) =>
                      setInfoPanelDraft((current) =>
                        current?.kind === "host"
                          ? {
                              kind: "host",
                              values: { ...current.values, note: event.target.value },
                            }
                          : current
                      )
                    }
                  />
                </div>
                {activeInfoPanel.kind === "hostAsset" ? (
                  <div className="info-section">
                    <h3>현재 연결</h3>
                    <div className="related-host-list">
                      {infoPanelHostAssetGroupNames.length > 0 ? (
                        infoPanelHostAssetGroupNames.map((groupName) => (
                          <span key={groupName} className="host-group-tag">
                            {groupName}
                          </span>
                        ))
                      ) : (
                        <span className="host-group-tag host-group-tag-empty">미소속</span>
                      )}
                    </div>
                  </div>
                ) : null}
              </>
            ) : activeInfoPanel.kind === "credentials" ? (
              <>{credentialManagerContent}</>
            ) : null}
          </div>

          <div className="info-panel-actions">
            {infoPanel?.kind === "credentials" ? (
              <div className="info-panel-actions-group info-panel-actions-group-end">
                <button
                  type="button"
                  className="btn btn-secondary info-panel-close"
                  onClick={closeInfoPanel}
                >
                  닫기
                </button>
              </div>
            ) : (
              <>
                <div className="info-panel-actions-group info-panel-actions-group-start">
                  {infoPanel?.kind !== "hostAsset" ? (
                    <button type="button" className="btn btn-danger" onClick={handleDeleteInfoPanel}>
                      삭제
                    </button>
                  ) : null}
                </div>
                <div className="info-panel-actions-group info-panel-actions-group-end">
                  <button
                    type="button"
                    className="btn btn-secondary info-panel-close"
                    onClick={closeInfoPanel}
                  >
                    닫기
                  </button>
                  <button type="button" className="btn btn-primary" onClick={handleSaveInfoPanel}>
                    저장
                  </button>
                </div>
              </>
            )}
          </div>
        </aside>
      </div>
          );
        })()
      : null;

  const confirmDialogContent = confirmDialog ? (
    <div className="discard-confirm-shell" aria-modal="true" role="alertdialog" aria-labelledby="discard-confirm-title" aria-describedby="discard-confirm-message">
      <button
        type="button"
        className="discard-confirm-backdrop"
        aria-label="확인 메시지 닫기"
        onClick={handleCancelConfirmDialog}
      />
      <div className="discard-confirm-dialog">
        <span className={`discard-confirm-kicker ${confirmDialog.tone === "danger" ? "danger" : ""}`}>{confirmDialog.kicker}</span>
        <div className="discard-confirm-copy">
          <div className={`discard-confirm-accent ${confirmDialog.tone === "danger" ? "danger" : ""}`} aria-hidden="true">
            {confirmDialog.tone === "danger" ? "!" : "i"}
          </div>
          <div>
            <h2 id="discard-confirm-title" className="discard-confirm-title">
              {confirmDialog.title}
            </h2>
            <p id="discard-confirm-message" className="discard-confirm-message">
              {confirmDialog.message}
            </p>
          </div>
        </div>
        <div className="discard-confirm-actions">
          <button type="button" className="btn btn-secondary" onClick={handleCancelConfirmDialog}>
            {confirmDialog.cancelLabel}
          </button>
          <button type="button" className="btn btn-danger" onClick={handleConfirmDialog}>
            {confirmDialog.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  const credentialOverlayContent =
    credentialOverlay && infoPanel?.kind === "host" && infoPanelHost ? (
      <div
        className="credential-overlay-shell"
        aria-modal="true"
        role="dialog"
        aria-labelledby="credential-overlay-title"
        aria-describedby="credential-overlay-description"
        data-testid="credential-manager-overlay"
      >
        <button
          type="button"
          className="credential-overlay-backdrop"
          aria-label="자격 증명 관리 닫기"
          onClick={closeCredentialOverlay}
        />
        <section className="credential-overlay-panel" data-testid="credential-manager-overlay-panel">
          <div className="credential-overlay-header">
            <div>
              <span className="pane-kicker">
                {credentialOverlay.source === "host-create"
                  ? "호스트 편집 · 자격 증명 추가"
                  : "호스트 편집 · 자격 증명 선택/관리"}
              </span>
              <h2 id="credential-overlay-title" className="credential-overlay-title">
                공용 자격 증명
              </h2>
              <p id="credential-overlay-description" className="panel-subtitle">
                {`${infoPanelHost.name} 호스트 초안을 유지한 채 ${
                  credentialOverlay.source === "host-create"
                    ? "새 자격 증명을 만들고 바로 연결할 수 있습니다."
                    : "선택, 추가, 편집, 삭제를 한 창에서 처리합니다."
                }`}
              </p>
            </div>
          </div>
          <div className="credential-overlay-body">{credentialManagerContent}</div>
          <div className="credential-overlay-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={closeCredentialOverlay}
              data-testid="credential-manager-overlay-close"
            >
              닫기
            </button>
          </div>
        </section>
      </div>
    ) : null;

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        <Header
          title="인벤토리 워크스페이스"
          subtitle="인벤토리, 그룹, 호스트를 한 화면에서 관리하고 서버에 저장합니다"
          actions={
            <>
              <Link href="/jobs/new" className="btn btn-primary preview-header-button">
                작업 실행으로
              </Link>
            </>
          }
        />

        <div className="app-content fade-in preview-page">
          {feedback && (
            <div
              className={`feedback-notice feedback-notice-${feedback.tone}`}
              role="status"
              aria-live="polite"
            >
              <span className="feedback-notice-label">
                {feedback.tone === "success"
                  ? "완료"
                  : feedback.tone === "error"
                    ? "주의"
                    : "안내"}
              </span>
              <p className="feedback-notice-message">{feedback.message}</p>
              <button
                type="button"
                className="feedback-notice-close"
                onClick={() => setFeedback(null)}
                aria-label="안내 메시지 닫기"
              >
                ×
              </button>
            </div>
          )}

          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            <section className="workspace-grid" aria-label="인벤토리 워크스페이스">
              <aside className="workspace-tree-pane" aria-label="인벤토리 / 그룹 트리">
                <div className="tree-pane-header">
                  <div className="pane-heading">
                    <h2 className="panel-title">인벤토리 / 그룹</h2>
                  </div>
                  <div className="pane-actions">
                    <button
                      type="button"
                      className="btn btn-secondary compact-action-button"
                      onClick={handleAddInventory}
                    >
                      + 인벤토리
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary compact-action-button"
                      onClick={handleAddGroup}
                    >
                      + 그룹
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary compact-action-button tree-bulk-button"
                      onClick={handleToggleAllInventories}
                      aria-label={
                        allInventoriesExpanded
                          ? "모든 인벤토리 그룹 접기"
                          : "모든 인벤토리 그룹 펼치기"
                      }
                      disabled={inventories.length === 0}
                    >
                      {allInventoriesExpanded ? "전체 접기" : "전체 펼치기"}
                    </button>
                    {selectedInventoryKeys.size > 0 && (
                      <button
                        type="button"
                        className="btn btn-danger compact-action-button tree-bulk-button"
                        onClick={handleBulkDeleteSelectedInventories}
                      >
                        선택 인벤토리 {selectedInventoryKeys.size}개 삭제
                      </button>
                    )}
                    {selectedGroupKeys.size > 0 && (
                      <button
                        type="button"
                        className="btn btn-danger compact-action-button tree-bulk-button"
                        onClick={handleBulkDeleteSelectedGroups}
                      >
                        선택 그룹 {selectedGroupKeys.size}개 삭제
                      </button>
                    )}
                    {(selectedInventoryKeys.size > 0 || selectedGroupKeys.size > 0) && (
                      <button
                        type="button"
                        className="btn btn-secondary compact-action-button tree-bulk-button"
                        onClick={clearAllSelections}
                      >
                        선택 해제
                      </button>
                    )}
                    <button
                      type="button"
                      className="mini-icon-button"
                      onClick={() =>
                        setFeedback({
                          tone: "info",
                          message:
                            "인벤토리·그룹을 선택하거나 호스트를 클릭하면 오른쪽 정보 패널에서 바로 수정할 수 있습니다.",
                        })
                      }
                      aria-label="트리 도움말"
                    >
                      ?
                    </button>
                  </div>
                </div>

                <div className="search-panel tree-search-panel" aria-label="인벤토리와 그룹 검색">
                  <div className="search-controls">
                    <label className="search-input-wrap" htmlFor="inventory-tree-search">
                      <input
                        id="inventory-tree-search"
                        className="form-input search-input"
                        value={treeSearchQuery}
                        onChange={(event) => setTreeSearchQuery(event.target.value)}
                        placeholder="인벤토리/그룹 검색..."
                        type="search"
                        aria-describedby="inventory-tree-search-count"
                      />
                    </label>
                    <button
                      type="button"
                      className="btn btn-secondary search-clear-button"
                      onClick={() => setTreeSearchQuery("")}
                      disabled={treeSearchQuery.length === 0}
                    >
                      지우기
                    </button>
                  </div>
                  <span id="inventory-tree-search-count" className="tree-search-count" aria-live="polite">
                    인벤토리 {visibleInventoryCount} · 그룹 {visibleGroupCount}
                  </span>
                </div>

                <div className="tree-scroll" role="tree">
                  {inventoryViews.filter((inventory) => inventory.visible).map((inventoryView) => {
                    const isInventoryFocused =
                      focusedScope.kind === "inventory" &&
                      focusedScope.inventoryId === inventoryView.inventory.id;
                    const isScopeChild =
                      focusedScope.kind === "group" &&
                      focusedScope.inventoryId === inventoryView.inventory.id;
                    const visibleGroups = inventoryView.groups.filter((groupView) => groupView.visible);
                    const isInventoryExpanded =
                      normalizedQuery.length > 0 ||
                      normalizedTreeQuery.length > 0 ||
                      expandedInventoryIds.has(inventoryView.inventory.id);
                    const groupListId = `inventory-group-list-${inventoryView.inventory.id}`;

                    return (
                      <article
                        key={inventoryView.inventory.id}
                        className="tree-inventory-block"
                        role="treeitem"
                        aria-expanded={isInventoryExpanded}
                        aria-selected={isInventoryFocused || isScopeChild}
                        data-expanded={isInventoryExpanded}
                      >
                        <div className="tree-node-row inventory-row">
                          <label
                            className="inventory-select-control"
                            aria-label={`${inventoryView.inventory.name} 인벤토리 선택`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedInventoryKeys.has(
                                getInventorySelectionKey(inventoryView.inventory.id)
                              )}
                              onChange={() => toggleInventorySelection(inventoryView.inventory.id)}
                              onClick={(event) => event.stopPropagation()}
                              data-testid={`inventory-select-${inventoryView.inventory.id}`}
                            />
                          </label>
                          <button
                            type="button"
                            className={`tree-expand-button ${isInventoryExpanded ? "expanded" : ""}`}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleInventoryToggle(inventoryView.inventory.id);
                            }}
                            aria-controls={groupListId}
                            aria-expanded={isInventoryExpanded}
                            aria-label={`${inventoryView.inventory.name} 그룹 ${
                              isInventoryExpanded ? "접기" : "펼치기"
                            }`}
                          >
                            <span className="tree-expand-icon" aria-hidden="true">
                              ▸
                            </span>
                          </button>
                          <button
                            type="button"
                            className={`tree-node inventory-node ${
                              isInventoryFocused || isScopeChild ? "active" : ""
                            }`}
                            onClick={() =>
                              setFocusedScope({
                                kind: "inventory",
                                inventoryId: inventoryView.inventory.id,
                              })
                            }
                            onDoubleClick={() => openInventoryPanel(inventoryView.inventory.id)}
                            aria-pressed={isInventoryFocused || isScopeChild}
                          >
                            <span className="tree-node-marker inventory-marker" aria-hidden="true" />
                            <span className="tree-node-main">
                              <strong className="node-title">{inventoryView.inventory.name}</strong>
                            </span>
                            <span className="tree-node-meta">
                              <span className="node-count">
                                호스트 {getCountLabel(
                                  inventoryView.displayHosts.length,
                                  inventoryView.inventory.hosts.length,
                                  normalizedQuery
                                )}
                              </span>
                            </span>
                          </button>
                          <button
                            type="button"
                            className="tree-info-button"
                            onClick={() => openInventoryPanel(inventoryView.inventory.id)}
                            aria-label={`${inventoryView.inventory.name} 정보 열기`}
                          >
                            i
                          </button>
                        </div>

                        {isInventoryExpanded && (
                          <div id={groupListId} className="tree-children" role="group">
                            {visibleGroups.map((groupView) => {
                              const isGroupFocused =
                                focusedScope.kind === "group" &&
                                focusedScope.inventoryId === inventoryView.inventory.id &&
                                focusedScope.groupId === groupView.group.id;

                              return (
                                <DroppableGroupTreeItem
                                  key={groupView.group.id}
                                  inventoryId={inventoryView.inventory.id}
                                  groupView={groupView}
                                  isFocused={isGroupFocused}
                                  isSelected={selectedGroupKeys.has(
                                    getGroupDraftKey(inventoryView.inventory.id, groupView.group.id)
                                  )}
                                  countLabel={getCountLabel(
                                    groupView.displayHosts.length,
                                    groupView.relatedHosts.length,
                                    normalizedQuery
                                  )}
                                  onSelect={() => {
                                    ensureInventoryExpanded(inventoryView.inventory.id);
                                    setFocusedScope({
                                      kind: "group",
                                      inventoryId: inventoryView.inventory.id,
                                      groupId: groupView.group.id,
                                    });
                                  }}
                                  onOpen={() =>
                                    openGroupPanel(inventoryView.inventory.id, groupView.group.id)
                                  }
                                  onToggleSelect={() =>
                                    toggleGroupSelection(inventoryView.inventory.id, groupView.group.id)
                                  }
                                />
                              );
                            })}
                          </div>
                        )}
                      </article>
                    );
                  })}

                  {isLoadingInventories && (
                    <div className="tree-empty-state">
                      <strong>인벤토리를 불러오는 중입니다.</strong>
                      <p>서버의 V2 인벤토리 데이터를 연결하고 있습니다.</p>
                    </div>
                  )}

                  {!isLoadingInventories && inventories.length === 0 && (
                    <div className="tree-empty-state">
                      <strong>등록된 인벤토리가 없습니다.</strong>
                      <p>+ 인벤토리를 눌러 첫 인벤토리를 만드세요.</p>
                    </div>
                  )}

                  {!isLoadingInventories && inventories.length > 0 && inventoryViews.every((inventory) => !inventory.visible) && (
                    <div className="tree-empty-state">
                      <strong>검색 결과가 없습니다.</strong>
                      <p>검색 조건을 확인하세요.</p>
                    </div>
                  )}
                </div>
              </aside>

              <section className="card workspace-host-pane">
                <div className="card-header host-pane-header">
                  <div className="host-pane-title-row">
                    <div className="host-pane-heading">
                      <h2 className="panel-title">호스트 등록 현황</h2>
                      <div className="host-header-chips">
                        <span className="inventory-chip">
                          결과 {filteredHostRows.length} / {scopeTotalHostCount}
                        </span>
                        <span className="inventory-chip">{scopeLabel}</span>
                      </div>
                    </div>
                  </div>
                  <div className="host-toolbar" aria-label="호스트 목록 도구막대">
                    <div className="host-header-actions">
                      <button
                        type="button"
                        className={`scope-reset-button ${focusedScope.kind === "all" ? "active" : ""}`}
                        onClick={() => setFocusedScope({ kind: "all" })}
                      >
                        전체 보기
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary compact-action-button"
                        onClick={handleAddHost}
                      >
                        + 호스트
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary compact-action-button"
                        onClick={handleOpenCredentialManagerFromSelection}
                        data-testid="open-credential-manager-button"
                      >
                        자격 증명
                      </button>
                      {selectedHostKeys.size > 0 && (
                        <button
                          type="button"
                          className="btn btn-danger compact-action-button"
                          onClick={handleBulkDeleteSelectedHosts}
                        >
                          선택 호스트 {selectedHostKeys.size}개 삭제
                        </button>
                      )}
                      {selectedHostKeys.size > 0 && (
                        <div className="host-bulk-assign-control" aria-label="선택 호스트 일괄 배정">
                          <select
                            className="form-input compact-select"
                            aria-label="선택 호스트를 넣을 인벤토리 / 그룹"
                            value={bulkHostAssignmentTarget}
                            onChange={(event) => setBulkHostAssignmentTarget(event.target.value)}
                            disabled={hostAssignmentTargetOptions.length === 0}
                          >
                            <option value="">인벤토리 / 그룹 선택</option>
                            {hostAssignmentTargetOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            className="btn btn-primary compact-action-button"
                            onClick={handleBulkAssignSelectedHosts}
                            disabled={
                              !bulkHostAssignmentTarget || selectedHostAssetsForToolbar.length === 0
                            }
                          >
                            선택 호스트 {selectedHostAssetsForToolbar.length}개 넣기
                          </button>
                        </div>
                      )}
                      {selectedHostKeys.size > 0 && (
                        <button
                          type="button"
                          className="btn btn-secondary compact-action-button"
                          onClick={clearHostSelection}
                        >
                          호스트 선택 해제
                        </button>
                      )}
                    </div>
                    <div className="search-panel host-search-panel">
                      <div className="search-controls">
                        <label className="search-input-wrap" htmlFor="inventory-preview-search">
                          <input
                            id="inventory-preview-search"
                            className="form-input search-input"
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            placeholder="모든 필드 검색..."
                          />
                        </label>
                        <button
                          type="button"
                          className="btn btn-secondary search-clear-button"
                          onClick={() => setSearchQuery("")}
                          disabled={searchQuery.length === 0}
                        >
                          지우기
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card-body host-pane-body">
                  <div className="table-wrapper">
                    <table className="table host-table">
                      <colgroup>
                        <col className="col-host" />
                        <col className="col-inventory" />
                        <col className="col-groups" />
                        <col className="col-address" />
                        <col className="col-platform" />
                        <col className="col-status" />
                      </colgroup>
                      <thead>
                        <tr>
                          <th scope="col">호스트</th>
                          <th scope="col">인벤토리</th>
                          <th scope="col">배정 그룹</th>
                          <th scope="col">주소</th>
                          <th scope="col">플랫폼 / 연결</th>
                          <th scope="col">상태</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredHostRows.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="table-empty preview-empty-cell">
                              <p>현재 범위와 검색어에 맞는 호스트가 없습니다.</p>
                              <span>범위 또는 검색어를 확인하세요.</span>
                            </td>
                          </tr>
                        ) : (
                          filteredHostRows.map(
                            ({
                              rowKey,
                              inventory,
                              inventoryLabel,
                                inventoryMeta,
                                host,
                                hostAssetId,
                                openAsHostAsset,
                                groupNames,
                                isOrphan,
                              }) => (
                            <DraggableHostRow
                              key={rowKey}
                              inventory={inventory}
                              inventoryLabel={inventoryLabel}
                              inventoryMeta={inventoryMeta}
                              host={host}
                              hostAssetId={hostAssetId}
                              groupNames={groupNames}
                              isSelected={selectedHostKeys.has(
                                getHostSelectionKey(hostAssetId, inventory?.id ?? null, host.id)
                              )}
                              onToggleSelect={() =>
                                toggleHostSelection(hostAssetId, inventory?.id ?? null, host.id)
                              }
                              isOrphan={isOrphan}
                              onOpen={
                                hostAssetId && openAsHostAsset
                                  ? () => openHostAssetPanel(hostAssetId)
                                  : inventory
                                    ? () => openHostPanel(inventory.id, host.id)
                                  : undefined
                              }
                            />
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </section>
            </section>
          </DndContext>

          {infoPanelContent}
          {credentialOverlayContent}
          {confirmDialogContent}

          <style jsx>{`
            .preview-page {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-lg);
              width: 100%;
              max-width: none;
              min-height: 0;
            }

            .feedback-notice {
              position: fixed;
              bottom: var(--spacing-lg);
              left: calc(50% + (var(--sidebar-width) / 2));
              transform: translateX(-50%);
              z-index: 220;
              display: flex;
              align-items: center;
              gap: var(--spacing-sm);
              width: min(440px, calc(100vw - var(--sidebar-width) - var(--spacing-xl)));
              padding: var(--spacing-sm) var(--spacing-md);
              border: 1px solid rgba(88, 166, 255, 0.22);
              border-radius: var(--radius-lg);
              background: rgba(88, 166, 255, 0.1);
              backdrop-filter: blur(18px);
              box-shadow: 0 18px 48px rgba(1, 4, 9, 0.28);
              animation: feedback-slide-in 180ms ease-out;
            }

            .feedback-notice-success {
              border-color: rgba(63, 185, 80, 0.24);
              background: rgba(63, 185, 80, 0.1);
            }

            .feedback-notice-error {
              border-color: rgba(248, 81, 73, 0.24);
              background: rgba(248, 81, 73, 0.1);
            }

            .feedback-notice-label {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              padding: 2px var(--spacing-xs);
              border-radius: 999px;
              background: rgba(88, 166, 255, 0.16);
              color: var(--color-primary);
              font-size: 11px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
            }

            .feedback-notice-message {
              flex: 1;
              margin: 0;
              font-size: 13px;
              color: var(--color-text-primary);
            }

            .feedback-notice-close,
            .mini-icon-button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: calc(var(--spacing-lg) + var(--spacing-xs));
              height: calc(var(--spacing-lg) + var(--spacing-xs));
              border: 1px solid var(--color-border);
              border-radius: 999px;
              background: var(--color-surface);
              color: var(--color-text-secondary);
              cursor: pointer;
              transition: all var(--transition-fast);
            }

            .feedback-notice-close:hover,
            .mini-icon-button:hover {
              border-color: var(--color-primary);
              color: var(--color-primary);
            }

            @keyframes feedback-slide-in {
              from {
                opacity: 0;
                transform: translateY(-8px);
              }
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }

            .preview-header-button {
              white-space: nowrap;
            }

            .pane-kicker,
            .search-label {
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 0.08em;
              color: var(--color-text-muted);
            }

            .panel-subtitle,
            .inventory-cell span,
            .platform-stack span,
            .host-identity span,
            .tree-empty-state p,
            .preview-empty-cell span,
            .info-panel-copy p,
            .info-section p {
              font-size: 13px;
              color: var(--color-text-secondary);
            }

            .workspace-grid {
              display: grid;
              grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
              gap: var(--spacing-lg);
              align-items: stretch;
              height: calc(100vh - var(--header-height) - 64px);
              min-height: 520px;
              overflow: hidden;
            }

            .panel-title {
              font-size: 15px;
              font-weight: 600;
              color: var(--color-text-primary);
            }

            .workspace-tree-pane {
              border: 1px solid var(--color-border);
              border-radius: var(--radius-lg);
              background: rgba(22, 27, 34, 0.88);
              padding: var(--spacing-lg);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-md);
              min-height: 0;
              overflow: hidden;
            }

            .tree-pane-header,
            .host-header-chips,
            .host-header-actions,
            .pane-actions,
            .search-controls,
            .inventory-cell,
            .platform-stack,
            .info-panel-header {
              display: flex;
              align-items: flex-start;
              justify-content: space-between;
              gap: var(--spacing-sm);
              flex-wrap: wrap;
            }

            .host-pane-header {
              display: flex;
              flex-direction: column;
              align-items: stretch;
              gap: var(--spacing-md);
            }

            .pane-heading,
            .host-pane-heading {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .pane-actions,
            .host-header-actions {
              align-items: center;
            }

            .host-pane-title-row,
            .host-toolbar {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: var(--spacing-sm);
              flex-wrap: wrap;
            }

            .host-pane-title-row {
              align-items: flex-start;
            }

            .host-toolbar {
              padding-top: var(--spacing-xs);
              border-top: 1px solid var(--color-border);
            }

            .host-search-panel {
              display: flex;
              flex: 1;
              width: 100%;
              max-width: 420px;
              min-width: min(100%, 360px);
              margin-left: auto;
              justify-content: flex-end;
            }

            .search-controls {
              width: 100%;
              align-items: center;
              justify-content: flex-end;
              flex-wrap: nowrap;
            }

            .node-tag-row,
            .host-group-tags,
            .related-host-list {
              display: flex;
              flex-wrap: wrap;
              gap: var(--spacing-xs);
            }

            .inventory-chip,
            .node-tag,
            .host-group-tag {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              padding: var(--spacing-xs) var(--spacing-sm);
              border-radius: 999px;
              border: 1px solid var(--color-border);
              background: var(--color-surface);
              color: var(--color-text-secondary);
              font-size: 12px;
            }

            .scope-reset-button {
              border: 1px solid var(--color-border);
              background: var(--color-surface);
              color: var(--color-text-secondary);
              border-radius: var(--radius-md);
              padding: var(--spacing-xs) var(--spacing-sm);
              font-size: 12px;
              cursor: pointer;
              transition: all var(--transition-fast);
            }

            .scope-reset-button:hover,
            .scope-reset-button.active {
              border-color: var(--color-primary);
              color: var(--color-primary);
              background: var(--color-primary-bg);
            }

            .compact-action-button {
              white-space: nowrap;
            }

            .host-bulk-assign-control,
            .host-asset-assignment-control {
              display: flex;
              align-items: center;
              gap: var(--spacing-sm);
              flex-wrap: wrap;
            }

            .host-bulk-assign-control .compact-select {
              width: auto;
              min-width: 220px;
              min-height: 34px;
              padding-top: 0;
              padding-bottom: 0;
            }

            .host-asset-assignment-control {
              align-items: flex-end;
              margin-top: var(--spacing-sm);
            }

            .host-asset-assignment-control .info-form-field {
              flex: 1;
              min-width: min(100%, 260px);
            }

            .tree-node-row {
              display: grid;
              grid-template-columns: minmax(0, 1fr) auto;
              align-items: center;
              gap: var(--spacing-sm);
            }

            .tree-scroll {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-lg);
              flex: 1;
              min-height: 0;
              overflow-y: auto;
              padding-right: var(--spacing-xs);
            }

            .tree-inventory-block {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .inventory-row {
              grid-template-columns: auto auto minmax(0, 1fr) auto;
              align-items: start;
            }

            .inventory-select-control,
            .group-select-control,
            .host-select-control {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              min-height: calc(var(--spacing-lg) + var(--spacing-sm));
              margin-top: 2px;
              color: var(--color-text-secondary);
            }

            .inventory-select-control input,
            .group-select-control input,
            .host-select-control input {
              width: 16px;
              height: 16px;
              accent-color: var(--color-primary);
              cursor: pointer;
            }

            .tree-node {
              flex: 1;
              display: flex;
              align-items: center;
              gap: var(--spacing-sm);
              width: 100%;
              border: 1px solid transparent;
              border-radius: var(--radius-md);
              background: transparent;
              color: inherit;
              text-align: left;
              padding: calc(var(--spacing-sm) + 2px) var(--spacing-sm);
              cursor: pointer;
              transition: border-color var(--transition-fast), background var(--transition-fast), color var(--transition-fast);
            }

            .tree-expand-button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: calc(var(--spacing-lg) + var(--spacing-sm));
              min-height: calc(var(--spacing-lg) + var(--spacing-sm));
              margin-top: 2px;
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
              color: var(--color-text-secondary);
              cursor: pointer;
              transition: border-color var(--transition-fast), background var(--transition-fast), color var(--transition-fast), transform var(--transition-fast);
            }

            .tree-expand-button:hover {
              border-color: rgba(88, 166, 255, 0.28);
              background: rgba(88, 166, 255, 0.08);
              color: var(--color-primary);
            }

            .tree-expand-button:focus-visible {
              outline: 2px solid rgba(88, 166, 255, 0.35);
              outline-offset: 2px;
            }

            .tree-expand-button.expanded {
              border-color: rgba(88, 166, 255, 0.22);
              background: rgba(88, 166, 255, 0.1);
              color: var(--color-primary);
            }

            .tree-expand-icon {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              font-size: 13px;
              line-height: 1;
              transform: rotate(0deg);
              transition: transform var(--transition-fast);
            }

            .tree-expand-button.expanded .tree-expand-icon {
              transform: rotate(90deg);
            }

            .tree-node:hover,
            .tree-node.active {
              border-color: rgba(88, 166, 255, 0.18);
              background: rgba(88, 166, 255, 0.08);
            }

            .tree-node-marker {
              width: 8px;
              height: 8px;
              border-radius: 999px;
              flex-shrink: 0;
              background: var(--color-text-muted);
            }

            .inventory-marker {
              background: var(--color-primary);
              box-shadow: 0 0 0 4px rgba(88, 166, 255, 0.12);
            }

            .tree-node-main {
              min-width: 0;
              flex: 1;
            }

            .tree-node-meta {
              display: inline-flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-xs);
              flex-wrap: wrap;
              flex-shrink: 0;
            }

            .node-count {
              font-size: 12px;
              color: var(--color-text-secondary);
              white-space: nowrap;
            }

            .tree-info-button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              flex: 0 0 24px;
              width: 24px;
              height: 24px;
              min-width: 24px;
              border: 0;
              border-radius: 999px;
              background: transparent;
              color: var(--color-text-muted);
              font-size: 11px;
              font-weight: 700;
              line-height: 1;
              cursor: pointer;
              transition: background var(--transition-fast), color var(--transition-fast);
            }

            .tree-info-button:hover {
              background: var(--color-surface);
              color: var(--color-primary);
            }

            .tree-children {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
              margin-left: calc(var(--spacing-sm) + 6px);
              padding-left: var(--spacing-md);
              border-left: 1px solid var(--color-border);
              position: relative;
            }

            .tree-children::before {
              content: "";
              position: absolute;
              inset: 0 auto 0 0;
              width: 1px;
              background: linear-gradient(180deg, rgba(88, 166, 255, 0.32), rgba(88, 166, 255, 0));
            }

            .tree-group-branch {
              position: relative;
            }

            .tree-group-branch.over::before {
              border-top-color: rgba(88, 166, 255, 0.4);
            }

            .tree-group-branch::before {
              content: "";
              position: absolute;
              top: 18px;
              left: calc(var(--spacing-md) * -1);
              width: calc(var(--spacing-sm) + 2px);
              border-top: 1px solid var(--color-border);
            }

            .node-title {
              display: block;
              font-size: 15px;
              color: var(--color-text-primary);
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .inventory-node .node-title {
              font-weight: 600;
            }

            .group-row {
              grid-template-columns: auto minmax(0, 1fr) auto;
              align-items: start;
            }

            .group-node {
              padding-left: calc(var(--spacing-sm) + 2px);
            }

            .tree-group-branch.over .group-node {
              border-color: rgba(88, 166, 255, 0.28);
              background: rgba(88, 166, 255, 0.12);
            }

            .group-dropzone {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              max-width: 0;
              min-height: 18px;
              overflow: hidden;
              opacity: 0;
              color: var(--color-text-muted);
              border: 0 solid transparent;
              background: rgba(88, 166, 255, 0.08);
              border-radius: 999px;
              padding: 0;
              font-size: 10px;
              font-weight: 600;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              white-space: nowrap;
              transform: translateY(2px);
              transition:
                max-width var(--transition-fast),
                opacity var(--transition-fast),
                padding var(--transition-fast),
                border-color var(--transition-fast),
                transform var(--transition-fast);
            }

            .tree-group-branch:hover .group-dropzone,
            .tree-group-branch:focus-within .group-dropzone,
            .tree-group-branch.over .group-dropzone {
              max-width: 88px;
              opacity: 1;
              padding: 2px 6px;
              border-width: 1px;
              border-color: rgba(88, 166, 255, 0.22);
              transform: translateY(0);
            }

            .group-dropzone.over {
              color: var(--color-primary);
              background: rgba(88, 166, 255, 0.16);
              border-color: rgba(88, 166, 255, 0.48);
            }

            .tree-empty-state,
            .preview-empty-cell {
              padding: var(--spacing-xl);
              border-radius: var(--radius-lg);
              border: 1px dashed var(--color-border-hover);
              background: var(--color-bg-secondary);
            }

            .tree-empty-state strong,
            .preview-empty-cell p {
              color: var(--color-text-primary);
            }

            .workspace-host-pane {
              min-height: 0;
              height: 100%;
              display: flex;
              flex-direction: column;
              overflow: hidden;
            }

            .host-pane-body {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
              flex: 1;
              min-height: 0;
              padding: 0 var(--spacing-lg) var(--spacing-lg);
            }

            .search-panel {
              display: flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-sm);
              width: min(100%, 520px);
              padding: 0;
              border-radius: 0;
              border: 0;
              background: transparent;
            }

            .tree-search-panel {
              width: 100%;
              flex-direction: column;
              align-items: stretch;
              justify-content: flex-start;
              gap: var(--spacing-xs);
            }

            .tree-search-panel .search-controls {
              justify-content: flex-start;
            }

            .tree-search-panel .search-input-wrap {
              min-width: 0;
            }

            .host-search-panel .search-input-wrap {
              min-width: 0;
              max-width: 360px;
            }

            .tree-search-count {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .search-panel .inventory-chip {
              background: var(--color-bg-secondary);
            }

            .table-wrapper {
              flex: 1;
              min-height: 0;
              overflow: auto;
              border: 1px solid var(--color-border);
              background: var(--color-bg-secondary);
              border-radius: var(--radius-lg);
            }

            .search-input-wrap {
              flex: 1;
              min-width: min(100%, 320px);
              display: flex;
              align-items: center;
              gap: var(--spacing-sm);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: var(--color-bg-secondary);
              padding: 0 var(--spacing-sm);
            }

            .search-icon {
              color: var(--color-text-muted);
              font-size: 14px;
            }

            .search-input {
              border: 0;
              background: transparent;
              padding-left: 0;
              padding-right: 0;
              min-height: calc(var(--spacing-lg) + var(--spacing-xs));
            }

            .search-input:focus {
              box-shadow: none;
            }

            .search-clear-button {
              flex: 0 0 auto;
              white-space: nowrap;
            }

            .host-table {
              width: 100%;
              min-width: 980px;
              table-layout: fixed;
              border-collapse: separate;
              border-spacing: 0;
            }

            .host-table :global(th),
            .host-table :global(td) {
              vertical-align: top;
            }

            .host-table :global(th) {
              position: sticky;
              top: 0;
              z-index: 1;
              padding: var(--spacing-sm) var(--spacing-md);
              background: var(--color-bg-secondary);
              box-shadow: inset 0 -1px 0 var(--color-border);
              white-space: nowrap;
            }

            .host-table :global(td) {
              padding: var(--spacing-sm) var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            .col-host {
              width: 24%;
            }

            .col-inventory {
              width: 16%;
            }

            .col-groups {
              width: 21%;
            }

            .col-address {
              width: 14%;
            }

            .col-platform {
              width: 17%;
            }

            .col-status {
              width: 8%;
            }

            .host-row {
              transition: background var(--transition-fast);
            }

            .host-row.dragging {
              opacity: 0.82;
            }

            .host-row:nth-child(even) :global(td) {
              background: var(--color-bg-secondary);
            }

            .host-row:hover :global(td) {
              background: var(--color-surface);
            }

            .drag-handle {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              border: 1px dashed var(--color-border-hover);
              background: transparent;
              color: var(--color-text-muted);
              border-radius: var(--radius-sm);
              width: 28px;
              min-width: 28px;
              min-height: 28px;
              cursor: grab;
              flex-shrink: 0;
              font-size: 14px;
              letter-spacing: -0.18em;
              line-height: 1;
            }

            .drag-handle.dragging {
              cursor: grabbing;
              border-color: rgba(88, 166, 255, 0.4);
              color: var(--color-primary);
            }

            .host-identity-button {
              border: 0;
              background: transparent;
              display: flex;
              width: 100%;
              padding: var(--spacing-xs) 0;
              min-width: 0;
              text-align: left;
              cursor: pointer;
              color: inherit;
              border-radius: var(--radius-sm);
            }

            .host-identity-button:hover .host-identity-name,
            .host-identity-button:focus-visible .host-identity-name {
              color: var(--color-primary);
            }

            .inventory-cell,
            .platform-stack {
              justify-content: flex-start;
            }

            .host-name-cell {
              display: grid;
              grid-template-columns: auto auto minmax(0, 1fr);
              align-items: start;
              gap: var(--spacing-sm);
            }

            .host-primary-cell,
            .host-group-cell,
            .host-status-cell {
              vertical-align: middle;
            }

            .host-identity,
            .inventory-cell,
            .platform-stack {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
            }

            .host-identity strong,
            .inventory-cell strong,
            .platform-stack strong,
            .info-panel-title,
            .info-metric-card strong {
              color: var(--color-text-primary);
            }

            .host-identity strong,
            .inventory-cell strong,
            .platform-stack strong {
              line-height: 1.35;
            }

            .host-identity span,
            .inventory-cell span,
            .platform-stack span {
              line-height: 1.4;
            }

            .host-identity {
              min-width: 0;
            }

            .host-identity-name {
              display: block;
              max-width: 100%;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              font-family: var(--font-mono);
              font-size: 13px;
            }

            .host-identity-meta {
              color: var(--color-text-muted);
              font-size: 12px;
            }

            .host-group-tags {
              gap: var(--spacing-xs);
              align-content: flex-start;
            }

            .host-group-tag {
              padding: 2px var(--spacing-sm);
              line-height: 1.3;
            }

            .host-group-tag-empty {
              border-style: dashed;
            }

            .host-address {
              font-size: 13px;
              line-height: 1.45;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
              max-width: 100%;
            }

            .host-status-cell {
              text-align: center;
            }

            .host-status-cell :global(.badge) {
              justify-content: center;
            }

            .info-note-preview {
              padding: var(--spacing-sm) var(--spacing-md);
              border-radius: var(--radius-md);
              border: 1px solid rgba(88, 166, 255, 0.18);
              background: rgba(88, 166, 255, 0.08);
              color: var(--color-text-primary);
              font-size: 13px;
              line-height: 1.55;
              white-space: pre-wrap;
            }

            .info-note-preview.empty {
              color: var(--color-text-secondary);
              border-style: dashed;
            }

            .info-section-helper {
              margin: 0;
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .preview-empty-cell span {
              display: block;
              margin-top: var(--spacing-xs);
            }

            .info-panel-shell {
              position: fixed;
              inset: 0;
              z-index: 120;
              pointer-events: none;
            }

            .discard-confirm-shell {
              position: fixed;
              inset: 0;
              z-index: 210;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: var(--spacing-xl);
            }

            .discard-confirm-backdrop {
              position: absolute;
              inset: 0;
              border: 0;
              background:
                radial-gradient(circle at top, rgba(88, 166, 255, 0.12), transparent 42%),
                rgba(1, 4, 9, 0.76);
              cursor: pointer;
            }

            .discard-confirm-dialog {
              position: relative;
              z-index: 1;
              width: min(440px, calc(100vw - (var(--spacing-xl) * 2)));
              padding: var(--spacing-lg);
              border: 1px solid rgba(248, 81, 73, 0.24);
              border-radius: var(--radius-lg);
              background:
                linear-gradient(180deg, rgba(248, 81, 73, 0.08), transparent 28%),
                var(--color-bg-secondary);
              box-shadow: 0 28px 64px rgba(1, 4, 9, 0.42);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-md);
            }

            .discard-confirm-kicker {
              display: inline-flex;
              align-items: center;
              width: fit-content;
              padding: 2px var(--spacing-xs);
              border-radius: 999px;
              border: 1px solid rgba(248, 81, 73, 0.24);
              background: rgba(248, 81, 73, 0.12);
              color: var(--color-primary);
              font-size: 11px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
            }

            .discard-confirm-kicker.danger {
              border-color: rgba(248, 81, 73, 0.24);
              background: rgba(248, 81, 73, 0.12);
              color: var(--color-danger, #f85149);
            }

            .discard-confirm-copy {
              display: grid;
              grid-template-columns: auto minmax(0, 1fr);
              align-items: start;
              gap: var(--spacing-md);
            }

            .discard-confirm-accent {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: calc(var(--spacing-xl) + var(--spacing-sm));
              min-width: calc(var(--spacing-xl) + var(--spacing-sm));
              height: calc(var(--spacing-xl) + var(--spacing-sm));
              border-radius: var(--radius-md);
              background: rgba(88, 166, 255, 0.16);
              color: var(--color-primary);
              font-size: 20px;
              font-weight: 700;
              line-height: 1;
            }

            .discard-confirm-accent.danger {
              background: rgba(248, 81, 73, 0.14);
              color: var(--color-danger, #f85149);
            }

            .discard-confirm-title {
              margin: 0;
              font-size: 20px;
              color: var(--color-text-primary);
            }

            .discard-confirm-message {
              margin: var(--spacing-xs) 0 0;
              font-size: 13px;
              line-height: 1.6;
              color: var(--color-text-secondary);
            }

            .discard-confirm-actions {
              display: flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-sm);
              padding-top: var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            .info-panel-backdrop {
              position: absolute;
              inset: 0;
              background: var(--color-bg-primary);
              opacity: 0.82;
              pointer-events: none;
            }

            .info-panel {
              position: absolute;
              top: 0;
              right: 0;
              width: min(420px, calc(100vw - var(--sidebar-width)));
              height: 100vh;
              padding: var(--spacing-xl);
              background: var(--color-bg-secondary);
              border-left: 1px solid var(--color-border);
              box-shadow: var(--shadow-lg);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-lg);
              pointer-events: auto;
            }

            .info-panel-body,
            .info-panel-copy,
            .info-section {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .info-panel-body {
              flex: 1;
              min-height: 0;
              overflow: auto;
            }

            .info-panel-title {
              margin-top: var(--spacing-xs);
              font-size: 22px;
            }

            .info-metric-grid {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: var(--spacing-sm);
            }

            .info-metric-card {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
              padding: var(--spacing-md);
              border-radius: var(--radius-md);
              border: 1px solid var(--color-border);
              background: var(--color-surface);
            }

            .info-metric-card span,
            .info-section h3 {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .info-metric-detail {
              font-size: 11px;
              color: var(--color-text-muted);
              line-height: 1.4;
            }

            .info-form-grid {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: var(--spacing-sm);
            }

            .info-form-field {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
            }

            .info-form-field span {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .info-form-textarea-compact {
              min-height: 96px;
            }

            .info-inline-message {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .info-inline-message.error {
              color: var(--color-error);
            }

            .credential-selection-helper {
              display: flex;
              flex-direction: column;
              gap: 2px;
              margin-top: var(--spacing-xs);
              font-size: 12px;
              color: var(--color-text-muted);
            }

            .credential-selection-helper strong {
              color: var(--color-warning);
              font-size: 12px;
              font-weight: 600;
            }

            .host-credential-section {
              gap: var(--spacing-md);
            }

            .host-group-assignment-section,
            .host-note-section {
              gap: var(--spacing-md);
            }

            :global(.credential-section-header) {
              display: flex;
              align-items: center;
              justify-content: space-between;
              flex-wrap: wrap;
              gap: var(--spacing-sm);
            }

            :global(.assignment-section-header) {
              display: flex;
              align-items: center;
              justify-content: space-between;
              flex-wrap: wrap;
              gap: var(--spacing-sm);
            }

            :global(.credential-section-header) > div:first-child,
            :global(.assignment-section-header) > div:first-child {
              min-width: 0;
            }

            :global(.credential-section-header h3),
            :global(.assignment-section-header h3) {
              margin: 0;
            }

            :global(.credential-header-controls) {
              display: flex;
              flex-flow: row wrap;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-xs);
              width: auto;
              margin-left: auto;
            }

            :global(.host-edit-section-controls) {
              display: flex;
              flex-flow: row wrap;
              align-items: center;
              justify-content: flex-start;
              gap: var(--spacing-xs);
              width: 100%;
              max-width: none;
            }

            .section-action-button {
              min-height: 32px;
              padding: 0 var(--spacing-sm);
              font-size: 12px;
              white-space: nowrap;
              justify-content: center;
              flex: 0 0 auto;
            }

            :global(.host-edit-toggle-button) {
              width: auto;
            }

            .host-summary-heading {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: var(--spacing-sm);
              flex-wrap: wrap;
            }

            .host-edit-collapsed-summary {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .host-group-summary-list {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .host-readonly-field {
              min-width: 0;
            }

            .host-readonly-card-stack {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
              min-width: 0;
            }

            .host-readonly-card {
              display: flex;
              align-items: center;
              min-height: 42px;
              padding: var(--spacing-sm) var(--spacing-md);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: var(--color-bg-primary);
              color: var(--color-text-primary);
              line-height: 1.45;
              word-break: break-word;
            }

            .host-readonly-card strong {
              color: var(--color-text-primary);
              font-size: 15px;
              line-height: 1.4;
              word-break: break-word;
            }

            .host-readonly-chip-card,
            .host-readonly-meta-card,
            .host-summary-primary-card {
              align-items: flex-start;
            }

            .host-readonly-empty-card {
              color: var(--color-text-muted);
            }

            .host-group-empty-message {
              margin: 0;
            }

            :global(.host-credential-unified-button) {
              width: auto;
            }

            .selected-credential-summary {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .selected-credential-meta {
              color: var(--color-text-secondary);
              font-size: 12px;
              line-height: 1.45;
              width: 100%;
            }

            .credential-warning-card {
              padding: var(--spacing-sm) var(--spacing-md);
              border: 1px solid rgba(245, 158, 11, 0.28);
              border-radius: var(--radius-md);
              background: rgba(245, 158, 11, 0.08);
            }

            .credential-tree-map {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .credential-tree-inventory {
              background: var(--color-bg-primary);
            }

            .credential-tree-title {
              grid-template-columns: auto minmax(0, 1fr) auto;
            }

            .credential-tree-summary-badge {
              justify-self: end;
              padding: 3px 8px;
              border: 1px solid rgba(63, 185, 80, 0.28);
              border-radius: 999px;
              background: var(--color-success-bg);
              color: var(--color-success);
              font-size: 11px;
              font-weight: 800;
              white-space: nowrap;
            }

            .credential-tree-groups {
              max-height: 320px;
              overflow: auto;
              padding-right: var(--spacing-xs);
            }

            .credential-tree-card {
              min-height: 74px;
            }

            .credential-tree-card:disabled {
              cursor: not-allowed;
              opacity: 0.62;
            }

            .credential-tree-badges {
              display: flex;
              flex-wrap: wrap;
              grid-column: 1 / -1;
              gap: var(--spacing-xs);
              margin-top: var(--spacing-xs);
            }

            .credential-detail-badge.warning {
              border-color: rgba(245, 158, 11, 0.32);
              color: var(--color-warning);
              background: rgba(245, 158, 11, 0.08);
            }

            .credential-detail-badge.muted {
              color: var(--color-text-muted);
              background: var(--color-surface);
            }

            .credential-state-badge {
              display: inline-flex;
              align-items: center;
              border-radius: 999px;
              padding: 2px var(--spacing-sm);
              font-size: 11px;
              font-weight: 700;
              color: var(--color-primary);
              border: 1px solid rgba(88, 166, 255, 0.28);
              background: rgba(88, 166, 255, 0.12);
            }

            .host-become-control {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            .host-become-switch {
              display: flex;
              align-items: center;
              gap: var(--spacing-xs);
              cursor: pointer;
              width: 100%;
              min-height: 24px;
            }

            .host-become-switch span:last-child {
              font-size: 12px;
              color: var(--color-text-primary);
              font-weight: 600;
              user-select: none;
            }

            .host-become-switch input {
              accent-color: var(--color-primary);
            }

            .host-readonly-control-card {
              justify-content: flex-start;
            }

            .host-credential-actions {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: var(--spacing-sm);
            }

            .host-credential-action-button {
              width: 100%;
              justify-content: center;
            }

            .host-section-inline-button {
              min-height: 32px;
              padding: 0 var(--spacing-sm);
              font-size: 12px;
              justify-content: center;
            }

            .info-panel-actions {
              display: flex;
              align-items: center;
              justify-content: space-between;
              flex-wrap: wrap;
              gap: var(--spacing-sm);
              padding-top: var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            .info-panel-actions-group {
              display: flex;
              align-items: center;
              gap: var(--spacing-sm);
            }

            .info-panel-actions-group-end {
              margin-left: auto;
            }

            :global(.tree-group-branch.over .group-node) {
              border-color: rgba(88, 166, 255, 0.28);
              background: rgba(88, 166, 255, 0.12);
            }

            :global(.group-dropzone) {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              max-width: 0;
              min-height: 18px;
              overflow: hidden;
              opacity: 0;
              color: var(--color-text-muted);
              border: 0 solid transparent;
              background: rgba(88, 166, 255, 0.08);
              border-radius: 999px;
              padding: 0;
              font-size: 10px;
              font-weight: 600;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              white-space: nowrap;
              transform: translateY(2px);
              transition:
                max-width var(--transition-fast),
                opacity var(--transition-fast),
                padding var(--transition-fast),
                border-color var(--transition-fast),
                transform var(--transition-fast);
            }

            :global(.tree-group-branch:hover .group-dropzone),
            :global(.tree-group-branch:focus-within .group-dropzone),
            :global(.tree-group-branch.over .group-dropzone) {
              max-width: 88px;
              opacity: 1;
              padding: 2px 6px;
              border-width: 1px;
              border-color: rgba(88, 166, 255, 0.22);
              transform: translateY(0);
            }

            :global(.group-dropzone.over) {
              color: var(--color-primary);
              background: rgba(88, 166, 255, 0.16);
              border-color: rgba(88, 166, 255, 0.48);
            }

            :global(.host-row) {
              transition: background var(--transition-fast);
            }

            :global(.host-row.dragging) {
              opacity: 0.82;
            }

            :global(.host-row:nth-child(even) td) {
              background: var(--color-bg-secondary);
            }

            :global(.host-row:hover td) {
              background: var(--color-surface);
            }

            :global(.host-name-cell) {
              display: grid;
              grid-template-columns: auto minmax(0, 1fr);
              align-items: start;
              gap: var(--spacing-sm);
            }

            :global(.drag-handle) {
              border: 1px solid rgba(139, 148, 158, 0.3);
              background: rgba(139, 148, 158, 0.08);
              color: var(--color-text-muted);
              border-radius: var(--radius-sm);
              width: 24px;
              height: 24px;
              padding: 0;
              cursor: grab;
              flex-shrink: 0;
              font-size: 12px;
              letter-spacing: -0.18em;
              line-height: 1;
            }

            :global(.drag-handle.dragging) {
              cursor: grabbing;
              border-color: rgba(88, 166, 255, 0.4);
              color: var(--color-primary);
            }

            :global(.host-identity-button) {
              border: 0;
              background: transparent;
              display: flex;
              width: 100%;
              padding: var(--spacing-xs) 0;
              min-width: 0;
              text-align: left;
              cursor: pointer;
              color: inherit;
              border-radius: var(--radius-sm);
            }

            :global(.host-identity-button:hover .host-identity-name),
            :global(.host-identity-button:focus-visible .host-identity-name) {
              color: var(--color-primary);
            }

            :global(.host-identity) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
              min-width: 0;
            }

            :global(.host-identity-name) {
              display: block;
              max-width: 100%;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              color: var(--color-text-primary);
              font-family: var(--font-mono);
              font-size: 13px;
              line-height: 1.35;
            }

            :global(.host-identity-meta) {
              color: var(--color-text-muted);
              font-size: 12px;
              line-height: 1.4;
            }

            :global(.host-group-tags) {
              display: flex;
              flex-wrap: wrap;
              gap: var(--spacing-xs);
              align-content: flex-start;
            }

            :global(.host-group-tag) {
              padding: 2px var(--spacing-sm);
              line-height: 1.3;
            }

            :global(.host-group-tag-empty) {
              border-style: dashed;
            }

            :global(.host-address) {
              font-size: 13px;
              line-height: 1.45;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
              max-width: 100%;
            }

            :global(.host-status-cell) {
              text-align: center;
              vertical-align: middle;
            }

            :global(.host-status-cell .badge) {
              justify-content: center;
            }

            :global(.tree-info-button) {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              flex: 0 0 24px;
              width: 24px;
              height: 24px;
              min-width: 24px;
              border: 0;
              border-radius: 999px;
              background: transparent;
              color: var(--color-text-muted);
              font-size: 11px;
              font-weight: 700;
              line-height: 1;
              cursor: pointer;
              transition: background var(--transition-fast), color var(--transition-fast);
            }

            :global(.tree-info-button:hover),
            :global(.tree-info-button:focus-visible) {
              background: var(--color-surface);
              color: var(--color-primary);
            }

            :global(.info-panel-shell) {
              position: fixed;
              inset: 0;
              z-index: 120;
              pointer-events: none;
            }

            :global(.info-panel-backdrop) {
              position: absolute;
              inset: 0;
              background: var(--color-bg-primary);
              opacity: 0.82;
              pointer-events: none;
            }

            :global(.info-panel) {
              position: absolute;
              top: 0;
              right: 0;
              width: min(420px, calc(100vw - var(--sidebar-width)));
              height: 100vh;
              padding: var(--spacing-xl);
              background: var(--color-bg-secondary);
              border-left: 1px solid var(--color-border);
              box-shadow: var(--shadow-lg);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-lg);
              pointer-events: auto;
            }

            :global(.info-panel-body),
            :global(.info-panel-copy),
            :global(.info-section) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            :global(.info-panel-body) {
              flex: 1;
              min-height: 0;
              overflow: auto;
            }

            :global(.info-panel-title) {
              margin-top: var(--spacing-xs);
              font-size: 22px;
            }

            :global(.info-metric-grid) {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: var(--spacing-sm);
            }

            :global(.info-metric-card) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
              padding: var(--spacing-md);
              border-radius: var(--radius-md);
              border: 1px solid var(--color-border);
              background: var(--color-surface);
            }

            :global(.info-metric-card span),
            :global(.info-section h3) {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            :global(.info-form-grid) {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: var(--spacing-sm);
            }

            :global(.info-form-field) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
            }

            :global(.info-form-field span) {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            :global(.host-become-toggle-field) {
              justify-content: flex-end;
            }

            :global(.host-become-toggle) {
              min-height: 42px;
            }

            :global(.info-inline-message) {
              font-size: 12px;
              color: var(--color-text-muted);
            }

            :global(.info-inline-message.error) {
              color: var(--color-error);
            }

            :global(.info-panel-actions) {
              display: flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-sm);
              padding-top: var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            /* Credential management styles */
            :global(.credential-manager-header) {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: var(--spacing-sm);
            }

            :global(.credential-search-bar) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-xs);
              padding: var(--spacing-sm);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: rgba(88, 166, 255, 0.04);
            }

            :global(.credential-search-label),
            :global(.credential-search-summary) {
              color: var(--color-text-muted);
              font-size: 12px;
            }

            :global(.credential-search-control) {
              display: flex;
              align-items: center;
              gap: var(--spacing-xs);
            }

            :global(.credential-search-control .form-input) {
              min-width: 0;
              flex: 1;
            }

            :global(.credential-editor-form) {
              padding: var(--spacing-md);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: var(--color-surface);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            :global(.credential-editor-actions) {
              display: flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-sm);
              padding-top: var(--spacing-sm);
              border-top: 1px solid var(--color-border);
            }

            :global(.credential-list) {
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            :global(.credential-card) {
              padding: var(--spacing-md);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-md);
              background: var(--color-surface);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-sm);
            }

            :global(.credential-card.selected) {
              border-color: rgba(88, 166, 255, 0.42);
              background: rgba(88, 166, 255, 0.1);
            }

            :global(.credential-card-selectable) {
              width: 100%;
              color: inherit;
              text-align: left;
              cursor: pointer;
            }

            :global(.credential-card-selectable:hover) {
              border-color: rgba(88, 166, 255, 0.38);
            }

            :global(.credential-select-state) {
              padding: 3px 8px;
              border: 1px solid rgba(88, 166, 255, 0.3);
              border-radius: 999px;
              background: rgba(88, 166, 255, 0.12);
              color: var(--color-primary);
              font-size: 11px;
              font-weight: 800;
              white-space: nowrap;
            }

            :global(.credential-card-header) {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: var(--spacing-sm);
            }

            :global(.credential-card-actions) {
              display: flex;
              align-items: center;
              gap: var(--spacing-xs);
            }

            :global(.credential-card-details) {
              display: flex;
              align-items: center;
              gap: var(--spacing-xs);
              flex-wrap: wrap;
            }

            :global(.credential-overlay-shell) {
              position: fixed;
              inset: 0;
              z-index: 190;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: var(--spacing-xl);
            }

            :global(.credential-overlay-backdrop) {
              position: absolute;
              inset: 0;
              border: 0;
              background:
                radial-gradient(circle at top, rgba(88, 166, 255, 0.14), transparent 40%),
                rgba(1, 4, 9, 0.72);
              cursor: pointer;
            }

            :global(.credential-overlay-panel) {
              position: relative;
              z-index: 1;
              width: min(760px, calc(100vw - (var(--spacing-xl) * 2)));
              max-height: calc(100vh - (var(--spacing-xl) * 2));
              padding: var(--spacing-xl);
              border: 1px solid var(--color-border);
              border-radius: var(--radius-lg);
              background:
                linear-gradient(180deg, rgba(88, 166, 255, 0.08), transparent 24%),
                var(--color-bg-secondary);
              box-shadow: var(--shadow-lg);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-lg);
            }

            :global(.credential-overlay-header),
            :global(.credential-overlay-actions) {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: var(--spacing-sm);
            }

            :global(.credential-overlay-title) {
              margin-top: var(--spacing-xs);
              font-size: 22px;
            }

            :global(.credential-overlay-body) {
              flex: 1;
              min-height: 0;
              overflow: auto;
            }

            :global(.credential-overlay-actions) {
              justify-content: flex-end;
              padding-top: var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            :global(.credential-detail-badge) {
              display: inline-flex;
              align-items: center;
              padding: 2px var(--spacing-sm);
              border-radius: 999px;
              border: 1px solid var(--color-border);
              background: var(--color-bg-secondary);
              color: var(--color-text-secondary);
              font-size: 11px;
            }

            :global(.credential-detail-text) {
              font-size: 13px;
              color: var(--color-text-primary);
            }

            :global(.credential-loading),
            :global(.credential-empty) {
              padding: var(--spacing-lg);
              text-align: center;
              border: 1px dashed var(--color-border);
              border-radius: var(--radius-md);
              color: var(--color-text-muted);
              font-size: 13px;
            }

            @media (max-width: 1400px) {
              .workspace-grid {
                grid-template-columns: 1fr;
                height: auto;
                min-height: 0;
                overflow: visible;
              }

              .workspace-tree-pane,
              .workspace-host-pane {
                max-height: none;
              }
            }

            @media (max-width: 920px) {
              .feedback-notice {
                left: 50%;
                width: min(440px, calc(100vw - var(--spacing-xl)));
              }

              .search-controls {
                align-items: center;
              }

              .host-header-actions,
              .pane-actions,
              .discard-confirm-actions,
              .info-panel-actions,
              .host-toolbar {
                justify-content: flex-start;
              }

              .host-search-panel {
                min-width: 100%;
              }

              .info-metric-grid {
                grid-template-columns: 1fr;
              }

              .info-form-grid {
                grid-template-columns: 1fr;
              }

              .info-panel {
                width: 100vw;
              }

              :global(.credential-overlay-shell) {
                padding: var(--spacing-md);
              }

              :global(.credential-overlay-panel) {
                width: min(100vw, calc(100vw - (var(--spacing-md) * 2)));
                max-height: calc(100vh - (var(--spacing-md) * 2));
                padding: var(--spacing-lg);
              }

              .discard-confirm-shell {
                padding: var(--spacing-md);
              }

              .discard-confirm-copy {
                grid-template-columns: 1fr;
              }

              :global(.info-panel) {
                width: 100vw;
              }
            }
          `}</style>

          <style jsx global>{`
            .discard-confirm-shell {
              position: fixed;
              inset: 0;
              z-index: 210;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: var(--spacing-xl);
            }

            .discard-confirm-backdrop {
              position: absolute;
              inset: 0;
              border: 0;
              background:
                radial-gradient(circle at top, rgba(88, 166, 255, 0.12), transparent 42%),
                rgba(1, 4, 9, 0.76);
              cursor: pointer;
            }

            .discard-confirm-dialog {
              position: relative;
              z-index: 1;
              width: min(440px, calc(100vw - (var(--spacing-xl) * 2)));
              padding: var(--spacing-lg);
              border: 1px solid rgba(248, 81, 73, 0.24);
              border-radius: var(--radius-lg);
              background:
                linear-gradient(180deg, rgba(248, 81, 73, 0.08), transparent 28%),
                var(--color-bg-secondary);
              box-shadow: 0 28px 64px rgba(1, 4, 9, 0.42);
              display: flex;
              flex-direction: column;
              gap: var(--spacing-md);
            }

            .discard-confirm-kicker {
              display: inline-flex;
              align-items: center;
              width: fit-content;
              padding: 2px var(--spacing-xs);
              border-radius: 999px;
              border: 1px solid rgba(248, 81, 73, 0.24);
              background: rgba(248, 81, 73, 0.12);
              color: var(--color-primary);
              font-size: 11px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
            }

            .discard-confirm-kicker.danger {
              border-color: rgba(248, 81, 73, 0.24);
              background: rgba(248, 81, 73, 0.12);
              color: var(--color-danger, #f85149);
            }

            .discard-confirm-copy {
              display: grid;
              grid-template-columns: auto minmax(0, 1fr);
              align-items: start;
              gap: var(--spacing-md);
            }

            .discard-confirm-accent {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: calc(var(--spacing-xl) + var(--spacing-sm));
              min-width: calc(var(--spacing-xl) + var(--spacing-sm));
              height: calc(var(--spacing-xl) + var(--spacing-sm));
              border-radius: var(--radius-md);
              background: rgba(88, 166, 255, 0.16);
              color: var(--color-primary);
              font-size: 20px;
              font-weight: 700;
              line-height: 1;
            }

            .discard-confirm-accent.danger {
              background: rgba(248, 81, 73, 0.14);
              color: var(--color-danger, #f85149);
            }

            .discard-confirm-title {
              margin: 0;
              font-size: 20px;
              color: var(--color-text-primary);
            }

            .discard-confirm-message {
              margin: var(--spacing-xs) 0 0;
              font-size: 13px;
              line-height: 1.6;
              color: var(--color-text-secondary);
            }

            .discard-confirm-actions {
              display: flex;
              align-items: center;
              justify-content: flex-end;
              gap: var(--spacing-sm);
              padding-top: var(--spacing-md);
              border-top: 1px solid var(--color-border);
            }

            @media (max-width: 720px) {
              .discard-confirm-shell {
                padding: var(--spacing-md);
              }

              .discard-confirm-copy {
                grid-template-columns: 1fr;
              }

              .discard-confirm-actions {
                justify-content: flex-start;
              }
            }
          `}</style>
        </div>
      </main>
    </div>
  );
}
