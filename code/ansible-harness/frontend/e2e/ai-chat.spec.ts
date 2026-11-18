import { expect, test } from "@playwright/test";

const aiSelectors = {
  sidebarLink: '[data-testid="sidebar-ai-link"]',
  healthStatus: '[data-testid="ai-health-status"]',
  kbToggle: '[data-testid="ai-kb-toggle"]',
  kbToggleOn: '[data-testid="ai-kb-toggle-on"]',
  kbToggleOff: '[data-testid="ai-kb-toggle-off"]',
  questionInput: '[data-testid="ai-question-input"]',
  submitButton: '[data-testid="ai-submit-button"]',
  sourcePanel: '[data-testid="ai-source-panel"]',
  answerPanel: '[data-testid="ai-answer-panel"]',
  sourceItem: '[data-testid="ai-source-item"]',
  errorBanner: '[data-testid="ai-error-banner"]',
  waitIndicator: '[data-testid="ai-wait-indicator"]',
} as const;

test.describe("AI 채팅 흐름 계약", () => {
  test("사이드바에서 AI 페이지로 진입해 기본 응답 UI 계약을 확인한다", async ({ page }) => {
    await page.route("**/api/ai/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          provider: "ollama",
          provider_reachable: true,
          base_url: "http://127.0.0.1:11434/v1",
          chat_model: "gemma4:e4b",
          chat_model_installed: true,
          embedding_model: "ibm/granite-embedding:278m",
          embedding_model_installed: true,
          timeout_seconds: 300,
          index_state: {
            status: "ready",
            document_count: 1,
            chunk_count: 3,
            last_rebuilt_at: "2026-04-11T00:00:00Z",
            detail: "AI 인덱스가 준비되었습니다.",
          },
        }),
      });
    });

    await page.route("**/api/ai/chat", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          'event: sources',
          'data: {"sources":[{"source":"knowledge_base/coding_rules/파이선가이드.md","filename":"파이선가이드.md","doc_group":"coding_rules","ext":".md","chunk_id":"0","excerpt":"PEP 8 기반 함수 스타일 가이드"}],"model":"gemma4:e4b","retrieval_count":1,"grounded":true,"index_state":{"status":"ready","document_count":1,"chunk_count":3,"last_rebuilt_at":"2026-04-11T00:00:00Z","detail":"AI 인덱스가 준비되었습니다."}}',
          '',
          'event: chunk',
          'data: "파이썬 함수는 snake_case를 사용하세요."',
          '',
        ].join('\n'),
      });
    });

    await page.goto("/");

    await page.click(aiSelectors.sidebarLink);
    await expect(page).toHaveURL(/\/ai$/);

    await expect(page.locator(aiSelectors.healthStatus)).toBeVisible();
    await expect(page.locator(aiSelectors.questionInput)).toBeVisible();
    await expect(page.locator(aiSelectors.submitButton)).toBeVisible();

    await page.fill(aiSelectors.questionInput, "knowledge_base 규칙을 요약해줘");
    await page.click(aiSelectors.submitButton);

    await expect(page.locator(aiSelectors.waitIndicator)).toBeVisible();
    await expect(page.locator(aiSelectors.sourcePanel)).toBeVisible();
    await expect(page.locator(aiSelectors.sourceItem).first()).toBeVisible();
    await expect(page.locator(aiSelectors.answerPanel)).toBeVisible();
    await expect(page.getByText("질문을 입력하면 여기에 답변이 표시됩니다.")).not.toBeVisible();
  });

  test("AI 실패 상태를 오류 배너 계약으로 노출한다", async ({ page }) => {
    await page.goto("/ai?mode=error-contract");

    await expect(page.locator(aiSelectors.errorBanner)).toBeVisible();
  });

  test("지식베이스를 끄면 일반 질문 모드로 source 패널 없이 답변한다", async ({ page }) => {
    let capturedRequest: { question?: string; use_knowledge_base?: boolean } | null = null;

    await page.route("**/api/ai/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "degraded",
          provider: "ollama",
          provider_reachable: true,
          base_url: "http://127.0.0.1:11434/v1",
          chat_model: "gemma4:e4b",
          chat_model_installed: true,
          embedding_model: "ibm/granite-embedding:278m",
          embedding_model_installed: false,
          timeout_seconds: 300,
          index_state: {
            status: "missing",
            document_count: 0,
            chunk_count: 0,
            last_rebuilt_at: null,
            detail: "index_missing",
          },
        }),
      });
    });

    await page.route("**/api/ai/chat", async (route) => {
      capturedRequest = route.request().postDataJSON() as {
        question?: string;
        use_knowledge_base?: boolean;
      };
      await new Promise((resolve) => setTimeout(resolve, 1200));
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          "event: sources",
          'data: {"sources":[],"model":"gemma4:e4b","retrieval_count":0,"grounded":false,"index_state":{"status":"missing","document_count":0,"chunk_count":0,"last_rebuilt_at":null,"detail":"index_missing"}}',
          "",
          "event: chunk",
          'data: "HTTP와 HTTPS의 차이는 TLS 암호화 적용 여부입니다."',
          "",
        ].join("\n"),
      });
    });

    await page.goto("/ai");

    await page.click(aiSelectors.kbToggleOff);
    await expect(page.locator(aiSelectors.kbToggleOff)).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(aiSelectors.errorBanner)).toHaveCount(0);

    await page.fill(aiSelectors.questionInput, "HTTP와 HTTPS 차이를 설명해줘");
    await page.click(aiSelectors.submitButton);

    await expect(page.locator(aiSelectors.waitIndicator)).toBeVisible();
    await expect(page.locator(aiSelectors.sourcePanel)).toHaveCount(0);
    await expect(page.locator(aiSelectors.answerPanel)).toBeVisible();
    await expect(page.getByText("질문을 입력하면 여기에 답변이 표시됩니다.")).not.toBeVisible();
    await expect.poll(() => capturedRequest).not.toBeNull();
    expect(capturedRequest).toMatchObject({
      question: "HTTP와 HTTPS 차이를 설명해줘",
      use_knowledge_base: false,
    });
  });
});
