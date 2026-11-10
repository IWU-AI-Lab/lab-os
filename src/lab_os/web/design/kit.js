// The module pages' shared bits (teleop, monitor, AI control, settings):
//   - the theme's colors and fonts (/theme.json) as CSS variables, like the hub;
//   - inside the hub (an iframe) or on its own screen: body.embedded drops the page's own frame;
//   - on its own screen: the place's name and the clock in the bar, and full screen with one press
//     (a page sent to another screen from the hub, `?screen=…`, asks for that press right away).
//   <script type="module" src="/web/design/kit.js"></script>
import { theme } from "/web/theme.js";

const root = document.documentElement.style;
const colors = theme.colors || {};
const font = theme.font || {};
const VARS = {
  bg: colors.background, surface: colors.surface, line: colors.line, text: colors.text, "text-dim": colors.text_dim,
  primary: colors.primary, hot: colors.hot, accent: colors.accent, danger: colors.danger, offline: colors.offline,
  ok: colors.ok, frozen: colors.frozen,
  "f-title": font.display, "f-ui": font.family, "f-lines": font.lines, "w-lines": font.lines_weight,
  "f-digits": font.digits, "f-mono": font.mono, arrive: theme.motion?.arrive,
};
for (const [k, v] of Object.entries(VARS)) if (v != null && v !== "") root.setProperty(`--${k}`, String(v));

export const embedded = window.self !== window.top;
document.body.classList.toggle("embedded", embedded);

// the bar: the place's name and the brain's clock (pages under lab-os-teleop have neither endpoint)
const place = document.querySelector(".bar .place");
const clock = document.querySelector(".bar .clock");
let offset = 0;
if (!embedded) {
  fetch("/api/hub", { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .then((h) => h?.title && place && (place.textContent = h.title))
    .catch(() => {});
  fetch("/api/status", { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .then((s) => s && (offset = s.time_ms - Date.now()))
    .catch(() => {});
}
function tick() {
  if (!clock) return;
  const d = new Date(Date.now() + offset), p = (n) => String(n).padStart(2, "0");
  clock.textContent = theme.clock === "12h"
    ? `${d.getHours() % 12 || 12}:${p(d.getMinutes())}:${p(d.getSeconds())}`
    : `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
tick();
setInterval(tick, 1000);

// full screen on its own screen: a button, or (sent here from the hub) a press anywhere
const params = new URLSearchParams(location.search);
if (!embedded && document.fullscreenEnabled) {
  const go = () => document.documentElement.requestFullscreen({ navigationUI: "hide" }).catch(() => {});
  if (params.has("screen") && !document.fullscreenElement) {
    const ask = document.createElement("div");
    ask.id = "fs-ask";
    ask.innerHTML = `<div>Click or tap for full screen<small>Sent to this screen from the hub. Esc leaves full screen.</small></div>`;
    ask.addEventListener("click", () => { go(); ask.remove(); });
    document.body.append(ask);
  }
  const btn = document.createElement("button");
  btn.id = "fs-btn";
  btn.type = "button";
  btn.className = "btn small";
  btn.innerHTML = `<svg class="ico"><use href="/web/design/icons.svg#i-open"/></svg>Full screen`;
  btn.addEventListener("click", go);
  const spot = document.querySelector(".bar .clock");
  if (spot) spot.before(btn); else document.body.append(btn);  // in the bar, out of the content's way
  const update = () => (btn.hidden = !!document.fullscreenElement);
  document.addEventListener("fullscreenchange", update);
  update();
}
// keep the screen awake while this page shows (localhost / https only; elsewhere nothing happens)
const wake = () => document.visibilityState === "visible" && navigator.wakeLock?.request("screen").catch(() => {});
if (!embedded) {
  wake();
  document.addEventListener("visibilitychange", wake);
}
