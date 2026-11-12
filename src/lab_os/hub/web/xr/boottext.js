// The startup's words in VR, like the designed hub's: the title decoding above the core (letters
// settling left to right, the spacing closing in), the greeting typed under it with a block cursor, and
// the real checks typing out below the core (icon, name, a dotted leader drawing to the value, the value
// lighting up; a scan bar sweeps each row open). Each is a canvas on a plane, redrawn only on change.
import { C, CanvasPlane, FONT, arrive, clamp, glowText, icon, rgba, spaced } from "./draw.js";

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>/#";
const CHECK_ICONS = { Theme: "i-hex", Sound: "i-chip", Display: "i-screen", Internet: "i-globe", AI: "i-chip", Assistant: "i-user", Arm: "i-arm" };

export class Title {
  constructor(w = 3.4, h = 0.26) {
    this.p = new CanvasPlane(w, h, 1000);
    this.text = "";
    this.t0 = null; // decoding started
    this.shown = "";
  }
  get mesh() { return this.p.mesh; }
  start(now) { this.t0 = now; }
  reset() { this.t0 = null; this.shown = ""; this.p.opacity = 0; }
  /** returns true on each new decoding frame (for the tick sound) */
  step(now) {
    if (this.t0 == null) { this.p.opacity = 0; return false; }
    const t = now - this.t0, f = Math.min(24, Math.floor(t / 34)), up = this.text.toUpperCase();
    const done = Math.floor((f / 24) * up.length);
    const frame = f >= 24 ? up : [...up].map((ch, i) => (i < done || ch === " " ? ch : GLYPHS[Math.floor(Math.random() * GLYPHS.length)])).join("");
    const k = arrive(t / 900), sp = 0.7 - 0.54 * k;
    this.p.opacity = k;
    const key = `${frame}|${sp.toFixed(3)}`;
    const changed = frame !== this.shown;
    this.shown = frame;
    this.p.paint((g, w, h) => {
      g.textAlign = "center"; g.textBaseline = "middle";
      g.font = `700 ${h * 0.5}px ${FONT.title}`; spaced(g, sp);
      glowText(g, frame, w / 2 + (h * 0.5 * sp) / 2, h / 2, C.hot, rgba(C.primary, 0.9), h * 0.12);
    }, key);
    return changed && f < 24;
  }
}

export class Greeting {
  constructor(w = 3.4, h = 0.14) {
    this.p = new CanvasPlane(w, h, 1000);
    this.text = "";
    this.t0 = null;
  }
  get mesh() { return this.p.mesh; }
  start(now) { this.t0 = now; }
  reset() { this.t0 = null; this.p.opacity = 0; }
  get done() { return this.t0 != null && this.n >= this.text.length; }
  step(now) {
    if (this.t0 == null) { this.p.opacity = 0; return; }
    this.p.opacity = 1;
    this.n = Math.min(this.text.length, Math.floor((now - this.t0) / 22));
    const cursor = this.n < this.text.length || Math.floor(now / 500) % 2 === 0;
    this.p.paint((g, w, h) => {
      g.textBaseline = "middle"; g.font = `500 ${h * 0.46}px ${FONT.ui}`; spaced(g, 0.04);
      const full = g.measureText(this.text).width, x0 = (w - full) / 2, part = this.text.slice(0, this.n);
      g.fillStyle = C.text; g.textAlign = "left";
      g.fillText(part, x0, h / 2);
      if (cursor && this.n < this.text.length + 1) {
        const x = x0 + g.measureText(part).width + h * 0.06;
        g.fillStyle = C.primary; g.fillRect(x, h * 0.26, h * 0.24, h * 0.48);
      }
    }, `${this.n}|${cursor}`);
  }
}

