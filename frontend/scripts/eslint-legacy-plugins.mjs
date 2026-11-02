import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

// These plugins still call the pre-v9 CommonJS minimatch export. Adapt only
// their loading; keep ESLint itself on the modern, patched package API.
function loadLegacyPlugin(name) {
  const pluginRequire = createRequire(require.resolve(name));
  const path = pluginRequire.resolve("minimatch");
  const modern = pluginRequire("minimatch");
  const cached = require.cache[path];
  cached.exports = Object.assign(modern.minimatch, modern);
  try {
    return require(name);
  } finally {
    cached.exports = modern;
  }
}

export const jsxA11y = loadLegacyPlugin("eslint-plugin-jsx-a11y");
export const react = loadLegacyPlugin("eslint-plugin-react");
