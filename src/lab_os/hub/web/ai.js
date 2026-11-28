// AI Control: the arm from its side (real geometry, /api/arm 5×/s), where the last move aimed, and every
// robot-tool call as it happens (/api/ai-calls 1×/s). STOP goes over the same WebSocket as every page's.
import { getLink } from "/static/link.js";
import { drawRes } from "/web/screen.js";
import { cap, jointLabel } from "/web/words.js";

const $ = (s) => document.querySelector(s);
const link = getLink("monitor");  // a watcher: it can only stop
$("#stop").addEventListener("click", () => link.send({ type: "stop" }));

const TOOL = {
  arm_status: "Read the arm", list_poses: "Listed the poses", move_joints: "Move joints", gripper: "Gripper",
  move_to: "Move to", go_to_pose: "Go to pose", stop: "Stop", pick_at: "Pick",
  camera_snapshot: "Took a picture", table_point: "Pixel → table", pose_view: "Drew the pose",
};
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function setPill(id, text, cls) {
  const el = $(id);
  el.textContent = text;
  el.className = `pill ${cls}`;
}

/* ---------- the calls ---------- */
let after = 0, count = 0, target = null;
function args(a) {
  return Object.entries(a || {})
    .filter(([k, v]) => v !== null && v !== undefined && k !== "arm")
    .map(([k, v]) => (typeof v === "object" ? Object.entries(v).map(([j, d]) => `${jointLabel(j)} ${d}`).join(", ") : `${k.replace(/_cm$|_pct$/, "")} ${v}`))
    .join(", ");
}
function summary(c) {
  const r = c.result;
  if (typeof r === "string") return r;
  if (!r || typeof r !== "object") return "";
  const out = [];
  if (r.result && typeof r.result === "string") out.push(r.result);
  if (r.problem) out.push(r.problem);
  if (r.message) out.push(r.message);
  if (Array.isArray(r.clipped) && r.clipped.length) out.push(`Clipped: ${r.clipped.join("; ")}`);
  const p = r.gripper_point_cm;
  if (p) out.push(`Gripper at ${p.x}, ${p.y}, ${p.z} cm`);
  if (r.poses) out.push(`Poses: ${Object.keys(r.poses).join(", ")}`);
  return out.map((t) => cap(t)).join(". ");
}
function addCall(c) {
  count += 1;
  if (c.tool === "move_to") target = { x: c.args.x_cm, y: c.args.y_cm, z: c.args.z_cm };
  const li = document.createElement("li");
  li.className = `call ${c.outcome}`;
  const time = new Date(c.t * 1000).toLocaleTimeString([], { hour12: false });
  const a = args(c.args), s = summary(c);
  li.innerHTML = `<span class="t">${time}</span><span class="tool">${esc(TOOL[c.tool] || c.tool)}</span><span class="o">${esc(cap(c.outcome))}</span>` +
    (a ? `<code>${esc(a)}</code>` : "") + (s ? `<p>${esc(s)}</p>` : "");
  $("#calls").prepend(li);
  while ($("#calls").children.length > 60) $("#calls").lastElementChild.remove();
}
async function pollCalls() {
  try {
    const res = await fetch(`/api/ai-calls?after=${after}`, { cache: "no-store" });
    const d = await res.json();
    for (const c of d.calls) { addCall(c); after = Math.max(after, c.t); }
    $("#empty").hidden = count > 0;
    $("#n-calls").textContent = count ? `${count} this run` : "";
    if (d.mcp) {
      setPill("#c-tools", `On, port ${new URL(d.mcp).port}`, "on");
      $("#add-cmd").textContent = `claude mcp add --transport http lab-os ${d.mcp}`;
    } else setPill("#c-tools", "Off", "off");
    setPill("#c-motion", d.motion_allowed ? "Allowed here" : "Not allowed here", d.motion_allowed ? "on" : "warn");
    const ctl = { ai: ["The AI, moving", "on"], teleop: ["Arm Control", "warn"], free: ["Free", "off"] }[d.control] || [cap(d.control), "off"];
    setPill("#c-control", ...ctl);
    document.body.classList.toggle("moving", d.control === "ai");
  } catch {
    setPill("#c-tools", "Brain not reachable", "bad");
  }
}

