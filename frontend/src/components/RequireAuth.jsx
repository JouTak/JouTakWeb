import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader } from "@gravity-ui/uikit";
import { hasStoredAuth, me } from "../services/api";

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (!hasStoredAuth()) {
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
