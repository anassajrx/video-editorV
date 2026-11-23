import path from "node:path";
import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
// No lint at build: the repo root's ESLint config is for the Remotion engine, not this site. Types are still checked.
export default {
  reactStrictMode: true,
  outputFileTracingRoot: path.dirname(fileURLToPath(import.meta.url)),
};
