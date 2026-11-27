// Drawing helpers for the hub in VR: flat things (text, panels, rings) are drawn with Canvas 2D onto
// textures, so they look like the designed hub (same shapes, fonts and icons) and stay sharp.
//   const p = new CanvasPlane(0.6, 0.2, 1400);   a 0.6 × 0.2 m plane, 1400 canvas pixels per metre
//   p.paint((g, w, h) => { ... });               draw in canvas pixels; uploads the texture
// Colors are the theme's (css() / C.primary …); icons are the hub's own (/web/design/icons.svg).
import * as THREE from "three";
import { theme } from "/web/theme.js";

const TC = theme.colors || {};
/** The theme's colors as CSS strings ("#29d4ff"). */
export const C = {
  bg: TC.background || "#05080b", surface: TC.surface || "#0b161c", line: TC.line || "#1f3d48",
  text: TC.text || "#d4eef5", dim: TC.text_dim || "#6d8c96", primary: TC.primary || "#29d4ff",
  hot: TC.hot || "#eafcff", accent: TC.accent || "#ff9a2e", danger: TC.danger || "#ff2436",
  offline: TC.offline || "#56636a", ok: TC.ok || "#3ee07f",
};
/** A theme color as a three.js Color. */
// Glow (quick job 10): adds light like additive blending, but leaves the picture's opacity alone. In AR the
// headset shows the room wherever the picture is see-through; additive blending also wrote opacity, so a dim or
// black glow (the network's links before the jump, faint stars) covered the room as a dark shape. In VR the
// background is black and opaque, so it looks the same either way.
export const GLOW = {
  blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
  blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
  blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor,
};
export const col = (name) => new THREE.Color(C[name] || name);
/** "#rrggbb" + alpha → "rgba(…)". */
// AR (quick job 157): over the real room, see-through panels and thin text washed out. While `PASS.ar` is
// on, a panel's dark fill (background or surface) is nearly opaque.
export const PASS = { ar: false };
export function rgba(hex, a) {
  if (PASS.ar && a >= 0.3 && a < 0.97 && (hex === C.bg || hex === C.surface)) a = 0.97;
  const h = hex.replace("#", "");
  return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
}
const F = theme.font || {};
/** Fonts per role, as in the hub (titles, interface, typed lines, digits). */
export const FONT = {
  title: F.display || "Orbitron, system-ui, sans-serif",
  ui: F.family || "'Chakra Petch', system-ui, sans-serif",
  lines: F.lines || "Inter, system-ui, sans-serif",
  linesW: F.lines_weight || 300,
  digits: F.digits || "DSEG7, monospace",
};
export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const rand = (a, b) => a + Math.random() * (b - a);
export const easeOut = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
export const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
// the hub's "arrive" curve, cubic-bezier(0.16, 1, 0.3, 1): starts fast, settles slowly
export const arrive = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 4);
export const TAU = Math.PI * 2;

/** Fonts are bundled; canvas text needs them loaded first or it falls back silently. */
export async function loadFonts() {
  if (!document.fonts) return;
  const want = [`700 40px ${FONT.title}`, `500 40px ${FONT.ui}`, `600 40px ${FONT.ui}`, `${FONT.linesW} 40px ${FONT.lines}`, `40px ${FONT.digits}`];
  await Promise.all(want.map((f) => document.fonts.load(f).catch(() => null)));
}

/* ---------- a plane with a canvas texture ---------- */
export class CanvasPlane {
  /**
   * @param {number} w width in metres  @param {number} h height in metres
   * @param {number} ppm canvas pixels per metre (sharpness)
   * @param {{additive?: boolean}} opts additive: light adds up (glows); otherwise drawn over
   */
  constructor(w, h, ppm = 1200, { additive = false } = {}) {
    this.w = w; this.h = h;
    this.canvas = document.createElement("canvas");
    this.canvas.width = Math.min(4096, Math.round(w * ppm));
    this.canvas.height = Math.min(4096, Math.round(h * ppm));
    this.g = this.canvas.getContext("2d");
    this.tex = new THREE.CanvasTexture(this.canvas);
    this.tex.colorSpace = THREE.SRGBColorSpace;
    this.tex.anisotropy = 4;
    this.mat = new THREE.MeshBasicMaterial({
      map: this.tex, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      ...(additive ? GLOW : {}),
    });
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), this.mat);
    this.key = null;
  }
  /** Draw (g, widthPx, heightPx); skipped when `key` is given and unchanged. */
  paint(fn, key) {
    if (key !== undefined && key === this.key) return false;
    this.key = key;
    const g = this.g;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, this.canvas.width, this.canvas.height);
    g.save();
    fn(g, this.canvas.width, this.canvas.height);
    g.restore();
    this.tex.needsUpdate = true;
    return true;
  }
  set opacity(v) { this.mat.opacity = v; this.mesh.visible = v > 0.002; }
  get opacity() { return this.mat.opacity; }
}

