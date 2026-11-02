import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PageDocumentContext } from "../../features/pageDocument/pageDocumentContext";
import Contact from "./Contact.jsx";

afterEach(cleanup);

describe("contact page rollout", () => {
  it.each(["legacy", "v2"])(
    "preserves the %s contact destinations",
    (variant) => {
      render(
        <PageDocumentContext.Provider
          value={{
            document: { effective_page_variant: variant },
            loading: false,
          }}
        >
          <Contact />
        </PageDocumentContext.Provider>,
      );
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        variant === "v2" ? "НАШИ КОНТАКТЫ" : "Наши сообщества",
      );
      for (const host of ["t.me", "vk.", "discord.gg"]) {
        expect(
          screen.getAllByRole("link").some((link) => link.href.includes(host)),
        ).toBe(true);
      }
      if (variant === "v2") expect(screen.getAllByRole("link")).toHaveLength(8);
    },
  );
});
