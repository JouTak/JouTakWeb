import manifest from "./manifest.json";

const sources = import.meta.glob("./*/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

export const documents = Object.fromEntries(
  Object.entries(manifest).map(([type, document]) => [
    type,
    {
      ...document,
      versions: document.versions.map((version) => {
        if (typeof sources[version.file] !== "string") {
          throw new Error(`Missing document source: ${version.file}`);
        }
        return { ...version, markdown: sources[version.file] };
      }),
    },
  ]),
);

export function findDocumentVersion(document, requestedVersion) {
  return document.versions.find(
    ({ id }) => id === (requestedVersion ?? document.currentVersion),
  );
}

export function formatDocumentDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
