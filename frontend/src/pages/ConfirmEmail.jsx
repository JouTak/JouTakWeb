import { Button, Loader } from "@gravity-ui/uikit";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  confirmEmailVerification,
  hasStoredAuth,
  inspectEmailVerification,
} from "../services/api";

const cardStyle = {
  maxWidth: 760,
  margin: "0 auto",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 20,
  display: "grid",
  gap: 12,
};

function extractErrorMessage(error, fallback) {
  const errors = error?.response?.data?.errors;
  if (Array.isArray(errors)) {
    const first = errors.find(
      (entry) =>
        entry &&
        typeof entry === "object" &&
        typeof entry.message === "string" &&
        entry.message.trim(),
    );
    if (first?.message) {
      return first.message;
    }
  }
  return error?.response?.data?.detail || fallback;
}

export default function ConfirmEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const key = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get("key") || "").trim();
  }, [location.search]);
  const isAuthenticated = hasStoredAuth();
  const accountPath = isAuthenticated ? "/account/security" : "/login";

  useEffect(() => {
    let active = true;

    async function load() {
      if (!key) {
        setError("В ссылке отсутствует ключ подтверждения email.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const response = await inspectEmailVerification(key);
        if (!active) {
          return;
        }
        setEmail(response?.data?.email || "");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(
          extractErrorMessage(
            err,
            "Ссылка подтверждения недействительна или уже устарела.",
          ),
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [key]);

  async function onConfirm() {
    setBusy(true);
    setError("");
    try {
      await confirmEmailVerification(key);
      setSuccess(true);
    } catch (err) {
      setError(
        extractErrorMessage(
          err,
          "Не удалось подтвердить email. Попробуйте запросить новое письмо.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={cardStyle}>
      <h2 style={{ margin: 0 }}>Подтверждение email</h2>

      {loading ? (
        <Loader size="m" />
      ) : success ? (
        <>
          <p style={{ margin: 0, opacity: 0.9 }}>Email успешно подтверждён.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button view="action" onClick={() => navigate(accountPath)}>
              {isAuthenticated ? "Перейти в аккаунт" : "Войти"}
            </Button>
            <Button view="outlined" onClick={() => navigate("/joutak")}>
              На главную
            </Button>
          </div>
        </>
      ) : error ? (
        <>
          <p style={{ margin: 0, opacity: 0.9 }}>{error}</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button view="outlined" onClick={() => navigate(accountPath)}>
              {isAuthenticated ? "Вернуться в аккаунт" : "Ко входу"}
            </Button>
            <Button view="flat" onClick={() => navigate("/joutak")}>
              На главную
            </Button>
          </div>
        </>
      ) : (
        <>
          <p style={{ margin: 0, opacity: 0.9 }}>
            {email
              ? `Подтвердите адрес ${email}, чтобы завершить операцию.`
              : "Подтвердите адрес электронной почты, чтобы завершить операцию."}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button view="action" loading={busy} onClick={onConfirm}>
              Подтвердить email
            </Button>
            <Button view="outlined" onClick={() => navigate("/joutak")}>
              Отмена
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
