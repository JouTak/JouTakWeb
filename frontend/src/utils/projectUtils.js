import { normalizeRoutePath } from "../routing/pageRegistry";

export const projectMapping = {
  jou_tak: "/joutak",
  mini_games: "/minigames",
  legacy: "/legacy",
  itmo_craft: "/",
};

export function isProjectLandingPath(path) {
  const normalizedPath = normalizeRoutePath(path);
  return (
    normalizedPath === "/itmocraft" ||
    Object.values(projectMapping).includes(normalizedPath)
  );
}

export function getProjectByPath(path) {
  const normalizedPath = normalizeRoutePath(path);
  if (
    normalizedPath === "/itmocraft" ||
    normalizedPath === "/cities" ||
    normalizedPath.startsWith("/cities/") ||
    normalizedPath === "/communities/itmocraft"
  )
    return "itmo_craft";
  const entry = Object.entries(projectMapping).find(
    ([, value]) => normalizedPath === value,
  );
  return entry ? entry[0] : "jou_tak";
}

export function getPathByProject(project) {
  return projectMapping[project] ?? null;
}
