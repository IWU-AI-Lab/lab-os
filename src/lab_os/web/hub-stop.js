// STOP on the hubs (quick job 43): the rule is STOP on every screen. In the lab (F.11), the builder had to open
// Monitor to stop the visitor wave. The designed hub and the plain hub call this once: a STOP button, fixed at
// the top centre above everything (cards, panels, module pages, the start screen), shown while a real arm is
// connected (/web/stop-state.js). It glows more while the arm moves. A press sends {"type": "stop"} on a
// watcher's link (/ws?role=monitor, the same as Monitor's STOP): it freezes the arm and ends an AI move.
// Each page styles #hub-stop (the button) and #hub-stop-wrap (its glow, outside the cut corners).
//   const b = hubStop();   b.state() → {show, moving}
import { getLink } from "/static/link.js";
import { stopState } from "/web/stop-state.js";

export function hubStop({ onPress = () => {} } = {}) {
  const wrap = document.createElement("div");
  wrap.id = "hub-stop-wrap";
  wrap.hidden = true;
  const b = document.createElement("button");
  b.id = "hub-stop";
  b.type = "button";
  b.textContent = "STOP";
  b.title = "Stop the arm at once (ends an AI move; works from every page)";
  wrap.append(b);
  document.body.append(wrap);
  let state = { show: false, moving: false }, said = 0;
  const link = getLink("monitor"); // a watcher: it can only stop
  link.on("status", (s) => {
    state = stopState(s);
    wrap.hidden = !state.show;
    wrap.classList.toggle("moving", state.moving);
  });
  link.on("close", () => { state = { show: false, moving: false }; wrap.hidden = true; }); // it can't reach the brain
  // a press must not also start the hub or close a panel under it
  for (const ev of ["pointerdown", "pointerup", "mousedown", "touchstart"]) b.addEventListener(ev, (e) => e.stopPropagation());
  b.addEventListener("click", (e) => {
    e.stopPropagation();
    link.send({ type: "stop" });
    onPress();
    b.textContent = "STOPPED";
    clearTimeout(said);
    said = setTimeout(() => (b.textContent = "STOP"), 1500);
  });
  return { el: wrap, state: () => state };
}
