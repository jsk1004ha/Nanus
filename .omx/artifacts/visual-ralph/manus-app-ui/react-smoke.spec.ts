import { expect, test } from "@playwright/test";

test("commercial workspace controls are wired", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "무엇을 실행할까요?" })).toBeVisible();

  await page.getByPlaceholder("작업을 할당하거나 /를 입력하여 더 많은 옵션을 확인하세요").fill("고양이 밈 생성 실험");
  await page.locator(".send-button").click();
  await expect(page.getByRole("heading", { name: "고양이 밈 생성 실험" })).toBeVisible();
  await expect(page.getByText("요청 해석")).toBeVisible();
  await expect(page.locator(".run-panel")).not.toContainText("학습지원 분석");
  await page.getByRole("button", { name: "런 패널 닫기" }).click();

  await page.getByRole("button", { name: "교육지원 사업 데이터를 분석하고 12장짜리 발표자료를 제작하세요." }).click();
  await expect(page.getByPlaceholder("작업을 할당하거나 /를 입력하여 더 많은 옵션을 확인하세요")).toHaveValue(
    "/deck-from-brief 교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘",
  );
  await page.locator(".send-button").click();
  await expect(page.getByRole("heading", { name: "교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘" })).toBeVisible();

  await page.getByRole("button", { name: "스킬 선택" }).click();
  await expect(page.getByRole("heading", { name: "설치 가능한 스킬" })).toBeVisible();
  await page.getByRole("button", { name: "검토" }).click();
  await expect(page.getByRole("button", { name: /Manus Research Skill/ })).toBeVisible();

  await page.getByPlaceholder("작업을 할당하거나 /를 입력하여 더 많은 옵션을 확인하세요").fill("/");
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
});
