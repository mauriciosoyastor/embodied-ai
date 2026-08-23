import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    open: false,
    proxy: {
      "/ws/percepcion": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
