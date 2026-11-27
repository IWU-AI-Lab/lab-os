// The assistant's core in VR, ring for ring the designed hub's (design.html → #orb, buildOrb, stepOrb):
// the same radii, dashes, speeds, the state's color and brightness, breathing, the speaking ripple,
// rings that lock on one by one at the startup (each from its own scale and turn, a flash and a ring
// of light), the corner brackets closing in, and the core igniting with a lens flare.
// Each ring is drawn once (Canvas 2D, white) on its own plane and tinted; the planes sit a few
// millimetres apart, so in the headset the rings have a little depth.
// Sizes are the hub's SVG units (viewBox -132…132); `unit` metres per unit.
import * as THREE from "three";
import { theme } from "/web/theme.js";
import { C, GLOW, CanvasPlane, TAU, arrive, clamp, rand } from "./draw.js";
import { maximal, minimal } from "./look.js";
import { Gyro } from "/web/core-gyro.js";

const AX = new THREE.Vector3(), ZAX = new THREE.Vector3(0, 0, 1), QZ = new THREE.Quaternion();
// depth (quick job 158): the rings about 3 cm apart, so they part as your head moves; minimal keeps them flat
const ringGap = () => (minimal() ? 0.004 : 0.026);
const PX = 1024; // canvas pixels across the 264-unit orb
const S = PX / 264;

// how each ring flies in (scale, turn in degrees) and its radius (for its ring of light): the hub's
const RING_FROM = { thin: [0.35, -200], arcs: [1.9, 170], seg: [0.5, -120], sat: [1.7, 240], tri: [0.2, 180], ticks: [1.5, -90], cross: [2.3, 45], bars: [1.3, 0], ripple: [0.5, 0] };
const RING_R = { thin: 58, arcs: 70, seg: 84, sat: 77, tri: 64, ticks: 101, cross: 127, bars: 120, ripple: 46 };
export const RING_ORDER = ["thin", "arcs", "seg", "sat", "tri", "ticks", "cross", "bars", "ripple"];
// degrees per second (the hub's), and whether the state's scale (listening contracts) applies
const SPIN = { ticks: 360 / 70, seg: -360 / 40, arcs: 360 / 25, thin: -360 / 55, sat: 360 / 12, tri: -360 / 90, cross: 360 / 160, bars: 0, ripple: 0 };
const SCALES = { tri: 1, seg: 1, arcs: 1 };
const STATE_MULT = {
  idle: { m: 1, scale: 1, breathe: 5 }, listening: { m: 0.5, scale: 0.9, breathe: 2 },
  thinking: { m: 5, scale: 1, breathe: 1.2 }, speaking: { m: 1.4, scale: 1, breathe: 0 },
  offline: { m: 0, scale: 1, breathe: 0 }, error: { m: 0, scale: 1, breathe: 0 },
};

