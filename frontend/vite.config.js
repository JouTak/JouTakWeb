import process from "node:process";

import react from "@vitejs/plugin-react-swc";
import { defineConfig, loadEnv } from "vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyTarget =
    env.DEV_BACKEND_PROXY_TARGET?.trim() || "http://127.0.0.1:8080";
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
      server: {
        deps: {
          inline: [/@gravity-ui\//],
        },
      },
      setupFiles: ["./src/test/setup.js"],
      exclude: ["e2e/**", "node_modules/**", "dist/**"],
      restoreMocks: true,
      clearMocks: true,
      pool: "threads",
    },
    build: {
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "react",
                test: /node_modules\/(react|react-dom|react-router|react-router-dom)\//,
              },
              {
                name: "gravity",
                test: /node_modules\/@gravity-ui\/(uikit|icons)\//,
              },
            ],
          },
        },
      },
    },
  };
});
