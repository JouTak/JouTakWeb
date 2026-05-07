import { useStringFlagValue } from "@openfeature/react-sdk";
import { useEffect, useState } from "react";

import { getHomepagePayload, pickFeatureOverrideParams } from "../services/api";
import HomepageV2 from "./joutak/HomepageV2.jsx";
import LegacyHomepage from "./joutak/LegacyHomepage.jsx";

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
    return (
      <div className="py-5 text-center text-danger">
        Не удалось загрузить главную страницу.
      </div>
    );
  }

  const variant = state.payload?.variant || bootstrapVariant || "legacy";
  const content = state.payload?.content || {};

  if (variant === "v2") {
    return <HomepageV2 content={content} />;
  }

  return <LegacyHomepage content={content} />;
}
