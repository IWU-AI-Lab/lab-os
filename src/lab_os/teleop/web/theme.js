// Design tokens from config/theme.yaml (served as /theme.json), loaded once per page.
//   import { theme, color } from "./theme.js";   color("arm3d.xarm.metal") → 0xb4b8bf
// If the theme can't be loaded, everything falls back to plain gray (and says so in the console),
// so a broken theme is obvious but never breaks the page.
let loaded = {};
try {
  const res = await fetch("/theme.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  loaded = await res.json();
} catch (e) {
  console.error(`theme: could not load /theme.json (${e.message}); using gray fallback`);
}

export const theme = loaded;

/** A color token by dotted path, as a three.js number (0xrrggbb). Unknown/invalid → gray. */
export function color(path) {
  const value = path.split(".").reduce((node, key) => node?.[key], loaded);
  if (typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value)) return parseInt(value.slice(1), 16);
  console.warn(`theme: missing or invalid color "${path}"`);
  return 0x999999;
}
