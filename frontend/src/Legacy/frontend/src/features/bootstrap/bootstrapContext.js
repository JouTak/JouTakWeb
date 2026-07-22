import { createContext, useContext } from "react";

export const BootstrapContext = createContext(null);

export function useBootstrap() {
  const context = useContext(BootstrapContext);
  if (!context) {
    throw new Error("useBootstrap must be used inside BootstrapProvider");
  }
  return context;
}
