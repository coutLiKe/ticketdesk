import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The browser only ever talks to this dev server. Requests to /api/... are forwarded to the
// FastAPI container, so the page and the API share one origin and no CORS setup is needed.
const apiTarget = process.env.API_TARGET ?? "http://localhost:8000";

// Where the built site is served from. "/" locally; a GitHub Pages project site lives under
// "/<repo>/", which the deploy workflow sets through VITE_BASE.
const base = process.env.VITE_BASE ?? "/";

export default defineConfig({
  base,
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, "") },
    },
  },
});
