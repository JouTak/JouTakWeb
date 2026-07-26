import { createContext, useContext } from "react";

export const ThemePreferenceContext = createContext(null);

export function useThemePreference() {
  const context = useContext(ThemePreferenceContext);
  if (!context) {
    throw new Error(
      "useThemePreference must be used inside ThemePreferenceProvider",
    );
  }
  return context;
}
