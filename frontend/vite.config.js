import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy API + WebSocket to the FastAPI backend (uvicorn on :8000).
const backend = process.env.BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/ws": { target: backend, ws: true },
    },
  },
});
