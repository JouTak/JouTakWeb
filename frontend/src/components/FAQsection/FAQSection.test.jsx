import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import FAQSection from "./FAQSection.jsx";

const items = [
  {
    question: "Как подключиться?",
    answer: "Используйте адрес сервера.",
  },
];

describe("FAQSection", () => {
  it("reveals an answer when its question is toggled", async () => {
    const user = userEvent.setup();
    render(<FAQSection items={items} />);

    const toggle = screen.getByRole("button", { name: "Как подключиться?" });

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Используйте адрес сервера.")).not.toBeVisible();

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Используйте адрес сервера.")).toBeVisible();
  });
});
