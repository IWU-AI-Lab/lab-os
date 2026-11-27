// Cameras in VR and AR (quick job 157: the VR hub's modules are the flat hub's, less what VR cannot
// show). The picture of every camera plugged in now, as the Cameras page (/api/cameras): up to four in a
// grid on one panel in front of you. A USB camera's picture comes as single JPEGs (/api/camera-feed/…,
// about 4 a second while the module is open: the brain closes the camera 5 s after the last one);
// raspbot1's through its relayed stream. It drives nothing.
import * as THREE from "three";
import { C, CanvasPlane, FONT, icon, rgba } from "./draw.js";

const PX = 900; // canvas pixels per metre
const W = 1.3, H = 0.82; // the panel, metres
const MAX = 4;
const EVERY_MS = 250; // a new picture from each camera
const LIST_MS = 3000; // the camera list again (a camera plugged in later shows by itself)

export class CamerasModule {
  constructor() {
    this.group = new THREE.Group();
    this.panel = new CanvasPlane(W, H, PX);
    this.panel.mesh.position.set(0, 0.5, -0.3); // under the tab (the group is 0.62 m below eye height)
    this.panel.mesh.userData.hit = { hit: () => ({ kind: "page" }) };
    this.group.add(this.panel.mesh);
    this.cams = []; // {id, title, img, ok, busy, stream}
    this.said = "Looking for cameras…";
  }
  targets() { return [this.panel.mesh]; }
  open() {
    this.closed = false;
    this._list();
    this.listTimer = setInterval(() => this._list(), LIST_MS);
    this.picTimer = setInterval(() => this._pictures(), EVERY_MS);
  }
  close() {
    this.closed = true;
    clearInterval(this.listTimer); clearInterval(this.picTimer);
    for (const c of this.cams) this._drop(c);
    this.cams = [];
  }
  _drop(c) { c.img.onload = c.img.onerror = null; c.img.removeAttribute("src"); }

  async _list() {
    let list = null;
    try { list = (await (await fetch("/api/cameras", { cache: "no-store" })).json()).cameras; } catch { /* below */ }
    if (this.closed) return;
    if (!list) { this.said = "The brain didn't answer."; return; }
    const want = list.slice(0, MAX);
    const key = want.map((c) => c.id).join("|");
    if (key === this.key) return;
    this.key = key;
    for (const c of this.cams) this._drop(c);
    this.cams = want.map((c) => {
      const img = new Image();
      const cam = { id: c.id, title: c.title || c.id, img, ok: false, busy: false, stream: c.stream || "" };
      img.onload = () => { cam.ok = true; cam.busy = false; };
      img.onerror = () => { cam.ok = false; cam.busy = false; };
      if (cam.stream) img.src = `${cam.stream}?t=${Date.now()}`; // raspbot1: a stream, drawn as it comes
      return cam;
    });
    this.said = this.cams.length ? "" : "There is no camera plugged in now. A camera shows here a few seconds after you plug it in.";
  }
  _pictures() {
    for (const c of this.cams) {
      if (c.stream || c.busy) continue;
      c.busy = true;
      c.img.src = `/api/camera-feed/${encodeURIComponent(c.id)}?t=${Date.now()}`;
    }
  }

  step() {
    this.group.scale.setScalar(1);
    this.panel.paint((g, w, h) => this._draw(g, w, h)); // every frame: the pictures change
  }
  _draw(g, w, h) {
    const cut = 0.04 * PX;
    g.beginPath(); g.moveTo(cut, 0); g.lineTo(w, 0); g.lineTo(w, h - cut); g.lineTo(w - cut, h); g.lineTo(0, h); g.lineTo(0, cut); g.closePath();
    g.fillStyle = rgba(C.surface, 0.92); g.fill();
    g.strokeStyle = rgba(C.primary, 0.45); g.lineWidth = 3; g.stroke();
    if (!this.cams.length) {
      icon(g, "i-cam", w / 2, h / 2 - 70, 90, C.primary, 1.6);
      g.fillStyle = C.dim; g.textAlign = "center"; g.font = `300 34px ${FONT.lines}`;
      wrapCentre(g, this.said, w / 2, h / 2 + 40, w * 0.7, 44);
      return;
    }
    const n = this.cams.length, cols = n > 1 ? 2 : 1, rows = Math.ceil(n / cols), pad = 24, top = 20;
    const cw = (w - pad * (cols + 1)) / cols, ch = (h - top - pad * (rows + 1)) / rows;
    this.cams.forEach((c, i) => {
      const x = pad + (i % cols) * (cw + pad), y = top + pad + Math.floor(i / cols) * (ch + pad), lh = 40;
      g.fillStyle = C.primary; g.textAlign = "left"; g.font = `500 28px ${FONT.ui}`;
      g.fillText(c.id, x, y + 26, cw);
      const bx = x, by = y + lh, bw = cw, bh = ch - lh;
      g.fillStyle = rgba(C.bg, 0.9); g.fillRect(bx, by, bw, bh);
      g.strokeStyle = rgba(C.line, 1); g.lineWidth = 2; g.strokeRect(bx, by, bw, bh);
      if (c.ok && c.img.naturalWidth) {
        const s = Math.min(bw / c.img.naturalWidth, bh / c.img.naturalHeight), iw = c.img.naturalWidth * s, ih = c.img.naturalHeight * s;
        try { g.drawImage(c.img, bx + (bw - iw) / 2, by + (bh - ih) / 2, iw, ih); } catch { /* not decoded yet */ }
      } else {
        g.fillStyle = C.dim; g.textAlign = "center"; g.font = `300 28px ${FONT.lines}`;
        g.fillText("Opening the camera…", bx + bw / 2, by + bh / 2);
      }
    });
  }
}

function wrapCentre(g, text, x, y, maxW, lh) {
  const words = String(text).split(" ");
  let line = "", yy = y;
  for (const wd of words) {
    const t = line ? `${line} ${wd}` : wd;
    if (g.measureText(t).width > maxW && line) { g.fillText(line, x, yy); line = wd; yy += lh; } else line = t;
  }
  if (line) g.fillText(line, x, yy);
}
