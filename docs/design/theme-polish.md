# Readable light and dark themes

The production V2 page after PR #146 mixed theme-aware text with fixed dark
backgrounds. In light mode, the main community/action card rendered dark text
on a dark panel. Several other surfaces used image-based frames or unrelated
palettes, and Bootstrap controls did not follow the Gravity theme.

## Changes

- Shared background, surface, inset surface, foreground, secondary text,
  accent, on-accent text and shadow roles for each theme.
- Gravity link, brand and secondary text roles follow the site palette;
  Bootstrap receives the same theme through `data-bs-theme`.
- Navigation, footers, action cards, events, gallery, contacts, account and
  system-page panels use theme-aware surfaces. Image artwork retains its colors.
- Consistent restrained borders and radii, more comfortable paragraph leading,
  less dominant heading shadows and responsive spacing.
- Action buttons preserve a usable height on mobile; focus outlines remain
  visible in both themes. The fallback header also exposes a theme switch.

## Verification

The browser suite checks both themes at 320 and 1440 px for horizontal overflow
and WCAG AA text contrast, including navigation/footer. It covers landing pages,
contacts, documents, login and system states. Authenticated account/security and
registration forms use synthetic read-only API fixtures at 320 px. Existing
legacy/V2 responsive tests cover 320–2560 px. This does not exercise real
payments, credentials, or account changes.

Local validation: frontend lint, Prettier, Stylelint, production build and
111 unit tests passed. The full 44-test browser matrix passed; after the final
palette and legal-footer edits, the six theme/account checks and six document
checks were rerun successfully. Legal documents now show only itmocraft@itmo.ru
in the feedback section and have no bottom navigation/contact buttons.
