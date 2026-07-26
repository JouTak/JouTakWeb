const ASSETS = {
  "events.bunker": "/img/бункер.png",
  "gallery.joutak.cover": "/img/gallery-bg.png",
  "itmocraft.hero.background": "/img/main-image.png",
  "itmocraft.logo": "/img/logo-maxi.svg",
  "joutak.hero.background": "/img/bg-itmocraft-joutak.png",
  "joutak.logo": "/img/itmocraft-joutak-logo.svg",
  "minigames.block-party": "/img/block-party.png",
  "minigames.hero.background": "/img/bg-minigames.png",
  "minigames.logo": "/img/minigames-logo.svg",
};

export function resolveMedia(media) {
  if (!media) return "";
  if (media.kind === "asset") return ASSETS[media.id] || "";
  if (media.kind === "remote") return media.url;
  if (media.kind === "design_placeholder" && media.broken) {
    return `/__design-placeholder__/${encodeURIComponent(media.id)}`;
  }
  return "";
}

export function resolveAction(action) {
  if (!action) return "#";
  if (action.kind === "internal") return action.path;
  if (action.kind === "external") return action.href;
  return action.behavior === "hash" ? "#" : undefined;
}
