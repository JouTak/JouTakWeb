import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { hasStoredAuth, me, readStoredTokens } from "../services/api";
import RequireAuth from "./RequireAuth";
vi.mock("../services/api", () => ({
  hasStoredAuth: vi.fn(),
  me: vi.fn(),
  readStoredTokens: vi.fn(),
}));
function Destination() {
  const l = useLocation();
  return (
    <p>
      {l.pathname}
      {l.search}
    </p>
  );
}
const renderRoute = () =>
  render(
    <MemoryRouter initialEntries={["/account?tab=city#invitations"]}>
      <Routes>
        <Route
          path="/account"
          element={
            <RequireAuth>
              <p>Protected</p>
            </RequireAuth>
          }
        />
        <Route path="/session-expired" element={<Destination />} />
      </Routes>
    </MemoryRouter>,
  );
describe("Protected navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hasStoredAuth.mockReturnValue(true);
    readStoredTokens.mockReturnValue({});
  });
  afterEach(cleanup);
  it("preserves the complete destination for a guest", async () => {
    hasStoredAuth.mockReturnValue(false);
    renderRoute();
    expect(await screen.findByText(/reason=auth_required/)).toHaveTextContent(
      "next=%2Faccount%3Ftab%3Dcity%23invitations",
    );
    expect(me).not.toHaveBeenCalled();
  });
  it("retries a temporary error without opening private content", async () => {
    me.mockRejectedValueOnce({
      response: { status: 503 },
    }).mockResolvedValueOnce({ username: "player" });
    renderRoute();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Не удалось проверить вход",
    );
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(await screen.findByText("Protected")).toBeInTheDocument();
  });
  it("never opens the page during pending MFA", async () => {
    readStoredTokens.mockReturnValue({ pending_mfa: true });
    renderRoute();
    expect(await screen.findByText(/reason=mfa_required/)).toBeInTheDocument();
    expect(me).not.toHaveBeenCalled();
  });
  it("handles real expiration", async () => {
    me.mockRejectedValue({ response: { status: 410 } });
    renderRoute();
    await waitFor(() =>
      expect(
        screen.getByText(/reason=SESSION_UNAUTHORIZED/),
      ).toBeInTheDocument(),
    );
  });
});
