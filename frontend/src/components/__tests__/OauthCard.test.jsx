import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OauthCard from "../account/OauthCard.jsx";

const addToast = vi.fn();

vi.mock("@gravity-ui/uikit", () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  DropdownMenu: () => <button type="button">menu</button>,
  Loader: () => <div data-testid="loader">loading</div>,
  useToaster: () => ({ add: addToast }),
}));

vi.mock("../../services/api", () => ({
  getOAuthLink: vi.fn(),
  getOAuthProviders: vi.fn(),
}));

const { getOAuthProviders } = await import("../../services/api");

describe("OauthCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addToast.mockClear();
    getOAuthProviders.mockReset();
  });

  it("shows an inline error and retry action when provider loading fails", async () => {
    getOAuthProviders
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce([{ id: "github", name: "github" }]);

    render(<OauthCard />);

    expect(
      await screen.findByText("Не удалось загрузить список провайдеров."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("loader")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));

    await waitFor(() => {
      expect(getOAuthProviders).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText("github")).toBeInTheDocument();
  });
});
