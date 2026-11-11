// Performance test: drifting dots linked when close, and 3D star streaks, at the screen's full size,
// drawn the same way as the concept's network and hyperspace (brute-force links, one stroke per link;
// streaks in brightness batches), so the numbers say what the real hub will cost. Plain gray on black.
import { fullscreenButton } from "/web/fullscreen.js";

const $ = (s) => document.querySelector(s);
const cv = $("#cv"), cx = cv.getContext("2d");
const rand = (a, b) => a + Math.random() * (b - a);

const DEFAULTS = { draw: "all", density: "90", stars: "3000", res: "2" };
const LINK = 140; // px: dots closer than this get a line (theme network.link_px)
const LV = 12, SEG = 6; // streak brightness levels, pieces per streak
const Z_NEAR = 0.05, Z_FAR = 3, F_SCALE = 0.5;
const CYCLE_S = 3.5; // the streaks speed up for 2 s, hold for 0.7 s, then start over

const opts = { ...DEFAULTS };
const query = new URLSearchParams(location.search);
for (const k of Object.keys(DEFAULTS)) {
  if (query.has(k)) opts[k] = query.get(k);
  $(`#${k}`).value = opts[k];
  $(`#${k}`).addEventListener("change", (e) => {
    opts[k] = e.target.value;
    const q = new URLSearchParams(opts);
    history.replaceState(null, "", `?${q}`);
    setup();
  });
}

let W = 0, H = 0, dpr = 1, dots = [], stars = [];
function setup() {
  dpr = Math.min(devicePixelRatio || 1, Number(opts.res) >= 2 ? 2 : Number(opts.res));
  W = innerWidth;
  H = innerHeight;
  cv.width = Math.round(W * dpr);
  cv.height = Math.round(H * dpr);
  cx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const n = opts.draw === "streaks" ? 0 : Math.max(40, Math.round(((W * H) / 1e6) * Number(opts.density)));
  dots = Array.from({ length: n }, () => {
    const a = rand(0, Math.PI * 2), v = rand(4, 14);
    return { x: rand(0, W), y: rand(0, H), vx: Math.cos(a) * v, vy: Math.sin(a) * v };
  });
  const m = opts.draw === "all" || opts.draw === "streaks" ? Number(opts.stars) : 0;
  stars = Array.from({ length: m }, newStar);
  resetStats();
}
function newStar() {
  // a third gathered around the middle, the rest over the whole screen
  const r = Math.random() < 0.33 ? rand(0, 0.25) : rand(0, 1.4), a = rand(0, Math.PI * 2);
  return { x: Math.cos(a) * r, y: Math.sin(a) * r, z: rand(Z_NEAR + 0.2, Z_FAR), w: Math.random() };
}
addEventListener("resize", setup);

function drawNetwork(dt) {
  for (const d of dots) {
    d.x += d.vx * dt;
    d.y += d.vy * dt;
    if (d.x < -20) d.x = W + 20;
    else if (d.x > W + 20) d.x = -20;
    if (d.y < -20) d.y = H + 20;
    else if (d.y > H + 20) d.y = -20;
  }
  if (opts.draw !== "dots") {
    const L2 = LINK * LINK;
    cx.lineWidth = 1;
    for (let i = 0; i < dots.length; i++) {
      const a = dots[i];
      for (let j = i + 1; j < dots.length; j++) {
        const b = dots[j], dx = a.x - b.x, dy = a.y - b.y, dd = dx * dx + dy * dy;
        if (dd < L2) {
          cx.strokeStyle = `rgba(200, 200, 200, ${(1 - Math.sqrt(dd) / LINK) * 0.32})`;
          cx.beginPath();
          cx.moveTo(a.x, a.y);
          cx.lineTo(b.x, b.y);
          cx.stroke();
        }
      }
    }
  }
  cx.fillStyle = "rgba(220, 220, 220, 0.6)";
  for (const d of dots) cx.fillRect(d.x - 1, d.y - 1, 2, 2);
}

