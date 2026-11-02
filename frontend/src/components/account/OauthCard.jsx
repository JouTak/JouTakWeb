import { Button, Loader, useToaster } from "@gravity-ui/uikit";
import { useCallback, useEffect, useRef, useState } from "react";

import { getOAuthLink, getOAuthProviders } from "../../services/api";
import { SectionCard } from "../ui/primitives";

const row = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

function readCsrfToken() {
  if (typeof document === "undefined") return "";
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const raw of cookies) {
    const trimmed = raw.trim();
    if (trimmed.startsWith("csrftoken=")) {
      const rawValue = trimmed.slice("csrftoken=".length);
      try {
        return decodeURIComponent(rawValue);
      } catch {
        return rawValue;
      }
    }
  }
  return "";
}

export default function OauthCard({ embedded = false, linkedProviders = [] }) {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const requestSeqRef = useRef(0);
  const mountedRef = useRef(false);
  const isCancelledRef = useRef(false);
  const { add } = useToaster();

  const loadProviders = useCallback(async () => {
    const requestSeq = ++requestSeqRef.current;
    setLoading(true);
    setLoadError(null);
    try {
      const list = await getOAuthProviders();
      if (
        !mountedRef.current ||
        isCancelledRef.current ||
        requestSeq !== requestSeqRef.current
      ) {
        return;
      }
      setProviders(Array.isArray(list) ? list : []);
      setReady(true);
    } catch (error) {
      if (
        !mountedRef.current ||
        isCancelledRef.current ||
        requestSeq !== requestSeqRef.current
      ) {
        return;
      }
      setReady(true);
      setLoadError(error);
    } finally {
      if (
        mountedRef.current &&
        !isCancelledRef.current &&
        requestSeq === requestSeqRef.current
      ) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    isCancelledRef.current = false;
    void loadProviders();
    return () => {
      mountedRef.current = false;
      isCancelledRef.current = true;
    };
  }, [loadProviders]);

  function submitPost(url, fields = {}) {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = url;
    const csrfToken = readCsrfToken();
    const mergedFields = csrfToken
      ? { csrfmiddlewaretoken: csrfToken, ...fields }
      : { ...fields };
    Object.entries(mergedFields).forEach(([k, v]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = k;
      input.value = v == null ? "" : String(v);
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  }

  async function connectProvider(providerId) {
    try {
      const { url, method } = await getOAuthLink(
        providerId,
        "/account/security#linked",
      );
      if (method === "GET") {
        window.location.href = url;
        return;
      }
      const u = new URL(url, window.location.origin);
      const params = Object.fromEntries(u.searchParams.entries());
      submitPost(u.toString(), params);
    } catch (error) {
      const response = error?.response?.data;
      if (response?.error_code === "PROFILE_PERSONALIZATION_REQUIRED") {
        add({
          name: "oauth-personalization-required",
          title: "Сначала заверши персонализацию профиля",
          content:
            "Связка внешних аккаунтов доступна после заполнения обязательных полей.",
          theme: "warning",
        });
        return;
      }
      add({
        name: "oauth-link-error",
        title: "Ошибка",
        content: "Не удалось получить ссылку провайдера",
        theme: "danger",
      });
    }
  }

  return (
    <SectionCard plain={embedded}>
      {!embedded && (
        <h3 style={{ margin: 0, fontSize: 18 }}>Связанные аккаунты</h3>
      )}
      {linkedProviders.length > 0 && (
        <p>Подключены: {linkedProviders.join(", ")}</p>
      )}
      {loading || !ready ? (
        <Loader size="m" />
      ) : loadError ? (
        <div role="alert">
          <p>Не удалось загрузить список провайдеров.</p>
          <Button view="outlined" onClick={() => void loadProviders()}>
            Повторить
          </Button>
        </div>
      ) : providers.length ? (
        <div className="security-session-list">
          {providers.map((provider) => (
            <div key={provider.id} style={{ ...row, flexWrap: "wrap" }}>
              <span style={{ textTransform: "capitalize" }}>
                {provider.name}
              </span>
              {linkedProviders.includes(provider.id) ? (
                <span className="security-muted">Подключён</span>
              ) : (
                <Button
                  view="outlined"
                  onClick={() => connectProvider(provider.id)}
                  extraProps={{ "aria-label": `Подключить ${provider.name}` }}
                >
                  Подключить
                </Button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="security-muted">
          Другие способы входа пока не настроены.
        </p>
      )}
    </SectionCard>
  );
}
