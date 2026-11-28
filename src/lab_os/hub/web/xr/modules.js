// The hub's modules in VR (decision 2026-11-12, the builder):
//   - ModuleButton: the designed hub's module button (cut-corner box, the icon in a turning dotted ring,
//     the name in caps, corner brackets that open when pointed at), left and right of the core.
//   - TeleopModule: Arm Control without leaving VR or AR (quick job 97; from 2026-11-21 to 11-23 it opened the
//     teleop page instead): the teleop page's own session (TeleopSession, /static/xr.js: the arm on its
//     table, its status box, controllers or hands, the same messages to the brain) inside the hub's
//     session. STOP is A/X; the brain freezes the arm when input stops, and one page drives at a time.
//     Under its status box: STOP, Options (the Arm Control page's options), then ⏻, EXIT and × (xr/teleop-panel.js,
//     quick job 102), in place of the tab.
//   - ArmHologram: Monitor and AI Control, watch-only: the arm as a line-drawn hologram over a round floor
//     grid with scan rings, turning slowly, its joints as hexagons with callouts (name and angle, from the
//     brain's status); AI Control adds the robot-tool calls as they happen (/api/ai-calls). Both have STOP,
//     like their pages (it works from any screen). With two arms, Monitor shows both, each on its own grid
//     (quick job 119).
//   - ModuleTab: the open module's title with ⏻, EXIT and × (xr/way.js), floating at the left.
//   - ExitButton: leaves VR or AR (quick job 78), under the hub on every page and on the off card.
//   - RaspbotModule (xr/raspbot.js, quick job 107): drive raspbot1 with its camera as your eyes.
//   - CamerasModule (xr/cameras.js, quick job 157): every camera's picture, as the Cameras page.
// The buttons are the flat hub's modules (`hub.modules`), less what VR cannot show (quick job 157):
// Training (LeLab on the desktop) and System Map (a 3D page made for a screen) have no VR version.
import * as THREE from "three";
import { getArmFeed } from "/static/arm/arm-feed.js";
import { loadArmModel } from "/static/arm/arm-model.js";
import { KINDS } from "/static/arm/kinds.js";
import { getLink } from "/static/link.js";
import { deviceName } from "/web/device.js";
import { jointLabel } from "/web/words.js";
import { C, GLOW, CanvasPlane, FONT, TAU, arrive, clamp, icon, rgba, spaced } from "./draw.js";
import { minimal } from "./look.js";
import { cutRect, drawWay, wayAt, wayWidth } from "./way.js";
import { wrap } from "./panels.js";
import { TeleopBar, TeleopOptions } from "./teleop-panel.js";
import { handChoiceAfter, optionMessage } from "./teleop-options.js";

// Monitor: every arm; monitor-so101 / monitor-xarm: one kind's arms, as their pages (quick job 147)
export const VR_MODULES = { teleop: ["Arm Control", "i-hand"], monitor: ["Monitor", "i-screen"], "monitor-so101": ["SO-101 Monitor", "i-screen"], "monitor-xarm": ["xArm Monitor", "i-screen"], ai: ["AI Control", "i-chip"], cameras: ["Cameras", "i-cam"], raspbot: ["Raspbot Control", "i-cam"] };
const PX = 900; // canvas pixels per metre

