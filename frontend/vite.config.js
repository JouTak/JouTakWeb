import process from "node:process";

import react from "@vitejs/plugin-react-swc";
import { defineConfig, loadEnv } from "vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyTarget =
    env.DEV_BACKEND_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";
  const usePolling =
    String(process.env.CHOKIDAR_USEPOLLING || env.CHOKIDAR_USEPOLLING)
      .trim()
      .toLowerCase() === "true";
  const backendProxy = () => ({
    target: backendProxyTarget,
    changeOrigin: false,
  });

  return {
    plugins: [react()],
    server: {
      strictPort: true,
      watch: {
        usePolling,
      },
      proxy: {
        "/accounts": backendProxy(),
        "/api": backendProxy(),
        "/bff": backendProxy(),
        "/health": backendProxy(),
        "/media": backendProxy(),
      },
    },
    css: {
      modules: {
        localsConvention: "camelCaseOnly",
      },
      preprocessorOptions: {
        scss: {
          api: "modern-compiler",
          additionalData: `@use "/src/assets/__fonts.scss" as *;`,
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.js"],
      exclude: ["e2e/**", "node_modules/**", "dist/**"],
      restoreMocks: true,
      clearMocks: true,
      pool: "threads",
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom", "react-router-dom"],
            gravity: ["@gravity-ui/uikit", "@gravity-ui/icons"],
          },
        },
      },
    },
  };
});
