import { useEffect, useState } from "react";

import { me } from "../services/api";
import {
  AUTH_STATE_EVENT,
  hasStoredAuth,
  readStoredTokens,
} from "../services/auth/tokenStore";

function canLoadProfile() {
  return hasStoredAuth() && !readStoredTokens().pending_mfa;
}

export function useAuthProfile(authOpen) {
  const [state, setState] = useState(() => ({
    profile: null,
    loadingProfile: canLoadProfile(),
  }));

  useEffect(() => {
    let sequence = 0;
    let active = true;
    async function load() {
      const request = ++sequence;
      if (!canLoadProfile()) return;
      try {
        const profile = await me();
        if (active && request === sequence && canLoadProfile()) {
          setState({ profile, loadingProfile: false });
        }
      } catch {
        if (active && request === sequence) {
          setState({ profile: null, loadingProfile: false });
        }
      }
    }
    function onAuthChanged() {
      setState({ profile: null, loadingProfile: canLoadProfile() });
      void load();
    }
    window.addEventListener(AUTH_STATE_EVENT, onAuthChanged);
    if (!authOpen) void load();
    return () => {
      active = false;
      window.removeEventListener(AUTH_STATE_EVENT, onAuthChanged);
    };
  }, [authOpen]);

  return state;
}
