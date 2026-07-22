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
});
