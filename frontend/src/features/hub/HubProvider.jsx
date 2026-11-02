import { useEffect, useState } from "react";

import { requestWithSession } from "../../services/auth/sessionClient";
import { AUTH_STATE_EVENT } from "../../services/auth/tokenStore";
import { rootClient } from "../../services/http/client";
import { HubContext } from "./context";
import { PROFILE_CHANGED_EVENT } from "./profileEvents";

export default function HubProvider({ children }) {
  const [state, setState] = useState({ flags: {}, loading: true, error: null });
  const [attempt, setAttempt] = useState(0);
  const [profileRevision, setProfileRevision] = useState(0);
  useEffect(() => {
    const update = () => setProfileRevision((n) => n + 1);
    window.addEventListener(PROFILE_CHANGED_EVENT, update);
    return () => window.removeEventListener(PROFILE_CHANGED_EVENT, update);
  }, []);
  useEffect(() => {
    let active = true;
    let sequence = 0;
    async function load() {
      const current = ++sequence;
      setState({ flags: {}, loading: true, error: null });
      try {
        const { data } = await requestWithSession("get", "/bff/bootstrap", {
          client: rootClient,
          hardLogoutOn401: false,
        });
        if (active && current === sequence)
          setState({
            flags: data.features || {},
            viewer: data.viewer,
            loading: false,
            error: null,
          });
      } catch (error) {
        if (active && current === sequence)
          setState({ flags: {}, loading: false, error });
      }
    }
    load();
    window.addEventListener(AUTH_STATE_EVENT, load);
    return () => {
      active = false;
      window.removeEventListener(AUTH_STATE_EVENT, load);
    };
  }, [attempt]);
  return (
    <HubContext.Provider
      value={{
        ...state,
        profileRevision,
        reload: () => setAttempt((n) => n + 1),
      }}
    >
      {children}
    </HubContext.Provider>
  );
}
