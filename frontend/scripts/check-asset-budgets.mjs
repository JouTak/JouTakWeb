import { readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const mediaRoot = path.join(frontendRoot, "src/assets/media/generated");
const files = await readdir(mediaRoot);
const sizes = new Map();

for (const file of files) {
  sizes.set(file, (await stat(path.join(mediaRoot, file))).size);
}

const mebibyte = 1024 * 1024;
const rasterLimit = 800 * 1024;
const catalogLimit = 10 * mebibyte;

for (const [file, size] of sizes) {
  if (file.endsWith(".webp") && size > rasterLimit) {
    throw new Error(`${file} exceeds the 800 KiB raster budget`);
  }
}

const catalogSize = [...sizes.values()].reduce(
  (total, size) => total + size,
  0,
);
if (catalogSize > catalogLimit) {
  throw new Error("Generated landing media exceeds the 10 MiB budget");
}

for (const product of ["itmocraft", "joutak", "minigames"]) {
  const mobile = [...sizes]
    .filter(([file]) => file.startsWith(`${product}-`) && file.includes("-480"))
    .reduce((total, [, size]) => total + size, 0);
  const desktop = [...sizes]
    .filter(
      ([file]) =>
        file.startsWith(`${product}-`) &&
        (file.includes("-1920") || file.endsWith(".svg")),
    )
    .reduce((total, [, size]) => total + size, 0);
  if (mobile > 1.5 * mebibyte) {
    throw new Error(`${product} exceeds the 1.5 MiB mobile image budget`);
  }
  if (desktop > 3 * mebibyte) {
    throw new Error(`${product} exceeds the 3 MiB desktop image budget`);
  }
}

console.log(
  `Asset budgets passed: ${(catalogSize / mebibyte).toFixed(2)} MiB catalog`,
);
