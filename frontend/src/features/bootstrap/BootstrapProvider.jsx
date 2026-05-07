import { OpenFeatureProvider } from "@openfeature/react-sdk";
import PropTypes from "prop-types";
import { useEffect, useMemo, useState } from "react";

import {
  getBootstrap,
  pickFeatureOverrideParams,
} from "../../services/api/bffApi";
import { AUTH_STATE_EVENT } from "../../services/auth/tokenStore";
import {
  initializeOpenFeature,
  updateFeatureConfiguration,
} from "../featureFlags/openFeature.js";
import { BootstrapContext } from "./bootstrapContext.js";

function RouteFallback() {
  return <div className="py-5 text-center text-secondary">Загрузка...</div>;
}

export function BootstrapProvider({ children, fallback = <RouteFallback /> }) {
  const [state, setState] = useState({
    bootstrap: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    initializeOpenFeature();

    async function loadBootstrap() {
      setState((current) => ({
        bootstrap: current.bootstrap,
        loading: true,
        error: null,
      }));

      try {
        const params = pickFeatureOverrideParams(window.location.search);
        const bootstrap = await getBootstrap(params);
        await updateFeatureConfiguration(bootstrap?.features || {});
        if (!cancelled) {
          setState({
            bootstrap,
            loading: false,
            error: null,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            bootstrap: null,
            loading: false,
            error,
          });
        }
      }
    }

    loadBootstrap();

    const handleAuthStateChange = () => {
      loadBootstrap();
    };
    window.addEventListener(AUTH_STATE_EVENT, handleAuthStateChange);

    return () => {
      cancelled = true;
      window.removeEventListener(AUTH_STATE_EVENT, handleAuthStateChange);
    };
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      reload: async () => {
        const params = pickFeatureOverrideParams(window.location.search);
        const bootstrap = await getBootstrap(params);
        await updateFeatureConfiguration(bootstrap?.features || {});
        setState({
          bootstrap,
          loading: false,
          error: null,
        });
        return bootstrap;
      },
    }),
    [state],
  );

  if (state.loading && !state.bootstrap) {
    return fallback;
  }

  if (state.error && !state.bootstrap) {
    return (
      <div className="py-5 text-center text-danger">
        Не удалось загрузить конфигурацию интерфейса.
      </div>
    );
  }

  return (
    <OpenFeatureProvider>
      <BootstrapContext.Provider value={value}>
        {children}
      </BootstrapContext.Provider>
    </OpenFeatureProvider>
  );
}

BootstrapProvider.propTypes = {
  children: PropTypes.node.isRequired,
  fallback: PropTypes.node,
};
