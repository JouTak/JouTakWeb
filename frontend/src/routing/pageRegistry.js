const PRODUCT_ROUTES = Object.freeze({
  "/": {
    productId: "itmocraft",
    endpoint: "/bff/pages/itmocraft",
  },
  "/itmocraft": {
    productId: "itmocraft",
    endpoint: "/bff/pages/itmocraft/legacy",
  },
  "/joutak": {
    productId: "joutak",
    endpoint: "/bff/pages/joutak",
  },
  "/minigames": {
    productId: "minigames",
    endpoint: "/bff/pages/minigames",
  },
});

export function normalizeRoutePath(pathname) {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export function getProductRoute(pathname) {
  return PRODUCT_ROUTES[normalizeRoutePath(pathname)] ?? null;
}

export { PRODUCT_ROUTES };
