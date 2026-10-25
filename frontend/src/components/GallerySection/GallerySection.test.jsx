import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import GallerySection from "./GallerySection.jsx";

const baseTestData = {
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
    {
      label: "empty",
      image: "/empty-main.jpg",
      photos: [],
    },
  ],
  leftArrowSrc: "/img/left-btn-gallery.png",
  rightArrowSrc: "/img/right-btn-gallery.png",
};

describe("GallerySection", () => {
  afterEach(() => {
    cleanup();
  });

  it("cycles through gallery images", async () => {
    const user = userEvent.setup();
    render(<GallerySection {...baseTestData} />);

    const img1 = screen.getByRole("img", { name: /first screenshot 1/i });
    expect(img1).toHaveAttribute("src", "/first-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next photo/i }));
    const img2 = screen.getByRole("img", { name: /first screenshot 2/i });
    expect(img2).toHaveAttribute("src", "/first-two.jpg");
    expect(screen.getByText("2/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /second/i }));
    const secondImg1 = screen.getByRole("img", {
      name: /second screenshot 1/i,
    });
    expect(secondImg1).toHaveAttribute("src", "/second-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next photo/i }));
    const secondImg2 = screen.getByRole("img", {
      name: /second screenshot 2/i,
    });
    expect(secondImg2).toHaveAttribute("src", "/second-two.jpg");
    expect(screen.getByText("2/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /previous photo/i }));
    const prevImg = screen.getByRole("img", { name: /second screenshot 1/i });
    expect(prevImg).toHaveAttribute("src", "/second-one.jpg");
    expect(screen.getByText("1/2")).toBeInTheDocument();
  });

  it("shows loading placeholder initially and hides it after image loads", () => {
    render(<GallerySection {...baseTestData} />);

    expect(screen.getByTestId("loading-placeholder")).toBeInTheDocument();

    const img = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.load(img);

    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
  });

  it("does not reset loaded status on repeated click of the active section", async () => {
    const user = userEvent.setup();
    render(<GallerySection {...baseTestData} />);

    const img = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.load(img);
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /first/i }));
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
  });

  it("shows error placeholder when image fails to load", () => {
    render(<GallerySection {...baseTestData} />);

    const img = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.error(img);

    expect(screen.getByTestId("error-placeholder")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
  });

  it("immediately shows error placeholder when image URL is empty string", () => {
    const emptyUrlData = {
      ...baseTestData,
      galleryItems: [
        {
          label: "with-empty-url",
          image: "/main.jpg",
          photos: [""],
        },
      ],
    };

    render(<GallerySection {...emptyUrlData} />);

    expect(screen.getByTestId("error-placeholder")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
  });

  it("allows switching to another photo even if current photo failed and loads next", async () => {
    const user = userEvent.setup();
    render(<GallerySection {...baseTestData} />);

    const img1 = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.error(img1);
    expect(screen.getByTestId("error-placeholder")).toBeInTheDocument();

    const nextBtn = screen.getByRole("button", { name: /next photo/i });
    expect(nextBtn).toBeEnabled();

    await user.click(nextBtn);

    expect(screen.queryByTestId("error-placeholder")).not.toBeInTheDocument();
    expect(screen.getByTestId("loading-placeholder")).toBeInTheDocument();
    expect(screen.getByText("2/2")).toBeInTheDocument();

    const img2 = screen.getByRole("img", { name: /first screenshot 2/i });
    expect(img2).toHaveAttribute("src", "/first-two.jpg");
    fireEvent.load(img2);

    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
  });

  it("handles empty gallery section and disables navigation buttons", async () => {
    const user = userEvent.setup();
    render(<GallerySection {...baseTestData} />);

    await user.click(screen.getByRole("button", { name: /empty/i }));

    expect(
      screen.getByText(/для этого раздела пока нет фотографий/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous photo/i }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: /next photo/i })).toBeDisabled();
    expect(screen.getByText("0/0")).toBeInTheDocument();
  });

  it("resets error state when changing section", async () => {
    const user = userEvent.setup();
    render(<GallerySection {...baseTestData} />);

    const img1 = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.error(img1);
    expect(screen.getByTestId("error-placeholder")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /second/i }));

    expect(screen.queryByTestId("error-placeholder")).not.toBeInTheDocument();
    expect(screen.getByTestId("loading-placeholder")).toBeInTheDocument();
  });
});
