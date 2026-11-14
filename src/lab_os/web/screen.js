// This device's drawing resolution, for every page that draws (canvases, the 3D arm): canvas pixels per CSS
// pixel. `?res=` in the address wins (the page's own, or the hub's when the page is open inside it), then
// "This device" in Settings (kept by the brain under the device's name: /web/device.js), then "auto" = the
// screen's own, up to 2×. Lower draws fewer
// pixels and the screen scales them up: softer, but far lighter on a 4K panel with a phone-class chip.
// Same scale as /perf?res=. The designed hub (design.html) has the same rule inline.
import { prefs } from "/web/device.js";

function wanted() {
  const own = new URLSearchParams(location.search).get("res");
  if (own) return own;
  try {
    const hub = new URLSearchParams(window.top.location.search).get("res"); // same brain: readable
    if (hub) return hub;
  } catch {
    // another origin above us: only our own address counts
  }
  return prefs().res || "auto";
}

export function drawRes() {
  const want = wanted(), n = Number(want);
  const dev = Math.min(window.devicePixelRatio || 1, 2);
  return want === "auto" || !(n > 0) ? dev : Math.min(dev, Math.max(0.25, n));
}
