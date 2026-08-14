import { expect, test, type Page } from "@playwright/test";

type InventoryDetail = {
  id: string;
  name: string;
  tags?: string[];
  revision: number;
  source_type: string;
  filename: string;
  host_count: number;
  group_count: number;
  protocol_mix: Record<string, number>;
  connection_summary: Record<string, number>;
  groups: Array<{
    name: string;
    tags?: string[];
    group_vars?: Record<string, string>;
    host_keys?: string[];
    hosts: Array<Record<string, unknown>>;
  }>;
  hosts: Array<{
    key: string;
    name: string;
    address: string;
    connection_type: string;
    port: number;
    login_credential_ref?: string;
    become_enabled?: boolean;
    become_user?: string | null;
    become_credential_ref?: string | null;
    host_vars?: Record<string, string>;
  }>;
  memberships: Array<{ group_name: string; host_key: string }>;
  rendered_content: string;
  created_at: string;
  updated_at: string;
};

type InventoryPayload = {
  name: string;
  tags: string[];
  groups: Array<{
    name: string;
    tags: string[];
    group_vars?: Record<string, string>;
    host_keys?: string[];
    hosts?: Array<Record<string, unknown>>;
  }>;
  hosts?: Array<{
    key: string;
    name: string;
    address: string;
    connection_type?: string;
    port?: number;
    login_credential_ref?: string;
    become_enabled?: boolean;
    become_user?: string;
    become_credential_ref?: string;
    host_vars?: Record<string, string>;
  }>;
  memberships?: Array<{ group_name: string; host_key: string }>;
};

type CredentialMock = {
  id?: string;
  ref?: string;
  name: string;
  credential_type: string;
  username: string;
  has_secret: boolean;
  has_become_secret: boolean;
  become_username?: string | null;
  last_rotated_at: string | null;
};

type MockState = {
  inventories: InventoryDetail[];
  hostAssets: Array<{
    id: string;
    key: string;
    name: string;
    address: string;
    connection_type: string;
    port: number;
    host_vars?: Record<string, string>;
    memberships: Array<{ inventory_id: string; inventory_name: string; group_name: string }>;
  }>;
  postBodies: InventoryPayload[];
  putBodies: Array<{ id: string; body: InventoryPayload }>;
  deleteIds: string[];
  hostDeleteIds: Array<{ inventoryId: string; hostKey: string }>;
  hostAssetDeleteIds: string[];
  credentials: CredentialMock[];
  credentialPosts: Array<{ body: Record<string, unknown> }>;
  credentialPuts: Array<{ credentialId: string; body: Record<string, unknown> }>;
  credentialDeleteIds: string[];
};

type MockBehavior = {
  failCreateMessage?: string;
  failUpdateMessagesById?: Record<string, string>;
};

function getCredentialRef(cred: { id?: string; ref?: string }): string {
  return cred.ref ?? cred.id ?? "";
}

const inventorySelectors = {
  sidebarLink: '[data-testid="sidebar-inventories-link"]',
  feedbackNotice: ".feedback-notice",
} as const;

function makeInventoryDetail({
  id,
  name,
  tags = [],
  sourceType = "project-alpha",
  filename = `inventories/${id}.yml`,
  groups = [],
  hosts = [],
  memberships = [],
}: {
  id: string;
  name: string;
  tags?: string[];
  sourceType?: string;
  filename?: string;
  groups?: InventoryDetail["groups"];
  hosts?: InventoryDetail["hosts"];
  memberships?: InventoryDetail["memberships"];
}): InventoryDetail {
  return {
    id,
    name,
    tags,
    revision: 1,
    source_type: sourceType,
    filename,
    host_count: hosts.length,
    group_count: groups.length,
    protocol_mix: {},
    connection_summary: {},
    groups,
    hosts,
    memberships,
    rendered_content: `# ${name}`,
    created_at: "2026-05-20T00:00:00Z",
    updated_at: "2026-05-20T00:00:00Z",
  };
}

function toInventoryListItem(detail: InventoryDetail) {
  return {
    id: detail.id,
    name: detail.name,
    tags: detail.tags ?? [],
    revision: detail.revision,
    source_type: detail.source_type,
    filename: detail.filename,
    host_count: detail.hosts.length,
    group_count: detail.groups.length,
    protocol_mix: detail.protocol_mix,
    connection_summary: detail.connection_summary,
    groups: detail.groups,
    rendered_content: detail.rendered_content,
    created_at: detail.created_at,
    updated_at: detail.updated_at,
  };
}

function detailFromPayload(id: string, body: InventoryPayload, existing?: InventoryDetail): InventoryDetail {
  const hosts = (body.hosts ?? []).map((host) => ({
    key: host.key,
    name: host.name,
    address: host.address,
    connection_type: host.connection_type ?? "ssh",
    port: host.port ?? 22,
    login_credential_ref: host.login_credential_ref,
    become_enabled: host.become_enabled,
    become_user: host.become_user,
    become_credential_ref: host.become_credential_ref,
    host_vars: host.host_vars ?? {},
  }));

  return {
    id,
    name: body.name,
    tags: body.tags,
    revision: (existing?.revision ?? 0) + 1,
    source_type: existing?.source_type ?? "project-alpha",
    filename: existing?.filename ?? `inventories/${id}.yml`,
    host_count: hosts.length,
    group_count: body.groups.length,
    protocol_mix: {},
    connection_summary: {},
    groups: body.groups.map((group) => ({
      name: group.name,
      tags: group.tags,
      group_vars: group.group_vars ?? {},
      host_keys: group.host_keys ?? [],
      hosts: group.hosts ?? [],
    })),
    hosts,
    memberships: body.memberships ?? [],
    rendered_content: `# ${body.name}`,
    created_at: existing?.created_at ?? "2026-05-20T00:00:00Z",
    updated_at: "2026-05-20T00:00:00Z",
  };
}

function createState(inventories: InventoryDetail[]): MockState {
  const hostAssets = inventories.flatMap((inventory) =>
    inventory.hosts.map((host) => ({
      id: `${inventory.id}:${host.key}`,
      key: host.key,
      name: host.name,
      address: host.address,
      connection_type: host.connection_type,
      port: host.port,
      host_vars: host.host_vars,
      memberships: inventory.memberships
        .filter((membership) => membership.host_key === host.key)
        .map((membership) => ({
          inventory_id: inventory.id,
          inventory_name: inventory.name,
          group_name: membership.group_name,
        })),
    }))
  );

  return {
    inventories,
    hostAssets,
    postBodies: [],
    putBodies: [],
    deleteIds: [],
    hostDeleteIds: [],
    hostAssetDeleteIds: [],
    credentials: [],
    credentialPosts: [],
    credentialPuts: [],
    credentialDeleteIds: [],
  };
}

