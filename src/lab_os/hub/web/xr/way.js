// The way out in VR and AR: ⏻ (its menu), EXIT (leave VR or AR) and × (close what is open), drawn the same
// and in this order on every page (quick job 157): under the core (xr/modules.js → WayOut), on a module's
// tab (ModuleTab) and on Teleop's bar (xr/teleop-panel.js). Sizes in the caller's units (pixels or metres).
import { C, FONT, icon, rgba, spaced } from "./draw.js";

const WAY = { gap: 0.16, exit: 2.4 }; // of the buttons' height: the gap, and EXIT's width
/** The width of the way-out buttons for height h (× included or not). */
export const wayWidth = (h, close = true) => h * (1 + WAY.gap + WAY.exit + (close ? WAY.gap + 1 : 0));
/** Which way-out button is at x (pixels from the group's left, height h): "power" | "exit" | "back" | null. */
export function wayAt(x, h, close = true) {
  const e0 = h * (1 + WAY.gap), e1 = e0 + h * WAY.exit, b0 = e1 + h * WAY.gap;
  return x < 0 ? null : x <= h ? "power" : x >= e0 && x <= e1 ? "exit" : close && x >= b0 && x <= b0 + h ? "back" : null;
}
export function cutRect(g, x, y, w, h, c) {
  g.beginPath(); g.moveTo(x + c, y); g.lineTo(x + w, y); g.lineTo(x + w, y + h - c); g.lineTo(x + w - c, y + h); g.lineTo(x, y + h); g.lineTo(x, y + c); g.closePath();
}
/** Draw the way-out buttons at (x, y), height h; `over`: the one pointed at. */
export function drawWay(g, x, y, h, over, close = true) {
  const one = (bx, bw, kind, draw) => {
    const on = over === kind;
    cutRect(g, bx, y, bw, h, h * 0.22);
    g.fillStyle = rgba(C.bg, 0.92); g.fill();
    if (on) { g.fillStyle = rgba(C.primary, 0.22); g.fill(); }
    g.strokeStyle = on ? C.primary : rgba(C.primary, 0.7); g.lineWidth = Math.max(2, h * 0.03); g.stroke();
    draw(on ? C.hot : C.text, bx, bw);
  };
  one(x, h, "power", (col, bx) => icon(g, "i-power", bx + h / 2, y + h / 2, h * 0.5, col, 1.8));
  const ex = x + h * (1 + WAY.gap), ew = h * WAY.exit;
  one(ex, ew, "exit", (col) => {
    icon(g, "i-headset", ex + h * 0.5, y + h / 2, h * 0.46, col, 1.6);
    g.font = `700 ${h * 0.38}px ${FONT.ui}`; spaced(g, 0.2); g.fillStyle = col; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText("EXIT", ex + ew / 2 + h * 0.28, y + h / 2); spaced(g, 0);
  });
  if (!close) return;
  const bx = ex + ew + h * WAY.gap;
  one(bx, h, "back", (col) => { // ×
    const r = h * 0.2, cx = bx + h / 2, cy = y + h / 2;
    g.strokeStyle = col; g.lineWidth = Math.max(2, h * 0.06); g.lineCap = "round";
    g.beginPath(); g.moveTo(cx - r, cy - r); g.lineTo(cx + r, cy + r); g.moveTo(cx + r, cy - r); g.lineTo(cx - r, cy + r); g.stroke();
  });
}
