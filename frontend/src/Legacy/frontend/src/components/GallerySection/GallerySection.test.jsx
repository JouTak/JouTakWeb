import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import GallerySection from "./GallerySection.jsx";

describe("GallerySection", () => {
  it("cycles through BFF gallery images", async () => {
    const user = userEvent.setup();
    render(<GallerySection items={["/one.jpg", "/two.jpg"]} />);

    expect(screen.getByRole("img")).toHaveAttribute("src", "/one.jpg");

    await user.click(screen.getByRole("button", { name: "Следующее фото" }));

    expect(screen.getByRole("img")).toHaveAttribute("src", "/two.jpg");
    expect(screen.getByText("2/2")).toBeInTheDocument();
  });
});
