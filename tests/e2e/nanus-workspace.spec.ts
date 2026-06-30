import { expect, test } from "@playwright/test";

test("sending a short prompt starts a visible Manus-like execution", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "무엇을 실행할까요?" })).toBeVisible();

  const composer = page.getByRole("textbox", { name: "작업 입력" });
  await composer.fill("안녕");
  await composer.press("Enter");

  const worklog = page.getByLabel("Active run workspace");
  await expect(worklog).toBeVisible();
  await expect(worklog.getByRole("heading", { name: "안녕" })).toBeVisible();
  await expect(worklog.getByText("/run 명령을 수신했습니다.")).toBeVisible();
  await expect(worklog.getByText("일반 실행 실행 그래프를 구성했습니다.")).toBeVisible();
  await expect(worklog.locator(".active-run-timeline").getByText("요청 해석", { exact: true })).toBeVisible();
  await expect(worklog.locator(".active-run-timeline").getByText("실행 계획 생성", { exact: true })).toBeVisible();
  await expect(worklog.getByLabel("OpenManus-inspired runtime").getByText("State loop")).toBeVisible();
  await expect(worklog.getByLabel("OpenManus-inspired runtime").getByText("Tool collection")).toBeVisible();

  await expect.poll(async () => Number(await worklog.getByTestId("run-progress-value").textContent())).toBeGreaterThan(60);
  await expect.poll(async () => (await worklog.getByTestId("run-status").textContent())?.trim()).toBe("완료됨");
  await expect(worklog.getByText("완료: 결과 작성")).toBeVisible();

  await worklog.getByRole("button", { name: "실행 기록" }).click();
  const inspector = page.getByLabel("Current run inspector");
  await expect(inspector.getByRole("heading", { name: "안녕" })).toBeVisible();
  await expect(inspector.getByText("완료됨")).toBeVisible();
  await expect(inspector.getByLabel("Artifact preview")).toContainText("Artifact Viewer");
  await expect(inspector.getByLabel("Artifact preview")).toContainText("안녕 결과");
  await expect(inspector.getByRole("button", { name: "일시정지" })).toBeDisabled();
});

test("run inspector mirrors workspace progress", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: "작업 입력" }).fill("진행률 일치 확인");
  await page.getByRole("textbox", { name: "작업 입력" }).press("Enter");

  const worklog = page.getByLabel("Active run workspace");
  await expect(worklog).toBeVisible();
  await worklog.getByRole("button", { name: "일시정지" }).click();

  const workspaceProgress = await worklog.getByTestId("run-progress-value").textContent();
  await worklog.getByRole("button", { name: "실행 기록" }).click();
  const inspector = page.getByLabel("Current run inspector");
  await expect(inspector.getByTestId("inspector-progress-value")).toHaveText(workspaceProgress ?? "");
});

test("new task starts unpaused after a paused run", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: "작업 입력" }).fill("잠시 멈출 작업");
  await page.getByRole("textbox", { name: "작업 입력" }).press("Enter");
  let worklog = page.getByLabel("Active run workspace");
  await expect(worklog).toBeVisible();
  await worklog.getByRole("button", { name: "일시정지" }).click();
  await expect(worklog.getByTestId("run-status")).toHaveText("일시정지됨");

  await page.getByRole("button", { name: "12장짜리 PPT 제작" }).click();
  worklog = page.getByLabel("Active run workspace");
  await expect(worklog.getByRole("heading", { name: "12장짜리 PPT 제작" })).toBeVisible();
  await expect(worklog.getByTestId("run-status")).toHaveText("실행 중");
  await expect.poll(async () => Number(await worklog.getByTestId("run-progress-value").textContent())).toBeGreaterThan(34);
});

