import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("AutoDL 实机结果、服务状态与地图显示", async ({ page }) => {
  test.skip(
    process.env.TERRA_VERIFY_LIVE_UI !== "1",
    "Run after scripts/verify_autodl.py with a live GPU service",
  );
  const evidence = JSON.parse(
    readFileSync(resolve("../docs/evidence/autodl-acceptance.json"), "utf8"),
  );
  const config = Object.fromEntries(
    readFileSync(resolve("../.env"), "utf8")
      .split("\n")
      .filter((line) => line && !line.startsWith("#"))
      .map((line) => {
        const i = line.indexOf("=");
        return [
          line.slice(0, i),
          line.slice(i + 1).replace(/^(['"])(.*)\1$/, "$2"),
        ];
      }),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page
    .getByLabel("用户名", { exact: true })
    .fill(config.TERRA_ADMIN_USERNAME);
  await page
    .getByLabel("密码", { exact: true })
    .fill(config.TERRA_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("heading", { name: "项目概览" })).toBeVisible();
  await page.goto(
    `/workbench/${evidence.image_id}?prediction=${evidence.runs[1].prediction_id}`,
  );
  await expect(page.getByTestId("coverage")).toHaveText("21.75%");
  await expect(page.locator(".result-option.selected")).toContainText(
    "本次推理",
  );
  await expect(page.locator(".map-target canvas").first()).toBeVisible();
  await page.screenshot({
    path: resolve("../docs/evidence/autodl-workbench.png"),
    animations: "disabled",
  });
  await page.getByRole("tab", { name: "分析设置", exact: true }).click();
  await expect(page.getByText(/NVIDIA A800 80GB PCIe/)).toBeVisible();
  await page.screenshot({
    path: resolve("../docs/evidence/autodl-connected.png"),
    animations: "disabled",
  });
  await page.goto("/settings");
  await expect(
    page.getByText("NVIDIA A800 80GB PCIe", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("已连接", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