function ringCanvas(draw, glow) {
  return (g) => {
    g.translate(PX / 2, PX / 2);
    g.scale(S, S);
    g.strokeStyle = "#fff"; g.fillStyle = "#fff"; g.lineCap = "butt";
    if (glow) { g.shadowColor = "rgba(255,255,255,0.9)"; g.shadowBlur = 14; }
    draw(g);
  };
}
const circle = (g, r, w, dash = []) => { g.lineWidth = w; g.setLineDash(dash); g.beginPath(); g.arc(0, 0, r, 0, TAU); g.stroke(); };
const radial = (g, a, r1, r2, w) => { g.lineWidth = w; g.beginPath(); g.moveTo(Math.cos(a) * r1, Math.sin(a) * r1); g.lineTo(Math.cos(a) * r2, Math.sin(a) * r2); g.stroke(); };
function drawTicks(g, upto = 1) {
  for (let i = 0; i < 72 * upto; i++) { const long = i % 6 === 0; radial(g, (i / 72) * TAU, long ? 92 : 96, 101, long ? 1.6 : 0.8); }
}
function drawBars(g, upto = 1) { for (let i = 0; i < 96 * upto; i++) radial(g, (i / 96) * TAU, 118, 121, 1.4); }
const DRAW = {
  bars: { op: 0.55, mx: true, fn: (g) => drawBars(g) },
  cross: { op: 0.6, mx: true, fn: (g) => { for (let i = 0; i < 4; i++) { const a = (i / 4) * TAU + Math.PI / 4; radial(g, a, 104, 114, 1); radial(g, a, 124, 130, 1); } } },
  ticks: { op: 0.5, fn: (g) => drawTicks(g) },
  seg: { op: 1, fn: (g) => circle(g, 84, 2, [30, 6, 4, 6]) },
  sat: { op: 0.75, mx: true, fn: (g) => { circle(g, 77, 0.8, [0.5, 3]); g.beginPath(); g.arc(77, 0, 2.2, 0, TAU); g.fill(); } },
  arcs: { op: 1, glow: true, fn: (g) => { g.lineWidth = 4; for (let i = 0; i < 3; i++) { const a0 = (i / 3) * TAU; g.beginPath(); g.arc(0, 0, 70, a0, a0 + TAU * 0.19); g.stroke(); } } },
  tri: { op: 0.8, mx: true, fn: (g) => {
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * TAU + Math.PI / 6, p = (ang, r) => [Math.cos(ang) * r, Math.sin(ang) * r];
      g.beginPath(); g.moveTo(...p(a, 58)); g.lineTo(...p(a - 0.06, 66)); g.lineTo(...p(a + 0.06, 66)); g.closePath(); g.fill();
    }
  } },
  thin: { op: 0.45, fn: (g) => circle(g, 58, 1, [1, 4]) },
};

