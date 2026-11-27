// This headset's look (⚙ → Level of Detail) in VR and AR (quick job 157: the VR hub read only the theme's
// default). The same order as the module pages (kit.js): ?quality=, else this device's own setting (in
// this browser, then from the brain), else the computer's reduced motion, else the theme's default.
// minimal: the core keeps its rings, still, with a still look for each state; no glow, no pulses, no
// jump; panels and modules appear with no unfolding.
import { theme } from "/web/theme.js";
import { deviceName, prefs } from "/web/device.js";

const LOOKS = ["maximal", "full", "reduced", "minimal"];
const pick = (q) => (LOOKS.includes(q) ? q : "");
const asked = pick(new URLSearchParams(location.search).get("quality"));

export const look = {
  q: asked || pick(prefs().quality)
    || (matchMedia("(prefers-reduced-motion: reduce)").matches ? "minimal" : pick(theme.quality?.default) || "full"),
};
export const minimal = () => look.q === "minimal";
export const maximal = () => look.q === "maximal";

/** Ask the brain for this device's look (a ?quality= in the address wins). */
export async function loadLook() {
  if (asked || !deviceName()) return look.q;
  try {
    const r = await fetch(`/api/hub-devices/${encodeURIComponent(deviceName())}/settings`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    const q = pick((r.ok ? await r.json() : null)?.settings?.quality);
    if (q) look.q = q;
  } catch { /* the theme's look */ }
  return look.q;
}