function drawStreaks(dt, now) {
  if (!stars.length) return;
  const t = (now / 1000) % CYCLE_S, p = Math.min(1, t / 2);
  const speed = 0.03 + 2.4 * ((Math.exp(4.2 * p) - 1) / (Math.exp(4.2) - 1));
  const trail = 0.002 + 3.5 * p * p, F = Math.min(W, H) * F_SCALE, ox = W / 2, oy = H / 2;
  const lines = Array.from({ length: LV }, () => []);
  for (const s of stars) {
    s.z -= speed * dt;
    const zt = Math.min(Z_FAR, s.z + trail), x1 = ox + (s.x / zt) * F, y1 = oy + (s.y / zt) * F;
    if (s.z < Z_NEAR || x1 < -40 || x1 > W + 40 || y1 < -40 || y1 > H + 40) {
      Object.assign(s, newStar(), { z: Z_FAR });
      continue;
    }
    const x2 = ox + (s.x / s.z) * F, y2 = oy + (s.y / s.z) * F, dx = x2 - x1, dy = y2 - y1;
    const a = Math.min(1, 1.25 - s.z / Z_FAR) * (0.55 + 0.45 * s.w);
    const n = Math.min(SEG, 1 + Math.floor((Math.abs(dx) + Math.abs(dy)) / 18));
    for (let i = 0; i < n; i++) {
      const lv = Math.min(LV - 1, Math.round(a * ((i + 1) / n) ** 1.8 * (LV - 1)));
      if (lv) lines[lv].push(x1 + (dx * i) / n, y1 + (dy * i) / n, x1 + (dx * (i + 1)) / n, y1 + (dy * (i + 1)) / n);
    }
  }
  cx.lineWidth = 1 + 1.3 * p;
  lines.forEach((pts, lv) => {
    if (!pts.length) return;
    cx.strokeStyle = `rgba(230, 230, 230, ${lv / (LV - 1)})`;
    cx.beginPath();
    for (let i = 0; i < pts.length; i += 4) {
      cx.moveTo(pts[i], pts[i + 1]);
      cx.lineTo(pts[i + 2], pts[i + 3]);
    }
    cx.stroke();
  });
}

/* ---------- frames per second: last second, slowest frame, average over the last 10 s ---------- */
let frames = 0, windowStart = 0, slowest = 0, fpsLog = [];
function resetStats() {
  frames = 0;
  windowStart = performance.now();
  slowest = 0;
  fpsLog = [];
}
function stats(now, frameMs) {
  frames++;
  slowest = Math.max(slowest, frameMs);
  if (now - windowStart < 1000) return;
  const fps = (frames * 1000) / (now - windowStart);
  fpsLog = [...fpsLog.slice(-9), fps];
  const avg = fpsLog.reduce((a, b) => a + b, 0) / fpsLog.length;
  $("#fps").textContent = `${fps.toFixed(0)} fps`;
  $("#info").textContent =
    `average ${avg.toFixed(1)} fps over ${fpsLog.length} s · slowest frame ${slowest.toFixed(0)} ms · ` +
    `canvas ${cv.width}×${cv.height} (${W}×${H} at ${dpr}×, device ${devicePixelRatio}×) · ` +
    `${dots.length} dots · ${stars.length} stars`;
  frames = 0;
  windowStart = now;
  slowest = 0;
}

let last = performance.now();
function frame(now) {
  const frameMs = now - last, dt = Math.min(0.05, frameMs / 1000);
  last = now;
  cx.clearRect(0, 0, W, H);
  drawStreaks(dt, now);
  drawNetwork(dt);
  stats(now, frameMs);
  requestAnimationFrame(frame);
}

fullscreenButton($("#full")); // hidden while full screen; says why where the browser can't
$("#hide").addEventListener("click", (e) => {
  e.stopPropagation();
  $("#controls").hidden = true;
});
$("#hud").addEventListener("click", () => ($("#controls").hidden = false)); // tap the numbers: controls back

setup();
requestAnimationFrame(frame);
