import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://localhost:8000",
      "/auth": "http://localhost:8000",
      "/opportunities": "http://localhost:8000",
      "/applications": "http://localhost:8000",
      "/placements": "http://localhost:8000",
      "/invitations": "http://localhost:8000",
      "/policies": "http://localhost:8000",
    },
  },
});