export class Checks {
  constructor(w = 1.15, rows = 7) {
    this.rowH = 0.066;
    this.p = new CanvasPlane(w, rows * this.rowH + 0.06, 1300);
    this.rows = []; // {k, v, ok, t0}
    this.fade = 1;
  }
  get mesh() { return this.p.mesh; }
  reset() { this.rows = []; this.fade = 1; this.p.opacity = 0; }
  add(k, v, ok, now) { this.rows.push({ k, v, ok, t0: now }); }
  /** returns the number of rows whose value just finished typing (for the sound) */
  step(now) {
    this.p.opacity = this.rows.length ? this.fade : 0;
    if (!this.rows.length) return 0;
    let popped = 0, key = "";
    const state = this.rows.map((r) => {
      const t = now - r.t0;
      const kN = Math.min(r.k.length, Math.floor(Math.max(0, t - 70) / 10));
      const lead = clamp((t - 70 - r.k.length * 10) / 300, 0, 1);
      const vT = t - 70 - r.k.length * 10 - 90;
      const vN = Math.min(r.v.length, Math.floor(Math.max(0, vT) / 10));
      const pop = vN >= r.v.length ? clamp((vT - r.v.length * 10) / 600, 0, 1) : -1;
      if (pop >= 0 && !r.popped) { r.popped = true; popped++; }
      const scan = clamp(t / 450, 0, 1);
      key += `${kN},${lead.toFixed(2)},${vN},${pop.toFixed(2)},${scan.toFixed(2)};`;
      return { ...r, kN, lead, vN, pop, scan, t };
    });
    this.p.paint((g, w, h) => {
      const rh = (h - 0.06 * 1300) / 7, pad = 0.03 * 1300;
      // corner brackets around the block
      g.strokeStyle = rgba(C.primary, 0.7); g.lineWidth = 2;
      const b = 18;
      g.beginPath(); g.moveTo(2, b + 2); g.lineTo(2, 2); g.lineTo(b + 2, 2); g.stroke();
      g.beginPath(); g.moveTo(w - 2, h - b - 2); g.lineTo(w - 2, h - 2); g.lineTo(w - b - 2, h - 2); g.stroke();
      state.forEach((r, i) => {
        const y = pad + rh * (i + 0.5), x0 = pad, x1 = w - pad;
        const reveal = arrive(Math.min(1, r.t / 400));
        g.save();
        g.beginPath(); g.rect(0, y - rh / 2, (x1 + 20) * reveal + 10, rh); g.clip();
        icon(g, CHECK_ICONS[r.k] || "i-hex", x0 + rh * 0.3, y, rh * 0.5, C.primary, 1.5);
        g.font = `${FONT.linesW} ${rh * 0.5}px ${FONT.lines}`; g.textBaseline = "middle";
        g.fillStyle = C.text; g.textAlign = "left";
        const kText = r.k.slice(0, r.kN);
        g.fillText(kText, x0 + rh * 0.8, y);
        const vText = r.v.slice(0, r.vN), vw = g.measureText(r.v).width;
        // the dotted leader, drawn from the name to the value
        const lx0 = x0 + rh * 0.8 + g.measureText(r.k).width + 12, lx1 = x1 - vw - 12;
        if (r.lead > 0 && lx1 > lx0) {
          g.strokeStyle = rgba(C.primary, 0.5); g.lineWidth = 1.5; g.setLineDash([2, 5]);
          g.beginPath(); g.moveTo(lx0, y + rh * 0.08); g.lineTo(lx0 + (lx1 - lx0) * r.lead, y + rh * 0.08); g.stroke(); g.setLineDash([]);
        }
        g.textAlign = "right";
        const vc = r.ok ? C.primary : C.offline;
        if (r.pop >= 0 && r.pop < 1 && r.ok) glowText(g, vText, x1, y, r.pop < 0.3 ? C.hot : vc, C.primary, 12 * (1 - r.pop));
        else { g.fillStyle = vc; g.fillText(vText, x1, y); }
        g.restore();
        if (r.scan < 1) { // the scan bar sweeping the row open
          const sx = (x1 + 10) * r.scan;
          g.fillStyle = rgba(C.hot, 1 - r.scan); g.shadowColor = C.primary; g.shadowBlur = 10;
          g.fillRect(sx, y - rh * 0.35, 3, rh * 0.7); g.shadowBlur = 0;
        }
      });
    }, key);
    return popped;
  }
}
