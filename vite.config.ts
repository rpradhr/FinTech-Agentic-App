import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// Forward /api/* to the FastAPI backend during development.
// Override with VITE_API_PROXY_TARGET (e.g. http://localhost:8000).
const target = process.env.VITE_API_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  vite: {
    server: {
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
      },
    },
  },
});
