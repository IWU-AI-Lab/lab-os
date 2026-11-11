// This screen's drawing resolution, for every page that draws (canvases, the 3D arm): canvas pixels per CSS
// pixel. `?res=` in the address wins (the page's own, or the hub's when the page is open inside it), then
// "This screen" in Settings (kept in this browser), then "auto" = the device's, up to 2×. Lower draws fewer
// pixels and the screen scales them up: softer, but far lighter on a 4K panel with a phone-class chip.
// Same scale as /perf?res=. The designed hub (design.html) has the same rule inline.

function wanted() {
  const own = new URLSearchParams(location.search).get("res");
  if (own) return own;
  try {
    const hub = new URLSearchParams(window.top.location.search).get("res"); // same brain: readable
    if (hub) return hub;
  } catch {
    // another origin above us: only our own address counts
  }
  try {
    return JSON.parse(localStorage.getItem("lab-os.screen"))?.res || "auto";
  } catch {
    return "auto";
  }
}

export function drawRes() {
  const want = wanted(), n = Number(want);
  const dev = Math.min(window.devicePixelRatio || 1, 2);
  return want === "auto" || !(n > 0) ? dev : Math.min(dev, Math.max(0.25, n));
}
