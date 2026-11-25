// The hub's VR and AR Teleop: its buttons and options beside the status box (quick job 102, the builder:
// "where I expect them", like ⚙ in the VR hub). Both hang in the teleop room, so they stay with the arm
// where you look while you drive it:
//   TeleopBar      under the status box, two rows of two: STOP, Options, Back (closes Teleop, back to the hub), Exit
//                  (leaves VR or AR). The way out, in view and pressable with the right controller or the
//                  right hand (point, then trigger or pinch); B closes Teleop too.
//   TeleopOptions  over the status box, opened by Options: the Teleop page's options for the headset
//                  (xr/teleop-options.js says what each row shows and sends).
// Drawn 200 units across, like Settings in VR (xr/settings.js).
import { C, CanvasPlane, FONT, icon, rgba, spaced } from "./draw.js";
import { wrap } from "./panels.js";
import { optionRows } from "./teleop-options.js";

const PX = 2600; // canvas pixels per metre: small text, close to you

function cutBox(g, w, h, c) {
  g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
}

/* ---------- the buttons under the status box: two rows of two, big enough for a bare hand ---------- */
const BAR = [
  { kind: "stop", label: "STOP", ico: "i-stop", danger: true },
  { kind: "tele", op: "options", label: "OPTIONS", ico: "i-gear" },
  { kind: "back", label: "BACK", ico: "i-back" },
  { kind: "exit", label: "EXIT", ico: "i-headset" },
];
const ROW_GAP = 0.06; // of the bar's height
export class TeleopBar {
  constructor(w = 0.42, h = 0.13) {
    this.p = new CanvasPlane(w, h, PX);
    this.p.mesh.userData.hit = this;
    this.hover = null;
    this.open = false; // the options are open: Options shows pressed
  }
  get mesh() { return this.p.mesh; }
  hit(u, v) {
    const b = BAR[(v > 0.5 ? 0 : 2) + (u > 0.5 ? 1 : 0)];
    return b.op ? { kind: b.kind, op: b.op } : { kind: b.kind };
  }
  paint() {
    const over = this.hover ? `${this.hover.kind}${this.hover.op || ""}` : "";
    this.p.paint((g, w, h) => {
      const gap = h * ROW_GAP, bw = (w - gap) / 2, bh = (h - gap) / 2;
      BAR.forEach((b, i) => {
        const x = (i % 2) * (bw + gap), y = Math.floor(i / 2) * (bh + gap);
        const on = over === `${b.kind}${b.op || ""}`, pressed = b.op === "options" && this.open;
        const col = b.danger ? C.danger : C.primary;
        g.save(); g.translate(x, y);
        cutBox(g, bw, bh, bh * 0.22);
        g.fillStyle = rgba(C.bg, 0.92); g.fill();
        if (on || pressed || b.danger) { g.fillStyle = rgba(col, on ? 0.4 : 0.2); g.fill(); }
        g.strokeStyle = on || pressed ? col : rgba(col, 0.7); g.lineWidth = 4; g.stroke();
        icon(g, b.ico, bh * 0.55, bh / 2, bh * 0.44, on ? C.hot : col, 1.6);
        g.font = `700 ${bh * 0.4}px ${FONT.ui}`; spaced(g, 0.16);
        g.fillStyle = on ? C.hot : C.text; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText(b.label, bw / 2 + bh * 0.3, bh / 2); spaced(g, 0);
        g.restore();
      });
    }, `${over}|${this.open}`);
  }
}

