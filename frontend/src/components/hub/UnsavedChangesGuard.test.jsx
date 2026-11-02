import { ThemeProvider } from "@gravity-ui/uikit";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { useState } from "react";
import { createMemoryRouter, Link, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import UnsavedChangesGuard from "./UnsavedChangesGuard";

function Editor() {
  const [text, setText] = useState("");
  const [saved, setSaved] = useState("");
  return (
    <>
      <UnsavedChangesGuard dirty={text !== saved} />
      <label>
        Описание
        <input value={text} onChange={(event) => setText(event.target.value)} />
      </label>
      <button onClick={() => setSaved(text)}>Сохранить</button>
      <Link to="/cities">Каталог</Link>
    </>
  );
}
function setup() {
  const router = createMemoryRouter(
    [
      { path: "/edit", element: <Editor /> },
      { path: "/cities", element: <h1>Города</h1> },
    ],
    { initialEntries: ["/cities", "/edit"], initialIndex: 1 },
  );
  render(
    <ThemeProvider theme="dark">
      <RouterProvider router={router} />
    </ThemeProvider>,
  );
  return router;
}

afterEach(cleanup);
describe("unsaved hub forms", () => {
  it("keeps edits when navigation is cancelled and leaves only after confirmation", async () => {
    const router = setup();
    fireEvent.change(screen.getByLabelText("Описание"), {
      target: { value: "Черновик" },
    });
    fireEvent.click(screen.getByRole("link", { name: "Каталог" }));
    await screen.findByText("Покинуть страницу без сохранения?");
    expect(router.state.location.pathname).toBe("/edit");
    fireEvent.click(screen.getByRole("button", { name: "Остаться" }));
    expect(screen.getByLabelText("Описание")).toHaveValue("Черновик");
    await act(() => router.navigate(-1));
    await screen.findByRole("button", { name: "Уйти без сохранения" });
    fireEvent.click(
      screen.getByRole("button", { name: "Уйти без сохранения" }),
    );
    await screen.findByRole("heading", { name: "Города" });
  });
  it("allows saved navigation and prevents reload only for dirty forms", async () => {
    setup();
    fireEvent.change(screen.getByLabelText("Описание"), {
      target: { value: "Черновик" },
    });
    const dirtyEvent = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(dirtyEvent);
    expect(dirtyEvent.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    const cleanEvent = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(cleanEvent);
    expect(cleanEvent.defaultPrevented).toBe(false);
    fireEvent.click(screen.getByRole("link", { name: "Каталог" }));
    await screen.findByRole("heading", { name: "Города" });
    expect(
      screen.queryByText("Покинуть страницу без сохранения?"),
    ).not.toBeInTheDocument();
  });
});