/* ---------- the module button ---------- */
export class ModuleButton {
  constructor(id) {
    this.id = id;
    [this.title, this.ico] = VR_MODULES[id];
    this.w = 0.64; this.h = 0.2; // like the screen's: 3 rem of icon, the name, padding
    this.p = new CanvasPlane(this.w + 0.06, this.h + 0.06, PX); // room for the brackets
    this.p.mesh.userData.hit = this;
    this.a = 0; this.hover = false; this.hoverK = 0;
  }
  get mesh() { return this.p.mesh; }
  hit() { return { kind: "module", id: this.id }; }
  step(dt) {
    this.hoverK += ((this.hover ? 1 : 0) - this.hoverK) * Math.min(1, dt * 12);
    this.a = (this.a + dt * (this.hover ? 220 : 9) * (this.side === "right" ? -1 : 1)) % 360;
    this.p.paint((g, cw, ch) => this._draw(g, cw, ch), `${Math.round(this.a / 3)}|${this.hoverK.toFixed(2)}`);
  }
  _draw(g, cw, ch) {
    const m = 0.03 * PX, w = cw - 2 * m, h = ch - 2 * m, cut = 0.7 * 0.058 * PX, k = this.hoverK;
    g.translate(m, m);
    g.beginPath(); g.moveTo(cut, 0); g.lineTo(w, 0); g.lineTo(w, h - cut); g.lineTo(w - cut, h); g.lineTo(0, h); g.lineTo(0, cut); g.closePath();
    g.fillStyle = rgba(C.surface, 0.86); g.fill();
    g.strokeStyle = rgba(C.primary, 0.32 + 0.48 * k); g.lineWidth = 2; g.stroke();
    // corner brackets just outside, opening a little when pointed at
    const b = 0.7 * 0.058 * PX * 0.9, o = 5 + 4 * k;
    g.strokeStyle = rgba(C.primary, 0.7); g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(w + o - b, -o); g.lineTo(w + o, -o); g.lineTo(w + o, -o + b); g.stroke();
    g.beginPath(); g.moveTo(-o + b, h + o); g.lineTo(-o, h + o); g.lineTo(-o, h + o - b); g.stroke();
    // the icon in its turning dotted rings
    const rem = 0.058 * PX, cx = 2 * rem, cy = h / 2, s = (3 * rem) / 60;
    g.save(); g.translate(cx, cy); g.rotate((this.a * Math.PI) / 180); g.scale(s, s);
    g.strokeStyle = C.primary;
    g.globalAlpha = 0.8; g.lineWidth = 1; g.setLineDash([14, 5, 2, 5]); g.beginPath(); g.arc(0, 0, 22, 0, TAU); g.stroke();
    g.globalAlpha = 0.5; g.lineWidth = 0.6; g.setLineDash([1, 3]); g.beginPath(); g.arc(0, 0, 27, 0, TAU); g.stroke();
    g.restore();
    if (k > 0.05) { g.save(); g.shadowColor = C.primary; g.shadowBlur = 10 * k; icon(g, this.ico, cx, cy, 22 * s, C.primary, 1.6); g.restore(); }
    else icon(g, this.ico, cx, cy, 22 * s, C.primary, 1.6);
    // the name
    const fs = 1.05 * 0.058 * PX;
    g.font = `600 ${fs}px ${FONT.ui}`; spaced(g, 0.12); g.textBaseline = "middle"; g.textAlign = "left";
    g.fillStyle = k > 0.5 ? C.hot : C.text;
    const tx = 4.1 * rem, lines = wrap(g, this.title.toUpperCase(), w - tx - 0.9 * rem, 2);
    lines.forEach((l, i) => g.fillText(l, tx, h / 2 + (i - (lines.length - 1) / 2) * fs * 1.1));
  }
}

/* ---------- the way out: ⏻ (its menu), EXIT (leave VR or AR) and × (close what is open), in this order and
   this look on every page (quick job 157: they were in different places on the hub and in Arm Control):
   under the core on the hub, a details page and Settings; on the tab of an open module; on Arm Control's bar.
   × in place of ← (choice 2). Cut corners, like every box of the hub. ---------- */
/* ---------- the open module's title tab, with the way out at its right ---------- */
const TAB_H = 0.14, TAB_W = 0.62 + wayWidth(TAB_H * 0.86);
export class ModuleTab {
  constructor() {
    this.p = new CanvasPlane(TAB_W, TAB_H, PX);
    this.p.mesh.userData.hit = this;
    this.title = ""; this.ico = ""; this.hover = null;
  }
  get mesh() { return this.p.mesh; }
  hit(u, v) {
    const bh = TAB_H * 0.86, x0 = TAB_W - wayWidth(bh) - TAB_H * 0.07;
    return v > 0.07 && v < 0.93 && { kind: wayAt(u * TAB_W - x0, bh) || "tab" } || { kind: "tab" };
  }
  paint() {
    const over = this.hover?.kind || "";
    this.p.paint((g, w, h) => {
      const c = h * 0.22;
      cutRect(g, 0, 0, w, h, c); g.fillStyle = rgba(C.bg, 0.85); g.fill();
      g.fillStyle = C.primary; g.fillRect(0, c, 3, h * 0.4); g.fillRect(c, 0, h * 0.4, 3);
      icon(g, this.ico, h * 0.42, h / 2, h * 0.42, C.primary, 1.6);
      g.font = `700 ${h * 0.3}px ${FONT.title}`; spaced(g, 0.18); g.fillStyle = C.hot; g.textBaseline = "middle"; g.textAlign = "left";
      g.fillText(this.title.toUpperCase(), h * 0.85, h / 2); spaced(g, 0);
      const bh = h * 0.86;
      drawWay(g, w - (wayWidth(TAB_H * 0.86) / TAB_W) * w - h * 0.07, h * 0.07, bh, over);
    }, `${this.title}|${over}`);
  }
}

