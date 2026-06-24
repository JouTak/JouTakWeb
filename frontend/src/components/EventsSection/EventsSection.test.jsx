import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EventsSection from "./EventsSection.jsx";

describe("EventsSection", () => {
  it("adapts legacy string events to the new cards", () => {
    render(<EventsSection items={["Командные стройки"]} />);

    expect(
      screen.getByRole("heading", { name: "Событие 1" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Командные стройки")).toBeInTheDocument();
  });
});
