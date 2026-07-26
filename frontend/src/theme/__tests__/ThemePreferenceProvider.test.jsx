import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useThemePreference } from "../themeContext";
import {
  THEME_STORAGE_KEY,
  ThemePreferenceProvider,
} from "../ThemePreferenceProvider";

function Consumer() {
  const { theme, toggleTheme } = useThemePreference();
  return (
    <button type="button" onClick={toggleTheme}>
      {theme}
    </button>
  );
}

describe("ThemePreferenceProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("defaults to dark and persists a light preference", () => {
    render(
      <ThemePreferenceProvider>
        <Consumer />
      </ThemePreferenceProvider>,
    );

    expect(screen.getByRole("button")).toHaveTextContent("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("button")).toHaveTextContent("light");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("falls back from corrupt storage and synchronizes tabs", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "sepia");
    render(
      <ThemePreferenceProvider>
        <Consumer />
      </ThemePreferenceProvider>,
    );
    expect(screen.getByRole("button")).toHaveTextContent("dark");

    fireEvent(
      window,
      new StorageEvent("storage", {
        key: THEME_STORAGE_KEY,
        newValue: "light",
      }),
    );
    expect(screen.getByRole("button")).toHaveTextContent("light");
  });

  it("keeps switching when storage writes are blocked", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked");
    });
    render(
      <ThemePreferenceProvider>
        <Consumer />
      </ThemePreferenceProvider>,
    );

    expect(() => fireEvent.click(screen.getByRole("button"))).not.toThrow();
    expect(screen.getByRole("button")).toHaveTextContent("light");
  });
});
