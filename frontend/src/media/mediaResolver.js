import { GENERATED_MEDIA } from "./generatedMedia";

export function getMediaDescriptor(media) {
  if (!media) return null;
  if (media.kind === "asset") {
    return GENERATED_MEDIA[media.id] ?? null;
  }
  if (media.kind === "remote") {
    return { src: media.url, sources: [] };
  }
  if (media.kind === "design_placeholder" && media.broken) {
    return {
      src: `/__design-placeholder__/${encodeURIComponent(media.id)}`,
      sources: [],
      designPlaceholder: media.id,
    };
  }
  return {
    src: "",
    sources: [],
    designPlaceholder: media.id,
  };
}

export function resolveMedia(media) {
  return getMediaDescriptor(media)?.src ?? "";
}

export function resolveAction(action) {
  if (!action) return "#";
  if (action.kind === "internal") return action.path;
  if (action.kind === "external") return action.href;
  return action.behavior === "hash" ? "#" : undefined;
}