/* ---------- STOP (a watcher can always stop) ---------- */
export class StopButton {
  constructor() {
    this.p = new CanvasPlane(0.32, 0.13, PX);
    this.p.mesh.userData.hit = this;
    this.hover = false;
  }
  get mesh() { return this.p.mesh; }
  hit() { return { kind: "stop" }; }
  paint() {
    this.p.paint((g, w, h) => {
      const c = h * 0.22;
      g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
      g.fillStyle = rgba(C.danger, this.hover ? 0.45 : 0.22); g.fill();
      g.strokeStyle = C.danger; g.lineWidth = 3; g.stroke();
      g.font = `700 ${h * 0.42}px ${FONT.ui}`; spaced(g, 0.2); g.fillStyle = this.hover ? C.hot : C.text; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText("STOP", w / 2, h / 2);
    }, this.hover);
  }
}

/* ---------- ⏻'s menu: back to the start screen, or Exit (leave VR or AR). Opens from ⏻ in the strip and from
   ⏻ on a module's tab, so it's on every page of the hub in VR (the builder, 2026-11-20) ---------- */
const PM = { pad: 0.05, title: 0.09, row: 0.11, notch: 0.025 }; // the power menu's sizes (metres)
export class PowerMenu {
  constructor() {
    // the flat hub's drop-down (quick job 154): "POWER" in the title font, an icon on each row, a notch toward ⏻
    this.items = [["start", "i-screen", "Back to the start screen"], ["exit", "i-headset", "Exit"]];
    this.p = new CanvasPlane(0.56, PM.pad * 2 + PM.title + PM.row * this.items.length, PX); // 0.82 m before (quick job 157)
    this.p.mesh.userData.hit = this;
    this.p.mesh.renderOrder = 13;
    this.p.mat.depthTest = false; // in front of everything, like the way out
    this.p.mesh.visible = false;
    this.hover = null;
    this.notch = 0.5; // where ⏻ is, 0..1 across the menu (hub.js → openMenu)
  }
  get mesh() { return this.p.mesh; }
  hit(u, v) {
    const y = (1 - v) * this.p.h - PM.pad - PM.title, i = Math.floor(y / PM.row);
    return y >= 0 && i < this.items.length ? { kind: "menu", id: this.items[i][0] } : { kind: "menu-pad" };
  }
  paint() {
    const over = this.hover?.kind === "menu" ? this.hover.id : "";
    this.p.paint((g, w, h) => {
      const k = h / this.p.h, m = PM.pad * k, rowH = PM.row * k, top = (PM.pad + PM.title) * k, n = PM.notch * k;
      // the box starts under the notch
      const c = h * 0.12, nx = clamp(this.notch * w, c + n * 1.5, w - n * 1.5);
      g.beginPath(); g.moveTo(c, n); g.lineTo(nx - n, n); g.lineTo(nx, 1.5); g.lineTo(nx + n, n); g.lineTo(w, n);
      g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, n + c); g.closePath();
      g.fillStyle = rgba(C.bg, 0.95); g.fill();
      g.strokeStyle = rgba(C.primary, 0.7); g.lineWidth = 3; g.stroke();
      g.font = `700 ${PM.title * k * 0.42}px ${FONT.title}`; spaced(g, 0.14); g.fillStyle = C.hot;
      g.textAlign = "left"; g.textBaseline = "middle"; g.fillText("POWER", m * 1.6, n + (top - n) / 2 + m * 0.3); spaced(g, 0);
      this.items.forEach(([id, ico, label], i) => {
        const y = top + i * rowH;
        if (id === over) { g.fillStyle = rgba(C.primary, 0.18); g.fillRect(m, y, w - 2 * m, rowH - 4); }
        icon(g, ico, m + rowH * 0.5, y + rowH / 2 - 2, rowH * 0.5, id === over ? C.hot : C.primary, 1.6);
        let size = rowH * 0.38;
        g.font = `600 ${size}px ${FONT.ui}`;
        const room = w - m * 2 - rowH * 1.1, tw = g.measureText(label).width;
        if (tw > room) { size *= room / tw; g.font = `600 ${size}px ${FONT.ui}`; } // shrunk to fit
        g.fillStyle = id === over ? C.hot : C.text; g.textAlign = "left"; g.textBaseline = "middle";
        g.fillText(label, m + rowH, y + rowH / 2 - 2);
      });
    }, `${over}|${this.notch.toFixed(2)}`);
  }
}
/* ---------- the way out under the core (the hub, a details page, Settings): ⏻, EXIT, and × while a page is
   open (quick job 157) ---------- */
