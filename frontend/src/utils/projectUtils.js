export const projectMapping = {
  jou_tak: "/joutak",
  mini_games: "/minigames",
  bed_rock: "/bedrock",
  itmocraft: "/itmocraft",
};

export function getProjectByPath(path) {
  const normalizedPath =
    path.endsWith("/") && path !== "/" ? path.slice(0, -1) : path;
  const entry = Object.entries(projectMapping).find(([, value]) => {
    const normalizedValue =
      value.endsWith("/") && value !== "/" ? value.slice(0, -1) : value;
    return normalizedPath === normalizedValue;
  });
  return entry ? entry[0] : "jou_tak";
}

export function getPathByProject(project) {
  return projectMapping[project] || "/";
}
