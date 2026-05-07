import { Button, DropdownMenu, Loader, useToaster } from "@gravity-ui/uikit";
import { useEffect, useState } from "react";

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
      return decodeURIComponent(trimmed.slice("csrftoken=".length));
    }
  }
  return "";
}

export default function OauthCard() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  // We only render the "no providers available" copy after the backend
  // has *actually* responded successfully. Otherwise a transient error
  // (or a slow response) briefly flashes the empty state before we
  // even know whether any providers exist, which looks like a bug to
  // the user.
  const [ready, setReady] = useState(false);
  const { add } = useToaster();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const list = await getOAuthProviders();
        if (cancelled) return;
        setProviders(Array.isArray(list) ? list : []);
        setReady(true);
      } catch (error) {
        void error;
        // Keep `ready` false so we don't render a misleading empty
        // state when the request failed. The card will just stay in
        // its loading shimmer until the next retry/remount.
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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
    <SectionCard>
      <h3 style={{ margin: 0, fontSize: 18 }}>Связанные аккаунты</h3>
      {loading || !ready ? (
        <Loader size="m" />
      ) : providers?.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {providers.map((p) => (
            <div key={p.id} style={row}>
              <div style={{ textTransform: "capitalize" }}>{p.name}</div>
              <DropdownMenu
                size="m"
                renderSwitcher={(props) => (
                  <Button {...props} view="outlined">
                    Действия
                  </Button>
                )}
                items={[
                  { text: "Связать", action: () => connectProvider(p.id) },
                ]}
              />
            </div>
          ))}
        </div>
      ) : (
        <div style={{ opacity: 0.8 }}>Доступных провайдеров нет.</div>
      )}
    </SectionCard>
  );
}
