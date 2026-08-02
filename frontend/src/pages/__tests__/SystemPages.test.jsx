import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import Contact from "../Contact.jsx";
import NotFound from "../NotFound.jsx";
import SessionExpired from "../SessionExpired.jsx";

afterEach(cleanup);

function LocationProbe() {
  const location = useLocation();
  return <div>{`${location.pathname}${location.search}`}</div>;
}

describe("V2 system pages", () => {
  it("returns from 404 to the canonical ITMOcraft homepage", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/missing"]}>
        <Routes>
          <Route path="/" element={<div>ITMOcraft homepage</div>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(
      screen.getByRole("button", { name: "На главную ITMOcraft" }),
    );

    expect(screen.getByText("ITMOcraft homepage")).toBeInTheDocument();
  });

  it("preserves the safe return path when a session expires", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          "/session-expired?reason=PASSWORD_CHANGED&next=%2Faccount%2Fsecurity",
        ]}
      >
        <Routes>
          <Route path="/session-expired" element={<SessionExpired />} />
          <Route path="/login" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Пароль был изменён/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Войти снова" }));

    expect(
      screen.getByText("/login?next=%2Faccount%2Fsecurity"),
    ).toBeInTheDocument();
  });

  it("renders community destinations as external links", () => {
    render(
      <MemoryRouter>
        <Contact />
      </MemoryRouter>,
    );

    for (const name of ["Telegram", "VK", "Discord"]) {
      const link = screen.getByRole("link", { name: new RegExp(name, "i") });
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    }
  });
});
