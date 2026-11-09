import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyReq, req) => {
            const origin = req.headers.origin;
            // Only rewrite the two explicit local Vite origins; arbitrary sites retain
            // their Origin and are rejected by the API's same-origin write protection.
            if (
              origin === "http://127.0.0.1:5173" ||
              origin === "http://localhost:5173"
            )
              proxyReq.setHeader("Origin", "http://127.0.0.1:8010");
          });
        },
      },
    },
  },
  build: { outDir: "dist" },
});
