import { useCallback, useEffect, useState } from "react";

import { useHub } from "../../features/hub/context";

export default function useResource(load, { retainOnReload = false } = {}) {
  const { viewer } = useHub();
  const viewerKey = viewer?.username || "guest";
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  });
  const reload = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    let cancelled = false;
    setState((previous) => ({
      data:
        retainOnReload &&
        previous.source === load &&
        previous.viewerKey === viewerKey
          ? previous.data
          : null,
      loading: true,
      error: null,
      source: load,
      viewerKey,
    }));
    Promise.resolve()
      .then(load)
      .then((data) => {
        if (!cancelled)
          setState({
            data,
            loading: false,
            error: null,
            source: load,
            viewerKey,
          });
      })
      .catch((error) => {
        if (!cancelled)
          setState({
            data: null,
            loading: false,
            error,
            source: load,
            viewerKey,
          });
      });
    return () => {
      cancelled = true;
    };
  }, [load, revision, viewerKey, retainOnReload]);
  return state.source === load && state.viewerKey === viewerKey
    ? { ...state, reload }
    : { data: null, loading: true, error: null, reload };
}
