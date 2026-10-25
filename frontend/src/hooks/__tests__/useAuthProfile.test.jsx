import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { me } from "../../services/api";
import {
  clearAuthStorage,
  markPendingMfaSession,
  writeStoredTokens,
} from "../../services/auth/tokenStore";
import { useAuthProfile } from "../useAuthProfile";

vi.mock("../../services/api", () => ({ me: vi.fn() }));
afterEach(() => {
  cleanup();
  clearAuthStorage();
  vi.resetAllMocks();
});

it("loads once and ignores a profile response arriving after logout", async () => {
  writeStoredTokens({ session_token: "session" });
  let resolve;
  me.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const { result } = renderHook(() => useAuthProfile(false));
  expect(result.current.loadingProfile).toBe(true);
  expect(me).toHaveBeenCalledTimes(1);
  act(() => clearAuthStorage());
  await act(async () => resolve({ email: "old@example.com" }));
  expect(result.current.profile).toBeNull();
  expect(result.current.loadingProfile).toBe(false);
});

it("waits for completed MFA before loading the account", async () => {
  writeStoredTokens({ session_token: "session", pending_mfa: true });
  me.mockResolvedValue({ email: "player@example.com" });
  const { result } = renderHook(() => useAuthProfile(false));
  expect(me).not.toHaveBeenCalled();
  act(() => markPendingMfaSession(false));
  await waitFor(() =>
    expect(result.current.profile?.email).toBe("player@example.com"),
  );
  expect(me).toHaveBeenCalledTimes(1);
});
