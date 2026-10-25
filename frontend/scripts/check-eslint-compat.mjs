import assert from "node:assert/strict";

import { ESLint } from "eslint";

const eslint = new ESLint();
const [result] = await eslint.lintText(
  `
import { useEffect, useState } from "react";
export default function Fixture() {
  const [value, setValue] = useState(0);
  useEffect(() => { setValue(1); }, []);
  return <main>{[1, 2].map(item => <img src={String(item)} />)}{value}</main>;
}
`,
  { filePath: "src/eslint-compat-fixture.jsx" },
);
for (const rule of [
  "jsx-a11y/alt-text",
  "react/jsx-key",
  "react-hooks/set-state-in-effect",
]) {
  assert(
    result.messages.some((message) => message.ruleId === rule),
    `${rule} must still reject invalid code`,
  );
}
