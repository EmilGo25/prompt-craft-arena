/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The backend base URL is read from VITE_API_BASE at build/runtime
// (defaults to http://localhost:8000 in src/config.ts).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  // Allow Cloudflare quick-tunnel hosts (scripts/share.sh) to reach the
  // `vite preview` server — otherwise Vite 403s the random *.trycloudflare.com Host.
  preview: { allowedHosts: [".trycloudflare.com"] },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
    // unit tests only — keep Playwright's e2e/*.spec.ts out of Vitest
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
