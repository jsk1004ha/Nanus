import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".omx/artifacts/visual-ralph/manus-app-ui",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
