# Readable light and dark themes

The production V2 page after PR #146 mixed theme-aware text with fixed dark
backgrounds. In light mode, the main community/action card rendered dark text
on a dark panel. Bootstrap controls also did not follow the Gravity theme.

## Changes

- Shared background, surface, inset surface, foreground, secondary text,
  accent, on-accent text and shadow roles for each theme.
- Only V2 layouts override Gravity link and brand roles;
  legacy layouts retain their original Gravity palette and dark navigation.
  Bootstrap receives the same theme through `data-bs-theme` only in V2.
  Neutral secondary text contrast is corrected in both variants.
- Footers, action cards, gallery, account and system-page panels use theme-aware
  surfaces. Original blue navigation, event and contact artwork and the original
  accent palette are preserved. Dark text provides contrast on blue artwork.
- Fallback header controls use centered SVG icons and equal 44 px hit areas.
- Legacy server carousels share JouTak’s edge-to-edge layout.
- The login dialog uses one responsive width with equal margins, wrapping text,
  a locally scoped legacy blue action, and accessible Email-only field labels.
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
111 unit tests passed. The initial full 44-test browser matrix passed. Follow-up
checks cover theme contrast, account forms, legacy responsive pages and centered
login dialogs in both themes. Legal documents show only itmocraft@itmo.ru in the
feedback section and have no bottom navigation/contact buttons.