export class WayOut {
  constructor(h = 0.13) {
    this.h = h; this.w = wayWidth(h);
    this.p = new CanvasPlane(this.w, h, PX);
    this.p.mesh.userData.hit = this;
    this.p.mesh.renderOrder = 12;
    this.p.mat.depthTest = false; // nothing may hide the way out
    this.hover = null; this.close = false;
  }
  get mesh() { return this.p.mesh; }
  hit(u) {
    const x0 = this.close ? 0 : (this.w - wayWidth(this.h, false)) / 2;
    return { kind: wayAt(u * this.w - x0, this.h, this.close) || "pad" };
  }
  paint() {
    const over = this.hover?.kind || "", close = this.close;
    this.p.paint((g, w, h) => {
      // centred: without ×, the two buttons sit in the middle
      const x = close ? 0 : (w - (wayWidth(this.h, false) / this.w) * w) / 2;
      drawWay(g, x, 0, h, over, close);
    }, `${over}|${close}`);
  }
}

/* ---------- Exit (quick job 78): leaves VR or AR, back to the browser. On the "lab-os is off" card ---------- */
export class ExitButton {
  constructor(w = 0.34, h = 0.12) {
    this.p = new CanvasPlane(w, h, PX);
    this.p.mesh.userData.hit = this;
    this.p.mesh.renderOrder = 12;
    this.p.mat.depthTest = false; // nothing may hide the way out
    this.hover = false;
  }
  get mesh() { return this.p.mesh; }
  hit() { return { kind: "exit" }; }
  paint() {
    this.p.paint((g, w, h) => {
      const c = h * 0.22;
      g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
      g.fillStyle = rgba(C.bg, 0.92); g.fill();
      if (this.hover) { g.fillStyle = rgba(C.primary, 0.22); g.fill(); }
      g.strokeStyle = this.hover ? C.primary : rgba(C.primary, 0.7); g.lineWidth = 3; g.stroke();
      icon(g, "i-headset", h * 0.62, h / 2, h * 0.5, this.hover ? C.hot : C.primary, 1.6);
      g.font = `700 ${h * 0.4}px ${FONT.ui}`; spaced(g, 0.2); g.fillStyle = this.hover ? C.hot : C.text; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText("EXIT", w / 2 + h * 0.3, h / 2);
    }, this.hover);
  }
}

/* ---------- Monitor and AI Control: the arm as a hologram ---------- */
const TOOL = { arm_status: "Read the arm", list_poses: "Listed the poses", move_joints: "Move joints", gripper: "Gripper", move_to: "Move to", go_to_pose: "Go to pose", stop: "Stop" };
const SCALE = 1.9; // the hologram is bigger than the real arm, so it reads from where you stand

export class ArmHologram {
  /** @param {"monitor"|"monitor-so101"|"monitor-xarm"|"ai"} id */
  constructor(id) {
    this.id = id;
    this.group = new THREE.Group();
    this.link = getLink("monitor"); // a watcher: it can only stop
    // one unit per arm (quick job 119): Monitor shows the left arm too while the brain drives two;
    // AI Control shows the arm the AI tools drive (the first arm), as its desktop page does.
    // monitor-<kind> (quick job 147): only the arms of that kind, as /monitor/<kind> does.
    const watch = id === "monitor" || id.startsWith("monitor-");
    this.kind = id.startsWith("monitor-") ? id.slice("monitor-".length) : null;
    this.units = [new HoloArm(getArmFeed(this.link, "right", this.kind), "right")];
    if (watch) this.units.push(new HoloArm(getArmFeed(this.link, "left", this.kind), "left"));
    for (const u of this.units) this.group.add(u.group);
    this.stop = new StopButton();
    this.stop.mesh.position.set(0, -0.14, 0.05);
    this.group.add(this.stop.mesh);
    this.status = new CanvasPlane(1.0, 0.1, PX);
    this.status.mesh.position.set(0, -0.32, 0.02);
    this.group.add(this.status.mesh);
    if (id === "ai") {
      this.calls = []; this.after = 0;
      this.log = new CanvasPlane(1.1, 1.0, PX);
      this.log.mesh.position.set(1.05, 0.62, -0.1);
      this.log.mesh.rotation.y = -0.45;
      this.log.mesh.userData.hit = { hit: () => ({ kind: "page" }) };
      this.group.add(this.log.mesh);
    }
    this.t0 = 0;
  }
  targets() { return [this.stop.mesh]; }
  open(now) {
    this.t0 = now;
    for (const u of this.units) u.load();
    if (this.id === "ai") { this.timer = setInterval(() => this._poll(), 1000); this._poll(); }
  }
  close() { clearInterval(this.timer); this.timer = null; }

