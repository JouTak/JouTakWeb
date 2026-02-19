import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { setupAxiosInterceptors } from "./services/api";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";

import {
  ThemeProvider,
  ToasterProvider,
  ToasterComponent,
  configure,
} from "@gravity-ui/uikit";
import "@gravity-ui/uikit/styles/fonts.css";
import "@gravity-ui/uikit/styles/styles.css";

import "./assets/index.css";

setupAxiosInterceptors(({ reason } = {}) => {
  const currentPath = window.location.pathname || "/";
  const isProtectedAccountPage = currentPath.startsWith("/account/");
  const isSessionExpiredPage = currentPath === "/session-expired";

  if (!isProtectedAccountPage || isSessionExpiredPage) {
    return;
  }

  const next = window.location.pathname;
  const params = new URLSearchParams({
    reason: reason || "SESSION_UNAUTHORIZED",
    next,
  });
  window.location.replace(`/session-expired?${params.toString()}`);
});

configure({ lang: "ru" });

export function Root() {
  return (
    <ThemeProvider theme="dark">
      <ToasterProvider>
        <App />
        <ToasterComponent />
      </ToasterProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById("root")).render(<Root />);
