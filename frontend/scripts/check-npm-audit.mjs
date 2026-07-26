import { spawnSync } from "node:child_process";

const result = spawnSync(
  process.platform === "win32" ? "npm.cmd" : "npm",
  ["audit", "--omit=dev", "--json"],
  { encoding: "utf8" },
);

if (!result.stdout) {
  process.stderr.write(result.stderr || "npm audit returned no report\n");
  process.exit(1);
}

let report;
try {
  report = JSON.parse(result.stdout);
} catch {
  process.stderr.write(result.stdout);
  process.exit(1);
}

const blockingSeverities = new Set(["high", "critical"]);
const acceptedRscAdvisory = "https://github.com/advisories/GHSA-qwww-vcr4-c8h2";

function isAcceptedSpaOnlyFinding(name, finding) {
  if (name === "react-router-dom") {
    return (
      finding.via.length === 1 &&
      finding.via[0] === "react-router" &&
      finding.range === ">=7.12.0-pre.0"
    );
  }
  if (name !== "react-router") return false;
  return finding.via.every(
    (advisory) =>
      typeof advisory === "object" &&
      advisory.url === acceptedRscAdvisory &&
      advisory.title.includes("RSC Mode"),
  );
}

const blocking = Object.entries(report.vulnerabilities ?? {}).filter(
  ([name, finding]) =>
    blockingSeverities.has(finding.severity) &&
    !isAcceptedSpaOnlyFinding(name, finding),
);

if (blocking.length > 0) {
  for (const [name, finding] of blocking) {
    process.stderr.write(
      `${finding.severity.toUpperCase()}: ${name} (${finding.range})\n`,
    );
  }
  process.exit(1);
}

const accepted = Object.entries(report.vulnerabilities ?? {}).filter(
  ([name, finding]) =>
    blockingSeverities.has(finding.severity) &&
    isAcceptedSpaOnlyFinding(name, finding),
);
if (accepted.length > 0) {
  process.stdout.write(
    "Accepted GHSA-qwww-vcr4-c8h2 for react-router 7.18.1: " +
      "this browser-only SPA does not enable React Server Components.\n",
  );
}
process.stdout.write("Production npm audit policy passed.\n");
