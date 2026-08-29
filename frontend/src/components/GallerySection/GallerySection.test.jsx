import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import GallerySection from "./GallerySection.jsx";

afterEach(cleanup);

describe("GallerySection", () => {
  it("cycles through gallery images", async () => {
    const testData = {
      title: "Галерея",
      galleryItems: [
        {
          label: "first",
          image: "/first-main.jpg",
          photos: ["/first-one.jpg", "/first-two.jpg"],
        },
        {
          label: "second",
          image: "/second-main.jpg",
          photos: ["/second-one.jpg", "/second-two.jpg"],
        },
      ],
      leftArrowSrc: "/img/left-btn-gallery.png",
      rightArrowSrc: "/img/right-btn-gallery.png",
    };
    const user = userEvent.setup();
    render(<GallerySection {...testData} />);
    expect(
      screen.getByRole("img", { name: /first screenshot 1/i }),
    ).toHaveAttribute("src", "/first-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /next photo/i }));
    expect(
      screen.getByRole("img", { name: /first screenshot 2/i }),
    ).toHaveAttribute("src", "/first-two.jpg");
    expect(screen.getByText("2/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /second/i }));
    expect(
      screen.getByRole("img", { name: /second screenshot 1/i }),
    ).toHaveAttribute("src", "/second-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /next photo/i }));
    expect(
      screen.getByRole("img", { name: /second screenshot 2/i }),
    ).toHaveAttribute("src", "/second-two.jpg");
    expect(screen.getByText("2/2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /previous photo/i }));
    expect(
      screen.getByRole("img", { name: /second screenshot 1/i }),
    ).toHaveAttribute("src", "/second-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();
  });

  it("renders missing design media as a deliberate placeholder", () => {
    render(
      <GallerySection
        galleryItems={[
          {
            label: "JouTak SMP",
            image: "/gallery-frame.jpg",
            photos: [
              {
                kind: "design_placeholder",
                id: "joutak-photo-1",
                broken: true,
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Скриншот готовится");
    expect(
      document.querySelector('[data-design-placeholder="joutak-photo-1"]'),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /JouTak SMP screenshot/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous photo/i }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: /next photo/i })).toBeDisabled();
  });
});
