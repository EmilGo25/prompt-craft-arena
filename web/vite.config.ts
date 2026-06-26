import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend base URL is read from VITE_API_BASE at build/runtime
// (defaults to http://localhost:8000 in src/config.ts).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
