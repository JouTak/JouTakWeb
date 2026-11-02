import { ThemeProvider } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ThemePreferenceContext } from "./themeContext";

export const THEME_STORAGE_KEY = "joutak_theme_v1";
const VALID_THEMES = new Set(["dark", "light"]);

function readTheme() {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return VALID_THEMES.has(stored) ? stored : "dark";
  } catch {
    return "dark";
  }
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export function ThemePreferenceProvider({ children }) {
  const [theme, setThemeState] = useState(readTheme);

  const setTheme = useCallback((nextTheme) => {
    const validTheme = VALID_THEMES.has(nextTheme) ? nextTheme : "dark";
    setThemeState(validTheme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, validTheme);
    } catch {
      // A blocked storage backend must not break theme switching.
    }
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    const synchronizeTabs = (event) => {
      if (event.key !== THEME_STORAGE_KEY) return;
      const nextTheme = VALID_THEMES.has(event.newValue)
        ? event.newValue
        : "dark";
      setThemeState(nextTheme);
    };
    window.addEventListener("storage", synchronizeTabs);
    return () => window.removeEventListener("storage", synchronizeTabs);
  }, []);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      toggleTheme: () => setTheme(theme === "dark" ? "light" : "dark"),
    }),
    [setTheme, theme],
  );

  return (
    <ThemePreferenceContext.Provider value={value}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </ThemePreferenceContext.Provider>
  );
}

ThemePreferenceProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
