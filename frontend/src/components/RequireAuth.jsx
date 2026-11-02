import { Button, Loader } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { hasStoredAuth, me, readStoredTokens } from "../services/api";

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [status, setStatus] = useState("checking");

  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setStatus("checking");
    let cancelled = false;

    async function verify() {
      if (!hasStoredAuth() || readStoredTokens()?.pending_mfa) {
        if (!cancelled)
          setStatus(
            readStoredTokens()?.pending_mfa ? "mfa_required" : "auth_required",
          );
        return;
      }
      try {
        await me();
        if (!cancelled) setStatus("ok");
      } catch (error) {
        if (!cancelled)
          setStatus(
            [401, 410].includes(error?.response?.status)
              ? "SESSION_UNAUTHORIZED"
              : "error",
          );
      }
    }

    verify();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  if (status === "ok") {
    return children;
  }

  if (status === "checking") {
    return (
      <section
        style={{
          display: "grid",
          placeItems: "center",
          minHeight: 200,
        }}
      >
        <Loader size="m" />
      </section>
    );
  }

  if (status === "error")
    return (
      <section className="hub-panel" role="alert">
        <h1>Не удалось проверить вход</h1>
        <p>Проверьте соединение и повторите попытку.</p>
        <Button onClick={() => setAttempt((value) => value + 1)}>
          Повторить
        </Button>
      </section>
    );
  const next = location.pathname + location.search + location.hash;
  const params = new URLSearchParams({
    reason: status,
    next,
  });

  return <Navigate to={`/session-expired?${params.toString()}`} replace />;
}

RequireAuth.propTypes = {
  children: PropTypes.node.isRequired,
};
