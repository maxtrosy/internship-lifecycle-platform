import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      watch: { usePolling: env.VITE_USE_POLLING === "true" },
      proxy: {
        "/health": apiTarget,
        "/auth": apiTarget,
        "/opportunities": apiTarget,
        "/applications": apiTarget,
        "/placements": apiTarget,
        "/invitations": apiTarget,
        "/policies": apiTarget,
        "/notifications": apiTarget,
        "/reports": apiTarget,
      },
    },
  };
});