async function installInventoryApiMocks(page: Page, state: MockState, behavior: MockBehavior = {}) {
  await page.route("**/api/hosts**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;

    if (path === "/api/hosts" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.hostAssets),
      });
      return;
    }

    const hostAssetMatch = path.match(/^\/api\/hosts\/([^/]+)$/);
    if (hostAssetMatch) {
      const hostId = decodeURIComponent(hostAssetMatch[1] ?? "");
      const hostAsset = state.hostAssets.find((host) => host.id === hostId);

      if (!hostAsset) {
        await route.fulfill({ status: 404, body: "not found" });
        return;
      }

      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(hostAsset),
        });
        return;
      }

      if (method === "PATCH") {
        const body = request.postDataJSON() as Partial<InventoryDetail["hosts"][number]>;
        const updatedHostAsset = {
          ...hostAsset,
          ...body,
          key: body.key ?? hostAsset.key,
          name: body.name ?? hostAsset.name,
          address: body.address ?? hostAsset.address,
          connection_type: body.connection_type ?? hostAsset.connection_type,
          port: body.port ?? hostAsset.port,
          host_vars: body.host_vars ?? hostAsset.host_vars,
        };
        state.hostAssets = state.hostAssets.map((host) =>
          host.id === hostId ? updatedHostAsset : host
        );
        state.inventories = state.inventories.map((inventory) => ({
          ...inventory,
          hosts: inventory.hosts.map((host) =>
            (host.key ?? host.name) === hostAsset.key
              ? {
                  ...host,
                  key: updatedHostAsset.key,
                  name: updatedHostAsset.name,
                  address: updatedHostAsset.address,
                  connection_type: updatedHostAsset.connection_type,
                  port: updatedHostAsset.port,
                  host_vars: updatedHostAsset.host_vars,
                }
              : host
          ),
          groups: inventory.groups.map((group) => ({
            ...group,
            hosts: (group.hosts ?? []).map((host) =>
              (host.key ?? host.name) === hostAsset.key
                ? {
                    ...host,
                    key: updatedHostAsset.key,
                    name: updatedHostAsset.name,
                    address: updatedHostAsset.address,
                    connection_type: updatedHostAsset.connection_type,
                    port: updatedHostAsset.port,
                    host_vars: updatedHostAsset.host_vars,
                  }
                : host
            ),
          })),
        }));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(updatedHostAsset),
        });
        return;
      }

      if (method === "DELETE") {
        state.hostAssetDeleteIds.push(hostId);
        state.hostAssets = state.hostAssets.filter((host) => host.id !== hostId);
        state.inventories = state.inventories.map((inventory) => ({
          ...inventory,
          hosts: inventory.hosts.filter((host) => (host.key ?? host.name) !== hostAsset.key),
          memberships: inventory.memberships.filter(
            (membership) => membership.host_key !== hostAsset.key
          ),
          groups: inventory.groups.map((group) => ({
            ...group,
            host_keys: (group.host_keys ?? []).filter((key) => key !== hostAsset.key),
            hosts: (group.hosts ?? []).filter(
              (host) => (host.key ?? host.name) !== hostAsset.key
            ),
          })),
        }));
        await route.fulfill({ status: 204, body: "" });
        return;
      }

      await route.fulfill({ status: 405, body: "method not allowed" });
      return;
    }

    await route.fulfill({ status: 404, body: "not found" });
  });

  await page.route("**/api/credentials**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;

    if (path === "/api/credentials") {
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(state.credentials),
        });
        return;
      }

      if (method === "POST") {
        const body = request.postDataJSON() as Record<string, unknown>;
        const createdId = `cred-${state.credentials.length + 1}`;
        const created: CredentialMock = {
          ref: createdId,
          name: (body.name as string) ?? "",
          credential_type: (body.credential_type as string) ?? "ssh_password",
          username: (body.username as string) ?? "",
          has_secret: Boolean(body.secret),
          has_become_secret: Boolean(body.become_secret),
          become_username: (body.become_username as string) ?? null,
          last_rotated_at: new Date().toISOString(),
        };
        state.credentials = [...state.credentials, created];
        state.credentialPosts.push({ body });
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(created),
        });
        return;
      }

      await route.fulfill({ status: 405, body: "method not allowed" });
      return;
    }

    const credentialDetailMatch = path.match(/^\/api\/credentials\/(.+)$/);
    if (credentialDetailMatch) {
      const credId = decodeURIComponent(credentialDetailMatch[1] ?? "");

      if (method === "PUT") {
        const body = request.postDataJSON() as Record<string, unknown>;
        state.credentials = state.credentials.map((c) =>
          getCredentialRef(c) === credId
            ? {
                ...c,
                name: (body.name as string) ?? c.name,
                username: (body.username as string) ?? c.username,
                become_username:
                  body.clear_become_secret
                    ? null
                    : ((body.become_username as string) ?? c.become_username),
                has_secret: body.secret ? true : c.has_secret,
                has_become_secret: body.become_secret
                  ? true
                  : body.clear_become_secret
                    ? false
                    : c.has_become_secret,
              }
            : c
        );
        state.credentialPuts.push({ credentialId: credId, body });
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(state.credentials.find((c) => getCredentialRef(c) === credId) ?? body),
        });
        return;
      }

      if (method === "DELETE") {
        state.credentials = state.credentials.filter((c) => getCredentialRef(c) !== credId);
        state.credentialDeleteIds.push(credId);
        await route.fulfill({ status: 204, body: "" });
        return;
      }
    }
  });

  await page.route("**/api/inventories**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;

    if (path === "/api/inventories" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.inventories.map(toInventoryListItem)),
      });
      return;
    }

    if (path === "/api/inventories" && method === "POST") {
      const body = request.postDataJSON() as InventoryPayload;
      state.postBodies.push(body);

      if (behavior.failCreateMessage) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: behavior.failCreateMessage }),
        });
        return;
      }

      const createdId = `inventory-${state.inventories.length + 1}`;
      const created = detailFromPayload(createdId, body, makeInventoryDetail({
        id: createdId,
        name: body.name,
        sourceType: "v2-api",
        filename: `api/inventories/${createdId}`,
      }));
      state.inventories.push(created);
      state.hostAssets = createState(state.inventories).hostAssets;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(created),
      });
      return;
    }

    // Backward-compatible inventory credential routes.
    const credentialsListMatch = path.match(/^\/api\/inventories\/([^/]+)\/credentials$/);
    const credentialsDetailMatch = path.match(/^\/api\/inventories\/([^/]+)\/credentials\/(.+)$/);

    if (credentialsListMatch) {
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(state.credentials),
        });
        return;
      }

      if (method === "POST") {
        const body = request.postDataJSON() as Record<string, unknown>;
        const createdId = `cred-${state.credentials.length + 1}`;
        const created: CredentialMock = {
          ref: createdId,
          name: (body.name as string) ?? "",
          credential_type: (body.credential_type as string) ?? "ssh_password",
          username: (body.username as string) ?? "",
          has_secret: Boolean(body.secret),
          has_become_secret: Boolean(body.become_secret),
          become_username: (body.become_username as string) ?? null,
          last_rotated_at: new Date().toISOString(),
        };
        state.credentials = [...state.credentials, created];
        state.credentialPosts.push({ body });
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(created),
        });
        return;
      }

      await route.fulfill({ status: 405, body: "method not allowed" });
      return;
    }

    if (credentialsDetailMatch) {
      const credId = decodeURIComponent(credentialsDetailMatch[2] ?? "");

      if (method === "PUT") {
        const body = request.postDataJSON() as Record<string, unknown>;
        state.credentials = state.credentials.map((c) =>
          getCredentialRef(c) === credId
            ? {
                ...c,
                name: (body.name as string) ?? c.name,
                username: (body.username as string) ?? c.username,
                become_username:
                  body.clear_become_secret
                    ? null
                    : ((body.become_username as string) ?? c.become_username),
                has_secret: body.secret ? true : c.has_secret,
                has_become_secret: body.become_secret
                  ? true
                  : body.clear_become_secret
                    ? false
                    : c.has_become_secret,
              }
            : c
        );
        state.credentialPuts.push({ credentialId: credId, body });
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
        return;
      }

      if (method === "DELETE") {
        state.credentials = state.credentials.filter((c) => getCredentialRef(c) !== credId);
        state.credentialDeleteIds.push(credId);
        await route.fulfill({ status: 204, body: "" });
        return;
      }

      await route.fulfill({ status: 405, body: "method not allowed" });
      return;
    }

    const hostDeleteMatch = path.match(/^\/api\/inventories\/([^/]+)\/hosts\/([^/]+)$/);
    if (hostDeleteMatch) {
      const inventoryId = decodeURIComponent(hostDeleteMatch[1] ?? "");
      const hostKey = decodeURIComponent(hostDeleteMatch[2] ?? "");
      if (method !== "DELETE") {
        await route.fulfill({ status: 405, body: "method not allowed" });
        return;
      }

      state.hostDeleteIds.push({ inventoryId, hostKey });
      state.inventories = state.inventories.map((inventory) =>
        inventory.id === inventoryId
          ? {
              ...inventory,
              hosts: inventory.hosts.filter((host) => (host.key ?? host.name) !== hostKey),
              memberships: inventory.memberships.filter((membership) => membership.host_key !== hostKey),
              groups: inventory.groups.map((group) => ({
                ...group,
                host_keys: (group.host_keys ?? []).filter((key) => key !== hostKey),
                hosts: (group.hosts ?? []).filter((host) => (host.key ?? host.name) !== hostKey),
              })),
            }
          : inventory
      );
      state.hostAssets = state.hostAssets.filter(
        (host) => !(host.key === hostKey && host.memberships.some((membership) => membership.inventory_id === inventoryId))
      );
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    const hostAttachMatch = path.match(/^\/api\/inventories\/([^/]+)\/hosts$/);
    if (hostAttachMatch) {
      const inventoryId = decodeURIComponent(hostAttachMatch[1] ?? "");

      if (method !== "POST") {
        await route.fulfill({ status: 405, body: "method not allowed" });
        return;
      }

      const body = request.postDataJSON() as { host_id?: string; group_name?: string };
      const groupName = body.group_name;
      const hostAsset = state.hostAssets.find((host) => host.id === body.host_id);
      const inventory = state.inventories.find((item) => item.id === inventoryId);
      const group = inventory?.groups.find((item) => item.name === groupName);

      if (!hostAsset || !inventory || !group || !groupName) {
        await route.fulfill({ status: 404, body: "not found" });
        return;
      }

      const targetGroupName = groupName;

      if (
        hostAsset.memberships.some(
          (membership) =>
            membership.inventory_id === inventoryId && membership.group_name === targetGroupName
        )
      ) {
        await route.fulfill({ status: 409, body: JSON.stringify({ detail: "already assigned" }) });
        return;
      }

      const nextHost = {
        key: hostAsset.key,
        name: hostAsset.name,
        address: hostAsset.address,
        connection_type: hostAsset.connection_type,
        port: hostAsset.port,
        host_vars: hostAsset.host_vars ?? {},
      };
      const updatedInventory: InventoryDetail = {
        ...inventory,
        hosts: inventory.hosts.some((host) => (host.key ?? host.name) === hostAsset.key)
          ? inventory.hosts
          : [...inventory.hosts, nextHost],
        memberships: [
          ...inventory.memberships,
          { group_name: targetGroupName, host_key: hostAsset.key },
        ],
        groups: inventory.groups.map((item) =>
          item.name === targetGroupName
            ? {
                ...item,
                host_keys: [...new Set([...(item.host_keys ?? []), hostAsset.key])],
                hosts: (item.hosts ?? []).some(
                  (host) => (host.key ?? host.name) === hostAsset.key
                )
                  ? item.hosts
                  : [...(item.hosts ?? []), nextHost],
              }
            : item
        ),
      };

      state.inventories = state.inventories.map((item) =>
        item.id === inventoryId ? updatedInventory : item
      );
      state.hostAssets = state.hostAssets.map((host) =>
        host.id === hostAsset.id
          ? {
              ...host,
              memberships: [
                ...host.memberships,
                {
                  inventory_id: inventoryId,
                  inventory_name: inventory.name,
                  group_name: targetGroupName,
                },
              ],
            }
          : host
      );

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(updatedInventory),
      });
      return;
    }

    const detailMatch = path.match(/^\/api\/inventories\/([^/]+)$/);
    if (!detailMatch) {
      await route.fulfill({ status: 404, body: "not found" });
      return;
    }

    const inventoryId = decodeURIComponent(detailMatch[1] ?? "");
    const current = state.inventories.find((item) => item.id === inventoryId);

    if (method === "GET") {
      if (!current) {
        await route.fulfill({ status: 404, body: "not found" });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(current),
      });
      return;
    }

    if (method === "PUT") {
      const body = request.postDataJSON() as InventoryPayload;
      state.putBodies.push({ id: inventoryId, body });

      const failMessage = behavior.failUpdateMessagesById?.[inventoryId];
      if (failMessage) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: failMessage }),
        });
        return;
      }

      const updated = detailFromPayload(inventoryId, body, current);
      state.inventories = state.inventories.map((item) =>
        item.id === inventoryId ? updated : item
      );
      state.hostAssets = createState(state.inventories).hostAssets;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(updated),
      });
      return;
    }

    if (method === "DELETE") {
      state.deleteIds.push(inventoryId);
      state.inventories = state.inventories.filter((item) => item.id !== inventoryId);
      state.hostAssets = state.hostAssets.map((host) => ({
        ...host,
        memberships: host.memberships.filter((membership) => membership.inventory_id !== inventoryId),
      }));
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    await route.fulfill({ status: 405, body: "method not allowed" });
  });
}

