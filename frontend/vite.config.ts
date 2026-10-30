import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    watch: { ignored: ["**/test-results/**", "**/playwright-report/**"] },
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  test: { include: ["src/**/*.test.ts"] },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          maps: ["ol"],
          charts: ["echarts"],
          ui: ["element-plus"],
        },
      },
    },
  },
});
