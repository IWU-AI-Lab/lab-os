// Entry point of the teleop page: status panel + readout, and the two input sources
// (Quest/WebXR in xr.js, keyboard + trackpad in desktop-input.js). Only one source is active at a time.
import { getLink } from "./link.js";
import { initXR } from "./xr.js";
import { isHeadset } from "./headset.js";
import { initDesktop } from "./desktop-input.js";
import { gate } from "./control-gate.js";
import { initCams } from "./cams.js";
import { deviceName } from "/web/device.js";
import { held } from "/web/words.js";

const $ = (id) => document.getElementById(id);
const link = getLink("input");

// Inside the hub the monitor has its own button, and a new tab would leave full screen.
if (window.self !== window.top) $("monitor-link").hidden = true;

function setPill(el, text, cls, why = "") {
  el.textContent = text;
  el.className = `pill ${cls}`;
  el.title = why;
}

link.on("open", () => {
  setPill($("conn"), "Connected", "on");
  link.send({ type: "hello", agent: navigator.userAgent, device: deviceName() });
});
link.on("close", () => setPill($("conn"), "Disconnected", "off"));
link.on("error", (m) => ($("xr-msg").textContent = m.message));
$("stop").onclick = () => link.send({ type: "stop" });

// Only one page drives at a time; the driver hands control over by leaving (Esc / exit XR).
const CONTROL = {
  you: ["This page", "on"],
  other: ["Another page (it must leave first)", "warn"],
  free: ["Free (start an input to take it)", "off"],
  ai: ["The AI tools (until their move ends)", "warn"],
};
link.on("status", (s) => {
  const [text, cls] = CONTROL[s.control] || ["—", "off"];
  setPill($("control"), s.control === "other" && s.driver ? `The page on ${s.driver} (it must leave first)` : text, cls);
  // quick job 76: the buttons that would take control, grey while it can't be taken (not the one in use)
  gate(s, Object.entries(sourceButtons).filter(([k]) => k !== ui.active).map(([, b]) => b), $("control-why"));
  if (s.arm?.connected === false) setPill($("state"), "Arm disconnected (USB)", "warn");
  else if (s.frozen) { const h = held(s.needs_release); setPill($("state"), h.text, "held", h.why); }
  else if (s.clutch) setPill($("state"), "Following (clutch)", "on");
  else setPill($("state"), "Holding", "off");
  const g = s.joints.gripper;
  const [lo, hi] = s.limits.gripper || [0, 1];
  $("gripper").textContent = g === undefined ? "—" : `${Math.round(((g - lo) / (hi - lo)) * 100)}% open`;
  $("speed").textContent = `${Math.round(s.speed_scale * 100)}%`;
  // the slider goes up to the venue's cap; it follows the arm's speed unless it's being dragged
  const sp = $("speed-set");
  if (!sp) return; // a page without the speed slider
  sp.disabled = false;
  sp.max = Math.round((s.max_speed_scale ?? 1) * 100);
  if (document.activeElement !== sp) sp.value = Math.round(s.speed_scale * 100);
});
// Two arms at once (preview 3): the left controller's arm, next to the right one's state.
link.on("status", (s) => {
  const l = s.left_arm;
  if (!$("left-chip")) return; // a page without the left-arm chip
  $("left-chip").hidden = !l;
  $("two-arms-hint").hidden = !l;
  $("arm-label").textContent = l ? "Right arm" : "Arm";
  if (!l) return;
  if (l.connected === false) setPill($("left-state"), "Disconnected (USB)", "warn");
  else if (l.frozen) { const h = held(l.needs_release); setPill($("left-state"), h.text, "held", h.why); }
  else if (l.clutch) setPill($("left-state"), "Following (clutch)", "on");
  else setPill($("left-state"), "Holding", "off");
});
// hand → arm: relative or 1:1 (the brain keeps it; 1:1 only for arms with kinematics)
link.on("status", (s) => {
  const sel = $("mode-set");
  if (!sel || !s.mode) return;
  sel.disabled = false;
  for (const o of sel.options) o.disabled = !(s.modes || ["relative"]).includes(o.value);
  if (document.activeElement !== sel) sel.value = s.mode;
  const off = !(s.modes || []).includes("one_to_one");
  const top = s.one_to_one_deg_per_s == null ? "the servos' own top speed" : `${s.one_to_one_deg_per_s}°/s`;
  const warm = s.servos?.hot ? ` Servos warm (${Math.round(s.servos.max_temp_c)} °C): slowed to relative speed.` : "";
  const both = s.left_arm ? " Both arms use it." : "";
  $("mode-speed").textContent = off
    ? "1:1 is off in this venue (⚙ Settings → Robots → Teleop 1:1 Top Joint Speed)."
    : `1:1 follows as fast as ${top}; the Speed slider applies to relative only.${both}${warm}`;
  $("mode-hint").hidden = s.mode !== "one_to_one";
});
if ($("mode-set")) $("mode-set").onchange = (e) => link.send({ type: "set_mode", mode: e.target.value });
if ($("speed-set")) $("speed-set").oninput = (e) => link.send({ type: "set_speed", speed_scale: e.target.value / 100 });

// ---- Shared UI helpers for the input sources ---------------------------------------------
function fmt(c) {
  if (!c.pos) return "Tracking lost";
  const n = (v) => (v >= 0 ? "+" : "") + v.toFixed(2);
  const b = Object.entries(c.buttons).filter(([, on]) => on).map(([k]) => k).join(",") || "-";
  return `pos ${c.pos.map(n).join(" ")}  grip ${c.grip.toFixed(2)}  trig ${c.trigger.toFixed(2)}  btn ${b}`;
}

let lastReadout = 0;
const sourceButtons = { xr: $("enter"), ar: $("enter-ar"), desktop: $("desktop") };
// In a headset there's no keyboard to drive with: Desktop control can't be chosen there (the builder,
// 2026-11-21); the Quest's way in is Enter VR or Enter AR. Told by the browser, so a desktop with a
// WebXR emulator keeps all three choices (quick job 87).
if (isHeadset()) {
  const d = $("desktop");
  d.dataset.unavailable = "1";
  d.disabled = true;
  d.title = "Desktop control is for a computer with a keyboard. In the headset, use Enter VR or Enter AR.";
}

const ui = {
  active: null,
  /** Mark which input source is running; the other one's button is disabled meanwhile. */
  setActive(name) {
    ui.active = name;
    for (const [key, btn] of Object.entries(sourceButtons)) btn.dataset.blocked = name && name !== key ? "1" : "";
    for (const [key, btn] of Object.entries(sourceButtons)) {
      const taken = btn.dataset.taken === "1" && name !== key; // quick job 76: someone else has control
      btn.disabled = btn.dataset.blocked === "1" || btn.dataset.unavailable === "1" || taken;
    }
  },
  showHands(hands, label = "") {
    const now = performance.now();
    if (now - lastReadout < 100) return;
    lastReadout = now;
    $("readout").textContent =
      (label ? `${label}\n` : "") +
      (Object.entries(hands).map(([side, c]) => `${side.padEnd(5)} ${fmt(c)}`).join("\n") || "No controllers");
  },
  message(text) {
    $("xr-msg").textContent = text;
  },
};

initXR(link, ui);
initCams(link); // the arm's camera pictures, under the joint angles (quick job 63)
initDesktop(link, ui);
