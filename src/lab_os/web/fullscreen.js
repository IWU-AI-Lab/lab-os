// Full screen for every page (docs/guides/hub.md → "Two taps": the full-screen button).
// The button shows only while the page isn't full screen, does what the hub's tap 1 does, and when
// full screen isn't possible or the browser refuses, it says why instead of hiding (GOTCHAS
// 2026-11-10: on pi01's Chromium, /teleop showed no button at all).
//   import { fullscreenButton } from "/web/fullscreen.js";
//   fullscreenButton(buttonElement, { say: (text) => … });   // `say` is optional

export const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
export const fsPossible = () => !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
// full screen without the Fullscreen API: kiosk mode, F11, an installed app
export const fullByOther = () =>
  matchMedia("(display-mode: fullscreen)").matches ||
  matchMedia("(display-mode: standalone)").matches ||
  (Math.abs(screen.width - innerWidth) <= 2 && Math.abs(screen.height - innerHeight) <= 2);
export const isFull = () => !!fsElement() || fullByOther();

const inFrame = window.self !== window.top;

// what to do instead: the browser's own full screen
export function browserWay() {
  if (/Mac/.test(navigator.platform)) return "Use the browser's own full screen instead: Ctrl+Cmd+F, or View → Enter Full Screen.";
  if (navigator.maxTouchPoints > 0 && !matchMedia("(any-pointer: fine)").matches) {
    return "Use the browser's own full screen instead, from its menu, if it has one.";
  }
  return "Use the browser's own full screen instead: F11, or its menu.";
}

// Why this page can't go full screen, as a sentence; "" when it can (as far as the browser says).
export function whyNot() {
  const el = document.documentElement;
  if (!el.requestFullscreen && !el.webkitRequestFullscreen) {
    return "This browser can't put a web page full screen (it has no Fullscreen API; Safari on an iPhone is like this).";
  }
  const policy = document.permissionsPolicy || document.featurePolicy;
  if (policy?.allowsFeature && !policy.allowsFeature("fullscreen")) {
    return inFrame
      ? "This page is shown inside another page that doesn't allow full screen."
      : "Full screen is blocked for this page by its permissions policy.";
  }
  if (!fsPossible()) {
    return inFrame
      ? "This page is shown inside another page that doesn't allow full screen."
      : "The browser says full screen isn't allowed here (document.fullscreenEnabled is false). " +
        "Its settings, a kiosk or managed policy, or the system can turn it off.";
  }
  return "";
}

// Go full screen (only from a press: browsers' rule). Resolves to "" on success, else why not.
export async function goFullscreen(el = document.documentElement) {
  const why = whyNot();
  if (why) return `${why} ${browserWay()}`;
  try {
    if (el.requestFullscreen) await el.requestFullscreen({ navigationUI: "hide" });
    else {
      el.webkitRequestFullscreen();
      await new Promise((r) => setTimeout(r, 400));
      if (!fsElement()) throw new Error("");
    }
  } catch (e) {
    const said = e?.message ? ` It said: "${e.message}".` : " It gave no reason.";
    return `The browser refused full screen.${said} ${browserWay()}`;
  }
  return "";
}

// Wire a button: hidden while full screen, a press goes full screen, a refusal is said out loud.
// Without `say`, the reason appears in a small note right after the button (class "fs-why").
export function fullscreenButton(btn, { say, onFull } = {}) {
  let note = null;
  const show = (text) => {
    console.warn(`full screen: ${text}`);
    if (say) return say(text);
    note ||= Object.assign(document.createElement("span"), { className: "fs-why", role: "status" });
    note.textContent = text;
    note.hidden = false;
    btn.after(note);
    clearTimeout(show.timer);
    show.timer = setTimeout(() => (note.hidden = true), 12000);
  };
  const update = () => {
    btn.hidden = isFull();
    if (btn.hidden && note) note.hidden = true;
    const why = whyNot();
    btn.title = why ? `Full screen isn't available here: ${why}` : "Full screen";
    btn.classList.toggle("fs-unavailable", !!why);
  };
  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const why = await goFullscreen();
    if (why) show(why);
    else onFull?.();
    update();
  });
  for (const ev of ["fullscreenchange", "webkitfullscreenchange"]) document.addEventListener(ev, update);
  addEventListener("resize", update); // F11 and kiosk changes show up only as a resize
  update();
  return { update, show };
}
