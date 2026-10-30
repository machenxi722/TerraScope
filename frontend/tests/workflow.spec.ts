import { test, expect } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const config = Object.fromEntries(
  readFileSync(resolve("../.env"), "utf-8")
    .split("\n")
    .filter((l) => l && !l.startsWith("#"))
    .map((l) => {
      const i = l.indexOf("=");
      return [l.slice(0, i), l.slice(i + 1)];
    }),
);

test("真实业务闭环：建项、案例、分析、地图、复核持久化、报告下载", async ({
  page,
}) => {
  const errors: string[] = [];
  const externalRequests: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (["127.0.0.1", "localhost"].includes(url.hostname))
      return route.continue();
    externalRequests.push(url.origin);
    return route.abort();
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  mkdirSync(resolve("../docs/evidence"), { recursive: true });
  await page.screenshot({
    path: resolve("../docs/evidence/ui-login.png"),
    animations: "disabled",
  });
  await page
    .getByLabel("用户名", { exact: true })
    .fill(config.TERRA_ADMIN_USERNAME);
  await page
    .getByLabel("密码", { exact: true })
    .fill(config.TERRA_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("heading", { name: "项目概览" })).toBeVisible();
  await page.getByRole("button", { name: "创建项目", exact: true }).click();
  const projectName = "验收项目 " + Date.now();
  await page.getByLabel("项目名称", { exact: true }).fill(projectName);
  await page.getByRole("button", { name: "保存项目", exact: true }).click();
  const card = page.locator("section.panel").filter({
    has: page.getByRole("heading", { name: projectName, exact: true }),
  });
  await card.getByRole("button", { name: "进入项目" }).click();
  await page.getByRole("button", { name: "从案例库导入" }).click();
  await page.getByLabel("搜索案例 ID", { exact: true }).fill("7301");
  const caseRow = page
    .locator(".case-tile")
    .filter({ has: page.getByText("7301", { exact: true }) });
  await caseRow.getByRole("button", { name: "导入", exact: true }).click();
  await page.getByRole("button", { name: "关闭此对话框" }).click();
  await page.getByRole("button", { name: "打开工作台" }).click();
  await page.getByRole("tab", { name: "分析设置", exact: true }).click();
  await page.getByRole("button", { name: "提交分析", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await expect(page.getByText("152,585", { exact: true })).toBeVisible();
  await expect(page.getByText("701,440", { exact: true })).toBeVisible();
  await expect(page.locator(".map-target canvas").first()).toBeVisible();
  const firstVersion = await page
    .locator(".result-option.selected .mono")
    .innerText();
  await page.getByRole("tab", { name: "分析设置", exact: true }).click();
  await page.getByRole("button", { name: "提交分析", exact: true }).click();
  await expect(page.locator(".result-option")).toHaveCount(2);
  const latestVersion = await page
    .locator(".result-option.selected .mono")
    .innerText();
  expect(latestVersion).not.toBe(firstVersion);
  await page.getByRole("button", { name: "下一个结果", exact: true }).click();
  await expect(page.locator(".result-option.selected")).toContainText(
    firstVersion,
  );
  await page.getByRole("button", { name: "上一个结果", exact: true }).click();
  await expect(page.locator(".result-option.selected")).toContainText(
    latestVersion,
  );
  await expect(
    page.getByRole("button", { name: "上一个结果", exact: true }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "可视化", exact: true }).click();
  // Filtering must not discard the selected result or its unsaved review.
  await page.getByLabel("筛选结果日期", { exact: true }).fill("2000-01-01");
  await expect(
    page.getByText("没有符合筛选条件的结果。", { exact: false }),
  ).toBeVisible();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await page.getByRole("button", { name: "重置筛选", exact: true }).click();
  await expect(page.locator(".result-option.selected")).toBeVisible();
  await page.getByRole("combobox", { name: "筛选数据来源" }).press("Enter");
  await page.getByRole("option", { name: "外部导入", exact: true }).click();
  await expect(page.locator(".filter-notice")).toBeVisible();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await page.getByRole("button", { name: "重置筛选", exact: true }).click();
  await page.getByRole("button", { name: "原始影像", exact: true }).click();
  await expect(page.locator(".map-label").first()).toHaveText("原始影像");
  await page.getByRole("button", { name: "预测图层", exact: true }).click();
  await page.getByText("卷帘", { exact: true }).first().click();
  await expect(page.locator(".swipe-divider")).toBeVisible();
  await page.getByText("同步对比", { exact: true }).click();
  await expect(page.getByRole("img", { name: "同步对比视图" })).toBeVisible();
  await page.getByRole("button", { name: "适配全图", exact: true }).click();
  await page.mouse.move(800, 120);
  await page.screenshot({
    path: resolve("../docs/evidence/ui-comparison.png"),
    animations: "disabled",
  });
  await page.getByText("叠加", { exact: true }).click();
  await page.getByRole("button", { name: "适配全图", exact: true }).click();
  await page.getByRole("button", { name: "区域选择", exact: true }).click();
  await page.getByRole("button", { name: "圈选复核区域" }).click();
  const map = page.getByRole("img", { name: "影像判读视图" });
  await map.scrollIntoViewIfNeeded();
  const box = (await map.boundingBox())!;
  await page.mouse.click(box.x + box.width * 0.35, box.y + box.height * 0.35, {
    delay: 150,
  });
  await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.35, {
    delay: 150,
  });
  await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.6, {
    delay: 150,
  });
  await page.mouse.click(box.x + box.width * 0.35, box.y + box.height * 0.35, {
    delay: 150,
  });
  await expect(page.getByText(/已圈选 1 个区域/)).toBeVisible();
  await page
    .getByLabel("复核判断依据")
    .fill("端到端验收：已核对真实道路边界，保留现场调查要求。");
  await page.getByRole("button", { name: "保存复核", exact: true }).click();
  await expect(page.getByText("v1 · 确认结果", { exact: true })).toBeVisible();
  await page.screenshot({
    path: resolve("../docs/evidence/ui-review.png"),
    animations: "disabled",
  });
  await page.reload();
  await page
    .getByRole("button", { name: "人工复核", exact: true })
    .last()
    .click();
  await expect(
    page.getByText("端到端验收：已核对真实道路边界，保留现场调查要求。", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(/已圈选 1 个区域/)).toBeVisible();
  await page.getByRole("link", { name: "影像资料", exact: true }).click();
  await page.getByRole("button", { name: "打开工作台" }).click();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await expect(page.getByText(/已圈选 1 个区域/)).toBeVisible();
  const pane = (await page.locator(".parameter-panel").boundingBox())!;
  const stage = (await page.locator(".geo-stage").boundingBox())!;
  expect(pane.width / 1366).toBeCloseTo(0.4, 2);
  expect(stage.y).toBe(0);
  expect(stage.width / 1366).toBeCloseTo(0.6, 2);
  mkdirSync(resolve("../docs/evidence"), { recursive: true });
  await page.getByRole("button", { name: "适配全图", exact: true }).click();
  await page.mouse.move(800, 120);
  await page.getByRole("button", { name: "填充视图", exact: true }).click();
  await page.mouse.move(800, 120);
  await page.screenshot({
    path: resolve("../docs/evidence/workbench.png"),
    fullPage: true,
    animations: "disabled",
  });
  // Collapsing panes resizes OpenLayers without losing the active prediction.
  const canvasWidth = (await map.boundingBox())!.width;
  await page.getByRole("button", { name: "统计分析", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  expect((await map.boundingBox())!.width).toBe(canvasWidth);
  await page.getByRole("button", { name: "关闭工具面板", exact: true }).click();
  await page.getByRole("button", { name: "收起参数面板", exact: true }).click();
  await expect
    .poll(async () => (await map.boundingBox())!.width)
    .toBeGreaterThan(canvasWidth + 400);
  await page.getByRole("button", { name: "展开参数面板", exact: true }).click();
  for (const viewport of [
    { width: 1024, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.getByRole("button", { name: "适配全图", exact: true }).click();
    await expect(map).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow, `horizontal overflow at ${viewport.width}px`).toBe(false);
    await page.getByRole("button", { name: "填充视图", exact: true }).click();
    await page.mouse.move(20, 20);
    await page.screenshot({
      path: resolve(`../docs/evidence/ui-${viewport.width}.png`),
      animations: "disabled",
    });
  }
  await page.setViewportSize({ width: 1366, height: 900 });
  await page.getByRole("button", { name: "统计分析", exact: true }).click();
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await page.getByRole("button", { name: "生成报告", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "ZIP 证据包" }).first(),
  ).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "ZIP 证据包" }).first().click();
  const download = await downloadPromise;
  await download.saveAs(resolve("../docs/evidence/7301-evidence.zip"));
  await page.getByRole("link", { name: "实验评估", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "实验评估", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("58.28%", { exact: true }).first()).toBeVisible();
  const library = await (await page.request.get("/api/v1/cases/summary")).json();
  if (library.total > 10)
    await expect(page.getByRole("button", { name: "导入并分析", exact: true }).first()).toBeVisible();
  else
    await expect(page.getByText("仅统计记录", { exact: true }).first()).toBeVisible();
  await page.getByRole("link", { name: "系统设置", exact: true }).click();
  const capabilities = await (
    await page.request.get("/api/v1/system/capabilities")
  ).json();
  await expect(
    page.getByText(
      capabilities.live_inference.available ? "已连接" : "未连接",
      { exact: true },
    ),
  ).toBeVisible();
  expect(errors).toEqual([]);
  expect(externalRequests).toEqual([]);
});
