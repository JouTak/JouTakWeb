import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthModal from "../AuthModal.jsx";

const navigate = vi.fn();
const addToast = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

vi.mock("@gravity-ui/uikit", async () => {
  return {
    Button: ({
      children,
      onClick,
      type = "button",
      disabled,
      loading,
      ...props
    }) => (
      <button
        type={type}
        onClick={onClick}
        disabled={disabled || loading}
        {...props}
      >
        {children}
      </button>
    ),
    Modal: ({ open, children }) => (open ? <div>{children}</div> : null),
    TextInput: ({
      value,
      onUpdate,
      type = "text",
      "aria-label": ariaLabel,
      label,
      controlRef,
      disabled,
    }) => (
      <label>
        <span>{label || ariaLabel}</span>
        <input
          ref={controlRef}
          aria-label={ariaLabel || label}
          type={type}
          value={value}
          disabled={disabled}
          onChange={(event) => onUpdate(event.target.value)}
        />
      </label>
    ),
    useToaster: () => ({ add: addToast }),
  };
});

vi.mock("../../services/api", () => ({
  doLogin: vi.fn(),
  doSignupAndLogin: vi.fn(),
  authenticateMfaCode: vi.fn(),
  authenticateWithWebAuthnCredential: vi.fn(),
  finalizeSessionAuthentication: vi.fn(),
  getMfaConfig: vi.fn().mockResolvedValue({
    supported_types: ["totp", "webauthn", "recovery_codes"],
    passkey_login_enabled: false,
  }),
  getWebAuthnRequestOptions: vi.fn(),
  me: vi.fn(),
  requestPasswordReset: vi.fn(),
}));

const { authenticateMfaCode, doLogin, finalizeSessionAuthentication, me } =
  await import("../../services/api");

describe("AuthModal MFA flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigate.mockReset();
    addToast.mockReset();
    finalizeSessionAuthentication.mockResolvedValue({});
    me.mockResolvedValue({
      email: "player@example.com",
      has_2fa: true,
      personalization_ui_enabled: false,
      account_active: true,
    });
  });

  it("switches from password login to MFA code confirmation", async () => {
    doLogin.mockResolvedValue({
      status: "pending_mfa",
      types: ["totp"],
    });
    authenticateMfaCode.mockResolvedValue({});

    render(
      <MemoryRouter>
        <AuthModal
          open
          onClose={vi.fn()}
          successRedirectTo="/account/security"
        />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Email или старый логин"), {
      target: { value: "player@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Пароль"), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect(await screen.findByText("Подтверждение входа")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Код подтверждения"), {
      target: { value: "314159" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить вход" }));

    await waitFor(() => {
      expect(authenticateMfaCode).toHaveBeenCalledWith("314159");
    });
    expect(finalizeSessionAuthentication).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/account/security", {
      replace: true,
    });
  });
});
