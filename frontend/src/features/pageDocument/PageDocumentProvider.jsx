import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState(null);
  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    if (!route) return undefined;
    const controller = new AbortController();
    async function load() {
      try {
        const document = validatePageDocument(
          await getPageDocument(route, { signal: controller.signal }),
        );
        if (!controller.signal.aborted)
          setResult({ route, revision, document, error: null });
      } catch (error) {
        if (!controller.signal.aborted)
          setResult({ route, revision, document: null, error });
      }
    }
    void load();
    return () => controller.abort();
  }, [route, revision]);

  useEffect(() => {
    window.addEventListener(AUTH_STATE_EVENT, reload);
    return () => window.removeEventListener(AUTH_STATE_EVENT, reload);
  }, [reload]);

  const value = useMemo(() => {
    const current = result?.route === route && result?.revision === revision;
    return {
      route,
      document: result?.route === route ? result.document : null,
      loading: Boolean(route) && !current,
      error: current ? result.error : null,
      reload,
    };
  }, [reload, result, revision, route]);

  return (
    <PageDocumentContext.Provider value={value}>
      {children}
    </PageDocumentContext.Provider>
  );
}

PageDocumentProvider.propTypes = { children: PropTypes.node.isRequired };
