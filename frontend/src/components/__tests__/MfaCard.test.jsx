import { create as createWebAuthnCredential } from "@github/webauthn-json";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MfaCard from "../account/MfaCard.jsx";

const addToast = vi.fn();

vi.mock("@github/webauthn-json", () => ({
  create: vi.fn(),
  get: vi.fn(),
}));

vi.mock("qrcode", () => ({
  default: { toDataURL: vi.fn() },
}));

vi.mock("@gravity-ui/uikit", async () => {
  return {
    Button: ({ children, loading, ...props }) => (
      <button {...props} disabled={props.disabled || loading}>
        {children}
      </button>
    ),
    Label: ({ children }) => <span>{children}</span>,
    Loader: () => <div>loading</div>,
    Modal: ({ open, children }) => (open ? <div>{children}</div> : null),
    TextInput: ({ label, value, onUpdate, disabled }) => (
      <label>
        <span>{label}</span>
        <input
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
  activateTotp: vi.fn(),
  addWebAuthnCredential: vi.fn(),
  authenticateWithWebAuthnCredential: vi.fn(),
  deactivateTotp: vi.fn(),
  deleteWebAuthnCredentials: vi.fn(),
  getMfaConfig: vi.fn().mockResolvedValue({
    supported_types: [],
    passkey_login_enabled: false,
  }),
  getRecoveryCodes: vi.fn(),
  getTotpStatus: vi.fn().mockResolvedValue({
    enabled: false,
    authenticator: null,
    recovery_codes_generated: false,
    blocked_by_email_verification: false,
    secret: "",
    totp_url: "",
  }),
  getWebAuthnRegistrationOptions: vi.fn(),
  getWebAuthnRequestOptions: vi.fn(),
  listAuthenticators: vi.fn().mockResolvedValue([]),
  reauthenticateWithMfaCode: vi.fn(),
  reauthenticateWithPassword: vi.fn(),
  regenerateRecoveryCodes: vi.fn(),
  renameWebAuthnCredential: vi.fn(),
}));

describe("MfaCard", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    addToast.mockClear();
  });

  it("shows a blocked state when email is not verified", async () => {
    const { findByText } = render(
      <MfaCard
        profile={{
          has_2fa: false,
          email_verified: false,
        }}
      />,
    );

    expect(await findByText("Email не подтверждён")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Двухфакторная защита недоступна, пока email не подтверждён.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Настроить" })).toBeNull();
  });

  it("passes the WebAuthn creation options directly to the browser API", async () => {
    window.PublicKeyCredential = function PublicKeyCredential() {};

    const {
      addWebAuthnCredential,
      getMfaConfig,
      getTotpStatus,
      getWebAuthnRegistrationOptions,
      listAuthenticators,
    } = await import("../../services/api");

    const creationOptions = {
      publicKey: {
        rp: { id: "joutak.ru", name: "JouTak" },
        challenge: "abc",
        user: { name: "user@example.com", id: "MQ", displayName: "user" },
        pubKeyCredParams: [],
        excludeCredentials: [],
        authenticatorSelection: {
          residentKey: "required",
          userVerification: "required",
          requireResidentKey: true,
        },
        extensions: { credProps: true },
      },
    };

    getMfaConfig.mockResolvedValue({
      supported_types: ["webauthn"],
      passkey_login_enabled: true,
    });
    getTotpStatus.mockResolvedValue({
      enabled: false,
      authenticator: null,
      recovery_codes_generated: false,
      blocked_by_email_verification: false,
      secret: "",
      totp_url: "",
    });
    listAuthenticators.mockResolvedValue([]);
    getWebAuthnRegistrationOptions.mockResolvedValue(creationOptions);
    createWebAuthnCredential.mockResolvedValue({ id: "credential-1" });
    addWebAuthnCredential.mockResolvedValue({
      recovery_codes_generated: false,
    });

    render(
      <MfaCard
        profile={{
          has_2fa: false,
          email_verified: true,
        }}
      />,
    );

    const controls = await screen.findAllByRole("button", {
      name: "Управление",
    });
    fireEvent.click(controls.at(-1));
    fireEvent.click(
      screen.getByRole("button", { name: "Добавить ключ безопасности" }),
    );

    await waitFor(() => {
      expect(createWebAuthnCredential).toHaveBeenCalledWith(creationOptions);
    });
  });
});
