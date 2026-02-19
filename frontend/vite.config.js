import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          gravity: ["@gravity-ui/uikit", "@gravity-ui/icons"],
          bootstrap: ["bootstrap/dist/js/bootstrap.bundle.min.js"],
        },
      },
    },
  },
});
