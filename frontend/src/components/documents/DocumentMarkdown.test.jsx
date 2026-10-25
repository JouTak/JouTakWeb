import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import DocumentMarkdown from "./DocumentMarkdown";

afterEach(cleanup);

it("renders Markdown structures and unique anchors from the same headings", () => {
  render(
    <DocumentMarkdown
      markdown={[
        "## О данных",
        "",
        "Текст с **выделением** и [контактом](/contact).",
        "",
        "### Повтор",
        "",
        "- Первый пункт",
        "- Второй пункт",
        "",
        "### Повтор",
        "",
        "| Поле | Значение |",
        "| --- | --- |",
        "| Версия | 1 |",
        "",
        "> Цитата",
        "",
        "```text",
        "## Это код, не заголовок",
        "```",
      ].join("\n")}
    />,
  );
  expect(screen.getByRole("link", { name: "контактом" })).toHaveAttribute(
    "href",
    "/contact",
  );
  expect(screen.getByRole("table")).toHaveTextContent("Версия");
  expect(screen.getByText("Первый пункт").tagName).toBe("LI");
  expect(screen.getByText("выделением").tagName).toBe("STRONG");
  const links = within(screen.getByRole("navigation")).getAllByRole("link");
  expect(links).toHaveLength(3);
  const ids = links.map((link) => link.getAttribute("href").slice(1));
  expect(new Set(ids).size).toBe(3);
  for (const id of ids) expect(document.getElementById(id)).toBeInTheDocument();
});

it("does not execute embedded HTML or javascript links", () => {
  const { container } = render(
    <DocumentMarkdown
      markdown={
        "<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n[Unsafe](javascript:alert%281%29)"
      }
    />,
  );
  expect(
    container.querySelector("script, img, [onclick], [onerror]"),
  ).toBeNull();
  expect(screen.getByText("Unsafe").closest("a")).toBeNull();
});
