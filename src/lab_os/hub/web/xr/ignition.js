// The ignition screen in VR, like the designed hub's (#ignite): a small core with a slow dashed ring, a
// dotted inner ring and eight bolts, floating where the jump's lines start and the real core lands; under
// it how to start ("Pull the trigger or pinch to start" with their icons), "Safe to start…", and the
// place and the clock. The unlock (unlock(), ~1.35 s, before the jump): a wind-up, the bolts pull back
// one by one, the ring turns and opens outward, the inner ring collapses, the core swells and bursts a
// ring of light. Units: metres; `unit` metres per unit of the hub's ignition SVG (viewBox ±70).
import * as THREE from "three";
import { C, GLOW, CanvasPlane, FONT, TAU, clamp, glowText, icon, spaced } from "./draw.js";

export const UNLOCK_MS = 1350;
const bez = (x1, y1, x2, y2) => (t) => { // CSS cubic-bezier, solved for x
  t = clamp(t, 0, 1);
  let u = t;
  for (let i = 0; i < 6; i++) {
    const x = 3 * (1 - u) * (1 - u) * u * x1 + 3 * (1 - u) * u * u * x2 + u * u * u - t;
    const dx = 3 * (1 - u) * (1 - u) * x1 + 6 * (1 - u) * u * (x2 - x1) + 3 * u * u * (1 - x2);
    if (Math.abs(dx) < 1e-6) break;
    u -= x / dx;
  }
  u = clamp(u, 0, 1);
  return 3 * (1 - u) * (1 - u) * u * y1 + 3 * (1 - u) * u * u * y2 + u * u * u;
};
const IN = bez(0.7, 0, 0.84, 0), OUT = bez(0.16, 1, 0.3, 1), INOUT = bez(0.65, 0, 0.25, 1), BOLT = bez(0.55, 0, 0.2, 1);
// a CSS transition: `dur` ms after `delay` ms, on `ease`
const tr = (t, delay, dur, ease) => ease(clamp((t - delay) / dur, 0, 1));

function layer(unit, draw, ppu = 8) {
  const s = 150 * unit, p = new CanvasPlane(s, s, (150 * ppu) / s, { additive: true });
  p.paint((g, w) => { g.translate(w / 2, w / 2); g.scale(ppu, ppu); g.strokeStyle = "#fff"; g.fillStyle = "#fff"; draw(g); });
  return p;
}

