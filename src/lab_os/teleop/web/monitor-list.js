// The Monitor list (quick job 147): a card for each kind of robot (KINDS), with a light live preview
// of each arm of that kind (a side view drawn from its joints, and its state). A tap opens that kind's
// Monitor page: in the hub as its module (the hub's views: monitor-so101, monitor-xarm), else the page.
import { getLink } from "/static/link.js";
import { armView } from "/static/arm/arm-feed.js";
import { KINDS } from "/static/arm/kinds.js";

const $ = (id) => document.getElementById(id);
const link = getLink("monitor"); // a watcher: it can only stop
// a side view: each segment's length (the upper arm = 1), so each kind's picture looks like it
const SEGMENTS = { so101: [1, 1.15, 0.75], xarm: [1, 0.95, 0.95] };
const BASE = 0.45; // the base, from the floor to the shoulder
const EVERY_MS = 200; // at most 5 pictures a second (a Pi's touchscreen)

let inHub = false;
try { inHub = parent !== window && parent.location.origin === location.origin && parent.location.pathname === "/"; } catch {}

const cards = {};
for (const [kind, k] of Object.entries(KINDS)) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "card kind";
  b.innerHTML = `<div class="in"><h2><span>${k.title}</span><small></small></h2><div class="arms"></div></div>`;
  b.onclick = () => {
    if (inHub) return parent.postMessage({ type: "lab-os-open-view", id: `monitor-${kind}` }, location.origin);
    location.href = `/monitor/${kind}${location.search}`; // ?device= stays
  };
  $("kinds").append(b);
  cards[kind] = { arms: b.querySelector(".arms"), count: b.querySelector("h2 small"), key: "" };
}

/** The side view of one arm: base, upper arm, forearm, wrist and the two fingers (SVG). */
function picture(kind, j) {
  const [upper, fore, wrist] = SEGMENTS[kind] || SEGMENTS.so101;
  const s = 30; // pixels for a length of 1
  let x = 50, y = 110 - BASE * s, a = 0;
  const pts = [[50, 110], [x, y]];
  for (const [len, joint] of [[upper, "shoulder_lift"], [fore, "elbow_flex"], [wrist, "wrist_flex"]]) {
    a += ((j[joint] || 0) * Math.PI) / 180; // 0 = upright, + tilts forward (to the right here)
    x += len * s * Math.sin(a);
    y -= len * s * Math.cos(a);
    pts.push([x, y]);
  }
  const open = (Math.min(Math.max(j.gripper || 0, 0), 90) * Math.PI) / 360;
  const finger = (da) => `M${x.toFixed(1)} ${y.toFixed(1)} l${(9 * Math.sin(a + da)).toFixed(1)} ${(-9 * Math.cos(a + da)).toFixed(1)}`;
  const line = pts.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join(" ");
  const dots = pts.slice(1).map(([px, py]) => `<circle class="dot" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="2.6"/>`).join("");
  return `<svg viewBox="0 0 160 120" aria-hidden="true"><line class="floor" x1="10" y1="110" x2="150" y2="110"/>` +
    `<path class="seg" d="${line} ${finger(open)} ${finger(-open)}"/>${dots}</svg>`;
}

function stateWord(s) {
  if (s.arm?.connected === false) return "unplugged (USB)";
  if (s.frozen) return "frozen";
  if (s.clutch) return "following";
  return "holding";
}

const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function draw(raw) {
  for (const [kind, k] of Object.entries(KINDS)) {
    const arms = ["right", "left"].map((side) => armView(raw, side, kind)).filter(Boolean);
    const html = arms.length
      ? arms.map((s) => `<div class="arm${s.frozen ? " frozen" : ""}">${picture(kind, s.joints || {})}` +
          `<span class="who">${esc(s.arm?.name)}: ${stateWord(s)}</span></div>`).join("")
      : `<p class="none">No ${k.robot} is connected to the brain.</p>`;
    const c = cards[kind];
    if (html === c.key) continue;
    c.key = html;
    c.arms.innerHTML = html;
    c.count.textContent = arms.length ? `${arms.length} connected` : "none connected";
  }
}

let last = 0, waiting = null, latest = null;
link.on("status", (s) => {
  latest = s;
  if (waiting) return;
  const wait = Math.max(0, last + EVERY_MS - performance.now());
  waiting = setTimeout(() => { waiting = null; last = performance.now(); draw(latest); }, wait);
});
const setConn = (text, cls) => { $("conn").textContent = text; $("conn").className = `pill ${cls}`; };
link.on("open", () => setConn("connected", "on"));
link.on("close", () => setConn("disconnected", "off"));
$("stop").onclick = () => link.send({ type: "stop" });
