#!/usr/bin/env node
/**
 * Copy Next static export (`out/`) into FastAPI's serve dir.
 * Destination is committed so Nix cattle (`container-smart-writer-v2`) includes UI
 * without a Node stage in flake.nix.
 */
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(webRoot, "out");
const dest = join(webRoot, "..", "app", "static", "ui");

if (!existsSync(join(outDir, "index.html"))) {
  console.error(`Missing ${outDir}/index.html — run \`npm run build\` first.`);
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(outDir, dest, { recursive: true });
console.log(`Copied static UI → ${dest}`);
