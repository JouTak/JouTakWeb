/**
 * Feature Flag Registry — frontend counterpart of the backend registry.
 *
 * Maps feature flag keys to their page context, rendering behavior,
 * and lazy-loaded components. This provides a single source of truth
 * for understanding what each flag controls on the frontend.
 *
 * Adding a new feature flag to the frontend:
 *   1. Add an entry to FEATURE_MAP below
 *   2. Create the component (or import existing)
 *   3. Use <FeatureGate flag="your_flag"> in your page
 *
 * For variant-based flags (multiple versions of a page/section):
 *   Use the `variants` key with lazy-loaded component imports.
 *
 * For boolean flags (show/hide a section):
 *   Use the `component` key for the new element.
 */

/**
 * @typedef {Object} BooleanFeature
 * @property {"boolean"} type
 * @property {string|string[]} page - Route path(s) or "*" for all
 * @property {string} slot - Where on the page this renders
 * @property {string} description - Human-readable description
 * @property {() => Promise} [component] - Lazy import for the new component
 */

/**
 * @typedef {Object} VariantFeature
 * @property {"variant"} type
 * @property {string|string[]} page
 * @property {string} slot
 * @property {string} description
 * @property {Object<string, () => Promise>} variants - Map of variant -> lazy import
 */

export const FEATURE_MAP = {
  // ─── Homepage variant (full page switch) ────────────────────────────
  site_homepage_version: {
    type: "variant",
    page: "/joutak",
    slot: "page-content",
    description:
      "Switches the /joutak homepage between legacy carousel and V2 layout",
    variants: {
      legacy: () => import("../../pages/joutak/LegacyHomepage.jsx"),
      v2: () => import("../../pages/joutak/HomepageV2.jsx"),
    },
  },

  // ─── New design elements (from website-dev / PR #85) ────────────────

  site_footer_v2: {
    type: "boolean",
    page: "*",
    slot: "footer",
    description: "New footer design from the website-dev branch",
    component: null, // TODO: lazy(() => import("../../components/FooterV2"))
  },

  site_header_v2: {
    type: "boolean",
    page: "*",
    slot: "header",
    description: "New header/navigation design from the website-dev branch",
    component: null, // TODO: lazy(() => import("../../components/HeaderV2"))
  },

  joutak_projects_section: {
    type: "boolean",
    page: "/joutak",
    slot: "section-projects",
    description: "Project cards grid section on the homepage",
    component: null, // Will be set when component is ready
  },

  joutak_events_section: {
    type: "boolean",
    page: "/joutak",
    slot: "section-events",
    description: "Events section on the homepage",
    component: null,
  },

  joutak_faq_section: {
    type: "boolean",
    page: "/joutak",
    slot: "section-faq",
    description: "FAQ accordion section on the homepage",
    component: null,
  },

  joutak_gallery_section: {
    type: "boolean",
    page: "/joutak",
    slot: "section-gallery",
    description: "Photo gallery with tab switching on the homepage",
    component: null,
  },

  itmocraft_new_header: {
    type: "boolean",
    page: "/itmocraft",
    slot: "page-header",
    description: "New header design for the /itmocraft page",
    component: null,
  },

  // ─── Profile personalization flags ──────────────────────────────────

  profile_personalization_ui: {
    type: "boolean",
    page: ["/account", "/joutak"],
    slot: "personalization-prompts",
    description: "Shows/hides personalization prompts site-wide",
    component: null, // Handled in account logic, not a visible component
  },

  profile_personalization_interstitial: {
    type: "boolean",
    page: "/account",
    slot: "interstitial",
    description: "Full-screen interstitial on login for new users",
    component: null,
  },

  profile_personalization_enforce: {
    type: "boolean",
    page: "*",
    slot: "enforcement",
    description: "Blocks users with incomplete profiles from certain actions",
    component: null, // Server-side enforcement, no frontend component
  },
};

/**
 * Get all feature flags relevant to a specific page path.
 * @param {string} pagePath - The current route path (e.g., "/joutak")
 * @returns {string[]} Array of flag keys relevant to this page
 */
export function getFlagsForPage(pagePath) {
  return Object.entries(FEATURE_MAP)
    .filter(([, spec]) => {
      const pages = Array.isArray(spec.page) ? spec.page : [spec.page];
      return pages.includes("*") || pages.includes(pagePath);
    })
    .map(([key]) => key);
}

/**
 * Get the feature spec for a given flag key.
 * @param {string} key
 * @returns {BooleanFeature|VariantFeature|undefined}
 */
export function getFeatureSpec(key) {
  return FEATURE_MAP[key];
}
