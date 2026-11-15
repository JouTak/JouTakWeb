import { useEffect, useState } from "react";

import { requestWithSession } from "../services/auth/sessionClient";
import { AUTH_STATE_EVENT } from "../services/auth/tokenStore";
import { rootClient } from "../services/http/client";

export function useBootstrapFeatures() {
  const [features, setFeatures] = useState({});
  const [loading, setLoading] = useState(true);
  const [authVersion, setAuthVersion] = useState(0);

  useEffect(() => {
    const handleAuthChange = () => {
      setLoading(true);
      setFeatures({});
      setAuthVersion((version) => version + 1);
    };

    window.addEventListener(AUTH_STATE_EVENT, handleAuthChange);
    return () => window.removeEventListener(AUTH_STATE_EVENT, handleAuthChange);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    requestWithSession("get", "/bff/bootstrap", {
      client: rootClient,
      hardLogoutOn401: false,
      signal: controller.signal,
    })
      .then((response) => {
        if (!controller.signal.aborted) {
          setFeatures(response.data?.features ?? {});
          setLoading(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFeatures({});
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [authVersion]);

  return { features, loading };
}
