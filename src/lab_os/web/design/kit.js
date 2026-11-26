// The module pages' shared bits (teleop, monitor, AI control, settings):
//   - the theme's colors and fonts (/theme.json) as CSS variables, like the hub;
//   - inside the hub (an iframe) or on its own screen: body.embedded drops the page's own frame;
//   - on its own screen: the place's name and the clock in the bar, and a choice: Full screen or
//     Window (so that several pages fit on one monitor), kept for each page in this browser. A page
//     sent to another screen from the hub (`?screen=…`) goes full screen by itself unless Window was
//     chosen: on the brain's computer the brain does it, elsewhere it asks for one press (quick job 74).
//     Where full screen isn't possible, the button says why (/web/fullscreen.js);
//   - on its own screen: ← Hub at the left of the bar, the way back to the hub (quick job 153);
//   - the device's look (⚙ → Level of Detail) as a class on <html>: q-maximal | q-full | q-reduced |
//     q-minimal. kit.css drops glow and motion in minimal (quick job 153: before, a page read only this
//     browser's storage, so it showed the theme's default).
//   <script type="module" src="/web/design/kit.js"></script>
import { brainWindow, fullscreenButton, goFullscreen, isFull } from "/web/fullscreen.js";
import { theme } from "/web/theme.js";
import "/web/no-menu.js";
import { deviceName, prefs } from "/web/device.js";

const root = document.documentElement.style;
const colors = theme.colors || {};
const font = theme.font || {};
const VARS = {
  bg: colors.background, surface: colors.surface, line: colors.line, text: colors.text, "text-dim": colors.text_dim,
  primary: colors.primary, hot: colors.hot, accent: colors.accent, danger: colors.danger, offline: colors.offline,
  ok: colors.ok, frozen: colors.frozen, "frozen-text": colors.frozen_text,
  "f-title": font.display, "f-ui": font.family, "f-lines": font.lines, "w-lines": font.lines_weight,
  "f-digits": font.digits, "f-mono": font.mono, arrive: theme.motion?.arrive,
};
for (const [k, v] of Object.entries(VARS)) if (v != null && v !== "") root.setProperty(`--${k}`, String(v));

export const embedded = window.self !== window.top;
document.body.classList.toggle("embedded", embedded);

// the device's look: the hub around this page, else ?quality=, else this device's own (from the brain),
// else the computer's reduced motion, else the theme's default
const LOOKS = ["maximal", "full", "reduced", "minimal"];
function setLook(q) {
  if (!LOOKS.includes(q)) return;
  const c = document.documentElement.classList;
  for (const l of LOOKS) c.toggle(`q-${l}`, l === q);
}
function hubLook() {
  try {
    const q = [...window.parent.document.body.classList].find((c) => /^q-(maximal|full|reduced|minimal)$/.test(c));
    return q ? q.slice(2) : "";
  } catch { return ""; } // another origin above
}
const fallbackLook = () => new URLSearchParams(location.search).get("quality") || prefs().quality
  || (matchMedia("(prefers-reduced-motion: reduce)").matches ? "minimal" : theme.quality?.default || "full");
setLook((embedded && hubLook()) || fallbackLook());
if (embedded && hubLook()) {
  // the hub's look changes while this page is open (⚙ → Level of Detail): follow it
  new MutationObserver(() => setLook(hubLook())).observe(window.parent.document.body, { attributes: true, attributeFilter: ["class"] });
} else if (!new URLSearchParams(location.search).has("quality") && deviceName()) {
  fetch(`/api/hub-devices/${encodeURIComponent(deviceName())}/settings`, { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .then((r) => r?.settings?.quality && setLook(r.settings.quality))
    .catch(() => {});
}

// ← Hub: on a page opened by itself, the way back to the hub under this device's name (shown once
// /api/hub answers: under lab-os-teleop alone there is no hub)
const toHub = document.createElement("a");
toHub.className = "btn small to-hub";
toHub.hidden = true;
toHub.href = deviceName() ? `/?device=${encodeURIComponent(deviceName())}` : "/";
toHub.title = "Back to the hub";
toHub.innerHTML = `<span aria-hidden="true">←</span>Hub`;
if (!embedded) document.querySelector(".bar")?.prepend(toHub);

// the bar: the place's name and the brain's clock (pages under lab-os-teleop have neither endpoint)
const place = document.querySelector(".bar .place");
const clock = document.querySelector(".bar .clock");
let offset = 0;
if (!embedded) {
  fetch("/api/hub", { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .then((h) => {
      if (!h) return;
      toHub.hidden = false;
      if (h.title && place) place.textContent = h.title;
    })
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

// full screen on its own screen: a button (shown while not full screen; says why when it can't), or
// (sent here from the hub) a press anywhere
const params = new URLSearchParams(location.search);
if (!embedded) {
  const btn = document.createElement("button");
  btn.id = "fs-btn";
  btn.type = "button";
  btn.className = "btn small";
  btn.innerHTML = `<svg class="ico"><use href="/web/design/icons.svg#i-open"/></svg>Full screen`;
  const spot = document.querySelector(".bar .clock");
  if (spot) spot.before(btn); else document.body.append(btn);  // in the bar, out of the content's way
  // the choice for this page: "full" (the default) or "window"
  const KEY = `lab-os.window:${location.pathname}`;
  const choice = () => { try { return localStorage.getItem(KEY) || "full"; } catch { return "full"; } };
  const choose = (v) => { try { localStorage.setItem(KEY, v); } catch { /* private window: not kept */ } };
  const fs = fullscreenButton(btn, { onFull: () => choose("full") });
  const win = document.createElement("button");
  win.id = "win-btn";
  win.type = "button";
  win.className = "btn small";
  win.title = "Show this page in a window, so that other pages fit beside it";
  win.innerHTML = `<svg class="ico"><use href="/web/design/icons.svg#i-window"/></svg>Window`;
  btn.after(win);
  const showWin = () => (win.hidden = !isFull());
  for (const ev of ["fullscreenchange", "webkitfullscreenchange"]) document.addEventListener(ev, showWin);
  addEventListener("resize", showWin);  // F11 and the brain's full screen show up only as a resize
  showWin();
  win.addEventListener("click", async (e) => {
    e.stopPropagation();
    choose("window");
    if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
    else if (await brainWindow("normal")) fs.show("Press F11 to leave full screen.");
    setTimeout(() => { showWin(); fs.update(); }, 300);
  });
  const askForPress = () => {
    const ask = document.createElement("div");
    ask.id = "fs-ask";
    ask.innerHTML = `<div>Click or tap for full screen<small>Sent to this screen from the hub. Esc leaves full screen.</small></div>`;
    ask.addEventListener("click", async () => {
      ask.remove();
      const why = await goFullscreen();
      if (why) fs.show(why);
    });
    document.body.append(ask);
  };
  if (params.has("screen") && !isFull() && choice() !== "window") {
    brainWindow("fullscreen").then((why) => {
      if (!why) return;
      console.info(`full screen: ${why}; asking for a press`);
      askForPress();
    });
  }
}
// keep the screen awake while this page shows (localhost / https only; elsewhere nothing happens)
const wake = () => document.visibilityState === "visible" && navigator.wakeLock?.request("screen").catch(() => {});
if (!embedded) {
  wake();
  document.addEventListener("visibilitychange", wake);
}
