// The hub's callouts in VR, drawn like the designed hub's (design.html → .side .panel): the title in a
// tab on a thin line, a node at the end facing the core with ticks beside it, a bright lead-in at the
// other end, the open mark (⤢) by the tab, and the content on a see-through fill with a cut corner.
// Current Project (the step bar, Next ›› …), AI Spend (the month against the budget), Commits (bars per
// day, 7d / 14d / 30d), Devices (a hive per kind, "List all"). Each reads the same real facts as the
// screen (/api/project, /api/spend, /api/commits, /api/devices) and is hidden when they aren't there.
// Pointing: hit(u, v) → what's under the pointer (a control of the callout, a device, or the callout
// itself, which opens its details page: DetailsPage below).
// Units: drawn in "rem" like the CSS (R canvas pixels per rem), shown at `remM` metres per rem.
import { C, CanvasPlane, FONT, TAU, clamp, icon, rgba, spaced } from "./draw.js";

const R = 80; // canvas pixels per rem
export const REM_M = 0.058; // metres per rem in VR (the panel ~0.8 m wide, readable at 2.4 m)
const W = 13.6; // a callout's width, rem (like the screen's column)
const HEAD = 1.75;

/** Wrap `text` to `maxW` px with the current font; at most `lines` lines (the last gets "…"). */
export function wrap(g, text, maxW, lines = 99) {
  const words = String(text || "").split(/\s+/), out = [];
  let cur = "";
  for (const w of words) {
    const t = cur ? `${cur} ${w}` : w;
    if (g.measureText(t).width <= maxW || !cur) cur = t;
    else { out.push(cur); cur = w; }
  }
  if (cur) out.push(cur);
  const cut = (line) => { // shorten with "…" to fit
    if (g.measureText(line).width <= maxW) return line;
    while (line && g.measureText(`${line}…`).width > maxW) line = line.slice(0, -1);
    return `${line}…`;
  };
  if (out.length > lines) { // more than fits: the last line ends with "…"
    const keep = out.slice(0, lines).map(cut);
    let last = keep[lines - 1].replace(/…$/, "");
    while (last && g.measureText(`${last}…`).width > maxW) last = last.slice(0, -1);
    keep[lines - 1] = `${last}…`;
    return keep;
  }
  return out.map(cut);
}
const fmtDay = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(y, m - 1, d).toLocaleDateString(undefined, { day: "numeric", month: "short" }); };
export const usd = (v, dec = 2) => `$${Number(v || 0).toFixed(dec)}`;
const SPEND_HOW = "Estimated · this computer's brain only"; // the AI Spend callout (quick job 41)
const KINDS = { arm: ["i-arm", "Arms"], headset: ["i-headset", "Headsets"], camera: ["i-cam", "Cameras"], pc: ["i-pc", "Computers"], pi: ["i-pi", "Raspberry Pis"] };
const KIND_OF = { so101: "arm", "so101-leader": "arm", xarm1s: "arm", fake: "arm", arm: "arm", camera: "camera", headset: "headset", quest: "headset", pc: "pc", pi: "pi" };
export function devicesFrom(list) {
  return (list || []).map((d) => ({
    name: d.name, kind: KIND_OF[d.kind] || "pc", brain: !!d.linked, on: d.linked ? true : undefined,
    lock: d.off_limits ? "another project's (never opened)" : "", use: d.notes || d.kind, borrowed: !!d.borrowed,
  }));
}

function hexPath(g, x, y, r) {
  g.beginPath();
  for (let i = 0; i < 6; i++) { const a = -Math.PI / 2 + (i * TAU) / 6; g[i ? "lineTo" : "moveTo"](x + Math.cos(a) * r, y + Math.sin(a) * r); }
  g.closePath();
}
function hatch(g, x, y, w, h, color) {
  g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip();
  g.strokeStyle = color; g.lineWidth = 1;
  for (let i = -h; i < w; i += 3) { g.beginPath(); g.moveTo(x + i, y + h); g.lineTo(x + i + h, y); g.stroke(); }
  g.restore();
}

export class Callout {
  /** @param {"project"|"spend"|"commits"|"devices"} id  @param {"left"|"right"} side */
  constructor(id, title, side) {
    this.id = id; this.title = title; this.side = side;
    this.hMax = id === "devices" ? 24 : 12; // rem: Devices grows when its list is open
    this.p = new CanvasPlane(W * REM_M, this.hMax * REM_M, R / REM_M);
    this.p.mesh.userData.hit = this;
    this.h = 9; // rem, the drawn height
    this.data = null;
    this.hover = null; // what the pointer is on
    this.regions = []; // {id, x, y, w, h} in rem, for hit()
    this.days = 14; // commits: the range
    this.open = false; // devices: the list
    this.t = 0;
  }
  get mesh() { return this.p.mesh; }
  get available() { return !!this.data?.available || (this.id === "devices" && !!this.data?.length); }