  async _poll() {
    try {
      const r = await fetch(`/api/ai-calls?after=${this.after}`, { cache: "no-store" });
      const d = await r.json();
      for (const c of d.calls) { this.calls.push(c); this.after = Math.max(this.after, c.t); }
      this.calls = this.calls.slice(-14);
      this.control = d.control;
    } catch { /* the brain will be back */ }
  }

  step(dt, now, cameraPos, hits) {
    const k = minimal() ? 1 : arrive((now - this.t0) / 700); // minimal: no growing in (quick job 157)
    this.group.scale.setScalar(0.3 + 0.7 * k);
    // two arms: the left arm on your left, the right arm on your right, each on its own floor grid
    const two = this.units.length > 1 && !!this.units[1].feed.status;
    for (const u of this.units) {
      u.group.visible = u === this.units[0] || two;
      u.group.position.x = two ? (u.side === "left" ? -0.8 : 0.8) : 0;
      if (u.group.visible) u.step(dt, now, cameraPos, this.group, k, two);
    }
    this.stop.hover = hits.some((h) => h.what.kind === "stop");
    this.stop.paint();
    // the state under the arm: who has control (each arm's own state is under that arm with two)
    const s = this.units[0].feed.status;
    const who = { free: "Free", ai: "The AI tools" }[s?.control] || (s ? "An input page" : "");
    const none = this.kind && !s && this.units[0].feed.heard; // no arm of this kind
    const line = none ? `No ${KINDS[this.kind].robot} is connected to the brain`
      : two ? (s ? `Control: ${who}` : "Connecting to the brain") : `${s?.arm?.name || "Arm"}: ${armWord(s)}${who ? `   Control: ${who}` : ""}`;
    this.status.paint((g, w, h) => {
      g.textAlign = "center"; g.textBaseline = "middle"; g.font = `${FONT.linesW} ${h * 0.4}px ${FONT.lines}`;
      g.fillStyle = C.dim;
      g.fillText(line, w / 2, h / 2);
    }, line);
    if (this.log) this._paintLog();
  }
  _paintLog() {
    const key = JSON.stringify(this.calls.map((c) => c.t));
    this.log.paint((g, w, h) => {
      g.fillStyle = rgba(C.bg, 0.85); g.fillRect(0, 0, w, h);
      g.strokeStyle = rgba(C.primary, 0.4); g.lineWidth = 2; g.strokeRect(1, 1, w - 2, h - 2);
      const u = h / 100;
      g.font = `500 ${4 * u}px ${FONT.ui}`; g.fillStyle = C.primary; g.textBaseline = "alphabetic"; g.textAlign = "left";
      g.fillText("Robot-tool calls", 5 * u, 9 * u);
      g.fillStyle = rgba(C.primary, 0.55); g.fillRect(5 * u, 11 * u, w - 10 * u, 1.5);
      if (!this.calls.length) {
        g.font = `${FONT.linesW} ${3.4 * u}px ${FONT.lines}`; g.fillStyle = C.dim;
        wrap(g, "No calls yet this run. An AI tool connected to the brain (docs/guides/ai-control.md) shows here as it reads and moves the arm.", w - 10 * u).forEach((l, i) => g.fillText(l, 5 * u, 20 * u + i * 5 * u));
        return;
      }
      [...this.calls].reverse().forEach((c, i) => {
        const y = 19 * u + i * 6 * u;
        if (y > h - 3 * u) return;
        const time = new Date(c.t * 1000).toLocaleTimeString([], { hour12: false });
        g.font = `${2.9 * u}px ${FONT.digits}`; g.fillStyle = rgba(C.primary, 0.8); g.fillText(time, 5 * u, y);
        g.font = `600 ${3.4 * u}px ${FONT.ui}`; g.fillStyle = C.text; g.fillText(TOOL[c.tool] || c.tool, 25 * u, y);
        g.font = `${FONT.linesW} ${3.1 * u}px ${FONT.lines}`;
        g.fillStyle = c.outcome === "ok" || c.outcome === "arrived" ? C.primary : c.outcome === "refused" || c.outcome === "error" ? C.accent : C.dim;
        g.textAlign = "right"; g.fillText(String(c.outcome || ""), w - 5 * u, y); g.textAlign = "left";
      });
    }, key);
  }
}