function getInfoPanel(page: Page) {
  return page.getByTestId("inventory-info-panel");
}

function getCredentialOverlay(page: Page) {
  return page.getByTestId("credential-manager-overlay");
}

function getDiscardConfirm(page: Page, title: string) {
  return page.getByRole("alertdialog", { name: title });
}

function truncateCredentialRef(value: string, maxLength = 36): string {
  return value.length <= maxLength
    ? value
    : `${value.slice(0, 20)}…${value.slice(-10)}`;
}

async function openInventoryWorkspaceFromSidebar(page: Page) {
  await page.goto("/");
  await page.click(inventorySelectors.sidebarLink);
  await expect(page).toHaveURL(/\/inventories$/);
  await expect(page.getByText("인벤토리 워크스페이스")).toBeVisible();
}

async function openInventoryWorkspace(page: Page) {
  await page.goto("/inventories");
  await expect(page.getByText("인벤토리 워크스페이스")).toBeVisible();
}

test.describe("인벤토리 워크스페이스 핵심 CRUD 계약", () => {
  test("새 인벤토리 초안은 저장할 때만 생성되고 실제 ID로 후속 동작을 remap한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "seeded-core" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspaceFromSidebar(page);

    await expect(page.getByRole("button", { name: "seeded-core 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 인벤토리" }).click();

    await expect.poll(() => state.postBodies.length).toBe(0);

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("인벤토리 편집");
    await expect(dialog).toContainText("새 인벤토리 2");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "새 인벤토리 초안을 만들었습니다. 저장을 눌러 서버에 반영하세요."
    );
    await expect(page.getByRole("button", { name: "새 인벤토리 2 정보 열기" })).toBeVisible();

    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.postBodies.length).toBe(1);
    expect(state.postBodies[0]).toMatchObject({
      name: "새 인벤토리 2",
      groups: [],
      hosts: [],
      memberships: [],
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 '새 인벤토리 2' 정보를 저장했습니다."
    );
    await expect(dialog).toHaveCount(0);

    await page.getByRole("button", { name: "새 인벤토리 2 정보 열기" }).click();
    const reopenedDialog = getInfoPanel(page);
    await expect(reopenedDialog).toContainText("새 인벤토리 2");

    await reopenedDialog.getByRole("button", { name: "삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "인벤토리 삭제");
    await expect(deleteConfirm).toContainText(
      "'새 인벤토리 2' 인벤토리를 삭제하시겠습니까? 그룹과 연결은 함께 삭제되지만 호스트 자산은 보존됩니다."
    );
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.deleteIds).toEqual(["inventory-2"]);
    await expect(page.getByRole("button", { name: "새 인벤토리 2 정보 열기" })).toHaveCount(0);
  });

  test("미저장 인벤토리 초안은 닫기 확인 후 폐기한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-draft-close-base" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(
      page.getByRole("button", { name: "inventory-draft-close-base 정보 열기" })
    ).toBeVisible();
    await page.getByRole("button", { name: "+ 인벤토리" }).click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("새 인벤토리 2");

    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "인벤토리 초안 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 인벤토리 초안이 있습니다.");
    await discardConfirm.getByRole("button", { name: "초안 버리기" }).click();

    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "새 인벤토리 2 정보 열기" })).toHaveCount(0);
    await expect.poll(() => state.postBodies.length).toBe(0);
  });

  test("미저장 인벤토리 초안에서 닫기 확인 UI는 깜빡이지 않고 취소할 때 유지된다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-close-confirm-stability" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "+ 인벤토리" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("새 인벤토리 2");
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "인벤토리 초안 폐기");
    await expect(discardConfirm).toBeVisible();
    await expect(discardConfirm).toContainText("저장하지 않은 인벤토리 초안이 있습니다.");
    await page.waitForTimeout(300);
    await expect(discardConfirm).toBeVisible();

    await discardConfirm.getByRole("button", { name: "계속 편집" }).click();

    await expect(discardConfirm).toHaveCount(0);
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("새 인벤토리 2");
    await expect(page.getByRole("button", { name: "새 인벤토리 2 정보 열기" })).toBeVisible();
    await expect.poll(() => state.postBodies.length).toBe(0);
  });

  test("인벤토리 저장은 필수 입력이 비면 막는다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-validation" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "inventory-validation 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("이름").fill("");
    await dialog.getByLabel("파일 경로").fill("");
    await dialog.getByLabel("프로젝트").fill("");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(0);
    await expect(dialog).toContainText("inventory-validation");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 이름, 파일 경로, 프로젝트를 입력하세요."
    );
  });

  test("인벤토리 저장 API 실패 시 편집 패널을 유지한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-save-api-failure" }),
    ]);
    await installInventoryApiMocks(page, state, {
      failUpdateMessagesById: { "inventory-1": "inventory save exploded" },
    });

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "inventory-save-api-failure 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("이름").fill("inventory-save-api-failure-updated");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    await expect(dialog).toContainText("inventory-save-api-failure");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "저장하지 못했습니다: inventory save exploded"
    );
  });

  test("인벤토리 이름을 저장한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-before-save" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "inventory-before-save 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("이름").fill("inventory-after-save");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]).toMatchObject({
      id: "inventory-1",
      body: { name: "inventory-after-save" },
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 'inventory-after-save' 정보를 저장했습니다."
    );
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "inventory-after-save 정보 열기" })).toBeVisible();
  });

  test("인벤토리를 삭제한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "inventory-delete-target" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "inventory-delete-target 정보 열기" }).click();
    await getInfoPanel(page).getByRole("button", { name: "삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "인벤토리 삭제");
    await expect(deleteConfirm).toContainText(
      "'inventory-delete-target' 인벤토리를 삭제하시겠습니까? 그룹과 연결은 함께 삭제되지만 호스트 자산은 보존됩니다."
    );
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.deleteIds).toEqual(["inventory-1"]);
    await expect(page.getByRole("button", { name: "inventory-delete-target 정보 열기" })).toHaveCount(0);
    await expect(page.getByText("등록된 인벤토리가 없습니다.")).toBeVisible();
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 'inventory-delete-target'를 삭제했습니다. 그룹과 연결은 제거되고 호스트 자산은 보존됩니다."
    );
  });

  test("선택한 인벤토리를 일괄 삭제하고 호스트 자산은 보존한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "delete-inventory-a",
        groups: [{ name: "web", host_keys: ["host-a"], hosts: [] }],
        hosts: [
          {
            key: "host-a",
            name: "host-a",
            address: "10.0.1.10",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [{ group_name: "web", host_key: "host-a" }],
      }),
      makeInventoryDetail({
        id: "inventory-2",
        name: "delete-inventory-b",
        groups: [{ name: "db", host_keys: ["host-b"], hosts: [] }],
        hosts: [
          {
            key: "host-b",
            name: "host-b",
            address: "10.0.1.11",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [{ group_name: "db", host_key: "host-b" }],
      }),
      makeInventoryDetail({ id: "inventory-3", name: "keep-inventory" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByLabel("delete-inventory-a 인벤토리 선택").check();
    await page.getByLabel("delete-inventory-b 인벤토리 선택").check();
    await page.getByRole("button", { name: "선택 인벤토리 2개 삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "인벤토리 일괄 삭제");
    await expect(deleteConfirm).toContainText("인벤토리 2개와 그룹 2개를 삭제합니다.");
    await expect(deleteConfirm).toContainText("호스트 2개는 삭제되지 않고 자산으로 보존됩니다.");
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.deleteIds).toEqual(["inventory-1", "inventory-2"]);
    await expect(page.getByRole("button", { name: "delete-inventory-a 정보 열기" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "delete-inventory-b 정보 열기" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "keep-inventory 정보 열기" })).toBeVisible();
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 2개를 삭제했습니다. 호스트 자산은 보존됩니다."
    );
    await expect.poll(() =>
      state.hostAssets
        .filter((host) => ["host-a", "host-b"].includes(host.key))
        .every((host) => host.memberships.length === 0)
    ).toBe(true);
  });

  test("전체 보기에서 orphan host asset도 표시한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "attached-hosts",
        groups: [{ name: "web", host_keys: ["host-1"], hosts: [] }],
        hosts: [
          {
            key: "host-1",
            name: "attached-host",
            address: "10.0.0.1",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [{ group_name: "web", host_key: "host-1" }],
      }),
    ]);
    state.hostAssets.push({
      id: "orphan-1",
      key: "orphan-1",
      name: "orphan-host",
      address: "10.0.0.99",
      connection_type: "ssh",
      port: 22,
      host_vars: {},
      memberships: [],
    });
    await installInventoryApiMocks(page, state);

    const hostAssetsLoaded = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/hosts" && response.status() === 200
    );
    await openInventoryWorkspace(page);
    await hostAssetsLoaded;
    await page.getByRole("button", { name: "전체 보기" }).click();

    await expect(page.getByRole("button", { name: "attached-host 정보 열기" })).toBeVisible();
    await expect(page.getByRole("button", { name: "orphan-host 정보 열기" })).toBeEnabled();
    await expect(page.locator(".host-table tbody")).toContainText("미소속");
    await expect(page.locator(".host-table tbody")).toContainText("orphan-host");
    await expect(page.locator(".host-table tbody")).toContainText("10.0.0.99");
  });

  test("전체 보기 orphan host asset을 편집하고 그룹에 추가한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "target-inventory",
        groups: [{ name: "prod", host_keys: [], hosts: [] }],
        hosts: [],
        memberships: [],
      }),
    ]);
    state.hostAssets.push({
      id: "orphan-edit-1",
      key: "orphan-edit-1",
      name: "orphan-edit-host",
      address: "10.0.0.50",
      connection_type: "ssh",
      port: 22,
      host_vars: {},
      memberships: [],
    });
    await installInventoryApiMocks(page, state);

    const hostAssetsLoaded = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/hosts" && response.status() === 200
    );
    await openInventoryWorkspace(page);
    await hostAssetsLoaded;
    await page.getByRole("button", { name: "전체 보기" }).click();

    await page.getByRole("button", { name: "orphan-edit-host 정보 열기" }).click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("호스트 편집");
    await dialog.getByLabel("주소").fill("10.0.0.51");
    await dialog.getByRole("button", { name: "저장" }).click();
    await expect(page.locator(".host-table tbody")).toContainText("10.0.0.51");

    const source = page.getByRole("button", { name: "orphan-edit-host 드래그 핸들" });
    const target = page.locator(".tree-group-branch", { hasText: "prod" });
    const sourceBox = await source.boundingBox();
    const targetBox = await target.boundingBox();
    expect(sourceBox).not.toBeNull();
    expect(targetBox).not.toBeNull();
    await page.mouse.move(sourceBox!.x + sourceBox!.width / 2, sourceBox!.y + sourceBox!.height / 2);
    await page.mouse.down();
    await page.mouse.move(targetBox!.x + targetBox!.width / 2, targetBox!.y + targetBox!.height / 2, {
      steps: 20,
    });
    await page.mouse.up();

    await expect.poll(() =>
      state.hostAssets.find((host) => host.id === "orphan-edit-1")?.memberships
    ).toEqual([
      { inventory_id: "inventory-1", inventory_name: "target-inventory", group_name: "prod" },
    ]);
    await expect(page.locator(".host-table tbody")).toContainText("target-inventory");
    await expect(page.locator(".host-table tbody")).toContainText("prod");
  });

  test("orphan host asset 편집 화면에서 인벤토리/그룹을 선택해 배정한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "edit-assign-target",
        groups: [{ name: "prod", host_keys: [], hosts: [] }],
        hosts: [],
        memberships: [],
      }),
    ]);
    state.hostAssets.push({
      id: "orphan-panel-1",
      key: "orphan-panel-1",
      name: "orphan-panel-host",
      address: "10.0.0.60",
      connection_type: "ssh",
      port: 22,
      host_vars: {},
      memberships: [],
    });
    await installInventoryApiMocks(page, state);

    const hostAssetsLoaded = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/hosts" && response.status() === 200
    );
    await openInventoryWorkspace(page);
    await hostAssetsLoaded;
    await page.getByRole("button", { name: "전체 보기" }).click();
    await page.getByRole("button", { name: "orphan-panel-host 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("호스트를 넣을 인벤토리 / 그룹").selectOption({ label: "edit-assign-target / prod" });
    await dialog.getByRole("button", { name: "선택한 그룹에 넣기" }).click();

    await expect.poll(() =>
      state.hostAssets.find((host) => host.id === "orphan-panel-1")?.memberships
    ).toEqual([
      { inventory_id: "inventory-1", inventory_name: "edit-assign-target", group_name: "prod" },
    ]);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "'orphan-panel-host' 호스트를 'edit-assign-target / prod' 그룹에 추가했습니다."
    );
    await expect(dialog).toContainText("edit-assign-target / prod");
  });

  test("선택한 orphan host asset 여러 개를 툴바에서 한 번에 인벤토리/그룹에 배정한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "toolbar-assign-target",
        groups: [{ name: "prod", host_keys: [], hosts: [] }],
        hosts: [],
        memberships: [],
      }),
    ]);
    state.hostAssets.push(
      {
        id: "orphan-toolbar-1",
        key: "orphan-toolbar-1",
        name: "toolbar-host-1",
        address: "10.0.4.10",
        connection_type: "ssh",
        port: 22,
        host_vars: {},
        memberships: [],
      },
      {
        id: "orphan-toolbar-2",
        key: "orphan-toolbar-2",
        name: "toolbar-host-2",
        address: "10.0.4.11",
        connection_type: "ssh",
        port: 22,
        host_vars: {},
        memberships: [],
      }
    );
    await installInventoryApiMocks(page, state);

    const hostAssetsLoaded = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/hosts" && response.status() === 200
    );
    await openInventoryWorkspace(page);
    await hostAssetsLoaded;
    await page.getByRole("button", { name: "전체 보기" }).click();
    await page.getByLabel("toolbar-host-1 호스트 선택").check();
    await page.getByLabel("toolbar-host-2 호스트 선택").check();
    await page.getByLabel("선택 호스트를 넣을 인벤토리 / 그룹").selectOption({ label: "toolbar-assign-target / prod" });
    await page.getByRole("button", { name: "선택 호스트 2개 넣기" }).click();

    await expect.poll(() =>
      state.hostAssets
        .filter((host) => ["orphan-toolbar-1", "orphan-toolbar-2"].includes(host.id))
        .map((host) => host.memberships)
    ).toEqual([
      [{ inventory_id: "inventory-1", inventory_name: "toolbar-assign-target", group_name: "prod" }],
      [{ inventory_id: "inventory-1", inventory_name: "toolbar-assign-target", group_name: "prod" }],
    ]);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "선택 호스트 2개를 'toolbar-assign-target / prod' 그룹에 추가했습니다."
    );
    await expect(page.locator(".host-table tbody")).toContainText("toolbar-assign-target");
  });

  test("인벤토리 삭제 직후 전체 보기 호스트 수를 유지한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "delete-source",
        groups: [{ name: "web", host_keys: ["host-1"], hosts: [] }],
        hosts: [
          {
            key: "host-1",
            name: "preserved-after-delete",
            address: "10.0.0.10",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [{ group_name: "web", host_key: "host-1" }],
      }),
      makeInventoryDetail({
        id: "inventory-2",
        name: "still-attached",
        groups: [{ name: "prod", host_keys: ["host-2"], hosts: [] }],
        hosts: [
          {
            key: "host-2",
            name: "still-attached-host",
            address: "10.0.0.20",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [{ group_name: "prod", host_key: "host-2" }],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "전체 보기" }).click();
    await expect(page.locator(".host-table tbody tr")).toHaveCount(2);

    await page.getByRole("button", { name: "delete-source 정보 열기" }).click();
    const deleteConfirm = getDiscardConfirm(page, "인벤토리 삭제");
    await getInfoPanel(page).getByRole("button", { name: "삭제" }).click();
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.deleteIds).toEqual(["inventory-1"]);
    await page.getByRole("button", { name: "전체 보기" }).click();
    await expect(page.locator(".host-table tbody tr")).toHaveCount(2);
    await expect(page.getByRole("button", { name: "preserved-after-delete 정보 열기" })).toBeEnabled();
    await expect(page.locator(".host-table tbody")).toContainText("미소속");
    await expect(page.locator(".host-table tbody")).toContainText("still-attached-host");
  });

  test("선택한 호스트 자산을 일괄 삭제한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "bulk-host-delete-base",
        groups: [{ name: "web", host_keys: ["host-1", "host-2"], hosts: [] }],
        hosts: [
          {
            key: "host-1",
            name: "delete-host-1",
            address: "10.0.2.10",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
          {
            key: "host-2",
            name: "delete-host-2",
            address: "10.0.2.11",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [
          { group_name: "web", host_key: "host-1" },
          { group_name: "web", host_key: "host-2" },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "전체 보기" }).click();
    await page.getByLabel("delete-host-1 호스트 선택").check();
    await page.getByLabel("delete-host-2 호스트 선택").check();
    await page.getByRole("button", { name: "선택 호스트 2개 삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "호스트 일괄 삭제");
    await expect(deleteConfirm).toContainText("호스트 자산 2개를 삭제합니다.");
    await expect(deleteConfirm).toContainText("membership도 함께 제거됩니다.");
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.hostAssetDeleteIds).toEqual([
      "inventory-1:host-1",
      "inventory-1:host-2",
    ]);
    await expect(page.getByRole("button", { name: "delete-host-1 정보 열기" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "delete-host-2 정보 열기" })).toHaveCount(0);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "호스트 2개를 삭제했습니다."
    );
  });

  test("선택한 호스트를 한 번에 다른 그룹으로 배정한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "bulk-assign-target",
        groups: [{ name: "prod", host_keys: [], hosts: [] }],
        hosts: [],
        memberships: [],
      }),
    ]);
    state.hostAssets.push(
      {
        id: "orphan-bulk-1",
        key: "orphan-bulk-1",
        name: "bulk-host-1",
        address: "10.0.3.10",
        connection_type: "ssh",
        port: 22,
        host_vars: {},
        memberships: [],
      },
      {
        id: "orphan-bulk-2",
        key: "orphan-bulk-2",
        name: "bulk-host-2",
        address: "10.0.3.11",
        connection_type: "ssh",
        port: 22,
        host_vars: {},
        memberships: [],
      }
    );
    await installInventoryApiMocks(page, state);

    const hostAssetsLoaded = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/hosts" && response.status() === 200
    );
    await openInventoryWorkspace(page);
    await hostAssetsLoaded;
    await page.getByRole("button", { name: "전체 보기" }).click();
    await page.getByLabel("bulk-host-1 호스트 선택").check();
    await page.getByLabel("bulk-host-2 호스트 선택").check();

    const source = page.getByRole("button", { name: "bulk-host-1 드래그 핸들" });
    const target = page.locator(".tree-group-branch", { hasText: "prod" });
    const sourceBox = await source.boundingBox();
    const targetBox = await target.boundingBox();
    expect(sourceBox).not.toBeNull();
    expect(targetBox).not.toBeNull();
    await page.mouse.move(sourceBox!.x + sourceBox!.width / 2, sourceBox!.y + sourceBox!.height / 2);
    await page.mouse.down();
    await page.mouse.move(targetBox!.x + targetBox!.width / 2, targetBox!.y + targetBox!.height / 2, {
      steps: 20,
    });
    await page.mouse.up();

    await expect.poll(() =>
      state.hostAssets
        .filter((host) => ["orphan-bulk-1", "orphan-bulk-2"].includes(host.id))
        .map((host) => host.memberships)
    ).toEqual([
      [{ inventory_id: "inventory-1", inventory_name: "bulk-assign-target", group_name: "prod" }],
      [{ inventory_id: "inventory-1", inventory_name: "bulk-assign-target", group_name: "prod" }],
    ]);
    await expect(page.locator(".host-table tbody")).toContainText("bulk-assign-target");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "선택 호스트 2개를 'bulk-assign-target / prod' 그룹에 추가했습니다."
    );
  });

  test("그룹 초안은 저장할 때만 서버에 반영한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "group-create-base" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("button", { name: "group-create-base 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 그룹" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("그룹 편집");
    await expect(dialog).toContainText("new_group_1");
    await expect(page.getByRole("button", { name: "new_group_1 정보 열기" })).toBeVisible();

    await expect.poll(() => state.putBodies.length).toBe(0);
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.groups[0]).toMatchObject({
      name: "new_group_1",
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "그룹 'new_group_1' 정보를 저장했습니다."
    );
  });

  test("미저장 그룹 초안은 닫기 확인 후 폐기한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "group-draft-close-base" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("button", { name: "group-draft-close-base 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 그룹" }).click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("new_group_1");

    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "그룹 초안 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 그룹 초안이 있습니다.");
    await discardConfirm.getByRole("button", { name: "초안 버리기" }).click();

    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "new_group_1 정보 열기" })).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("미저장 그룹 초안에서 닫기 확인 UI는 깜빡이지 않고 취소할 때 유지된다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "group-close-confirm-stability" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("button", { name: "group-close-confirm-stability 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 그룹" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("new_group_1");
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "그룹 초안 폐기");
    await expect(discardConfirm).toBeVisible();
    await expect(discardConfirm).toContainText("저장하지 않은 그룹 초안이 있습니다.");
    await page.waitForTimeout(300);
    await expect(discardConfirm).toBeVisible();

    await discardConfirm.getByRole("button", { name: "계속 편집" }).click();

    await expect(discardConfirm).toHaveCount(0);
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("new_group_1");
    await expect(page.getByRole("button", { name: "new_group_1 정보 열기" })).toBeVisible();
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("그룹 저장은 이름이 비면 막는다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "group-validation-base",
        groups: [
          {
            name: "existing-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "dmz",
              _preview_vars_summary: "ansible_port=22",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "existing-group 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("그룹 이름").fill("");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(0);
    await expect(dialog).toContainText("existing-group");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText("그룹 이름을 입력하세요.");
  });

  test("그룹 정보를 저장한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "group-update-base",
        groups: [
          {
            name: "group-before-save",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "before-note",
              _preview_zone: "before-zone",
              _preview_vars_summary: "before-summary",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "group-before-save 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("그룹 이름").fill("group-after-save");
    await dialog.getByLabel("태그").fill("zone-after-save, edge");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.groups[0]).toMatchObject({
      name: "group-after-save",
      tags: ["zone-after-save", "edge"],
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "그룹 'group-after-save' 정보를 저장했습니다."
    );
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "group-after-save 정보 열기" })).toBeVisible();
  });

  test("그룹을 삭제한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "group-delete-base",
        groups: [
          {
            name: "group-delete-target",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "dmz",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-in-group",
            address: "10.0.0.10",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "host note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "group-delete-target", host_key: "host-1" }],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "group-delete-target 정보 열기" }).click();
    await getInfoPanel(page).getByRole("button", { name: "삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "그룹 삭제");
    await expect(deleteConfirm).toContainText("'group-delete-target' 항목을 삭제하시겠습니까?");
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.groups).toHaveLength(1);
    expect(state.putBodies[0]?.body.groups[0]).toMatchObject({
      name: "__ansibleharness_unassigned__",
    });
    expect(state.putBodies[0]?.body.memberships).toEqual([]);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "그룹 'group-delete-target'을 삭제했습니다."
    );
    await expect(page.getByRole("button", { name: "group-delete-target 정보 열기" })).toHaveCount(0);
  });

  test("선택한 그룹을 일괄 삭제하고 호스트 자산은 보존한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "bulk-group-delete-base",
        groups: [
          { name: "delete-a", host_keys: ["host-1"], hosts: [] },
          { name: "delete-b", host_keys: ["host-2"], hosts: [] },
          { name: "keep", host_keys: ["host-3"], hosts: [] },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-delete-a",
            address: "10.0.0.11",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
          {
            key: "host-2",
            name: "host-delete-b",
            address: "10.0.0.12",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
          {
            key: "host-3",
            name: "host-keep",
            address: "10.0.0.13",
            connection_type: "ssh",
            port: 22,
            host_vars: {},
          },
        ],
        memberships: [
          { group_name: "delete-a", host_key: "host-1" },
          { group_name: "delete-b", host_key: "host-2" },
          { group_name: "keep", host_key: "host-3" },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByLabel("delete-a 그룹 선택").check();
    await page.getByLabel("delete-b 그룹 선택").check();
    await page.getByRole("button", { name: "선택 그룹 2개 삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "그룹 일괄 삭제");
    await expect(deleteConfirm).toContainText("그룹 2개를 삭제합니다.");
    await expect(deleteConfirm).toContainText("호스트 2개는 삭제되지 않고");
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.groups.map((group) => group.name)).toEqual([
      "keep",
      "__ansibleharness_unassigned__",
    ]);
    expect(state.putBodies[0]?.body.hosts).toHaveLength(3);
    expect(state.putBodies[0]?.body.memberships).toEqual([
      { group_name: "keep", host_key: "host-3" },
    ]);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "그룹 2개를 삭제했습니다. 호스트 자산은 보존됩니다."
    );
    const tree = page.getByRole("tree");
    await expect(tree.getByRole("button", { name: "delete-a 정보 열기", exact: true })).toHaveCount(0);
    await expect(tree.getByRole("button", { name: "delete-b 정보 열기", exact: true })).toHaveCount(0);
    await expect(tree.getByRole("button", { name: "keep 정보 열기", exact: true })).toBeVisible();
  });

  test("호스트를 생성한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-create-base",
        groups: [
          {
            name: "host-create-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("heading", { name: "호스트 등록 현황" })).toBeVisible();
    await expect(page.getByRole("button", { name: "host-create-base 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 호스트" }).click();

    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "인벤토리 'host-create-base'에 새 호스트 초안을 만들었습니다. 저장을 눌러 반영하세요."
    );
    await expect.poll(() => state.putBodies.length).toBe(0);

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("호스트 편집");
    await expect(dialog).toContainText("new-host-1");
    await expect(page.getByRole("button", { name: "new-host-1 정보 열기" })).toBeVisible();

    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.hosts).toHaveLength(1);
    expect(state.putBodies[0]?.body.hosts?.[0]).toMatchObject({
      name: "new-host-1",
      address: "10.0.0.1",
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "호스트 'new-host-1' 정보를 저장했습니다."
    );
    await expect(dialog).toHaveCount(0);
  });

  test("미저장 호스트 초안은 닫기 전에 확인하고 취소하면 유지한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-draft-close-base",
        groups: [
          {
            name: "host-draft-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(
      page.getByRole("button", { name: "host-draft-close-base 정보 열기" })
    ).toBeVisible();
    await page.getByRole("button", { name: "+ 호스트" }).click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("new-host-1");

    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "호스트 초안 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 호스트 초안이 있습니다.");
    await discardConfirm.getByRole("button", { name: "계속 편집" }).click();

    await expect(dialog).toContainText("new-host-1");
    await expect(page.getByRole("button", { name: "new-host-1 정보 열기" })).toBeVisible();
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("미저장 호스트 초안에서 닫기 확인 UI는 깜빡이지 않고 취소할 때 유지된다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-close-confirm-stability",
        groups: [
          {
            name: "host-stability-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("button", { name: "host-close-confirm-stability 정보 열기" })).toBeVisible();
    await page.getByRole("button", { name: "+ 호스트" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("new-host-1");
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "호스트 초안 폐기");
    await expect(discardConfirm).toBeVisible();
    await expect(discardConfirm).toContainText("저장하지 않은 호스트 초안이 있습니다.");
    await page.waitForTimeout(300);
    await expect(discardConfirm).toBeVisible();

    await discardConfirm.getByRole("button", { name: "계속 편집" }).click();

    await expect(discardConfirm).toHaveCount(0);
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("new-host-1");
    await expect(page.getByRole("button", { name: "new-host-1 정보 열기" })).toBeVisible();
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("미저장 호스트 초안은 닫기 확인 후 폐기한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-draft-discard-base",
        groups: [
          {
            name: "host-draft-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(
      page.getByRole("button", { name: "host-draft-discard-base 정보 열기" })
    ).toBeVisible();
    await page.getByRole("button", { name: "+ 호스트" }).click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("new-host-1");

    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "호스트 초안 폐기");
    await expect(discardConfirm).toContainText("주소와 그룹 배정 변경이 서버에 반영되지 않은 채 사라집니다.");
    await discardConfirm.getByRole("button", { name: "초안 버리기" }).click();

    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "new-host-1 정보 열기" })).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("그룹이 없는 인벤토리에서는 호스트 생성을 막고 안내는 자동으로 사라진다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "host-guard-base" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await expect(page.getByRole("button", { name: "host-guard-base 정보 열기" })).toBeVisible();
    await page.locator(".inventory-node", { hasText: "host-guard-base" }).click();
    await page.getByRole("button", { name: "+ 호스트" }).click();

    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "호스트를 추가하려면 'host-guard-base' 인벤토리에 그룹을 하나 이상 먼저 만드세요."
    );
    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);

    await page.waitForTimeout(5200);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toHaveCount(0);
  });

  test("호스트 저장은 이름과 주소가 비면 막는다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-validation-base",
        hosts: [
          {
            key: "host-1",
            name: "host-before-validation",
            address: "10.0.0.20",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "host note",
              _preview_status: "pending",
            },
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-before-validation 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("호스트 이름").fill("");
    await dialog.getByLabel("주소").fill("");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(0);
    await expect(dialog).toContainText("host-before-validation");
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText("호스트 이름과 주소를 입력하세요.");
  });

  test("호스트 정보를 저장한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-update-base",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "group-note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-before-save",
            address: "10.0.0.30",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "before-note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-before-save 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await dialog.getByLabel("호스트 이름").fill("host-after-save");
    await dialog.getByLabel("주소").fill("10.0.0.31");
    await dialog.getByLabel("플랫폼").fill("Rocky Linux 9");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.body.hosts?.[0]).toMatchObject({
      key: "host-1",
      name: "host-after-save",
      address: "10.0.0.31",
      host_vars: expect.objectContaining({
        _preview_platform: "Rocky Linux 9",
      }),
    });
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "호스트 'host-after-save' 정보를 저장했습니다."
    );
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "host-after-save 정보 열기" })).toBeVisible();
  });

  test("호스트를 삭제한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-delete-base",
        hosts: [
          {
            key: "host-1",
            name: "host-delete-target",
            address: "10.0.0.40",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "host note",
              _preview_status: "pending",
            },
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-delete-target 정보 열기" }).click();
    await getInfoPanel(page).getByRole("button", { name: "삭제" }).click();

    const deleteConfirm = getDiscardConfirm(page, "호스트 삭제");
    await expect(deleteConfirm).toContainText("'host-delete-target' 항목을 삭제하시겠습니까?");
    await deleteConfirm.getByRole("button", { name: "삭제하기" }).click();

    await expect.poll(() => state.hostDeleteIds.length).toBe(1);
    expect(state.hostDeleteIds[0]).toEqual({ inventoryId: "inventory-1", hostKey: "host-1" });
    expect(state.putBodies).toEqual([]);
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "호스트 'host-delete-target'를 삭제했습니다."
    );
    await expect(page.getByRole("button", { name: "host-delete-target 정보 열기" })).toHaveCount(0);
  });

  test("기존 인벤토리 수정 후 닫기 시 변경 폐기 확인창이 나타나고 취소 시 편집이 유지된다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "existing-inv-close" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "existing-inv-close 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("existing-inv-close");

    // Change name to make dirty
    await dialog.getByLabel("이름").fill("existing-inv-close-edited");

    // Close -> should show change discard confirm
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "인벤토리 변경 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 인벤토리 변경이 있습니다.");
    await expect(discardConfirm).toContainText("변경 버리기");
    await expect(discardConfirm).toContainText("계속 편집");

    // Cancel -> edits preserved
    await discardConfirm.getByRole("button", { name: "계속 편집" }).click();
    await expect(getInfoPanel(page)).toBeVisible();
    await expect(getInfoPanel(page).getByLabel("이름")).toHaveValue("existing-inv-close-edited");

    // Close again -> confirm -> discard changes
    await getInfoPanel(page).getByRole("button", { name: "닫기", exact: true }).click();
    const discardConfirm2 = getDiscardConfirm(page, "인벤토리 변경 폐기");
    await discardConfirm2.getByRole("button", { name: "변경 버리기" }).click();

    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("기존 그룹 수정 후 닫기 시 변경 폐기 확인창이 나타난다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "existing-group-close",
        groups: [
          {
            name: "editable-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: [],
            hosts: [],
          },
        ],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "editable-group 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("그룹 편집");

    // Edit name to make dirty
    await dialog.getByLabel("그룹 이름").fill("editable-group-edited");

    // Close -> should show change discard confirm
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "그룹 변경 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 그룹 변경이 있습니다.");
    await expect(discardConfirm).toContainText("변경 버리기");

    // Discard changes
    await discardConfirm.getByRole("button", { name: "변경 버리기" }).click();
    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("기존 호스트 수정 후 닫기 시 변경 폐기 확인창이 나타난다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "existing-host-close",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "editable-host",
            address: "10.0.0.1",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "editable-host 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("호스트 편집");

    // Edit name to make dirty
    await dialog.getByLabel("호스트 이름").fill("editable-host-edited");

    // Close -> should show change discard confirm
    await dialog.getByRole("button", { name: "닫기", exact: true }).click();

    const discardConfirm = getDiscardConfirm(page, "호스트 변경 폐기");
    await expect(discardConfirm).toContainText("저장하지 않은 호스트 변경이 있습니다.");
    await expect(discardConfirm).toContainText("변경 버리기");

    // Discard changes
    await discardConfirm.getByRole("button", { name: "변경 버리기" }).click();
    await expect(getInfoPanel(page)).toHaveCount(0);
    await expect.poll(() => state.putBodies.length).toBe(0);
  });

  test("자격 증명 관리 화면을 워크스페이스 버튼으로 열 수 있고 빈 상태를 표시한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "cred-mgmt-workspace" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.locator(".inventory-node", { hasText: "cred-mgmt-workspace" }).click();

    // Open credential manager from toolbar button
    await page.getByTestId("open-credential-manager-button").click();

    // Should see credential management panel
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("자격 증명 목록", { timeout: 5000 });
    await expect(dialog).toContainText("등록된 자격 증명이 없습니다");
    await expect(dialog.getByTestId("credential-add-button")).toBeVisible();

    // Close the panel
    await dialog.getByRole("button", { name: "닫기" }).click();
    await expect(getInfoPanel(page)).toHaveCount(0);
  });

  test("자격 증명 관리 화면에서 자격 증명을 생성하고 목록에 표시한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "cred-mgmt-create" }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.locator(".inventory-node", { hasText: "cred-mgmt-create" }).click();

    // Open credential manager
    await page.getByTestId("open-credential-manager-button").click();
    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("자격 증명 목록", { timeout: 5000 });

    // Click add button
    await dialog.getByTestId("credential-add-button").click();

    // Fill credential form
    await dialog.getByPlaceholder("자격 증명 이름").fill("test-credential");
    await dialog.getByPlaceholder("사용자명").fill("admin");
    await dialog.getByPlaceholder("비밀번호 또는 키").fill("secret123");

    // Save
    await dialog.getByRole("button", { name: "저장" }).click();

    // Verify credential was created via API
    await expect.poll(() => state.credentialPosts.length).toBe(1);
    expect(state.credentialPosts[0]?.body.name).toBe("test-credential");
    expect(state.credentialPosts[0]?.body.username).toBe("admin");

    // Verify credential appears in list
    // Wait for refresh - the list re-renders after credential saved
    await expect(dialog.getByTestId("credential-card-cred-1")).toBeVisible({ timeout: 3000 });
    await expect(dialog.getByTestId("credential-card-cred-1")).toContainText("test-credential");
    await expect(dialog.getByTestId("credential-card-cred-1")).toContainText("ssh_password");
    await expect(dialog.getByTestId("credential-card-cred-1")).toContainText("admin");

    // Close
    await dialog.getByRole("button", { name: "닫기" }).click();
    await expect(getInfoPanel(page)).toHaveCount(0);
  });

  test("기계 생성 자격 증명 이름은 사용자용 라벨로 표시한다", async ({ page }) => {
    const generatedName = "embedded-login-after-change-c565253371c44667b94efeb56c08f52e";
    const state = createState([
      makeInventoryDetail({ id: "inventory-1", name: "generated-credential-label" }),
    ]);
    state.credentials = [
      {
        ref: "cred-generated",
        name: generatedName,
        credential_type: "ssh_password",
        username: "admin",
        has_secret: true,
        has_become_secret: true,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.locator(".inventory-node", { hasText: "generated-credential-label" }).click();
    await page.getByTestId("open-credential-manager-button").click();

    const dialog = getInfoPanel(page);
    const card = dialog.getByTestId("credential-card-cred-generated");
    await expect(card).toBeVisible({ timeout: 5000 });
    await expect(card).toContainText("admin · ssh_password");
    await expect(card).toContainText("become 가능");
    await expect(dialog.getByText(generatedName)).toHaveCount(0);
  });

  test("호스트 편집에서 자격 증명 관리 오버레이를 열어도 dirty draft를 유지하고 자동 선택하지 않는다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-cred-selector",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-with-cred",
            address: "10.0.0.1",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    // Seed a shared credential so every inventory selector has the same option pool.
    state.credentials = [
      {
        ref: "cred-1",
        name: "pre-seeded-cred",
        credential_type: "ssh_password",
        username: "root",
        has_secret: true,
        has_become_secret: false,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-with-cred 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("호스트 편집");
    await dialog.getByLabel("호스트 이름").fill("host-with-cred-edited");

    await expect(dialog.getByLabel("로그인 자격 증명")).toBeVisible();
    await expect(dialog.getByLabel("로그인 자격 증명")).toBeEnabled();
    await expect(dialog.getByText("become 사용자")).toHaveCount(0);
    await expect(dialog.getByText("become 자격 증명")).toHaveCount(0);

    await expect(dialog.getByLabel("로그인 자격 증명")).toContainText("pre-seeded-cred", { timeout: 5000 });

    const manageCredButton = dialog.getByTestId("host-edit-manage-credentials");
    await expect(manageCredButton).toBeVisible();
    await expect(manageCredButton).toContainText("자격 증명 관리");

    await manageCredButton.click();
    await expect(page.getByRole("alertdialog")).toHaveCount(0);

    const overlay = getCredentialOverlay(page);
    await expect(overlay).toContainText("공용 자격 증명");
    await expect(overlay.getByTestId("credential-card-cred-1")).toBeVisible();

    await overlay.getByTestId("credential-add-button").click();
    await overlay.getByPlaceholder("자격 증명 이름").fill("manage-only-cred");
    await overlay.getByPlaceholder("사용자명").fill("ops");
    await overlay.getByPlaceholder("비밀번호 또는 키").fill("ops-secret");
    await overlay.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.credentialPosts.length).toBe(1);
    await expect(overlay.getByTestId("credential-card-cred-2")).toBeVisible({ timeout: 3000 });

    await overlay.getByTestId("credential-manager-overlay-close").click();
    await expect(overlay).toHaveCount(0);

    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("호스트 이름")).toHaveValue("host-with-cred-edited");
    await expect(dialog.getByLabel("로그인 자격 증명")).toHaveValue("");
  });

  test("호스트 편집에서 + 자격 증명 추가는 discard 없이 오버레이를 열고 저장 후 자동 선택한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-cred-create-entry",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-create-cred",
            address: "10.0.0.11",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-create-cred 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog).toContainText("호스트 편집");
    await dialog.getByLabel("호스트 이름").fill("host-create-cred-edited");

    const addCredButton = dialog.getByTestId("host-edit-add-credential");
    await expect(addCredButton).toBeVisible();
    await expect(addCredButton).toContainText("+ 자격 증명 추가");

    await addCredButton.click();
    await expect(page.getByRole("alertdialog")).toHaveCount(0);

    const overlay = getCredentialOverlay(page);
    await expect(overlay.getByPlaceholder("자격 증명 이름")).toBeVisible();
    await expect(overlay.getByPlaceholder("비밀번호 또는 키")).toBeVisible();
    await expect
      .poll(() =>
        overlay.evaluate((element) => {
          const shell = element.closest(".credential-overlay-shell");

          if (!shell) {
            return false;
          }

          const style = window.getComputedStyle(shell);
          const rect = shell.getBoundingClientRect();

          return (
            style.position === "fixed" &&
            style.display === "flex" &&
            Number(style.zIndex) >= 190 &&
            Math.round(rect.top) === 0 &&
            Math.round(rect.bottom) === window.innerHeight
          );
        })
      )
      .toBe(true);

    await overlay.getByPlaceholder("자격 증명 이름").fill("new-overlay-credential");
    await overlay.getByPlaceholder("사용자명").fill("deploy");
    await overlay.getByPlaceholder("비밀번호 또는 키").fill("deploy-secret");
    await overlay.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.credentialPosts.length).toBe(1);
    await expect(overlay).toHaveCount(0);

    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("호스트 이름")).toHaveValue("host-create-cred-edited");
    await expect(dialog.getByLabel("로그인 자격 증명")).toHaveValue("cred-1");
    await expect(dialog.getByLabel("로그인 자격 증명")).toContainText("new-overlay-credential");
  });

  test("누락된 로그인 자격 증명은 읽기 쉬운 fallback으로 표시한다", async ({ page }) => {
    const missingCredentialRef =
      "embedded-login-after-change-c565253371c44667b94efeb56c08f52e";
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "host-missing-credential",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-with-missing-credential",
            address: "10.0.0.51",
            connection_type: "ssh",
            port: 22,
            login_credential_ref: missingCredentialRef,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "cred-available",
        name: "available-login",
        credential_type: "ssh_password",
        username: "root",
        has_secret: true,
        has_become_secret: false,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-with-missing-credential 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    const loginCredentialSelect = dialog.getByLabel("로그인 자격 증명");
    const truncatedRef = truncateCredentialRef(missingCredentialRef);

    await expect(loginCredentialSelect).toContainText("현재 연결된 자격 증명 (사용 불가)");
    await expect(dialog).toContainText("현재 연결된 자격 증명을 찾을 수 없습니다.");
    await expect(dialog).toContainText(`참조 ${truncatedRef}`);
    await expect(dialog.getByText(missingCredentialRef)).toHaveCount(0);
  });

  test("공용 자격 증명은 다른 인벤토리의 호스트 편집에서도 같은 목록으로 표시된다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "first-inventory",
        groups: [],
        hosts: [],
        memberships: [],
      }),
      makeInventoryDetail({
        id: "inventory-2",
        name: "second-inventory",
        groups: [
          {
            name: "shared-group",
            group_vars: {
              _preview_id: "group-2",
              _preview_note: "note",
              _preview_zone: "zone-2",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-2"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-2",
            name: "host-shared-cred",
            address: "10.0.0.22",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "shared-group", host_key: "host-2" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "global-cred-1",
        name: "global-shared-login",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: false,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "second-inventory 호스트" }).click();
    await page.getByRole("button", { name: "host-shared-cred 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog.getByLabel("로그인 자격 증명")).toContainText("global-shared-login", { timeout: 5000 });

    await dialog.getByLabel("로그인 자격 증명").selectOption("global-cred-1");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    expect(state.putBodies[0]?.id).toBe("inventory-2");
    expect(state.putBodies[0]?.body.hosts?.[0]?.login_credential_ref).toBe("global-cred-1");
  });

  test("become 정보가 없는 로그인 자격 증명은 호스트 편집에서 권한 상승에 사용할 수 없다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "become-guard-inventory",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-without-become-credential",
            address: "10.0.0.31",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "global-cred-no-become",
        name: "global-login-only",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-without-become-credential 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    const loginCredentialSelect = dialog.getByLabel("로그인 자격 증명");
    const becomeToggle = dialog.getByLabel("become 사용");

    await loginCredentialSelect.selectOption("global-cred-no-become");
    await becomeToggle.click();

    await expect(becomeToggle).not.toBeChecked();
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "become을 사용하려면 become 계정 정보가 포함된 로그인 자격 증명을 선택하거나 새로 만드세요."
    );
  });

  test("become 사용 중 become 정보가 없는 로그인 자격 증명으로 바꾸면 권한 상승을 자동 해제한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "become-switch-inventory",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-switch-become-credential",
            address: "10.0.0.42",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "global-cred-with-become",
        name: "global-login-with-become",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: true,
        become_username: "root",
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
      {
        ref: "global-cred-no-become",
        name: "global-login-only",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-switch-become-credential 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    const loginCredentialSelect = dialog.getByLabel("로그인 자격 증명");
    const becomeToggle = dialog.getByLabel("become 사용");

    await loginCredentialSelect.selectOption("global-cred-with-become");
    await becomeToggle.check();
    await expect(becomeToggle).toBeChecked();

    await loginCredentialSelect.selectOption("global-cred-no-become");

    await expect(becomeToggle).not.toBeChecked();
    await expect(page.locator(inventorySelectors.feedbackNotice)).toContainText(
      "become을 사용하려면 become 계정 정보가 포함된 로그인 자격 증명을 선택하거나 새로 만드세요."
    );
  });

  test("become 정보가 있는 로그인 자격 증명은 권한 상승 저장에 그대로 사용한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "become-save-inventory",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-with-become-credential",
            address: "10.0.0.41",
            connection_type: "ssh",
            port: 22,
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "global-cred-with-become",
        name: "global-login-with-become",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: true,
        become_username: "root",
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-with-become-credential 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    const loginCredentialSelect = dialog.getByLabel("로그인 자격 증명");
    const becomeToggle = dialog.getByLabel("become 사용");

    await loginCredentialSelect.selectOption("global-cred-with-become");
    await becomeToggle.check();
    await expect(becomeToggle).toBeChecked();

    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    const savedHost = state.putBodies[0]?.body.hosts?.[0];
    expect(savedHost).toMatchObject({
      login_credential_ref: "global-cred-with-become",
      become_enabled: true,
    });
    expect(savedHost).not.toHaveProperty("become_credential_ref");
    expect(savedHost).not.toHaveProperty("become_user");
  });

  test("기존 separate become 설정은 호스트 편집 저장 시 화면에 숨기되 보존한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "legacy-become-roundtrip-inventory",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-legacy-become",
            address: "10.0.0.51",
            connection_type: "ssh",
            port: 22,
            login_credential_ref: "legacy-login-cred",
            become_enabled: true,
            become_user: "root",
            become_credential_ref: "legacy-become-cred",
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "legacy note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "legacy-login-cred",
        name: "legacy-login",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
      {
        ref: "legacy-become-cred",
        name: "legacy-become",
        credential_type: "become_password",
        username: "root",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-legacy-become 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    await expect(dialog.getByText("become 사용자")).toHaveCount(0);
    await expect(dialog.getByText("become 자격 증명")).toHaveCount(0);

    await dialog.locator("textarea.form-textarea").fill("legacy note updated");
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    const savedHost = state.putBodies[0]?.body.hosts?.[0];
    expect(savedHost).toMatchObject({
      login_credential_ref: "legacy-login-cred",
      become_enabled: true,
      become_user: "root",
      become_credential_ref: "legacy-become-cred",
    });
  });

  test("기존 separate become 설정에서 로그인 자격 증명을 바꾸면 숨겨진 separate become 값을 제거한다", async ({ page }) => {
    const state = createState([
      makeInventoryDetail({
        id: "inventory-1",
        name: "legacy-become-change-login-inventory",
        groups: [
          {
            name: "host-group",
            group_vars: {
              _preview_id: "group-1",
              _preview_note: "note",
              _preview_zone: "zone-1",
              _preview_vars_summary: "vars",
            },
            host_keys: ["host-1"],
            hosts: [],
          },
        ],
        hosts: [
          {
            key: "host-1",
            name: "host-legacy-change-login",
            address: "10.0.0.52",
            connection_type: "ssh",
            port: 22,
            login_credential_ref: "legacy-login-cred",
            become_enabled: true,
            become_user: "root",
            become_credential_ref: "legacy-become-cred",
            host_vars: {
              _preview_platform: "Linux",
              _preview_note: "legacy change note",
              _preview_status: "pending",
            },
          },
        ],
        memberships: [{ group_name: "host-group", host_key: "host-1" }],
      }),
    ]);
    state.credentials = [
      {
        ref: "legacy-login-cred",
        name: "legacy-login",
        credential_type: "ssh_password",
        username: "ops",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
      {
        ref: "legacy-become-cred",
        name: "legacy-become",
        credential_type: "become_password",
        username: "root",
        has_secret: true,
        has_become_secret: false,
        become_username: null,
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
      {
        ref: "global-login-with-become",
        name: "global-login-with-become",
        credential_type: "ssh_password",
        username: "deploy",
        has_secret: true,
        has_become_secret: true,
        become_username: "admin",
        last_rotated_at: "2026-05-20T00:00:00Z",
      },
    ];
    await installInventoryApiMocks(page, state);

    await openInventoryWorkspace(page);
    await page.getByRole("button", { name: "host-legacy-change-login 정보 열기" }).click();

    const dialog = getInfoPanel(page);
    const loginCredentialSelect = dialog.getByLabel("로그인 자격 증명");
    await loginCredentialSelect.selectOption("global-login-with-become");
    await expect(dialog.getByLabel("become 사용")).toBeChecked();
    await dialog.getByRole("button", { name: "저장" }).click();

    await expect.poll(() => state.putBodies.length).toBe(1);
    const savedHost = state.putBodies[0]?.body.hosts?.[0];
    expect(savedHost).toMatchObject({
      login_credential_ref: "global-login-with-become",
      become_enabled: true,
    });
    expect(savedHost).not.toHaveProperty("become_user");
    expect(savedHost).not.toHaveProperty("become_credential_ref");
  });
});
