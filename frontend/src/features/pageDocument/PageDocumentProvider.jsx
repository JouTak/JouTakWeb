import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { getProductRoute } from "../../routing/pageRegistry";
import { getPageDocument } from "../../services/api/pageApi";
import { AUTH_STATE_EVENT } from "../../services/auth/tokenStore";
import { PageDocumentContext } from "./pageDocumentContext";
import { validatePageDocument } from "./validatePageDocument";

export function PageDocumentProvider({ children }) {
  const location = useLocation();
  const route = useMemo(
    () => getProductRoute(location.pathname),
    [location.pathname],
  );
  const sequence = useRef(0);
  const [state, setState] = useState({
    route: null,
    document: null,
    loading: false,
    error: null,
  });

  const load = useCallback(async (activeRoute, signal) => {
    const requestSequence = ++sequence.current;
    if (!activeRoute) {
      setState({
        route: null,
        document: null,
        loading: false,
        error: null,
      });
      return null;
    }
    setState((current) => ({
      route: activeRoute,
      document:
        current.route?.endpoint === activeRoute.endpoint
          ? current.document
          : null,
      loading: true,
      error: null,
    }));
    try {
      const document = validatePageDocument(
        await getPageDocument(activeRoute, { signal }),
      );
      if (signal?.aborted || requestSequence !== sequence.current) return null;
      setState({
        route: activeRoute,
        document,
        loading: false,
        error: null,
      });
      return document;
    } catch (error) {
      if (signal?.aborted || requestSequence !== sequence.current) return null;
      setState({
        route: activeRoute,
        document: null,
        loading: false,
        error,
      });
      return null;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(route, controller.signal);
    return () => controller.abort();
  }, [load, route]);

  useEffect(() => {
    const reloadAfterAuth = () => {
      const controller = new AbortController();
      void load(route, controller.signal);
    };
    window.addEventListener(AUTH_STATE_EVENT, reloadAfterAuth);
    return () => window.removeEventListener(AUTH_STATE_EVENT, reloadAfterAuth);
  }, [load, route]);

  const value = useMemo(
    () => ({
      ...state,
      reload: () => load(route),
    }),
    [load, route, state],
  );

  return (
    <PageDocumentContext.Provider value={value}>
      {children}
    </PageDocumentContext.Provider>
  );
}

PageDocumentProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
