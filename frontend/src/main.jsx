import "bootstrap/dist/css/bootstrap.min.css";
import "@gravity-ui/uikit/styles/fonts.css";
import "@gravity-ui/uikit/styles/styles.css";
import "./assets/index.css";

import {
  configure,
  ThemeProvider,
  ToasterComponent,
  ToasterProvider,
} from "@gravity-ui/uikit";
import { createRoot } from "react-dom/client";

import App from "./App.jsx";
import { BootstrapProvider } from "./features/bootstrap/BootstrapProvider.jsx";
import { setupOpenTelemetry } from "./observability/otel.js";
import { setupAxiosInterceptors } from "./services/api";
import { migrateLegacyTokenStorage } from "./services/auth/tokenStore";

migrateLegacyTokenStorage();
setupOpenTelemetry();
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
        <BootstrapProvider>
          <App />
        </BootstrapProvider>
        <ToasterComponent />
      </ToasterProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById("root")).render(<Root />);