/** "Holding", "Following", "Held still", ... for an arm's status (null: not connected yet). */
function armWord(s) {
  return !s ? "Connecting to the brain" : s.arm?.connected === false ? "Disconnected" : s.frozen ? "Held still" : s.clutch ? "Following" : "Holding";
}

/** One arm as a hologram: the line-drawn model turning slowly on its floor grid, a callout per joint
 *  and, with two arms, its name and state under it. Each unit has the same look (quick job 119). */
class HoloArm {
  constructor(feed, side) {
    this.feed = feed; this.side = side;
    this.group = new THREE.Group();
    this.turn = new THREE.Group(); // turns slowly
    this.group.add(this.turn);
    this.grid = floorGrid();
    this.group.add(this.grid);
    this.arm = null; this.loading = null; this.kind = null;
    this.callouts = [];
    this.name = new CanvasPlane(1.0, 0.1, PX);
    this.name.mesh.position.set(0, -0.08, 0.02); // under its grid, beside STOP
    this.group.add(this.name.mesh);
  }
  load() {
    const kind = this.feed.modelKind;
    if (!kind && this.side === "left") return; // no left arm yet: step() loads it when it comes
    if (this.loading && this.kind === (kind || "so101")) return;
    this.kind = kind || "so101";
    this.loading = this._load(this.kind);
  }
  async _load(kind) {
    let arm;
    try {
      arm = await loadArmModel(kind, { style: kind === "so101" ? "mesh" : "boxes" });
    } catch {
      arm = await loadArmModel(kind, { style: "stick" });
    }
    if (kind !== this.kind) return; // another arm came meanwhile
    if (this.arm) this.turn.remove(this.arm.object);
    for (const c of this.callouts) for (const o of [c.label.mesh, c.line, c.hex]) this.group.remove(o);
    this.callouts = [];
    this.arm = arm;
    // line-drawn: see-through cyan, its edges brighter
    arm.object.traverse((o) => {
      if (!o.isMesh) return;
      o.material = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.12, ...GLOW, depthWrite: false });
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 25), new THREE.LineBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.55, ...GLOW, depthWrite: false }));
      o.add(edges);
    });
    arm.object.scale.setScalar(SCALE);
    this.turn.add(arm.object);
    // a callout per joint: a hexagon on the joint, a line with an elbow to its name and angle
    for (const name of arm.jointNames) {
      const joint = arm.object.getObjectByName(name);
      if (!joint) continue;
      const label = new CanvasPlane(0.42, 0.075, PX);
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.7, depthTest: false }));
      const hex = new THREE.Mesh(new THREE.CircleGeometry(0.016, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.85, depthTest: false }));
      for (const o of [label.mesh, line, hex]) { o.renderOrder = 30; this.group.add(o); }
      this.callouts.push({ name, joint, label, line, hex });
    }
  }
  /** `two`: both arms show, so the callouts go to the outer side and the name and state show under it. */
  step(dt, now, cameraPos, root, k, two) {
    const s = this.feed.status;
    if (s?.arm?.model && s.arm.model !== this.kind) this.load(); // the left arm came, or another arm
    if (this.arm && s?.joints) this.arm.setJoints(s.joints);
    if (this.arm) this.arm.setTint(null);
    if (this.arm) this.arm.setHeld(!!s?.frozen); // held still: a dim ring at the base (quick jobs 153, 155)
    this.turn.rotation.y += dt * 0.12;
    this.grid.userData.step(now);
    // the callouts: from the joint, out to a side (two arms: the outer side, so they never meet)
    const lim = s?.limits || {};
    const world = new THREE.Vector3();
    root.updateMatrixWorld(true);
    this.callouts.forEach((c, i) => {
      c.joint.getWorldPosition(world);
      const p = this.group.worldToLocal(world.clone());
      const side = two ? (this.side === "left" ? -1 : 1) : i % 2 ? 1 : -1;
      const row = two ? 0.12 + i * 0.11 : 0.12 + i * 0.13;
      const elbow = p.clone().add(new THREE.Vector3(side * 0.12, 0.05, 0)), end = new THREE.Vector3(side * 0.62, row, p.z);
      c.hex.position.copy(p);
      c.hex.lookAt(cameraPos);
      const pts = c.line.geometry.attributes.position;
      pts.setXYZ(0, p.x, p.y, p.z); pts.setXYZ(1, elbow.x, end.y, elbow.z); pts.setXYZ(2, end.x, end.y, end.z); pts.needsUpdate = true;
      c.label.mesh.position.set(end.x + side * 0.22, end.y + 0.035, end.z);
      const v = s?.joints?.[c.name];
      const out = v != null && lim[c.name] && (v < lim[c.name][0] || v > lim[c.name][1]);
      c.label.paint((g, w, h) => {
        g.textBaseline = "middle"; g.font = `${FONT.linesW} ${h * 0.42}px ${FONT.lines}`; g.fillStyle = C.text;
        g.textAlign = side < 0 ? "right" : "left";
        const x = side < 0 ? w - 4 : 4;
        g.fillText(jointLabel(c.name), x + (side < 0 ? -h * 2.3 : h * 2.3), h / 2);
        g.font = `${h * 0.48}px ${FONT.digits}`; g.fillStyle = out ? C.accent : C.primary;
        // numbers never shift: a sign slot and fixed digit places ("!" is DSEG7's digit-wide blank)
        g.fillText(v == null ? "--" : `${v >= 0 ? "!" : "-"}${Math.abs(v).toFixed(1).padStart(5, "!")}`, x, h / 2);
      }, `${v?.toFixed(1)}|${out}|${side}`);
      c.label.opacity = k;
    });
    // two arms: "RIGHT ARM so101-white   Holding" under each arm, in the same style for both
    this.name.mesh.visible = two;
    if (!two) return;
    const word = armWord(s), title = `${this.side === "left" ? "LEFT" : "RIGHT"} ARM`, name = s?.arm?.name || "";
    this.name.paint((g, w, h) => {
      g.textBaseline = "middle"; g.textAlign = "center";
      g.font = `600 ${h * 0.36}px ${FONT.ui}`; spaced(g, 0.18);
      const a = `${title}   `; const aw = g.measureText(a).width;
      g.font = `${FONT.linesW} ${h * 0.4}px ${FONT.lines}`; spaced(g, 0);
      const b = `${name}   ${word}`; const bw = g.measureText(b).width;
      const x0 = (w - aw - bw) / 2;
      g.textAlign = "left";
      g.font = `600 ${h * 0.36}px ${FONT.ui}`; spaced(g, 0.18); g.fillStyle = C.primary; g.fillText(a, x0, h / 2);
      g.font = `${FONT.linesW} ${h * 0.4}px ${FONT.lines}`; spaced(g, 0); g.fillStyle = C.dim; g.fillText(b, x0 + aw, h / 2);
    }, `${name}|${word}`);
  }
}

