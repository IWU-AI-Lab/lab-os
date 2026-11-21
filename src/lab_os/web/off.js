// "lab-os is off" (quick job 6; since 2026-11-21 like a normal program, the builder): when "Shut down lab-os"
// or Ctrl+C in the brain's terminal stops the brain, it tells every page first ({"type": "brain_off"} on /ws
// and /ws/hub-device, docs/dev/protocol.md). Each page then leaves full screen and tries to close itself. A
// browser closes only a window that a script opened ("Open on…" → another monitor); lab-os's own hub window
// (the "Start lab-os" icon) is closed by the brain. Any other page (a tab you opened yourself, on any device)
// can't close, so it shows only a small card with a big Close button, out of full screen, so nobody is stuck.
// Once the brain answers again, the page reloads by itself (the builder, 2026-11-21: screens like the
// Newline come back without a tap). "Restart Now" keeps full screen and says it's restarting.
//
//   showOff(msg)   cover the page (msg: the brain_off message, for who and when)
//   isOff()        has this page been told?
//   offMessage()   the brain_off message it was told with, or null (the headset's panels say it too)
//   backOn()       the brain answers again: reload (only if it was off)

let off = false;
let told = null;

const css = `
#lab-os-off { position: fixed; inset: 0; z-index: 2147483000; display: grid; place-items: center; padding: 1rem;
  background: var(--bg, #05080b); color: var(--text, #d4eef5); font: 500 1rem/1.5 var(--f-ui, system-ui, sans-serif); }
#lab-os-off .box { max-width: 30rem; display: grid; justify-items: center; gap: 0.8rem; text-align: center; }
#lab-os-off svg { width: 2.6rem; height: 2.6rem; stroke: var(--offline, #56636a); stroke-width: 1.5; fill: none; stroke-linecap: round; }
#lab-os-off h1 { margin: 0; font: 700 clamp(1.1rem, 3vw, 1.5rem)/1.2 var(--f-title, system-ui, sans-serif); letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--offline, #56636a); }
#lab-os-off p { margin: 0; font: var(--w-lines, 300) 0.95rem/1.5 var(--f-lines, system-ui, sans-serif); color: var(--text-dim, #6d8c96); }
#lab-os-off button { margin: 0.4rem 0; min-width: 11rem; min-height: 3.2rem; padding: 0 1.6rem; cursor: pointer;
  font: 600 1.15rem/1 var(--f-ui, system-ui, sans-serif); letter-spacing: 0.06em; color: var(--hot, #eafcff);
  background: color-mix(in srgb, var(--primary, #29d4ff) 16%, transparent); border: 1px solid var(--primary, #29d4ff); }
#lab-os-off button:hover, #lab-os-off button:focus-visible { background: color-mix(in srgb, var(--primary, #29d4ff) 30%, transparent); outline: none; }
#lab-os-off .how { color: var(--text, #d4eef5); }
`;

const hhmm = (ms) => new Date(ms || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const mac = /Mac|iPhone|iPad/.test(navigator.platform);
const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
// full screen that a page can't leave by itself: the browser's own (F11, kiosk)
const browserFull = () => !fsElement() && Math.abs(screen.width - innerWidth) <= 2 && Math.abs(screen.height - innerHeight) <= 2;

function leaveFullScreen() {
  navigator.keyboard?.unlock?.();
  document.exitPointerLock?.();
  if (!fsElement()) return;
  (document.exitFullscreen || document.webkitExitFullscreen)?.call(document)?.catch?.(() => {});
}

function tryClose() {
  try { window.close(); } catch { /* not allowed here */ }
}

/** Cover this page: lab-os is off (or restarting). */
export function showOff(msg = {}) {
  off = true;
  told = msg;
  const restarting = !!msg.restart;  // Settings' "Restart Now": it comes back by itself
  if (!restarting) {
    leaveFullScreen();
    tryClose();  // a window a script opened closes here; everything else gets the card
  }
  if (document.getElementById("lab-os-off")) return;
  const style = document.createElement("style");
  style.textContent = css;
  const box = document.createElement("div");
  box.id = "lab-os-off";
  box.setAttribute("role", "alert");
  const who = msg.from ? ` from ${msg.from}` : "";
  box.innerHTML = `<div class="box">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5v8"/><path d="M7.2 6.5a7 7 0 1 0 9.6 0"/></svg>
    <h1></h1><p class="when"></p>${restarting ? "" : '<button type="button">Close</button>'}<p class="how"></p><p class="back"></p>
  </div>`;
  box.querySelector("h1").textContent = restarting ? "lab-os is restarting" : "lab-os is off";
  box.querySelector(".when").textContent = `${restarting ? "Restarted" : "Shut down"}${who} at ${hhmm(msg.time_ms)}.`;
  box.querySelector(".back").textContent = restarting
    ? "It starts again by itself in a few seconds, and this page comes back then."
    : "This page comes back by itself when lab-os runs again.";
  const how = box.querySelector(".how");
  if (!restarting && browserFull()) how.textContent = `Press ${mac ? "Ctrl+Cmd+F" : "F11"} to leave full screen.`;
  box.querySelector("button")?.addEventListener("click", () => {
    tryClose();
    // still here: the browser keeps a tab that a person opened (every browser's rule)
    setTimeout(() => {
      how.textContent = `This browser keeps tabs that you opened yourself: press ${mac ? "Cmd+W" : "Ctrl+W"} to close it.`;
    }, 300);
  });
  document.head.append(style);
  document.body.append(box);
  box.querySelector("button")?.focus();
}

export const isOff = () => off;
export const offMessage = () => told;

/** The brain answers again: start fresh (the page's own state is from before the shutdown). */
export function backOn() {
  if (off) location.reload();
}
