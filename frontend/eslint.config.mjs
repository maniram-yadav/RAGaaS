// Flat ESLint config (ESLint 9+ requires this format; `.eslintrc.json` is kept
// only as a fallback for tools that still read the legacy format, e.g. some
// editor integrations). `eslint-config-next` does not yet ship a native flat
// config for this version, so we bridge it with `@eslint/eslintrc`'s
// `FlatCompat`, mirroring what `next lint` does internally.
import { fileURLToPath } from "node:url";
import path from "node:path";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "coverage/**",
      "playwright-report/**",
      "next-env.d.ts",
    ],
  },
];

export default eslintConfig;
