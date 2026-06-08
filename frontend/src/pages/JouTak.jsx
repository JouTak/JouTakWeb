import { useStringFlagValue } from "@openfeature/react-sdk";
import { useEffect, useState } from "react";

import { getHomepagePayload, pickFeatureOverrideParams } from "../services/api";
import HomepageV2 from "./joutak/HomepageV2.jsx";
import LegacyHomepage from "./joutak/LegacyHomepage.jsx";

const FALLBACK_HOMEPAGE_CONTENT = {
  hero: {
    title: "JouTak",
    description:
      "Интерфейс доступен без backend. API-зависимые действия будут падать, пока бэкенд не поднят.",
    server_ip: "mc.joutak.ru",
    primary_cta: {
      href: "https://joutak.ru",
      label: "Открыть JouTak",
    },
    secondary_cta: {
      to: "/joutak/pay",
      label: "Оплатить проходку",
    },
  },
  carousel: [],
  projects: [],
  events: [],
  gallery: [],
  faq: [],
};

export default function JouTak() {
  const bootstrapVariant = useStringFlagValue(
    "site_homepage_version",
    "legacy",
  );
  const [state, setState] = useState({
    payload: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadHomepage() {
      try {
        const params = pickFeatureOverrideParams(window.location.search);
        const payload = await getHomepagePayload(params);
        if (!cancelled) {
          setState({
            payload,
            loading: false,
            error: null,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            payload: null,
            loading: false,
            error,
          });
        }
      }
    }

    loadHomepage();

    return () => {
      cancelled = true;
    };
  }, [bootstrapVariant]);

  if (state.loading && !state.payload) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }

  if (state.error && !state.payload) {
    if (bootstrapVariant === "v2") {
      return <HomepageV2 content={FALLBACK_HOMEPAGE_CONTENT} />;
    }
    return <LegacyHomepage content={FALLBACK_HOMEPAGE_CONTENT} />;
  }

  const variant = state.payload?.variant || bootstrapVariant || "legacy";
  const content = state.payload?.content || FALLBACK_HOMEPAGE_CONTENT;

  if (variant === "v2") {
    return <HomepageV2 content={content} />;
  }

  return <LegacyHomepage content={content} />;
}
