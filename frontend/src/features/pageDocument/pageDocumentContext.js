import { createContext, useContext } from "react";

export const PageDocumentContext = createContext(null);

export function usePageDocument() {
  const context = useContext(PageDocumentContext);
  if (!context) {
    throw new Error("usePageDocument must be used inside PageDocumentProvider");
  }
  return context;
}