export class Ignition {
  constructor(unit = 0.0058) {
    this.unit = unit;
    this.group = new THREE.Group();
    this.orb = new THREE.Group();
    this.group.add(this.orb);
    const ring = layer(unit, (g) => { g.lineWidth = 1.5; g.setLineDash([34, 8, 6, 8]); g.beginPath(); g.arc(0, 0, 62, 0, TAU); g.stroke(); });
    const shut = layer(unit, (g) => { g.lineWidth = 0.8; g.globalAlpha = 0.7; g.setLineDash([1, 4]); g.beginPath(); g.arc(0, 0, 52, 0, TAU); g.stroke(); });
    const core = layer(unit, (g) => { g.globalAlpha = 0.9; g.beginPath(); g.arc(0, 0, 12, 0, TAU); g.fill(); g.globalAlpha = 0.5; g.lineWidth = 1; g.beginPath(); g.arc(0, 0, 22, 0, TAU); g.stroke(); });
    this.ring = ring; this.shut = shut; this.core = core;
    this.bolts = [];
    for (let i = 0; i < 8; i++) {
      const b = new THREE.Mesh(new THREE.PlaneGeometry(12 * unit, 4.4 * unit), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.8, ...GLOW, depthWrite: false }));
      const holder = new THREE.Group();
      holder.rotation.z = -((22.5 + i * 45) * Math.PI) / 180;
      holder.add(b);
      this.orb.add(holder);
      this.bolts.push(b);
    }
    this.burst = new THREE.Mesh(new THREE.RingGeometry(13.2 * unit, 14.8 * unit, 96), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.hot), transparent: true, opacity: 0, ...GLOW, depthWrite: false, side: THREE.DoubleSide }));
    for (const p of [ring, shut, core]) { p.mat.color.set(C.primary); this.orb.add(p.mesh); }
    this.orb.add(this.burst);
    // the words: how to start, the icons, "safe to start"; then the place and the clock at the foot
    this.words = new CanvasPlane(2.0, 0.56, 1200);
    this.words.mesh.position.y = -0.72;
    this.group.add(this.words.mesh);
    this.foot = new CanvasPlane(1.6, 0.09, 1200);
    this.foot.mesh.position.y = -1.25;
    this.group.add(this.foot.mesh);
    this.place = "";
    this.t0 = null; // the unlock's start
  }
  /** How to start, with the inputs there are: the headset's ("trigger", "pinch") or a screen's. */
  paintWords(screen, hasHands) {
    const line = screen ? "Click or press any key to start" : "Pull the trigger or pinch to start";
    this.words.paint((g, w, h) => {
      g.textAlign = "center"; g.textBaseline = "middle";
      g.font = `600 ${h * 0.15}px ${FONT.ui}`; spaced(g, 0.06);
      glowText(g, line, w / 2, h * 0.14, C.hot, "rgba(41,212,255,0.35)", 10);
      spaced(g, 0);
      const ic = h * 0.15, gap = ic * 1.9, ids = screen ? ["i-mouse", "i-key"] : hasHands ? ["i-pad", "i-hand"] : ["i-pad"];
      ids.forEach((id, i) => icon(g, id, w / 2 + (i - (ids.length - 1) / 2) * gap, h * 0.42, ic, C.primary, 1.3));
      g.font = `${FONT.linesW} ${h * 0.095}px ${FONT.lines}`;
      const text = "Safe to start. This only opens the hub; no robot moves.", tw = g.measureText(text).width, sh = h * 0.11;
      const x0 = w / 2 - (tw + sh * 1.4) / 2;
      icon(g, "i-shield", x0 + sh / 2, h * 0.72, sh, C.primary, 1.4);
      g.textAlign = "left"; g.fillStyle = C.text;
      g.fillText(text, x0 + sh * 1.4, h * 0.72);
    }, `w${screen}${hasHands}`);
  }
  paintFoot(clock) {
    this.foot.paint((g, w, h) => {
      g.textBaseline = "middle"; g.textAlign = "right";
      g.font = `${FONT.linesW} ${h * 0.42}px ${FONT.lines}`; g.fillStyle = C.dim;
      g.fillText(this.place, w / 2 - h * 0.4, h / 2);
      g.textAlign = "left"; g.font = `${h * 0.45}px ${FONT.digits}`; g.fillStyle = C.primary;
      g.fillText(clock, w / 2 + h * 0.4, h / 2);
    }, `${this.place}|${clock}`);
  }
  unlock(now) { if (this.t0 == null) this.t0 = now; }
  get unlocking() { return this.t0 != null; }
  reset() { this.t0 = null; }

  step(dt, now, clock) {
    this.paintFoot(clock);
    const t = this.t0 == null ? -1 : now - this.t0;
    // idle: the ring turns (14 s), the inner one the other way (22 s), the core breathes (2.6 s)
    this._a = (this._a || 0) + dt * (TAU / 14);
    this._b = (this._b || 0) - dt * (TAU / 22);
    const br = 0.5 - 0.5 * Math.cos((now / 2600) * TAU); // 0..1..0
    let wind = 1, ringRot = 0, ringSc = 1, ringOp = 1, shutSc = 1, shutOp = 1, coreSc = 1 + 0.25 * br, coreOp = 1 - 0.3 * br;
    let textOp = 1, textDrop = 0, burstK = -1;
    if (t >= 0) {
      const k = t / 1450; // the wind-up: dips, comes back, swells a little
      wind = k < 0.14 ? 1 - 0.1 * (k / 0.14) : k < 0.32 ? 0.9 + 0.1 * ((k - 0.14) / 0.18) : 1 + 0.04 * clamp((k - 0.32) / 0.68, 0, 1);
      ringRot = -150 * tr(t, 550, 750, INOUT) * (Math.PI / 180);
      ringSc = 1 + 0.7 * tr(t, 1150, 450, IN);
      ringOp = 1 - tr(t, 1250, 350, (x) => x);
      shutSc = 1 - 0.75 * tr(t, 1000, 400, IN);
      shutOp = 1 - tr(t, 1150, 300, (x) => x);
      coreSc = 1 + 1.4 * tr(t, 1150, 500, OUT);
      coreOp = 1 - tr(t, 1300, 450, (x) => x);
      textOp = 1 - tr(t, 0, 350, (x) => x);
      textDrop = 0.03 * tr(t, 0, 500, IN);
      burstK = (t - 1200) / 800;
    }
    this.orb.scale.setScalar(wind);
    this.ring.mesh.rotation.z = -this._a + ringRot; this.ring.mesh.scale.setScalar(ringSc); this.ring.opacity = ringOp;
    this.shut.mesh.rotation.z = -this._b; this.shut.mesh.scale.setScalar(shutSc); this.shut.opacity = shutOp;
    this.core.mesh.scale.setScalar(coreSc); this.core.opacity = coreOp;
    this.bolts.forEach((b, i) => {
      const k = t < 0 ? 0 : tr(t, 200 + i * 60, 340, BOLT);
      b.position.x = (35 + 20 * k) * this.unit;
      b.material.opacity = t < 0 ? 0.8 : 0.8 * (1 - tr(t, 450 + i * 60, 350, (x) => x));
    });
    this.burst.visible = burstK >= 0 && burstK < 1;
    if (this.burst.visible) { this.burst.scale.setScalar(1 + 5 * (1 - Math.pow(1 - burstK, 2))); this.burst.material.opacity = 1 - burstK; }
    this.words.opacity = textOp; this.foot.opacity = textOp;
    this.words.mesh.position.y = -0.72 - textDrop; this.foot.mesh.position.y = -1.25 - textDrop;
    return t >= UNLOCK_MS; // the unlock is over: start the jump
  }
}
