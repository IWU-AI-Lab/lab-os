// "lab-os is off" (quick job 6): when the hub's "Shut down lab-os" stops the brain, it tells every page
// first ({"type": "brain_off"} on /ws and /ws/hub-device, docs/dev/protocol.md), and each page covers itself
// with this screen instead of "brain not reachable". Offline look (DESIGN.md: gray, dim, no glow). Once the
// brain answers again (started from its icon), the page reloads by itself.
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
#lab-os-off .box { max-width: 34rem; display: grid; justify-items: center; gap: 0.9rem; text-align: center; }
#lab-os-off svg { width: 3.2rem; height: 3.2rem; stroke: var(--offline, #56636a); stroke-width: 1.5; fill: none; stroke-linecap: round; }
#lab-os-off h1 { margin: 0; font: 700 clamp(1.1rem, 3vw, 1.6rem)/1.2 var(--f-title, system-ui, sans-serif); letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--offline, #56636a); }
#lab-os-off p { margin: 0; font: var(--w-lines, 300) 1rem/1.5 var(--f-lines, system-ui, sans-serif); color: var(--text-dim, #6d8c96); }
`;

const hhmm = (ms) => new Date(ms || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

/** Cover this page: lab-os is off. */
export function showOff(msg = {}) {
  off = true;
  told = msg;
  if (document.getElementById("lab-os-off")) return;
  const style = document.createElement("style");
  style.textContent = css;
  const box = document.createElement("div");
  box.id = "lab-os-off";
  box.setAttribute("role", "alert");
  const who = msg.from ? ` from ${msg.from}` : "";
  const restarting = !!msg.restart;  // Settings' "Restart Now": it comes back by itself
  box.innerHTML = `<div class="box">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5v8"/><path d="M7.2 6.5a7 7 0 1 0 9.6 0"/></svg>
    <h1>${restarting ? "lab-os is restarting" : "lab-os is off"}</h1>
    <p>It was shut down${who} at ${hhmm(msg.time_ms)}. The arm was let go, and the cameras and microphones are closed.</p>
    <p>${restarting ? "It starts again by itself in a few seconds, and this page comes back then." : 'To start it again, use the "Start lab-os" icon on the brain\'s computer. This page comes back by itself once it runs.'}</p>
  </div>`;
  box.querySelector("p").textContent = `It was ${restarting ? "restarted" : "shut down"}${who} at ${hhmm(msg.time_ms)}. The arm was let go, and the cameras and microphones are closed.`;
  document.head.append(style);
  document.body.append(box);
  document.exitPointerLock?.();
}

export const isOff = () => off;
export const offMessage = () => told;

/** The brain answers again: start fresh (the page's own state is from before the shutdown). */
export function backOn() {
  if (off) location.reload();
}
