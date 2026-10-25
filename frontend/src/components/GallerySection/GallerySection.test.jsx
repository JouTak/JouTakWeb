import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import GallerySection from "./GallerySection.jsx";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

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

describe("gallery failure and refresh states", () => {
  it("shows an empty state for blank and hash photo sources", () => {
    render(
      <GallerySection
        galleryItems={[
          { label: "empty", image: "/cover.jpg", photos: ["", "#", "  "] },
        ]}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("пока нет фотографий");
    expect(screen.getByText("0/0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next photo/i })).toBeDisabled();
  });

  it("recovers from a failed photo when choosing another frame", async () => {
    const user = userEvent.setup();
    render(
      <GallerySection
        galleryItems={[
          {
            label: "test",
            image: "/cover.jpg",
            photos: ["/missing.jpg", "/available.jpg"],
          },
        ]}
      />,
    );
    fireEvent.error(screen.getByRole("img", { name: "test screenshot 1" }));
    expect(screen.getByRole("status")).toHaveTextContent("Фото недоступно");
    await user.click(screen.getByRole("button", { name: /next photo/i }));
    expect(
      screen.getByRole("img", { name: "test screenshot 2" }),
    ).toHaveAttribute("src", "/available.jpg");
  });

  it("keeps the current photo in bounds when content is refreshed", async () => {
    const user = userEvent.setup();
    const item = {
      label: "test",
      image: "/cover.jpg",
      photos: ["/one.jpg", "/two.jpg"],
    };
    const { rerender } = render(<GallerySection galleryItems={[item]} />);
    await user.click(screen.getByRole("button", { name: /next photo/i }));
    rerender(
      <GallerySection galleryItems={[{ ...item, photos: ["/one.jpg"] }]} />,
    );
    expect(screen.getByText("1/1")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "test screenshot 1" }),
    ).toHaveAttribute("src", "/one.jpg");
  });
});

describe("gallery image loading states", () => {
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

    await user.click(screen.getByRole("button", { name: /next photo/i }));
    const img = screen.getByRole("img", { name: /first screenshot 2/i });
    fireEvent.load(img);
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /first/i }));
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
    expect(screen.getByText("2/2")).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/first-two.jpg");
  });

  it("shows error placeholder when image fails to load", () => {
    render(<GallerySection {...baseTestData} />);

    const img = screen.getByRole("img", { name: /first screenshot 1/i });
    fireEvent.error(img);

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

  it("preserves loaded state when sections share the same photo URL", async () => {
    const user = userEvent.setup();
    render(
      <GallerySection
        galleryItems={[
          { label: "first", photos: ["/shared.jpg"] },
          { label: "second", photos: ["/shared.jpg"] },
        ]}
      />,
    );
    fireEvent.load(screen.getByRole("img", { name: "first screenshot 1" }));
    await user.click(screen.getByRole("button", { name: "second" }));
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "second screenshot 1" }),
    ).toHaveAttribute("src", "/shared.jpg");
  });

  it("shows an error after a stalled request and accepts a late successful load", () => {
    vi.useFakeTimers();
    render(<GallerySection {...baseTestData} />);
    const image = screen.getByRole("img", { name: "first screenshot 1" });
    act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByTestId("error-placeholder")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-placeholder")).not.toBeInTheDocument();
    fireEvent.load(image);
    expect(screen.queryByTestId("error-placeholder")).not.toBeInTheDocument();
  });
});