  /** (u, v) on the plane (0..1, v up) → {kind: "open" | "control" | "device", id} or null */
  hit(u, v) {
    const x = u * W, y = (1 - v) * this.hMax;
    if (y > this.h + 0.2) return null;
    for (const r of this.regions) if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) return r;
    return { kind: "open", id: this.id };
  }

  paint(now) {
    const key = JSON.stringify([this.data, this.hover?.id, this.days, this.open, this.id === "project" ? Math.floor(now / 400) : 0]);
    this.p.paint((g) => this._draw(g, now), key);
  }

  _draw(g, now) {
    g.scale(R, R);
    g.lineWidth = 1 / R;
    const left = this.side === "left", lit = this.hover?.kind === "open";
    this.regions = [];
    // content first (it sets this.h), into its own layer
    g.save(); g.translate(1.15, HEAD + 0.55);
    const ch = this._content(g, now, W - 2.3);
    g.restore();
    this.h = HEAD + 0.55 + ch + 1.05;
    // the fill under the line: a touch brighter just under it, a cut corner at the bottom right
    const top = HEAD + 3 / R, cut = 0.7;
    g.save();
    g.globalCompositeOperation = "destination-over";
    g.beginPath(); g.moveTo(0, top); g.lineTo(W, top); g.lineTo(W, this.h - cut); g.lineTo(W - cut, this.h); g.lineTo(0, this.h); g.closePath();
    const fill = g.createLinearGradient(0, top, 0, top + 2.5);
    fill.addColorStop(0, rgba(C.primary, 0.07)); fill.addColorStop(1, rgba(C.primary, 0));
    g.fillStyle = fill; g.fill();
    g.fillStyle = rgba(C.surface, 0.8); g.fill();
    g.restore();
    // the line, the end node (facing the core), the lead-in, the ticks
    const lineC = lit ? C.primary : rgba(C.primary, 0.55);
    g.fillStyle = lineC; g.fillRect(0, HEAD - 1 / R, W, 1 / R);
    g.fillStyle = C.primary;
    g.fillRect(left ? W - 3 / R - 2 / R : -2 / R, HEAD - 3 / R, 5 / R, 5 / R);
    g.fillRect(left ? 0 : W - 2.2, HEAD - 2 / R, 2.2, 2 / R);
    for (let i = 0; i < 1.6 * R; i += 5) g.fillRect((left ? W - 0.9 - 1.6 : 0.9) + i / R, HEAD - 5 / R, 1 / R, 5 / R);
    // the tab with the title
    g.font = `500 0.95px ${FONT.ui}`; spaced(g, 0.03);
    const tw = g.measureText(this.title).width + 1.55, th = 1.6, tx = left ? 0 : W - tw, ty = HEAD - th;
    const tabC = lit ? C.primary : rgba(C.primary, 0.55), c6 = 0.6;
    g.beginPath();
    if (left) { g.moveTo(tx, HEAD); g.lineTo(tx, ty); g.lineTo(tx + tw - c6, ty); g.lineTo(tx + tw, ty + c6); g.lineTo(tx + tw, HEAD); }
    else { g.moveTo(tx + tw, HEAD); g.lineTo(tx + tw, ty); g.lineTo(tx + c6, ty); g.lineTo(tx, ty + c6); g.lineTo(tx, HEAD); }
    const tf = g.createLinearGradient(0, ty, 0, HEAD);
    tf.addColorStop(0, rgba(C.primary, 0.16)); tf.addColorStop(1, rgba(C.primary, 0.04));
    g.fillStyle = tf; g.fill();
    g.strokeStyle = tabC; g.lineWidth = 1 / R; g.stroke();
    g.fillStyle = C.primary; g.fillRect(left ? tx : tx + tw - 1, ty - 1 / R, 1, 2 / R); // the bright notch
    g.fillStyle = lit ? C.hot : C.primary; g.textBaseline = "middle"; g.textAlign = "left";
    g.fillText(this.title, tx + (left ? 0.7 : 0.85), ty + th / 2 + 0.05);
    spaced(g, 0);
    // the open mark, beside the tab toward the core
    const ox = left ? tx + tw + 0.25 + 0.95 : tx - 0.25 - 0.95;
    icon(g, "i-open", ox, ty + th / 2, 0.95, lit ? C.hot : C.dim, 1.5);
  }

  _content(g, now, w) {
    const d = this.data;
    g.textBaseline = "alphabetic";
    if (this.id === "project") {
      g.font = `600 1.1px ${FONT.ui}`; g.fillStyle = C.text; g.textAlign = "left";
      const lines = wrap(g, d?.focus || "", w, 2);
      lines.forEach((l, i) => g.fillText(l, 0, 1.0 + i * 1.375));
      let y = lines.length * 1.375 + 0.55;
      // the step bar: done, now (pulsing, part lit), later
      g.font = `${FONT.linesW} 0.78px ${FONT.lines}`;
      const label = `Step ${d?.step} of ${d?.of}`, lw = g.measureText(label).width, bw = w - lw - 0.8, n = d?.steps?.length || 1, gap = 3 / R, sw = (bw - gap * (n - 1)) / n;
      const pulse = 0.55 + 0.45 * Math.abs(Math.sin((now / 2400) * Math.PI));
      (d?.steps || []).forEach((s, i) => {
        const x = i * (sw + gap);
        g.fillStyle = C.line; g.fillRect(x, y, sw, 5 / R);
        if (s.done) { g.fillStyle = rgba(C.primary, 0.75); g.fillRect(x, y, sw, 5 / R); }
        else if (s.n === d.step) { g.fillStyle = rgba(C.primary, pulse); g.fillRect(x, y, sw * 0.6, 5 / R); }
      });
      g.fillStyle = C.dim; g.textAlign = "right"; g.fillText(label, w, y + 0.32);
      y += 1.45;
      g.textAlign = "left"; g.font = `600 0.82px ${FONT.ui}`; spaced(g, 0.1); g.fillStyle = C.primary;
      g.fillText("NEXT", 0, y);
      const kx = g.measureText("NEXT").width + 0.65; spaced(g, 0);
      // the pixel double chevron; light runs through it now and then
      const ph = (now % 3200) / 3200;
      for (let k = 0; k < 2; k++) for (let i = 0; i < 3; i++) {
        const lit2 = ph > 0.7 + (k * 3 + i) * 0.012 && ph < 0.82 + (k * 3 + i) * 0.012;
        g.fillStyle = rgba(C.primary, lit2 ? 1 : 0.45);
        const px = kx + k * 0.42 + (i === 1 ? 0.14 : 0), py = y - 0.62 + i * 0.2;
        g.fillRect(px, py, 0.14, 0.14);
      }
      g.font = `500 0.98px ${FONT.ui}`; g.fillStyle = C.text;
      g.fillText(wrap(g, d?.next || "all steps done", w - kx - 1.6, 1)[0], kx + 1.6, y);
      return y + 0.3;
    }
    if (this.id === "spend") {
      const B = d?.budget_usd, spent = d?.spent_usd || 0;
      g.font = `1.35px ${FONT.digits}`; g.fillStyle = C.hot; g.textAlign = "left";
      const money = `$${spent.toFixed(2)}`;
      g.fillText(money, 0, 1.5);
      const mw = g.measureText(money).width;
      g.font = `${FONT.linesW} 0.74px ${FONT.lines}`; g.fillStyle = C.dim;
      if (B) g.fillText(`of ${usd(B, 0)}`, mw + 0.5, 1.5);
      g.textAlign = "right"; g.font = `${FONT.linesW} 0.78px ${FONT.lines}`; g.fillText("this month", w, 1.5);
      g.fillStyle = C.line; g.fillRect(0, 2.3, w, 6 / R);
      g.fillStyle = C.primary; g.fillRect(0, 2.3, Math.max(2 / R, B ? (w * Math.min(1, spent / B)) : 0), 6 / R);
      // what the total is (quick job 41): this brain's own estimate, not the bill
      g.textAlign = "left"; g.font = `${FONT.linesW} 0.7px ${FONT.lines}`; g.fillStyle = C.dim;
      g.fillText(SPEND_HOW, 0, 3.6);
      return 3.8;
    }
    if (this.id === "commits") {
      const per = (d?.per_day || []).map((x) => x.count), days = this.days, counts = per.slice(-days);
      const tot = counts.reduce((a, b) => a + b, 0);
      g.font = `1.15px ${FONT.digits}`; g.fillStyle = C.hot; g.textAlign = "left";
      g.fillText(String(tot), 0, 1.4);
      const tw = g.measureText(String(tot)).width;
      g.font = `${FONT.linesW} 0.78px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText("commits", tw + 0.3, 1.4);
      // the range buttons
      g.font = `500 0.7px ${FONT.ui}`;
      let bx = w;
      for (const r of [30, 14, 7]) {
        const label = `${r}d`, bw = g.measureText(label).width + 0.6, x = bx - bw, sel = r === days, hov = this.hover?.id === `days${r}`;
        g.fillStyle = sel ? C.primary : hov ? rgba(C.primary, 0.16) : "transparent"; g.fillRect(x, 0.45, bw, 1.15);
        g.strokeStyle = sel || hov ? C.primary : C.line; g.lineWidth = 1 / R; g.strokeRect(x, 0.45, bw, 1.15);
        g.fillStyle = sel ? C.bg : hov ? C.hot : C.dim; g.textAlign = "center"; g.fillText(label, x + bw / 2, 1.25);
        this.regions.push({ kind: "control", id: `days${r}`, x: 1.15 + x, y: HEAD + 0.55 + 0.45, w: bw, h: 1.15 });
        bx = x - 2 / R;
      }
      // the bars: the busiest day white-hot with its count
      const top = 2.1, h = 3.4, max = Math.max(1, ...counts), step = w / Math.max(1, counts.length);
      g.fillStyle = C.line; g.fillRect(0, top + h, w, 1 / R);
      counts.forEach((n, i) => {
        const px = w / 220, bw2 = Math.max(1.5 * px, step - (days > 20 ? 2 : 4) * px), x = i * step + (step - bw2) / 2, bh = Math.max(1 / R, (n / max) * (h - 0.9));
        g.fillStyle = n === max ? C.hot : rgba(C.primary, 0.6); g.fillRect(x, top + h - bh, bw2, bh);
        if (n === max && n) { g.font = `0.62px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "center"; g.fillText(String(n), x + bw2 / 2, top + h - bh - 0.25); }
      });
      g.font = `${FONT.linesW} 0.6px ${FONT.lines}`; g.fillStyle = C.dim;
      const first = d?.per_day?.[d.per_day.length - days];
      g.textAlign = "left"; if (first) g.fillText(fmtDay(first.date), 0, top + h + 0.85);
      g.textAlign = "right"; g.fillText("today", w, top + h + 0.85);
      return top + h + 0.95;
    }
    if (this.id === "devices") {
      const devs = this.data || [], conn = devs.filter((x) => x.brain).length;
      g.textAlign = "left"; g.font = `600 0.85px ${FONT.ui}`; g.fillStyle = C.primary;
      g.fillText(String(conn), 0, 1.55);
      const cw = g.measureText(String(conn)).width;
      g.font = `${FONT.linesW} 0.78px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText(` of ${devs.length} linked`, cw, 1.55);
      // "List all" / "Show map": a framed button, sized to its words
      g.font = `500 0.82px ${FONT.ui}`; spaced(g, 0.04);
      const label = this.open ? "Show map" : "List all", bw = g.measureText(label).width + 2.6, bh = 2.3, x = w - bw, hov = this.hover?.id === "list";
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x + bw, 0); g.lineTo(x + bw, bh - 0.45); g.lineTo(x + bw - 0.45, bh); g.lineTo(x, bh); g.closePath();
      g.fillStyle = rgba(C.primary, hov ? 0.16 : 0.07); g.fill();
      g.strokeStyle = hov ? C.primary : rgba(C.primary, 0.4); g.lineWidth = 1 / R; g.stroke();
      g.fillStyle = hov ? C.hot : C.primary; g.fillText(label, x + 0.8, 1.42); spaced(g, 0);
      g.save(); g.translate(x + bw - 0.95, bh / 2); if (!this.open) g.rotate(Math.PI); icon(g, "i-chev", 0, 0, 1.1, hov ? C.hot : C.primary, 1.6); g.restore();
      this.regions.push({ kind: "control", id: "list", x: 1.15 + x, y: HEAD + 0.55, w: bw, h: bh });
      let y = bh + 0.7;
      if (!this.open) { // the hive: one row per kind, a hexagon per device
        const r = 0.42, dx = r * 2.05, per = Math.floor((w - 2.9) / dx);
        for (const [kind, [ico]] of Object.entries(KINDS)) {
          const list = devs.filter((x) => x.kind === kind);
          if (!list.length) continue;
          icon(g, ico, 0.5, y + 0.1, 0.95, C.dim, 1.4);
          list.forEach((dv, i) => {
            const hx = 2.9 + (i % per) * dx + r, hy = y + 0.1 + Math.floor(i / per) * 1.1, hov2 = this.hover?.id === `dev:${dv.name}`;
            hexPath(g, hx, hy, r);
            if (dv.lock) { g.save(); g.clip(); hatch(g, hx - r, hy - r, 2 * r, 2 * r, C.dim); g.restore(); hexPath(g, hx, hy, r); g.setLineDash([2 / R, 2 / R]); g.strokeStyle = C.dim; }
            else if (dv.brain) { const beat = (now / 5000) % 1 > 0.86 && (now / 5000) % 1 < 0.98; g.fillStyle = rgba(C.primary, beat ? 1 : 0.75); g.fill(); g.strokeStyle = beat ? C.hot : C.primary; }
            else g.strokeStyle = C.offline;
            if (hov2) { g.strokeStyle = C.hot; g.lineWidth = 2 / R; }
            g.stroke(); g.setLineDash([]); g.lineWidth = 1 / R;
            this.regions.push({ kind: "device", id: `dev:${dv.name}`, dev: dv, x: 1.15 + hx - r, y: HEAD + 0.55 + hy - r, w: 2 * r, h: 2 * r });
          });
          y += Math.ceil(list.length / per) * 1.1 + 0.25;
        }
        return y;
      }
      // the list: grouped by kind; columns Device, Power, Linked (statuses as words with a dot)
      g.font = `500 0.68px ${FONT.ui}`; g.fillStyle = C.dim; g.textAlign = "left";
      const PW = w - 5.7, LK = w - 1.9; // the status columns
      g.fillText("Device", 1.5, y); g.fillText("Power", PW, y); g.fillText("Linked", LK, y);
      y += 0.3;
      for (const [kind, [ico, label]] of Object.entries(KINDS)) {
        const list = devs.filter((x) => x.kind === kind);
        if (!list.length) continue;
        y += 0.95; g.font = `500 0.68px ${FONT.ui}`; spaced(g, 0.08); g.fillStyle = C.dim; g.fillText(label, 0.2, y); spaced(g, 0);
        g.fillStyle = C.line; g.fillRect(0, y + 0.25, w, 1 / R); y += 0.3;
        for (const dv of list) {
          const hov2 = this.hover?.id === `dev:${dv.name}`;
          if (hov2) { g.fillStyle = rgba(C.primary, 0.12); g.fillRect(0, y + 0.1, w, 1.25); }
          icon(g, ico, 0.6, y + 0.72, 0.8, C.dim, 1.4);
          g.font = `0.88px ${FONT.ui}`; g.fillStyle = C.text;
          g.fillText(wrap(g, dv.name, PW - 1.9, 1)[0], 1.5, y + 1.0);
          g.font = `${FONT.linesW} 0.72px ${FONT.lines}`;
          const st = (x, ok, yes, no) => { g.fillStyle = ok ? C.primary : C.offline; g.beginPath(); g.arc(x + 0.2, y + 0.72, 0.17, 0, TAU); ok ? g.fill() : (g.strokeStyle = C.offline, g.stroke()); g.fillText(ok ? yes : no, x + 0.6, y + 1.0); };
          if (dv.lock) { g.fillStyle = C.dim; g.fillText("Locked", PW, y + 1.0); }
          else {
            if (dv.on === undefined) { g.fillStyle = C.offline; g.fillText("not known", PW, y + 1.0); } else st(PW, dv.on, "On", "Off");
            st(LK, dv.brain, "Yes", "No");
          }
          this.regions.push({ kind: "device", id: `dev:${dv.name}`, dev: dv, x: 1.15, y: HEAD + 0.55 + y + 0.1, w, h: 1.25 });
          y += 1.3;
        }
      }
      return Math.min(y + 0.2, this.hMax - HEAD - 2);
    }
    return 0;
  }
}

/** The card beside a callout for one device: which it is first, then its two statuses (like the screen). */
export class DeviceCard {
  constructor() {
    this.p = new CanvasPlane(13 * REM_M, 7 * REM_M, R / REM_M);
    this.dev = null;
    this.p.opacity = 0;
    this.p.mesh.userData.hit = this;
  }
  get mesh() { return this.p.mesh; }
  hit() { return { kind: "card" }; }
  show(dev) {
    this.dev = dev;
    this.p.opacity = dev ? 1 : 0;
    if (!dev) return;
    const [ico] = KINDS[dev.kind] || KINDS.pc, usb = dev.kind === "arm" || dev.kind === "camera";
    this.p.paint((g, cw, chh) => {
      g.scale(R, R); const w = cw / R, h = chh / R;
      g.beginPath(); g.moveTo(0.7, 0); g.lineTo(w, 0); g.lineTo(w, h - 0.7); g.lineTo(w - 0.7, h); g.lineTo(0, h); g.lineTo(0, 0.7); g.closePath();
      g.fillStyle = rgba(C.surface, 0.95); g.fill(); g.strokeStyle = rgba(C.primary, 0.5); g.lineWidth = 1 / R; g.stroke();
      icon(g, ico, 1.2, 1.2, 1.1, C.primary, 1.5);
      g.font = `600 1px ${FONT.ui}`; g.fillStyle = C.text; g.textAlign = "left"; g.textBaseline = "middle";
      g.fillText(dev.name, 2.1, 1.25);
      g.font = `${FONT.linesW} 0.78px ${FONT.lines}`; g.fillStyle = C.text; g.textBaseline = "alphabetic";
      wrap(g, dev.use, w - 1.6, 3).forEach((l, i) => g.fillText(l, 0.8, 2.75 + i * 1.0));
      const row = (y, ok, text) => { g.fillStyle = ok ? C.primary : C.offline; g.beginPath(); g.arc(1.0, y - 0.25, 0.2, 0, TAU); ok ? g.fill() : (g.strokeStyle = C.offline, g.stroke()); g.fillStyle = ok ? C.text : C.dim; g.fillText(text, 1.5, y); };
      if (dev.lock) { g.fillStyle = C.dim; g.fillText("Locked: the hub shows it but never opens its ports.", 0.8, h - 1.0); }
      else {
        row(h - 1.9, dev.on, dev.on === undefined ? "Power: not known until the roll call" : dev.on ? (usb ? "Plugged in" : "On the network") : usb ? "Not plugged in" : "Off, or not on the network");
        row(h - 0.8, dev.brain, dev.brain ? "Linked to the brain" : "Not linked");
      }
    }, dev.name);
  }
}

/* ---------- the details pages: the whole story behind a callout (like the screen's showDetail) ---------- */
export class DetailsPage {
  constructor(w = 2.0, h = 1.2) {
    this.w = w; this.h = h;
    this.p = new CanvasPlane(w, h, 1100);
    this.p.mesh.userData.hit = this;
    this.id = null;
    this.hover = null;
  }
  get mesh() { return this.p.mesh; }
  hit(u, v) {
    const x = u * this.w, y = (1 - v) * this.h;
    if (x > this.w - 0.16 && y < 0.16) return { kind: "back" };
    return { kind: "page" };
  }
  paint(id, facts, title, now) {
    this.id = id;
    const key = JSON.stringify([id, facts[id], this.hover?.kind, Math.floor(now / 1000)]);
    this.p.paint((g, cw, chh) => this._draw(g, cw, chh, id, facts, title), key);
  }
  _draw(g, cw, chh, id, f, title) {
    const w = 200, h = (200 * this.h) / this.w, u = cw / w, c = 3; // drawn 200 units across, whatever the page's size
    g.scale(u, u);
    // the page: near-black, a cut-corner frame, the title tab, Back
    g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
    g.fillStyle = rgba(C.bg, 0.94); g.fill();
    g.strokeStyle = rgba(C.primary, 0.45); g.lineWidth = 0.2; g.stroke();
    g.fillStyle = C.primary; g.fillRect(0, c, 0.4, 6); g.fillRect(c, 0, 8, 0.4);
    g.font = `700 3.2px ${FONT.title}`; spaced(g, 0.18); g.fillStyle = C.hot; g.textBaseline = "middle"; g.textAlign = "left";
    g.fillText(title.toUpperCase(), 9, 7); spaced(g, 0);
    icon(g, { project: "i-next", spend: "i-coin", commits: "i-commit", devices: "i-net" }[id], 5, 7, 4, C.primary, 1.5);
    const bh = this.hover?.kind === "back";
    g.strokeStyle = bh ? C.primary : rgba(C.primary, 0.5); g.lineWidth = 0.25; g.strokeRect(w - 14, 2.5, 11, 9);
    if (bh) { g.fillStyle = rgba(C.primary, 0.16); g.fillRect(w - 14, 2.5, 11, 9); }
    icon(g, "i-back", w - 8.5, 7, 6, bh ? C.hot : C.text, 1.6);
    const L = 9, top = 17, colW = (w - 2 * L - 10) / 2, R2 = L + colW + 10;
    const dline = (x, y, text, ww) => { g.font = `500 2.4px ${FONT.ui}`; g.fillStyle = C.primary; g.textBaseline = "alphabetic"; g.textAlign = "left"; g.fillText(text, x, y); g.fillStyle = rgba(C.primary, 0.55); g.fillRect(x, y + 1, ww, 0.15); };
    const para = (x, y, text, ww, size = 2.3, color = C.text) => { g.font = `${FONT.linesW} ${size}px ${FONT.lines}`; g.fillStyle = color; g.textAlign = "left"; const ls = wrap(g, text, ww); ls.forEach((l, i) => g.fillText(l, x, y + i * size * 1.45)); return y + ls.length * size * 1.45; };
    const bigNum = (x, y, n, small) => { g.font = `9px ${FONT.digits}`; g.fillStyle = C.hot; g.textAlign = "left"; g.fillText(n, x, y); const nw = g.measureText(n).width; g.font = `${FONT.linesW} 2.4px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText(small, x + nw + 2, y); };
    if (id === "project") {
      const p = f.project?.available ? f.project : { steps: [] }, done = p.steps.filter((s) => s.done).length;
      dline(L, top, "The goal", colW);
      g.font = `600 3.4px ${FONT.ui}`; g.fillStyle = C.text;
      let y = top + 7;
      wrap(g, p.focus || "", colW).forEach((l) => { g.fillText(l, L, y); y += 4.4; });
      y = para(L, y + 2, "From docs/plan/current-focus.md: what the project works on now, in small steps that each work on their own.", colW);
      bigNum(L, y + 10, String(done), `of ${p.steps.length} steps done`);
      if (p.next) para(L, y + 17, `Now: step ${p.step}, ${p.next}.`, colW);
      dline(R2, top, "Steps", colW);
      const rowH = Math.min(5.2, (h - top - 10) / Math.max(1, p.steps.length));
      p.steps.forEach((s, i) => {
        const yy = top + 4 + i * rowH, now = !s.done && s.n === p.step;
        g.fillStyle = now ? C.primary : C.line; g.fillRect(R2, yy, 0.35, rowH - 0.6);
        if (now) { g.fillStyle = rgba(C.primary, 0.1); g.fillRect(R2, yy, colW, rowH - 0.6); }
        g.font = `${rowH * 0.5}px ${FONT.digits}`; g.fillStyle = now ? C.hot : C.dim; g.textBaseline = "middle"; g.fillText(String(s.n), R2 + 2, yy + rowH / 2 - 0.3);
        g.font = `600 ${rowH * 0.46}px ${FONT.ui}`; g.fillStyle = s.done || now ? C.text : C.dim; g.fillText(s.title, R2 + 7, yy + rowH / 2 - 0.3);
        g.font = `${FONT.linesW} ${rowH * 0.4}px ${FONT.lines}`; g.fillStyle = now ? C.primary : C.dim; g.textAlign = "right";
        g.fillText(now ? "Now" : s.done ? `Done ${s.done_on || ""}` : "", R2 + colW - 1, yy + rowH / 2 - 0.3); g.textAlign = "left";
      });
    } else if (id === "spend") {
      const s = f.spend || {}, B = s.budget_usd, spent = s.spent_usd || 0, now = new Date();
      dline(L, top, "This month, estimated", colW);
      bigNum(L, top + 12, usd(spent), B ? `of ${usd(B, 0)}` : "no budget set");
      g.fillStyle = C.line; g.fillRect(L, top + 16, colW, 0.8); g.fillStyle = C.primary; g.fillRect(L, top + 16, Math.max(0.3, B ? colW * Math.min(1, spent / B) : 0), 0.8);
      let y = para(L, top + 23, `${s.chats || 0} answer${s.chats === 1 ? "" : "s"} so far this month; each one logs what it cost.`, colW);
      if (B) y = para(L, y + 2, `Budget: ${usd(B, 0)} a month. At the budget the chat pauses and says why. It resets on the 1st.`, colW);
      para(L, y + 2, "This is an estimate by this computer's brain: the token counts times the prices in models.yaml. Another brain that uses the same key is not counted.", colW, 2.1, C.dim);
      dline(R2, top, B ? `Spent so far, against an even pace to ${usd(B, 0)}` : "Spent so far", colW);
      const dim = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(), today = now.getDate(), ch = 34, cy = top + 6, topV = Math.max(B || 0, spent, 0.01);
      const X = (dd) => R2 + (dd / dim) * colW, Y = (v) => cy + ch - (v / topV) * (ch - 4);
      g.fillStyle = C.line; g.fillRect(R2, cy + ch, colW, 0.15);
      if (B) { g.strokeStyle = C.dim; g.lineWidth = 0.2; g.setLineDash([0.8, 1]); g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(dim), Y(B)); g.stroke(); g.setLineDash([]); }
      g.fillStyle = C.hot; g.beginPath(); g.arc(X(today), Y(spent), 0.8, 0, TAU); g.fill();
      g.font = `${FONT.linesW} 2px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "left"; g.fillText("1st", R2, cy + ch + 3);
      g.textAlign = "center"; g.fillText("today", X(today), cy + ch + 3); g.textAlign = "right"; g.fillText(`${dim}th`, R2 + colW, cy + ch + 3);
      dline(R2, cy + ch + 11, "By AI setup", colW);
      const rows = Object.entries(s.by_setup || {});
      g.textAlign = "left"; g.font = `${FONT.linesW} 2.3px ${FONT.lines}`;
      if (!rows.length) { g.fillStyle = C.dim; g.fillText("No chats yet this month", R2, cy + ch + 17); }
      rows.forEach(([k, v], i) => { g.fillStyle = C.text; g.textAlign = "left"; g.fillText(k, R2, cy + ch + 17 + i * 3.4); g.textAlign = "right"; g.fillText(usd(v, 4), R2 + colW, cy + ch + 17 + i * 3.4); });
    } else if (id === "commits") {
      const c = f.commits || {}, per = (c.per_day || []).map((x) => x.count), n = per.length || 1, max = Math.max(1, ...per);
      const cw2 = w - 2 * L, chH = 30, cy = top + 6, step = cw2 / n;
      dline(L, top, `Commits per day, last ${n} days, all branches`, cw2);
      g.fillStyle = C.line; g.fillRect(L, cy + chH, cw2, 0.15);
      per.forEach((k, i) => {
        const bh = Math.max(0.15, (k / max) * (chH - 4)), bx = L + i * step + 0.4, bw = Math.max(0.2, step - 0.8);
        g.fillStyle = k === max ? C.hot : rgba(C.primary, k ? 0.7 : 0.25); g.fillRect(bx, cy + chH - bh, bw, bh);
        if (k) { g.font = `1.5px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "center"; g.fillText(String(k), bx + bw / 2, cy + chH - bh - 0.8); }
      });
      g.font = `${FONT.linesW} 1.9px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "center";
      [n - 1, Math.round((n - 1) * 0.75), Math.round((n - 1) * 0.5), Math.round((n - 1) * 0.25), 0].forEach((k) => {
        const d = c.per_day?.[n - 1 - k];
        if (d) g.fillText(k ? fmtDay(d.date) : "today", L + (n - 1 - k) * step + step / 2, cy + chH + 3);
      });
      const total = per.reduce((a, b) => a + b, 0), active = per.filter(Boolean).length, top3 = per.indexOf(Math.max(...per));
      const stats = [[String(total), "commits"], [String(active), "days with commits"], [String(Math.max(0, ...per)), `on ${c.per_day?.[top3] ? fmtDay(c.per_day[top3].date) : "-"}, the busiest day`]];
      stats.forEach(([nb, t], i) => { const x = L + i * (cw2 / 3); g.textAlign = "left"; g.font = `5px ${FONT.digits}`; g.fillStyle = C.hot; g.fillText(nb, x, cy + chH + 12); g.font = `${FONT.linesW} 2.1px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText(t, x, cy + chH + 16); });
      dline(L, cy + chH + 23, "Latest", cw2);
      (c.recent || []).slice(0, Math.floor((h - (cy + chH + 28)) / 3.3)).forEach((r, i) => {
        const y = cy + chH + 28 + i * 3.3;
        g.textAlign = "left"; g.font = `${FONT.linesW} 2.1px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText(fmtDay(r.date), L, y);
        g.fillStyle = C.text; g.font = `${FONT.linesW} 2.3px ${FONT.lines}`; g.fillText(wrap(g, r.subject, cw2 - 12, 1)[0], L + 10, y);
      });
    } else if (id === "devices") {
      const devs = f.devices || [], cw2 = w - 2 * L;
      dline(L, top, `${devs.filter((d) => d.brain).length} of ${devs.length} linked`, cw2);
      const cols = [["", 3], ["Device", 30], ["Power", 16], ["Linked", 12], ["Use", cw2 - 61]];
      g.font = `500 2px ${FONT.ui}`; g.fillStyle = C.dim; g.textAlign = "left";
      let x = L; for (const [hd, cwid] of cols) { g.fillText(hd, x, top + 6); x += cwid; }
      let y = top + 7;
      const rowH = Math.min(4, (h - y - 6) / Math.max(1, devs.length + 4));
      for (const [kind, [ico, label]] of Object.entries(KINDS)) {
        const list = devs.filter((d) => d.kind === kind);
        if (!list.length) continue;
        y += rowH; g.font = `500 1.9px ${FONT.ui}`; spaced(g, 0.08); g.fillStyle = C.dim; g.fillText(label, L, y); spaced(g, 0);
        g.fillStyle = C.line; g.fillRect(L, y + 0.8, cw2, 0.12); y += 0.5;
        for (const d of list) {
          y += rowH;
          icon(g, ico, L + 1.2, y - 0.8, 2.4, C.dim, 1.4);
          g.font = `${rowH * 0.62}px ${FONT.ui}`; g.fillStyle = C.text; g.fillText(d.name, L + 3, y);
          g.font = `${FONT.linesW} ${rowH * 0.55}px ${FONT.lines}`;
          g.fillStyle = d.lock ? C.dim : d.on ? C.primary : C.offline;
          g.fillText(d.lock ? "Locked" : d.on === undefined ? "not known" : d.on ? "● On" : "○ Off", L + 33, y);
          g.fillStyle = d.brain ? C.primary : C.offline; g.fillText(d.lock ? "" : d.brain ? "● Yes" : "○ No", L + 49, y);
          g.fillStyle = C.dim; g.fillText(wrap(g, d.use, cw2 - 62, 1)[0], L + 61, y);
        }
      }
    }
  }
}

export { clamp };