/* ---------- the arm ---------- */
let arm = null, shown = null;
async function pollArm() {
  try {
    arm = await (await fetch("/api/arm", { cache: "no-store" })).json();
  } catch {
    arm = null;
  }
  if (!arm) return setPill("#c-arm", "Brain not reachable", "bad");
  $("#arm-name").textContent = arm.name;
  setPill("#c-arm", arm.connected ? "Answering" : "Disconnected", arm.connected ? "on" : "bad");
  const p = arm.gripper_point_cm;
  $("#gx").textContent = p ? p.x.toFixed(1) : "—";
  $("#gy").textContent = p ? p.y.toFixed(1) : "—";
  $("#gz").textContent = p ? p.z.toFixed(1) : "—";
  $("#gopen").textContent = arm.gripper_open_pct != null ? `${Math.round(arm.gripper_open_pct)}%` : "—"; // a unit (quick job 155)
  $("#side-note").textContent = arm.side_cm ? "Seen from its side, cm" : "No side view for this arm model";
}

/* ---------- the side view ---------- */
const cv = $("#side"), cx = cv.getContext("2d");
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const res = drawRes(); // this screen's drawing resolution (Settings → This device, ?res=)
function draw() {
  requestAnimationFrame(draw);
  const box = cv.getBoundingClientRect(), dpr = res;
  if (!box.width) return;
  if (cv.width !== Math.round(box.width * dpr) || cv.height !== Math.round(box.height * dpr)) {
    cv.width = Math.round(box.width * dpr);
    cv.height = Math.round(box.height * dpr);
  }
  const w = box.width, h = box.height;
  cx.setTransform(dpr, 0, 0, dpr, 0, 0);
  cx.clearRect(0, 0, w, h);
  const C = css("--primary") || "#29d4ff", LINE = css("--line") || "#1f3d48", DIM = css("--text-dim") || "#6d8c96";
  const HOT = css("--hot") || "#eafcff", AMBER = css("--accent") || "#ff9a2e", BG = css("--bg") || "#05080b";
  const fLines = css("--f-lines") || "sans-serif", fDigits = css("--f-digits") || "monospace";
  // k: the text and marks grow with the drawing (quick job 155: on the 4K they stayed small)
  const k = Math.max(1, Math.min(w / 760, h / 440, 4));
  const labelW = Math.min(220 * k, w * 0.3);
  // the world: 12 cm behind the base to 45 cm in front, the table to 42 cm up
  const R0 = -12, R1 = 45, Z0 = -3, Z1 = 42;
  const s = Math.min((w - labelW - 30) / (R1 - R0), (h - 30 * k) / (Z1 - Z0));
  const ox = 20 - R0 * s, oy = h - 20 * k + Z0 * s;
  const P = (r, z) => [ox + r * s, oy - z * s];
  // floor, with a mark every 5 cm and a number every 10
  cx.strokeStyle = LINE; cx.fillStyle = DIM; cx.lineWidth = 1; cx.font = `300 ${11 * k}px ${fLines}`;
  cx.beginPath(); cx.moveTo(...P(R0, 0)); cx.lineTo(...P(R1, 0)); cx.stroke();
  for (let r = -10; r <= R1; r += 5) {
    const [x, y] = P(r, 0);
    cx.beginPath(); cx.moveTo(x, y); cx.lineTo(x, y + (r % 10 ? 4 : 7) * k); cx.stroke();
    if (r > 0 && r % 10 === 0) cx.fillText(`${r}${r === 40 ? " cm" : ""}`, x - 6 * k, y + 18 * k);
  }
  for (let z = 10; z <= 40; z += 10) { const [x, y] = P(R0, z); cx.fillText(String(z), x, y + 4 * k); }
  const pts = arm?.side_cm;
  if (!pts) return;
  // ease toward the newest reading
  if (!shown || shown.length !== pts.length) shown = pts.map((p) => ({ ...p }));
  for (let i = 0; i < pts.length; i++) { shown[i].r += (pts[i].r - shown[i].r) * 0.25; shown[i].z += (pts[i].z - shown[i].z) * 0.25; }
  // reach: a dashed arc around the shoulder
  const sh = shown[2] || shown[1], reach = shown.slice(2).reduce((a, p, i, all) => (i ? a + Math.hypot(p.r - all[i - 1].r, p.z - all[i - 1].z) : 0), 0);
  cx.setLineDash([2, 6]); cx.strokeStyle = LINE;
  cx.beginPath(); cx.arc(...P(sh.r, sh.z), reach * s, Math.PI, 2 * Math.PI); cx.stroke(); cx.setLineDash([]);
  // where the last move aimed (its forward distance and height)
  if (target && target.x != null) {
    const far = Math.hypot(target.x, target.y || 0), out = far > R1 - 2;
    const [tx, ty] = P(Math.min(far, R1 - 2), target.z);
    cx.strokeStyle = AMBER; cx.lineWidth = 1;
    const m = 12 * k;
    cx.beginPath(); cx.arc(tx, ty, 7 * k, 0, 2 * Math.PI); cx.moveTo(tx - m, ty); cx.lineTo(tx + m, ty); cx.moveTo(tx, ty - m); cx.lineTo(tx, ty + m); cx.stroke();
    cx.fillStyle = AMBER; cx.font = `300 ${11 * k}px ${fLines}`; cx.textAlign = "right"; cx.fillText(out ? `Last target: ${far.toFixed(0)} cm out, off this view` : "Last target", tx - 4 * k, ty + 24 * k); cx.textAlign = "left";
  }
  // the arm: a glowing line through the joints, a hexagon on each, the jaws at the tip
  cx.strokeStyle = C; cx.lineWidth = 3 * k; cx.shadowColor = C; cx.shadowBlur = 10 * k;
  cx.beginPath(); shown.forEach((p, i) => cx[i ? "lineTo" : "moveTo"](...P(p.r, p.z))); cx.stroke();
  const [bx, by] = P(0, shown[0].z); // the base's bottom: above the table on a plate
  cx.beginPath(); cx.moveTo(bx - 4 * s, by); cx.lineTo(bx + 4 * s, by); cx.stroke();
  cx.shadowBlur = 0;
  const tip = shown.at(-1), wr = shown.at(-2), ang = Math.atan2(-(tip.z - wr.z), tip.r - wr.r), open = ((arm.gripper_open_pct ?? 30) / 100) * 0.6 + 0.12;
  cx.lineWidth = 2 * k;
  for (const sgn of [-1, 1]) { const [tx, ty] = P(tip.r, tip.z), a = ang + sgn * open; cx.beginPath(); cx.moveTo(tx, ty); cx.lineTo(tx + Math.cos(a) * 3 * s, ty + Math.sin(a) * 3 * s); cx.stroke(); }
  // labels: a column on the right, a leader line to each joint
  const named = shown.filter((p) => ["shoulder_lift", "elbow_flex", "wrist_flex", "tip"].includes(p.name));
  const lx = w - labelW + 30 * k;
  named.forEach((p, n) => {
    const [x, y] = P(p.r, p.z), ly = h * 0.16 + n * Math.min(70 * k, h * 0.17);
    cx.fillStyle = BG; cx.strokeStyle = C; cx.lineWidth = 1.5 * k;
    const hr = 6 * k;
    cx.beginPath(); for (let i = 0; i < 6; i++) { const a = (i / 6) * 2 * Math.PI + Math.PI / 6; cx[i ? "lineTo" : "moveTo"](x + Math.cos(a) * hr, y + Math.sin(a) * hr); } cx.closePath(); cx.fill(); cx.stroke();
    cx.strokeStyle = `${C}80`; cx.lineWidth = k;
    cx.beginPath(); cx.moveTo(x + hr + k, y); cx.lineTo(lx - 30 * k, ly); cx.lineTo(lx - 8 * k, ly); cx.stroke();
    const isTip = p.name === "tip", deg = arm.joints?.[p.name];
    cx.fillStyle = DIM; cx.font = `300 ${12 * k}px ${fLines}`;
    cx.fillText(isTip ? "Gripper tip, cm" : jointLabel(p.name), lx, ly - 7 * k);
    cx.fillStyle = HOT; cx.font = isTip ? `500 ${16 * k}px ${css("--f-ui")}` : `${18 * k}px ${fDigits}`;
    cx.fillText(isTip ? `${p.r.toFixed(1)} out, ${p.z.toFixed(1)} up` : `${deg >= 0 ? " " : "-"}${Math.abs(deg ?? 0).toFixed(1)}°`, lx, ly + 15 * k);
  });
}

pollArm();
pollCalls();
setInterval(pollArm, 200);
setInterval(pollCalls, 1000);
requestAnimationFrame(draw);
