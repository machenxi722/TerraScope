import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const config = Object.fromEntries(
  readFileSync(resolve("../.env"), "utf8")
    .split("\n")
    .filter((s) => s && !s.startsWith("#"))
    .map((s) => [s.slice(0, s.indexOf("=")), s.slice(s.indexOf("=") + 1)]),
);
async function login(page: Page) {
  await page.goto("/login");
  await page
    .getByLabel("用户名", { exact: true })
    .fill(config.TERRA_ADMIN_USERNAME);
  await page
    .getByLabel("密码", { exact: true })
    .fill(config.TERRA_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "项目概览", exact: true }),
  ).toBeVisible();
  return (await (await page.request.get("/api/v1/auth/me")).json()).csrf_token;
}
async function project(page: Page, csrf: string) {
  const response = await page.request.post("/api/v1/projects", {
    headers: { "X-CSRF-Token": csrf },
    data: { name: `接口回归 ${Date.now()}` },
  });
  expect(response.ok()).toBeTruthy();
  const created = await response.json();
  await page.evaluate(
    (id) => localStorage.setItem("terra_project", id),
    created.id,
  );
  return created;
}
test("实验记录按策略导入、导出，外部掩膜完成后自动打开新结果", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const csrf = await login(page);
  await project(page, csrf);
  await page.goto("/experiments");
  await page.getByPlaceholder("按样本 ID 搜索").fill("7301");
  await page.getByRole("combobox", { name: "评估策略" }).press("Enter");
  await page.getByRole("option", { name: "优化单视图", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "导入并分析", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("img", { name: "单视图与四视图全局 IoU 对比" })
      .locator("canvas"),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../docs/evidence/connections-experiments.png"),
    animations: "disabled",
  });
  const csvDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出逐景 CSV" }).click();
  expect((await csvDownload).suggestedFilename()).toBe(
    "floodnet-test-single_view.csv",
  );
  await page.getByRole("button", { name: "导入并分析", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("20.96%");
  await expect(page.locator(".map-label").first()).toContainText("single_view");
  const initialPrediction = new URL(page.url()).searchParams.get("prediction");
  expect(initialPrediction).toBeTruthy();
  await page.getByRole("tab", { name: "分析设置", exact: true }).click();
  await page.getByRole("button", { name: "导入外部结果", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "导入外部结果" });
  await dialog.getByLabel("外部掩膜").setInputFiles({
    name: "7301.png",
    mimeType: "image/png",
    buffer: readFileSync(resolve("../data/demo/images/7301/tta4.png")),
  });
  await expect
    .poll(
      async () =>
        JSON.parse(await dialog.getByLabel("外部结果元数据").inputValue())
          .mask_sha256,
    )
    .toMatch(/^[0-9a-f]{64}$/);
  const meta = JSON.parse(
    await dialog.getByLabel("外部结果元数据").inputValue(),
  );
  meta.source = "外部导入接口回归";
  meta.strategy = "tta4";
  await dialog.getByLabel("外部结果元数据").fill(JSON.stringify(meta));
  await dialog.getByRole("button", { name: "校验并导入", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await expect(page.locator(".result-option.selected")).toContainText(
    "外部导入",
  );
  await expect(page.getByLabel("当前分析任务")).toContainText("已完成");
  expect(new URL(page.url()).searchParams.get("prediction")).not.toBe(
    initialPrediction,
  );
  await page.getByRole("button", { name: "下一个结果", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("20.96%");
  await expect
    .poll(() => new URL(page.url()).searchParams.get("prediction"))
    .toBe(initialPrediction);
  await page.reload();
  await expect(page.getByTestId("coverage")).toHaveText("20.96%");
  await page.getByRole("link", { name: "实验评估", exact: true }).click();
  await page.getByPlaceholder("按样本 ID 搜索").fill("7301");
  await page.getByRole("combobox", { name: "评估策略" }).press("Enter");
  await page.getByRole("option", { name: "优化单视图", exact: true }).click();
  await page.getByRole("button", { name: "查看结果", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("20.96%");
  await page.screenshot({
    path: resolve("../docs/evidence/connections-workbench.png"),
    animations: "disabled",
  });
  expect(errors).toEqual([]);
});
test("会话失效跳回登录，重新登录返回原页面", async ({ page }) => {
  const csrf = await login(page);
  await page.request.post("/api/v1/auth/logout", {
    headers: { "X-CSRF-Token": csrf },
  });
  await page.getByRole("link", { name: "系统设置", exact: true }).click();
  await expect(page).toHaveURL(/\/login\?redirect=/);
  await page
    .getByLabel("用户名", { exact: true })
    .fill(config.TERRA_ADMIN_USERNAME);
  await page
    .getByLabel("密码", { exact: true })
    .fill(config.TERRA_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(
    page.getByRole("heading", { name: "系统设置", exact: true }),
  ).toBeVisible();
});
test("成员编辑与移除、审计记录刷新", async ({ page }) => {
  const csrf = await login(page);
  const created = await project(page, csrf);
  const username = `audit_${Date.now()}`;
  const headers = { "X-CSRF-Token": csrf };
  const response = await page.request.post("/api/v1/users", {
    headers,
    data: { username, password: "connection-ui-test-password" },
  });
  expect(response.ok()).toBeTruthy();
  await page.request.put(`/api/v1/projects/${created.id}/members`, {
    headers,
    data: { username, role: "viewer" },
  });
  await page.goto("/settings");
  const row = page
    .getByRole("row")
    .filter({ has: page.getByText(username, { exact: true }) });
  await row.getByRole("button", { name: "编辑", exact: true }).click();
  await expect(page.getByPlaceholder("填写已有账号")).toHaveValue(username);
  await row.getByRole("button", { name: "移除", exact: true }).click();
  await page
    .locator(".el-popconfirm")
    .getByRole("button", { name: "移除", exact: true })
    .click();
  await expect(row).toHaveCount(0);
  await expect(
    page.getByRole("cell", { name: "member.remove", exact: true }),
  ).toBeVisible();
});
