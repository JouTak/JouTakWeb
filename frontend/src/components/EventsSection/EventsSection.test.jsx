import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import events from "./events.data.js";
import EventsSection from "./EventsSection.jsx";

describe("EventSection", () => {
  it("shows event section properly", () => {
    render(<EventsSection events={events} />);
    screen.logTestingPlaygroundURL();
    expect(screen.getByRole("heading", { name: "Бункер" })).toBeInTheDocument();
  });

  it("renders an unfinished registration as disabled", () => {
    render(
      <EventsSection
        events={[
          {
            ...events[0],
            actionLabel: "Регистрация скоро",
            actionDisabled: true,
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Регистрация скоро" }),
    ).toBeDisabled();
  });
});
