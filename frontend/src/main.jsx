import React from "react";
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

setupAxiosInterceptors(() => {
  localStorage.removeItem("joutak_auth");
  delete axios.defaults.headers.common["Authorization"];
  window.location.href = "/login";
});

configure({ lang: "ru" });

function Root() {
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
