import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { tokenStore } from "../../services/auth/tokenStore";
import AuthModal from "../AuthModal.jsx";

const navigate = vi.fn();
const addToast = vi.fn();

afterEach(cleanup);

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
  announceAuthenticatedSession: vi.fn(),
  finalizeSessionAuthentication: vi.fn(),
  getMfaConfig: vi.fn().mockResolvedValue({
    supported_types: ["totp", "webauthn", "recovery_codes"],
    passkey_login_enabled: false,
  }),
  getWebAuthnRequestOptions: vi.fn(),
  me: vi.fn(),
  requestPasswordReset: vi.fn(),
}));

const {
  announceAuthenticatedSession,
  authenticateMfaCode,
  doLogin,
  finalizeSessionAuthentication,
  me,
} = await import("../../services/api");

describe("AuthModal MFA flow", () => {
  beforeEach(() => {
    sessionStorage.clear();
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
    expect(me).toHaveBeenCalled();
    expect(announceAuthenticatedSession).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/account/security", {
      replace: true,
    });
  });
});

async function submitPasswordLogin() {
  fireEvent.change(screen.getByLabelText("Email или старый логин"), {
    target: { value: "player@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Пароль"), {
    target: { value: "StrongPass123!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Войти" }));
}

describe("AuthModal completion ordering", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    doLogin.mockResolvedValue({ status: "authenticated" });
    finalizeSessionAuthentication.mockResolvedValue({});
    me.mockResolvedValue({
      account_active: true,
      personalization_ui_enabled: false,
    });
  });

  it("waits for the profile before announcing auth and navigating", async () => {
    let resolveProfile;
    me.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveProfile = resolve;
      }),
    );
    render(
      <MemoryRouter>
        <AuthModal open successRedirectTo="/account/security" />
      </MemoryRouter>,
    );
    await submitPasswordLogin();
    await waitFor(() => expect(me).toHaveBeenCalledTimes(1));
    expect(finalizeSessionAuthentication).toHaveBeenCalledTimes(1);
    expect(announceAuthenticatedSession).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
    resolveProfile({ account_active: true, personalization_ui_enabled: false });
    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith("/account/security", {
        replace: true,
      }),
    );
    expect(announceAuthenticatedSession).toHaveBeenCalledTimes(1);
  });

  it("does not load the profile or announce login after a failed exchange", async () => {
    finalizeSessionAuthentication.mockRejectedValueOnce(
      new Error("Exchange unavailable"),
    );
    render(
      <MemoryRouter>
        <AuthModal open successRedirectTo="/account/security" />
      </MemoryRouter>,
    );
    await submitPasswordLogin();
    await waitFor(() =>
      expect(addToast).toHaveBeenCalledWith(
        expect.objectContaining({ theme: "danger" }),
      ),
    );
    expect(me).not.toHaveBeenCalled();
    expect(announceAuthenticatedSession).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("does not mark an unfinished MFA session complete when the modal closes", async () => {
    tokenStore.set({ session_token: "pending", pending_mfa: true });
    doLogin.mockResolvedValueOnce({ status: "pending_mfa", types: ["totp"] });
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <AuthModal open onClose={onClose} />
      </MemoryRouter>,
    );
    await submitPasswordLogin();
    await screen.findByText("Подтверждение входа");
    fireEvent.click(screen.getByRole("button", { name: "Закрыть" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(tokenStore.get().pending_mfa).toBe(true);
    expect(announceAuthenticatedSession).not.toHaveBeenCalled();
  });
});