/** A round floor grid: rings and spokes, with faint scan rings running outward. */
function floorGrid() {
  const g = new THREE.Group(), mat = new THREE.LineBasicMaterial({ color: new THREE.Color(C.line), transparent: true, opacity: 0.9 });
  const pts = [];
  for (const r of [0.15, 0.3, 0.45, 0.6]) for (let i = 0; i < 64; i++) {
    const a0 = (i / 64) * TAU, a1 = ((i + 1) / 64) * TAU;
    pts.push(new THREE.Vector3(Math.cos(a0) * r, 0, Math.sin(a0) * r), new THREE.Vector3(Math.cos(a1) * r, 0, Math.sin(a1) * r));
  }
  for (let i = 0; i < 12; i++) { const a = (i / 12) * TAU; pts.push(new THREE.Vector3(Math.cos(a) * 0.15, 0, Math.sin(a) * 0.15), new THREE.Vector3(Math.cos(a) * 0.6, 0, Math.sin(a) * 0.6)); }
  g.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), mat));
  const scan = new THREE.Mesh(new THREE.RingGeometry(0.97, 1, 96), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: 0.3, ...GLOW, depthWrite: false, side: THREE.DoubleSide }));
  scan.rotation.x = -Math.PI / 2;
  g.add(scan);
  g.userData.step = (now) => { const k = (now / 3500) % 1; scan.scale.setScalar(0.05 + 0.6 * k); scan.material.opacity = 0.35 * (1 - k); };
  return g;
}