/* ---------- the hub's icons (icons.svg), drawn as paths ---------- */
let ICONS = {};
export async function loadIcons() {
  try {
    const txt = await (await fetch("/web/design/icons.svg")).text();
    const doc = new DOMParser().parseFromString(txt, "image/svg+xml");
    for (const s of doc.querySelectorAll("symbol")) ICONS[s.id] = [...s.children];
  } catch {
    ICONS = {};
  }
}
/** Draw icon `id` (e.g. "i-hand") centred at x, y, `size` px, stroked like the hub (no fills). */
export function icon(g, id, x, y, size, color, lw = 1.6) {
  const parts = ICONS[id];
  if (!parts) return;
  g.save();
  g.translate(x - size / 2, y - size / 2);
  g.scale(size / 24, size / 24);
  g.strokeStyle = color; g.fillStyle = color;
  g.lineWidth = lw; g.lineCap = "round"; g.lineJoin = "round";
  const n = (e, a) => parseFloat(e.getAttribute(a) || 0);
  for (const e of parts) {
    const filled = e.getAttribute("fill") && e.getAttribute("fill") !== "none";
    const dash = e.getAttribute("stroke-dasharray");
    g.setLineDash(dash ? dash.split(/[ ,]+/).map(Number) : []);
    let p = null;
    if (e.tagName === "path") p = new Path2D(e.getAttribute("d"));
    else if (e.tagName === "circle") { p = new Path2D(); p.arc(n(e, "cx"), n(e, "cy"), n(e, "r"), 0, TAU); }
    else if (e.tagName === "rect") { p = new Path2D(); p.rect(n(e, "x"), n(e, "y"), n(e, "width"), n(e, "height")); }
    else if (e.tagName === "line") { p = new Path2D(); p.moveTo(n(e, "x1"), n(e, "y1")); p.lineTo(n(e, "x2"), n(e, "y2")); }
    if (!p) continue;
    if (filled) g.fill(p); else g.stroke(p);
  }
  g.restore();
}

/** A box with 45° cut corners (the hub's panels and buttons): which corners are cut, size c px. */
export function cutPath(g, x, y, w, h, c, corners = "tl br") {
  const cut = (k) => (corners.includes(k) ? c : 0);
  g.beginPath();
  g.moveTo(x + cut("tl"), y);
  g.lineTo(x + w - cut("tr"), y); g.lineTo(x + w, y + cut("tr"));
  g.lineTo(x + w, y + h - cut("br")); g.lineTo(x + w - cut("br"), y + h);
  g.lineTo(x + cut("bl"), y + h); g.lineTo(x, y + h - cut("bl"));
  g.lineTo(x, y + cut("tl"));
  g.closePath();
}

/** Text with a glow: a soft halo, then the sharp text (the hub's text-shadow). */
export function glowText(g, text, x, y, color, glow, blur = 18) {
  g.save();
  g.shadowColor = glow; g.shadowBlur = blur; g.fillStyle = color;
  g.fillText(text, x, y);
  g.shadowBlur = blur * 0.35;
  g.fillText(text, x, y);
  g.restore();
}

/** Letter-spaced text (canvas letterSpacing where the browser has it). */
export function spaced(g, em) {
  if ("letterSpacing" in g) g.letterSpacing = `${em}em`;
}

let DOT = null;
/** A soft round dot (points, glows, pulses). */
export function dotTexture() {
  if (DOT) return DOT;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d"), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.25, "rgba(255,255,255,0.6)"); r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  return (DOT = new THREE.CanvasTexture(c));
}