test("commercial workspace controls are wired", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "무엇을 실행할까요?" })).toBeVisible();

  await page.getByRole("button", { name: "워크벤치" }).click();
  await expect(page.getByRole("heading", { name: "코딩 · 디자인 · 리서치 · 문서" })).toBeVisible();
  const workbench = page.getByLabel("Workbench panel");
  await expect(workbench.getByText("코딩", { exact: true })).toBeVisible();
  await expect(workbench.getByText("디자인", { exact: true })).toBeVisible();
  await expect(workbench.getByText("리서치", { exact: true })).toBeVisible();
  await expect(workbench.getByText("문서", { exact: true })).toBeVisible();
  await expect(workbench.getByLabel("문서 실행 레인")).toContainText("파싱");
  await expect(workbench.getByText("다운로드 파일과 화면 프리뷰가 같은 artifact 레코드에서 나오는지 확인")).toBeVisible();
  await workbench.getByRole("button", { name: "바로 실행" }).first().click();
  let worklog = page.getByLabel("Active run workspace");
  await expect(worklog.getByRole("heading", { name: /코드베이스를 분석/ })).toBeVisible();
  await worklog.getByRole("button", { name: "실행 기록" }).click();
  await expect(page.getByLabel("Current run inspector").getByRole("heading", { name: /코드베이스를 분석/ })).toBeVisible();
  await page.getByRole("button", { name: "런 패널 닫기" }).click();

  await page.getByRole("textbox", { name: "작업 입력" }).fill("고양이 밈 생성 실험");
  await page.locator(".send-button").click();
  worklog = page.getByLabel("Active run workspace");
  await expect(worklog.getByRole("heading", { name: "고양이 밈 생성 실험" })).toBeVisible();
  await expect(worklog.locator(".active-run-timeline").getByText("요청 해석", { exact: true })).toBeVisible();
  await expect(worklog).not.toContainText("학습지원 분석");

  await page.getByRole("button", { name: "생산성 엔진 Manus 대비 절감 시간과 병렬 레인 측정" }).click();
  await expect(page.getByRole("heading", { name: "Manus 대비 생산성 계획" })).toBeVisible();
  await expect(page.getByText("예상 절감")).toBeVisible();
  await expect(page.getByText("병렬 실행 레인")).toBeVisible();
  await expect(page.getByLabel("병렬 레인 시간 분포")).toBeVisible();
  await expect(page.getByLabel("병렬 레인 시간 분포").locator(".lane-chart-row")).toHaveCount(3);
  await expect(page.getByText("스킬화 후보")).toBeVisible();
  await expect(page.getByText("다음 실행 액션")).toBeVisible();
  await page.getByRole("button", { name: "ledger 저장" }).click();
  await expect
    .poll(async () => page.evaluate(() => JSON.parse(localStorage.getItem("nanus-productivity-ledger") ?? "[]").length))
    .toBeGreaterThan(0);
  await page.getByLabel("Productivity panel").getByRole("button", { name: "패널 닫기" }).click();

  await page.getByRole("button", { name: "교육지원 사업 데이터를 분석하고 12장짜리 발표자료를 제작하세요." }).click();
  await expect(page.getByRole("textbox", { name: "작업 입력" })).toHaveValue(
    "/deck-from-brief 교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘",
  );
  await page.locator(".send-button").click();
  await expect(page.getByLabel("Active run workspace").getByRole("heading", { name: "교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘" })).toBeVisible();
  await page.getByLabel("Active run workspace").getByRole("button", { name: "실행 기록" }).click();
  await expect(page.getByLabel("Current run inspector").getByLabel("Artifact preview")).toContainText("초안.pptx");
  await expect(page.getByLabel("Current run inspector").getByLabel("Artifact preview")).toContainText("pptx");
  await page.getByRole("button", { name: "런 패널 닫기" }).click();

  await page.getByRole("button", { name: "스킬 선택" }).click();
  await expect(page.getByRole("heading", { name: "설치 가능한 스킬" })).toBeVisible();
  await page.getByRole("button", { name: "검토" }).click();
  await expect(page.getByRole("button", { name: /Manus Research Skill/ })).toBeVisible();

  await page.getByRole("textbox", { name: "작업 입력" }).fill("/");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
  await page.getByLabel("명령 입력").fill("settings");
  await page.getByRole("button", { name: /설정 열기/ }).click();
  await expect(page.getByRole("heading", { name: "작업공간 설정" })).toBeVisible();

  await page.getByRole("button", { name: "라이트", exact: true }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "컴팩트", exact: true }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("data-density", "compact");

  await page.getByRole("button", { name: "프로젝트 추가" }).click();
  await page.getByLabel("프로젝트 이름").fill("교육지원 사업 분석");
  await page.getByRole("button", { name: "생성", exact: true }).click();
  await expect(page.getByRole("button", { name: /교육지원 사업 분석/ })).toBeVisible();
});

test("mobile first screen does not clip primary workspace actions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "무엇을 실행할까요?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "스킬 생성 반복 작업을 팀 라이브러리로 승격" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Mobile" })).toBeVisible();
  await page.getByRole("button", { name: "Engine" }).click();
  await expect(page.getByRole("heading", { name: "Manus 대비 생산성 계획" })).toBeVisible();
  await page.getByRole("button", { name: "Work" }).click();
  await expect(page.getByRole("heading", { name: "코딩 · 디자인 · 리서치 · 문서" })).toBeVisible();
});
