import { readFileSync } from "node:fs";

const messageFile = process.argv[2];
const message = readFileSync(messageFile, "utf8").trim();
const firstLine = message.split(/\r?\n/, 1)[0] || "";

const allowedMergePrefixes = [
  "Merge branch ",
  "Merge pull request ",
  'Revert "',
];

const conventionalPattern =
  /^(feat|fix|chore|refactor|docs|test|ci|build|perf|style|revert)\([a-z0-9._-]+\): .{1,}$/;

if (
  allowedMergePrefixes.some((prefix) => firstLine.startsWith(prefix)) ||
  conventionalPattern.test(firstLine)
) {
  process.exit(0);
}

console.error("Invalid commit message.");
console.error("Required format: type(scope): description");
console.error(
  "Allowed types: feat, fix, chore, refactor, docs, test, ci, build, perf, style, revert",
);
process.exit(1);
