import { createContext, useContext } from "react";

export const HubContext = createContext({
  flags: {},
  loading: false,
  error: null,
});
export const useHub = () => useContext(HubContext);