/* ---------- Arm Control, inside the hub's session ---------- */
export class TeleopModule {
  constructor({ ar, refType }) {
    this.ar = ar; this.refType = refType;
    this.tele = null;
  }
  async open() {
    const { TeleopSession, armStyle, STYLE_KEY } = await import("/static/xr.js");
    this.styleKey = STYLE_KEY; // the same as the Arm Control page's "3D arm in the headset"
    const link = getLink("input");
    // its device name, so the other pages say who has control (quick job 76); again after a reconnect
    const hello = () => link.send({ type: "hello", agent: navigator.userAgent, device: deviceName() });
    if (!this.helloOn) { link.on("open", hello); this.helloOn = true; }
    hello(); // dropped when the link isn't open yet: then "open" sends it
    // the teleop page's "3D arm in the headset" (or ?xrarm=stick): the light model if frames drop
    this.style = armStyle() || "";
    this.tele = new TeleopSession(link, { ar: this.ar, style: this.style, refType: this.refType });
    this.link = link; // STOP on the bar (hub.js sends it)
    // the buttons under the status box and the options over it (quick job 102), in the teleop room's
    // space like the status box (xr-scene.js: 0.42 × 0.197 m at 0.48, 1.12, -0.62, turned -0.35)
    const sc = this.tele.xrScene, at = sc.panel.mesh;
    this.bar = new TeleopBar();
    this.opts = new TeleopOptions();
    this.bar.mesh.position.set(at.position.x, at.position.y - 0.197 / 2 - 0.012 - this.bar.p.h / 2, at.position.z);
    this.opts.mesh.position.set(at.position.x, at.position.y + 0.197 / 2 + 0.012 + this.opts.h / 2, at.position.z);
    for (const m of [this.bar.mesh, this.opts.mesh]) { m.rotation.y = at.rotation.y; sc.root.add(m); }
    this.opts.mesh.visible = false;
    this.said = { text: "", t: 0 };
    return this.tele.scene;
  }
  /** What the pointer can land on: the bar, and the options while they're open. */
  targets() { return this.tele ? [this.bar.mesh, ...(this.opts.mesh.visible ? [this.opts.mesh] : [])] : []; }
  /** A press on the bar's Options or on an option (`what`: {kind: "tele", op, key?, value?}). */
  press(what) {
    if (!this.tele) return;
    if (what.op === "options") { this.opts.mesh.visible = !this.opts.mesh.visible; return; }
    const s = this.tele.feed.status;
    const msg = optionMessage(what.key, what.op, what.value, s);
    if (msg) this.link.send(msg);
    // Hands, or the switch to hands by itself: this headset's choice (quick job 114)
    const choice = handChoiceAfter(what.key, what.op, what.value, this.tele.handChoice);
    if (choice) this.tele.setHandChoice(choice);
    if (what.key === "style" && what.op === "pick") {
      this.style = what.value;
      try { localStorage.setItem(this.styleKey, what.value); } catch { /* private window: this session only */ }
      this.tele.xrScene.setStyle(what.value);
    }
    if (what.key === "place") { this.tele.putBack(); this.said = { text: "The 3D arm is back at its first place.", t: performance.now() }; }
  }
  step(dt, now, cameraPos, hits) {
    if (!this.tele) return;
    this.bar.hover = hits.find((h) => h.obj === this.bar.mesh)?.what || null;
    this.opts.hover = hits.find((h) => h.obj === this.opts.mesh)?.what || null;
    this.bar.open = this.opts.mesh.visible;
    this.bar.paint();
    if (this.opts.mesh.visible) this.opts.paint(this.tele.feed.status, this.style, this.tele.handChoice, performance.now() - this.said.t < 4000 ? this.said.text : "");
  }
  frame(t, xrFrame, refSpace) { return this.tele?.frame(t, xrFrame, refSpace); }
  close() { this.tele?.end(); this.tele = null; } // session_end: the arm freezes, control is free
}

export { clamp };
