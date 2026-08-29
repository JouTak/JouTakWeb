import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { hasStoredAuth, me, readStoredTokens } from "../services/api";
import { LoadingPage } from "./ui/PageShell.jsx";

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (!hasStoredAuth() || readStoredTokens()?.pending_mfa) {
        if (!cancelled) setStatus("denied");
        return;
      }
      try {
        await me();
        if (!cancelled) setStatus("ok");
      } catch {
        if (!cancelled) setStatus("denied");
      }
    }

    verify();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "ok") {
    return children;
  }

  if (status === "checking") {
    return <LoadingPage description="Проверяем защищённую сессию аккаунта" />;
  }

  const next = location.pathname;
  const params = new URLSearchParams({
    reason: "auth_required",
    next,
  });

  return <Navigate to={`/session-expired?${params.toString()}`} replace />;
}

RequireAuth.propTypes = {
  children: PropTypes.node.isRequired,
};
