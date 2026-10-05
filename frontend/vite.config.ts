import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser only ever talks to this dev server. Requests to /api/... are forwarded to the
// FastAPI container, so the page and the API share one origin and no CORS setup is needed.
const apiTarget = process.env.API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, "") },
    },
  },
});
