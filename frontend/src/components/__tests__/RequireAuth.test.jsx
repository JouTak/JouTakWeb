import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { me } from "../../services/api";
import { tokenStore } from "../../services/auth/tokenStore";
import RequireAuth from "../RequireAuth.jsx";

vi.mock("../../services/api", async () => ({
  ...(await vi.importActual("../../services/auth/tokenStore")),
  me: vi.fn(),
}));

afterEach(cleanup);
beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

function ReturnPath() {
  const location = useLocation();
  return <p>{new URLSearchParams(location.search).get("next")}</p>;
}

function renderProtectedPage() {
  render(
    <MemoryRouter initialEntries={["/account/security?tab=sessions#current"]}>
      <Routes>
        <Route
          path="/account/security"
          element={
            <RequireAuth>
              <p>Protected account</p>
            </RequireAuth>
          }
        />
        <Route path="/session-expired" element={<ReturnPath />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("protected route return path", () => {
  it("preserves the query and fragment for login", async () => {
    renderProtectedPage();
    expect(
      await screen.findByText("/account/security?tab=sessions#current"),
    ).toBeInTheDocument();
    expect(me).not.toHaveBeenCalled();
  });

  it("does not load account data with an unfinished MFA session", async () => {
    tokenStore.set({ session_token: "pending", pending_mfa: true });
    renderProtectedPage();
    expect(
      await screen.findByText("/account/security?tab=sessions#current"),
    ).toBeInTheDocument();
    expect(me).not.toHaveBeenCalled();
  });
});