export class Core {
  /** @param {number} unit metres per SVG unit of the hub's orb (0.005 ≈ a 1 m wide core) */
  constructor(unit = 0.005) {
    this.unit = unit;
    this.group = new THREE.Group(); // placed by the caller; scaled for the startup (arrive big)
    this.inner = new THREE.Group(); // breathing etc. stay inside
    this.group.add(this.inner);
    this.state = "idle";
    this.loud = 0; // 0..1 while speaking (the voice's loudness), or the microphone's while listening
    this.voiceLoud = null; // set from outside when a real voice plays
    this.spinBoost = 1;
    this.scaleNow = 1;
    this.igniteAt = 0;
    this.color = new THREE.Color(C.primary);
    this.rings = {};
    // the 3D core (quick job 159): each ring tilted on its own turning axis, the persona's own set
    this.gyro = new Gyro("");
    const size = 264 * unit;
    let z = 0;
    for (const id of ["bars", "cross", "ticks", "seg", "sat", "arcs", "tri", "thin"]) {
      const d = DRAW[id];
      if (d.mx && !maximal()) continue;
      const p = new CanvasPlane(size, size, PX / size, { additive: true });
      p.paint(ringCanvas(d.fn, d.glow && !minimal())); // minimal: no glow
      p.mesh.position.z = z;
      z += ringGap();
      p.mesh.renderOrder = 20;
      this.inner.add(p.mesh);
      this.rings[id] = { p, op: d.op, a: 0, v: SPIN[id], cur: SPIN[id], on: 0, onAt: null, hitAt: -1e9, from: RING_FROM[id] };
    }
    // the speaking ripple: a circle that ripples with the voice
    this.ripplePts = new Float32Array(121 * 3);
    const rg = new THREE.BufferGeometry();
    rg.setAttribute("position", new THREE.BufferAttribute(this.ripplePts, 3).setUsage(THREE.DynamicDrawUsage));
    this.ripple = new THREE.LineLoop(rg, new THREE.LineBasicMaterial({ color: this.color, transparent: true, ...GLOW, depthWrite: false, depthTest: false }));
    this.ripple.renderOrder = 21;
    this.ripple.position.z = z;
    this.inner.add(this.ripple);
    this.rings.ripple = { op: 1, a: 0, v: 0, cur: 0, on: 0, onAt: null, hitAt: -1e9, from: RING_FROM.ripple, line: this.ripple };
    // the heart: the hub's radial gradient (hot in the middle, the state's color at the rim)
    this.heart = new CanvasPlane(68 * unit * 1.25, 68 * unit * 1.25, 256 / (68 * unit * 1.25), { additive: true });
    this.heart.mesh.position.z = z + 0.004;
    this.heart.mesh.renderOrder = 22;
    this.inner.add(this.heart.mesh);
    this._paintHeart();
    // the lens flare: a long bright streak across, a shorter one up and down
    this.flare = new CanvasPlane(320 * unit, 140 * unit, 3.2 / unit, { additive: true });
    this.flare.mesh.position.z = z + 0.008;
    this.flare.mesh.renderOrder = 23;
    this.flare.opacity = 0;
    this.inner.add(this.flare.mesh);
    this._paintFlare();
    this.flareAt = -1e9;
    // rings of light as rings lock on (a few, reused)
    this.waves = Array.from({ length: 4 }, () => {
      const m = new THREE.Mesh(new THREE.RingGeometry(0.985, 1, 128), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.hot), transparent: true, opacity: 0, ...GLOW, depthWrite: false, depthTest: false, side: THREE.DoubleSide }));
      m.renderOrder = 24; m.visible = false; this.inner.add(m);
      return { m, t0: -1e9, r: 1 };
    });
    // corner brackets that close in on the core at the startup
    this.reticle = new THREE.Group();
    const bm = new THREE.LineBasicMaterial({ color: this.color, transparent: true, opacity: 0, depthTest: false, depthWrite: false });
    for (let i = 0; i < 4; i++) {
      const sx = i % 2 ? 1 : -1, sy = i < 2 ? 1 : -1, L = 0.12;
      const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(sx * (1 - L), sy, 0), new THREE.Vector3(sx, sy, 0), new THREE.Vector3(sx, sy * (1 - L), 0)]);
      const l = new THREE.Line(geo, bm); l.renderOrder = 25; this.reticle.add(l);
    }
    this.reticle.visible = false;
    this.reticleMat = bm;
    this.reticleAt = -1e9;
    this.group.add(this.reticle);
    this.setRingsOn(true);
  }

  _paintHeart() {
    const c = `#${this.color.getHexString()}`, hot = C.hot;
    this.heart.paint((g, w) => {
      const r = w / 2 / 1.25; // the gradient's radius; the plane has a little room for the glow
      const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, r);
      gr.addColorStop(0, hot); gr.addColorStop(0.35, hot); gr.addColorStop(0.6, c + "8c"); gr.addColorStop(1, c + "00");
      g.fillStyle = gr; g.fillRect(0, 0, w, w);
    }, c);
  }
  _paintFlare() {
    const c = `#${this.color.getHexString()}`, hot = C.hot;
    this.flare.paint((g, w, h) => {
      const hg = g.createLinearGradient(0, 0, w, 0);
      hg.addColorStop(0, c + "00"); hg.addColorStop(0.5, hot); hg.addColorStop(1, c + "00");
      g.fillStyle = hg; g.fillRect(0, h / 2 - (1.2 * h) / 140, w, (2.4 * h) / 140);
      const vg = g.createLinearGradient(0, 0, 0, h);
      vg.addColorStop(0, c + "00"); vg.addColorStop(0.5, hot + "cc"); vg.addColorStop(1, c + "00");
      g.fillStyle = vg; g.fillRect(w / 2 - w / 320, 0, (2 * w) / 320, h);
    }, c);
  }

  /** All rings shown (the hub, or a skipped startup) or hidden (before the lock-on). */
  setRingsOn(on) {
    for (const r of Object.values(this.rings)) { r.on = on ? 1 : 0; r.onAt = on ? -1e9 : null; }
    this.igniteAt = on ? -1e9 : 0;
  }
  /** One ring locks on: flies in from its own scale and turn, flashes, sends out a ring of light. */
  lockRing(id, now) {
    const r = this.rings[id];
    if (!r) return;
    r.onAt = now; r.hitAt = now;
    if (id === "ticks" || id === "bars") r.sweepAt = now; // they sweep around like a radar
    const w = this.waves.find((x) => now - x.t0 > 750) || this.waves[0];
    w.t0 = now; w.r = RING_R[id] * this.unit;
  }
  /** Corner brackets close in on the core, hold, and let go. */
  lockOn(now) { this.reticleAt = now; }
  /** The core ignites: it overshoots and settles, with a lens flare. */
  ignite(now) { this.igniteAt = now; this.flareAt = now; }

  step(dt, now) {
    const look = theme.assistant?.[this.state] || {};
    // minimal (quick job 157): the rings stay still, and each state has a still look of its own:
    // listening brighter, thinking the dotted ring bright and the arcs dim, speaking the hot colour
    const still = minimal();
    const target = new THREE.Color(still && this.state === "speaking" ? C.hot : C[look.color] || C.primary);
    if (!target.equals(this.color)) {
      this.color.lerp(target, Math.min(1, dt * 4));
      if (Math.abs(this.color.r - target.r) + Math.abs(this.color.g - target.g) + Math.abs(this.color.b - target.b) < 0.01) this.color.copy(target);
      this._paintHeart(); this._paintFlare();
    }
    const m = STATE_MULT[this.state] || STATE_MULT.idle;
    if (!still) this.gyro.step(dt, this.state, this.loud);
    const dim = this.state === "offline" ? 0.45 : 1;
    this.spinBoost += (1 - this.spinBoost) * Math.min(1, dt * 1.3);
    this.scaleNow += (m.scale - this.scaleNow) * Math.min(1, dt * 4);
    for (const [id, r] of Object.entries(this.rings)) {
      const tgt = still ? 0 : r.v * m.m * (id === "arcs" && this.state === "thinking" ? 2 : 1) * this.spinBoost;
      r.cur += (tgt - r.cur) * Math.min(1, dt * 1.5);
      r.a = (r.a + r.cur * dt) % 360;
      // the lock-on: opacity 0.35 s, scale 0.8 s and turn 1.1 s on the hub's "arrive" curve
      let op = r.on, sc = 1, rot = 0;
      if (r.onAt == null) op = 0;
      else if (r.on < 1) {
        const t = now - r.onAt;
        op = clamp(t / 350, 0, 1);
        sc = r.from[0] + (1 - r.from[0]) * arrive(t / 800);
        rot = r.from[1] * (1 - arrive(t / 1100));
        if (t > 1100) r.on = 1;
      }
      const hit = now - r.hitAt < 260 ? 2 : 1;
      const obj = r.p ? r.p.mesh : r.line;
      const spin = -((r.a + rot) * Math.PI) / 180, gy = still ? null : this.gyro.of(id);
      if (gy) { // tilted on its axis (in the core's plane), then turned about its own centre
        AX.set(Math.cos(gy.phi), Math.sin(gy.phi), 0);
        obj.quaternion.setFromAxisAngle(AX, gy.tilt).multiply(QZ.setFromAxisAngle(ZAX, spin));
      } else obj.rotation.set(0, 0, spin);
      obj.scale.setScalar(sc * (SCALES[id] ? this.scaleNow : 1));
      obj.visible = op > 0.002;
      if (r.p) {
        r.p.mat.color.copy(this.color).multiplyScalar(hit);
        const stateOp = !still ? 1 : this.state === "listening" ? 1.4
          : this.state === "thinking" ? (id === "thin" ? 2.2 : id === "arcs" ? 0.35 : 1) : 1;
        r.p.mat.opacity = Math.min(1, r.op * stateOp) * op * dim;
        if (r.sweepAt != null) { // the ticks and bars appear around the ring in 0.45 s
          const k = clamp((now - r.sweepAt) / 450, 0, 1);
          r.p.paint(ringCanvas((g) => (id === "ticks" ? drawTicks(g, k) : drawBars(g, k))), `sweep${Math.round(k * 40)}`);
          if (k >= 1) r.sweepAt = null;
        }
      }
    }
    // breathing, or the voice's loudness
    let s = 1;
    if (this.state === "speaking") {
      if (this.voiceLoud != null) this.loud += (this.voiceLoud - this.loud) * Math.min(1, dt * 18);
      else {
        if (!this.nextSyl || now > this.nextSyl) { this.loudTarget = Math.random() < 0.15 ? 0 : rand(0.25, 1); this.nextSyl = now + rand(70, 160); }
        this.loud += ((this.loudTarget || 0) - this.loud) * Math.min(1, dt * 14);
      }
      s = still ? 1 : 1 + this.loud * 0.16;
    } else if (this.state === "listening" && this.micLevel != null) {
      this.loud += (Math.min(1, this.micLevel * 8) - this.loud) * Math.min(1, dt * 12);
      s = still ? 0.9 : 0.9 + this.loud * 0.12;
    } else {
      this.loud += (0 - this.loud) * Math.min(1, dt * 6);
      if (m.breathe && !still) s = 1 + 0.07 * Math.sin((now / 1000) * (TAU / m.breathe));
      if (this.state === "offline") s = 0.88;
    }
    // the ignition: the heart overshoots, then settles
    const ig = this.igniteAt ? clamp((now - this.igniteAt) / 800, 0, 1) : 0, ige = 1 - Math.pow(1 - ig, 3);
    const igb = ig >= 1 ? 1 : 1 + 3.2 * Math.pow(ig - 1, 3) + 2.2 * Math.pow(ig - 1, 2);
    this.heart.mesh.scale.setScalar(s * Math.max(0.05, igb));
    this.heart.opacity = dim * ige;
    // the ripple
    const R = this.rings.ripple, t = now / 1000;
    for (let i = 0; i <= 120; i++) {
      const a = (i / 120) * TAU, r = (46 + this.loud * 7 * (0.6 * Math.sin(a * 6 + t * 9) + 0.4 * Math.sin(a * 11 - t * 6))) * this.unit;
      this.ripplePts[i * 3] = Math.cos(a) * r; this.ripplePts[i * 3 + 1] = Math.sin(a) * r; this.ripplePts[i * 3 + 2] = 0;
    }
    this.ripple.geometry.attributes.position.needsUpdate = true;
    this.ripple.material.color.copy(this.color).multiplyScalar(now - R.hitAt < 260 ? 2 : 1);
    this.ripple.material.opacity = (R.onAt == null ? 0 : clamp((now - R.onAt) / 350, 0, 1)) * dim;
    // the flare (1.1 s): a quick bright streak that stretches and fades
    const fk = (now - this.flareAt) / 1100;
    this.flare.opacity = !still && fk >= 0 && fk < 1 ? Math.sin(Math.PI * Math.min(1, fk * 1.6)) * (1 - fk) * 1.4 : 0;
    this.flare.mesh.scale.set(0.4 + 1.2 * arrive(fk), 1, 1);
    // rings of light
    for (const w of this.waves) {
      const k = (now - w.t0) / 700;
      w.m.visible = !still && k >= 0 && k < 1;
      if (!w.m.visible) continue;
      w.m.scale.setScalar(w.r * (1 + 0.35 * (1 - Math.pow(1 - k, 2))));
      w.m.material.opacity = 0.9 * (1 - k);
    }
    // the corner brackets: from far out to around the core in 0.55 s, gone after 1.5 s
    const rk = (now - this.reticleAt) / 1000;
    this.reticle.visible = rk >= 0 && rk < 1.9;
    if (this.reticle.visible) {
      const size = 101 * this.unit * 1.3, k = arrive(rk / 0.55);
      this.reticle.scale.setScalar(size * (1.6 - 0.6 * k));
      this.reticleMat.color.copy(this.color);
      this.reticleMat.opacity = rk < 1.5 ? k : Math.max(0, 1 - (rk - 1.5) / 0.4);
    }
  }
}
