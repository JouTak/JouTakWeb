import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountSecurity from "../AccountSecurity.jsx";

const navigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

vi.mock("@gravity-ui/uikit", async () => {
  return {
    Button: ({ children, onClick, disabled, loading, ...props }) => (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled || loading}
        {...props}
      >
        {children}
      </button>
    ),
  };
});

vi.mock("../../components/account/AccountHero.jsx", () => ({
  default: () => <div>account-hero</div>,
}));
vi.mock("../../components/account/DeleteAccountCard.jsx", () => ({
  default: () => <div>delete-account-card</div>,
}));
vi.mock("../../components/account/EmailCard.jsx", () => ({
  default: () => <div>email-card</div>,
}));
vi.mock("../../components/account/MfaCard.jsx", () => ({
  default: () => <div>mfa-card</div>,
}));
vi.mock("../../components/account/PasswordCard.jsx", () => ({
  default: () => <div>password-card</div>,
}));
vi.mock("../../components/account/ProfileCard.jsx", () => ({
  default: () => <div>profile-card</div>,
}));
vi.mock("../../components/account/SessionsCard.jsx", () => ({
  default: () => <div>sessions-card</div>,
}));
vi.mock("../../services/api", () => ({
  getEmailStatus: vi.fn(),
  listSessionsHeadless: vi.fn(),
  me: vi.fn(),
}));

const { getEmailStatus, listSessionsHeadless, me } = await import(
  "../../services/api"
);

function buildProfile(overrides = {}) {
  return {
    username: "player",
    email: "player@example.com",
    profile_state: "basic",
    profile_complete: false,
    account_active: false,
    registration_completed: false,
    profile_tier: "basic",
    personalization_ui_enabled: true,
    personalization_interstitial_enabled: true,
    personalization_enforce_enabled: false,
    personalization_context: "new_registration",
    personalization_prompt_variant: "registration_setup",
    missing_fields: ["vk_username"],
    ...overrides,
  };
}

describe("AccountSecurity feature flag rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigate.mockReset();
    getEmailStatus.mockResolvedValue({
      email: "player@example.com",
      verified: false,
      pending_email: "",
      resend_target: "",
    });
    listSessionsHeadless.mockResolvedValue({ sessions: [] });
  });

  afterEach(() => {
    cleanup();
  });

  it("shows the personalization gate for an account with the UI flag enabled", async () => {
    me.mockResolvedValue(
      buildProfile({
        personalization_ui_enabled: true,
        personalization_interstitial_enabled: true,
      }),
    );

    render(
      <MemoryRouter>
        <AccountSecurity />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(
        "Для доступа к аккаунту нужен завершённый профиль",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Завершить персонализацию")).toBeInTheDocument();
    expect(screen.queryByText("account-hero")).toBeNull();
  });

  it("keeps the account page open when the UI flag is disabled", async () => {
    me.mockResolvedValue(
      buildProfile({
        personalization_ui_enabled: false,
        personalization_interstitial_enabled: false,
      }),
    );

    render(
      <MemoryRouter>
        <AccountSecurity />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("account-hero")).toBeInTheDocument();
    });
    expect(
      screen.queryByText("Для доступа к аккаунту нужен завершённый профиль"),
    ).toBeNull();
    expect(screen.getByText("profile-card")).toBeInTheDocument();
  });
});
