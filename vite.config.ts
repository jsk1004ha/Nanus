import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendProxy = {
  "/api": "http://127.0.0.1:8765",
  "/mcp": "http://127.0.0.1:8765",
  "/ws": {
    target: "ws://127.0.0.1:8765",
    ws: true,
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: backendProxy,
  },
  preview: {
    proxy: backendProxy,
  },
});
