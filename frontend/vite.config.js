import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
});
