// Live view of the arm: one bar per joint, driven by the server's `status` messages. Two arms at once
// (status.left_arm): the left arm's bars in their own card, and its state next to the right arm's.
// An arm whose USB is unplugged (quick job 109): its joints card goes, and its chip says "unplugged",
// within a second (the brain checks the USB every half second); it comes back when it is plugged in.
// One page for each kind of robot (quick job 147): /monitor/so101 and /monitor/xarm show only the arms
// of that kind (armView), and say so while none is connected. /monitor is the list (monitor-list.js).
import { armView } from "/static/arm/arm-feed.js";
import { KINDS, pageKind } from "/static/arm/kinds.js";

const $ = (id) => document.getElementById(id);
const KIND = pageKind(location.pathname);
if (KIND) {
  document.title = KINDS[KIND].title;
  $("page-title").textContent = KINDS[KIND].title;
}
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws?role=monitor`;
const rows = {};

function setPill(el, text, cls) {
  el.textContent = text;
  el.className = `pill ${cls}`;
}

function row(name, lo, hi, box = "joints") {
  const key = `${box}/${name}`;
  if (rows[key]) return rows[key];
  const el = document.createElement("div");
  el.className = "joint";
  el.innerHTML = `<span class="label">${name}</span>
    <div class="track"><div class="zero"></div><div class="knob"></div></div>
    <span class="value"></span>`;
  $(box).appendChild(el);
  rows[key] = { el, lo, hi, knob: el.querySelector(".knob"), value: el.querySelector(".value") };
  return rows[key];
}

function armState(el, a) {
  if (a.connected === false) setPill(el, `${a.name || "arm"}: unplugged (USB)`, "warn");
  else if (a.frozen) setPill(el, a.needs_release ? "frozen: release grip" : "frozen", "warn");
  else if (a.clutch) setPill(el, "following (clutch)", "on");
  else setPill(el, "holding", "off");
}

function bars(joints, limits, box) {
  for (const [name, v] of Object.entries(joints)) {
    const [lo, hi] = limits[name] || [-180, 180];
    const r = row(name, lo, hi, box);
    r.knob.style.left = `${((v - lo) / (hi - lo)) * 100}%`;
    r.value.textContent = `${v >= 0 ? "+" : ""}${v.toFixed(1)}°`;
  }
}

/** An arm's status with its name and USB state at the top, as armState reads them. */
const plain = (s) => ({ ...s, connected: s.arm?.connected, name: s.arm?.name });

function show(raw) {
  setPill($("input"), raw.connected ? "live" : "none", raw.connected ? "on" : "off");
  const who = { free: "free", ai: "the AI tools" }[raw.control] || "an input page";
  setPill($("control"), who, raw.control === "free" ? "off" : "on");
  const s = armView(raw, "right", KIND);
  document.body.classList.toggle("no-arm", !s);
  if (!s) { // no arm of this page's kind is connected
    setPill($("state"), "not connected", "off");
    $("joints-title").textContent = `No ${KINDS[KIND].robot} is connected`;
    $("right-name").textContent = "";
    $("left-chip").hidden = $("left-card").hidden = true;
    document.body.classList.remove("two-arms");
    return;
  }
  const gone = s.arm?.connected === false;
  armState($("state"), plain(s));
  bars(s.joints, s.limits, "joints");
  $("joints").closest(".card").classList.toggle("unplugged", gone);
  const left = armView(raw, "left", KIND);
  const l = left && plain(left);
  $("left-chip").hidden = !l;
  $("left-card").hidden = !l || l.connected === false;
  $("arm-label").textContent = l ? "Right arm" : "Arm";
  $("joints-title").textContent = gone ? `${s.arm?.name || "The arm"} is unplugged` : l ? "Right arm" : "Joints";
  // two arms: both cards say the arm's name, in the same place (quick job 119)
  $("right-name").textContent = l && !gone ? s.arm?.name || "" : gone ? "" : "what the arm reports";
  document.body.classList.toggle("two-arms", !!l);
  if (!l) return;
  armState($("left-state"), l);
  $("left-name").textContent = l.name;
  bars(l.joints, l.limits, "joints-left");
}

let socket = null;
$("stop").onclick = () => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify({ type: "stop" }));

function connect() {
  const ws = new WebSocket(WS_URL);
  socket = ws;
  ws.onopen = () => setPill($("conn"), "connected", "on");
  ws.onclose = () => {
    setPill($("conn"), "disconnected", "off");
    setTimeout(connect, 1000);
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "status") show(msg);
  };
}

connect();
