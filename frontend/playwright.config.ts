import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: process.env.TERRA_E2E_URL || "http://127.0.0.1:5173",
    viewport: { width: 1366, height: 900 },
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.TERRA_CHROME_PATH
      ? { executablePath: process.env.TERRA_CHROME_PATH }
      : {},
  },
  reporter: [["list"], ["html", { open: "never" }]],
});
