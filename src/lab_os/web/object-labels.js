// Labels on what a camera sees (quick job 128): a thin box around each object the detector finds, and a label
// with its name, how sure it is and, for the object in front of the car, the ultrasonic distance.
// The detector (MediaPipe's ObjectDetector, EfficientDet-Lite0: the 80 COCO kinds such as person, cup, chair,
// bottle) runs in a Web Worker (object-labels-worker.js) on a small copy of the picture, one picture at a time,
// at most every `every` ms. It loads only when the labels are first switched on (the wasm file is 14.6 MB).
//
//   const L = new ObjectLabels();
//   L.setOn(true)              start (loads the detector the first time); false: stop and clear
//   L.feed(source, now)        after the picture is drawn: send a copy when the last answer is back
//   L.found                    [{name, score, box: {x, y, w, h}}], the box as fractions of the picture
//   L.state                    "off" | "loading" | "ready" | "failed"; L.why: the reason it failed
//   drawLabels(g, w, h, L.found, {front, distanceMm, color, bg, font})   on the picture's canvas
//   frontIndex(found, panDeg)  which object the ultrasonic sensor measures, or -1

const SIZE = 320; // the width of the copy the detector sees (EfficientDet-Lite0 takes 320 × 320)
export const FRONT_PAN_DEG = 15; // the ultrasonic sensor looks ahead: only with the camera this near the centre

export class ObjectLabels {
  constructor({ every = 200, minScore = 0.45, max = 6 } = {}) {
    Object.assign(this, { every, minScore, max });
    this.on = false;
    this.state = "off";
    this.why = "";
    this.found = [];
    this.worker = null;
    this.busy = false;
    this.lastT = -Infinity;
    this.onState = null; // (state, why) => {}: tell the person (loading, failed)
  }

  setOn(on) {
    this.on = !!on;
    this.found = [];
    if (!this.on) { if (this.state !== "failed") this.state = "off"; return; }
    if (this.worker) { if (this.state === "off") this.state = "ready"; return; }
    this._set("loading");
    try {
      this.worker = new Worker("/web/object-labels-worker.js", { type: "module" });
    } catch (e) {
      return this._set("failed", String(e?.message || e));
    }
    this.worker.onmessage = (e) => this._message(e.data);
    this.worker.onerror = (e) => { this.busy = false; this._set("failed", e.message || "the detector stopped"); };
    this.worker.postMessage({ type: "load", minScore: this.minScore, max: this.max });
  }

  _set(state, why = "") {
    this.state = state;
    this.why = why;
    this.onState?.(state, why);
  }

  _message(m) {
    if (m.type === "ready") this._set(this.on ? "ready" : "off");
    else if (m.type === "failed") this._set("failed", m.message);
    else if (m.type === "found") {
      this.busy = false;
      if (this.on) this.found = m.found;
      if (m.error) console.warn(`labels: ${m.error}`);
    }
  }

  /** Send a copy of `source` (an image or canvas with the picture) when the detector is free. */
  feed(source, now = performance.now()) {
    if (!this.on || this.state !== "ready" || this.busy || now - this.lastT < this.every) return;
    // the copy keeps the picture's shape: a squashed picture made dogs read as cats
    const sw = source.naturalWidth || source.videoWidth || source.width, sh = source.naturalHeight || source.videoHeight || source.height;
    if (!sw || !sh) return;
    this.small ||= document.createElement("canvas");
    const w = SIZE, h = Math.max(1, Math.round((SIZE * sh) / sw));
    if (this.small.width !== w || this.small.height !== h) Object.assign(this.small, { width: w, height: h });
    try {
      this.small.getContext("2d").drawImage(source, 0, 0, w, h);
    } catch {
      return; // the picture is not decoded yet
    }
    this.busy = true;
    this.lastT = now;
    createImageBitmap(this.small)
      .then((bitmap) => this.worker.postMessage({ type: "frame", bitmap }, [bitmap]))
      .catch(() => { this.busy = false; });
  }

  close() {
    this.worker?.terminate();
    this.worker = null;
    this.on = false;
    this.state = "off";
    this.found = [];
    this.busy = false;
  }
}

/** The object the ultrasonic sensor measures: the biggest box over the picture's middle, while the camera
 * looks ahead (the sensor is fixed on the car's front; the camera turns). -1: none. */
export function frontIndex(found, panDeg) {
  if (!found.length || !(Math.abs(panDeg || 0) <= FRONT_PAN_DEG)) return -1;
  let best = -1, area = 0;
  found.forEach((f, i) => {
    const a = f.box.w * f.box.h;
    if (f.box.x <= 0.5 && f.box.x + f.box.w >= 0.5 && a > area) { best = i; area = a; }
  });
  return best;
}

const nice = (name) => name.charAt(0).toUpperCase() + name.slice(1);

/** The label's words: "Cup   82%", and for the object in front "Cup   82%   34 cm". */
export function labelText(f, distanceMm) {
  const parts = [nice(f.name), `${Math.round(f.score * 100)}%`];
  if (distanceMm != null) parts.push(`${Math.round(distanceMm / 10)} cm`);
  return parts.join("   ");
}

/** Draw the boxes and labels on a canvas `w` × `h` that shows the picture. */
export function drawLabels(g, w, h, found, { front = -1, distanceMm = null, color = "#3ad0ff", bg = "rgba(4,10,14,0.85)", font = "sans-serif" } = {}) {
  const size = Math.max(12, Math.round(h * 0.04)), pad = size * 0.35, line = Math.max(1.5, h / 320);
  g.save();
  g.font = `600 ${size}px ${font}`;
  g.textBaseline = "middle";
  g.textAlign = "left";
  found.forEach((f, i) => {
    const x = f.box.x * w, y = f.box.y * h, bw = f.box.w * w, bh = f.box.h * h;
    g.strokeStyle = color;
    g.lineWidth = line;
    g.strokeRect(x, y, bw, bh);
    const text = labelText(f, i === front ? distanceMm : null);
    const tw = g.measureText(text).width + pad * 2, th = size + pad * 2;
    const lx = Math.min(Math.max(0, x), w - tw), ly = y - th >= 0 ? y - th : Math.min(h - th, y + bh);
    g.fillStyle = bg;
    g.fillRect(lx, ly, tw, th);
    g.fillStyle = color;
    g.fillText(text, lx + pad, ly + th / 2);
  });
  g.restore();
}