/* ---------- the options, over the status box ---------- */
export class TeleopOptions {
  constructor(w = 0.42, h = 0.48) {
    this.w = w; this.h = h;
    this.p = new CanvasPlane(w, h, PX);
    this.p.mesh.userData.hit = this;
    this.hover = null;
    this.regions = []; // where the controls were drawn: {x, y, w, h, what}
  }
  get mesh() { return this.p.mesh; }
  hit(u, v) {
    const x = u * 200, y = (1 - v) * (200 * this.h / this.w);
    const r = this.regions.find((r) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h);
    return r ? { kind: "tele", ...r.what } : { kind: "page" };
  }
  /** `s`: the brain's status; `style`: the 3D arm's look here; `input`: controllers or hands here
   * ({hands, auto}); `said`: the last thing a press did. */
  paint(s, style, input, said = "") {
    const rows = optionRows(s, style, input);
    const key = JSON.stringify([rows, this.hover, said]);
    this.p.paint((g, cw) => this._draw(g, cw, rows, said), key);
  }
  _draw(g, cw, rows, said) {
    const w = 200, h = (200 * this.h) / this.w, u = cw / w;
    g.scale(u, u);
    this.regions = [];
    const hv = this.hover || {};
    const same = (what) => hv.kind === "tele" && Object.keys(what).every((k) => hv[k] === what[k]);
    const label = (text, x, y, size, color, align = "left", weight = 600, font = FONT.ui) => {
      g.font = `${weight} ${size}px ${font}`; g.fillStyle = color; g.textAlign = align; g.textBaseline = "middle"; g.fillText(text, x, y);
    };
    const box = (x, y, bw, bh, what, on, enabled) => {
      const over = enabled && same(what);
      if (on || over) { g.fillStyle = rgba(C.primary, on ? 0.24 : 0.14); g.fillRect(x, y, bw, bh); }
      g.strokeStyle = on || over ? C.primary : !enabled ? rgba(C.dim, 0.4) : rgba(C.primary, 0.5);
      g.lineWidth = 0.5; g.strokeRect(x, y, bw, bh);
      if (enabled) this.regions.push({ x, y, w: bw, h: bh, what });
    };
    // the panel: like the status box (cut corners, a nearly opaque fill, a lead-in), the title in caps
    cutBox(g, w, h, 7);
    g.fillStyle = rgba(C.bg, 0.92); g.fill();
    g.strokeStyle = C.line; g.lineWidth = 0.5; g.stroke();
    g.strokeStyle = C.primary; g.lineWidth = 0.9; g.beginPath(); g.moveTo(0.5, 22); g.lineTo(0.5, 7); g.lineTo(7, 0.5); g.lineTo(60, 0.5); g.stroke();
    icon(g, "i-gear", 10, 10, 8, C.primary, 1.5);
    spaced(g, 0.16); label("TELEOP OPTIONS", 18, 10, 5.4, C.hot, "left", 700, FONT.title); spaced(g, 0);
    const L = 8, R = w - 8, ctlW = 96, top = 21, rowH = (h - top - 12) / rows.length;
    rows.forEach((r, i) => {
      const y = top + i * rowH, cy = y + 1, ch = 11, cx = R - ctlW;
      if (i) { g.fillStyle = C.line; g.fillRect(L, y - 1, R - L, 0.3); }
      label(r.label, L, cy + ch / 2, 6, C.text);
      if (r.help) {
        g.font = `400 4.6px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "left"; g.textBaseline = "middle";
        wrap(g, r.help, R - L, 2).forEach((l, n) => g.fillText(l, L, cy + ch + 5 + n * 5.6));
      }
      if (r.kind === "number") {
        box(cx, cy, 16, ch, { key: r.key, op: "minus" }, false, r.can.minus); label("−", cx + 8, cy + ch / 2, 7, r.can.minus ? C.text : C.dim, "center");
        box(R - 16, cy, 16, ch, { key: r.key, op: "plus" }, false, r.can.plus); label("+", R - 8, cy + ch / 2, 7, r.can.plus ? C.text : C.dim, "center");
        label(r.value, (cx + R) / 2, cy + ch / 2, 6, C.hot, "center", 500, FONT.ui);
      } else if (r.kind === "choice") {
        const n = r.choices.length, bw = ctlW / n;
        r.choices.forEach((c, j) => {
          const x = cx + j * bw, on = c.value === r.value;
          box(x, cy, bw - 1, ch, { key: r.key, op: "pick", value: c.value }, on, c.enabled && !on);
          label(c.label, x + (bw - 1) / 2, cy + ch / 2, 5.2, !c.enabled ? C.dim : on ? C.hot : C.text, "center", 500);
        });
      } else {
        box(cx, cy, ctlW, ch, { key: r.key, op: "do" }, false, true);
        label("Put Back", cx + ctlW / 2, cy + ch / 2, 5.2, C.text, "center", 500);
      }
    });
    if (said) { g.font = `400 4.6px ${FONT.lines}`; g.fillStyle = C.ok; g.textAlign = "left"; g.fillText(said, L, h - 5); }
  }
}
