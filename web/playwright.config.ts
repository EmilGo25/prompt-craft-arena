import { defineConfig, devices } from "@playwright/test";

// E2E + mobile-visual tests run against an isolated stack on test ports
// (backend 8123 with the offline stub generator + random judge, frontend 5180),
// so they never touch the dev servers on 8000/5173.
const BACKEND = "http://localhost:8123";
const FRONTEND = "http://localhost:5180";

// All projects use Chromium (it emulates mobile viewport + touch); the iPhone
// presets would otherwise pull in WebKit.
const mobile = (name: string) => ({ ...devices[name], browserName: "chromium" as const });

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: FRONTEND,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "iphone-se", use: mobile("iPhone SE") },
    { name: "iphone-12", use: mobile("iPhone 12") },
    { name: "iphone-14-pro-max", use: mobile("iPhone 14 Pro Max") },
    { name: "galaxy-s9", use: mobile("Galaxy S9+") },
    { name: "pixel-5", use: mobile("Pixel 5") },
  ],
  webServer: [
    {
      command: "uv run uvicorn server.app:app --port 8123",
      cwd: "..",
      env: {
        IMAGE_PROVIDER: "stub",
        JUDGE: "random",
        LEADERBOARD_PATH: "./data/test_leaderboard.json",
        TOTAL_ROUNDS: "2",
        ROUND_SECONDS: "5",
      },
      url: `${BACKEND}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5180 --strictPort",
      env: { VITE_API_BASE: BACKEND },
      url: FRONTEND,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
