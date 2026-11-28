// Labels on what a camera sees (quick job 128): a thin box around each object the brain's detector finds,
// and a label with its name, how sure it is and, for the object in front of the car, the ultrasonic distance.
// The detector runs on the brain (lab_os/object_labels.py: YOLOE, the words in config/labels.yaml); a page
// sends {"type": "labels", "on": true} on /ws/raspbot and gets {"type": "labels", "found": [...]} back.
//
//   found                      [{name, score, box: {x, y, w, h}}], the box as fractions of the picture
//   drawLabels(g, w, h, found, {front, distanceMm, color, bg, font})   on the picture's canvas
//   frontIndex(found, panDeg)  which object the ultrasonic sensor measures, or -1
//   labelsSwitch({button, canvas, img, say, send, status})   a page's Labels button (the Raspbot Control page, Monitor)
//
// The labels look like a HUD: corner brackets on a thin light outline around each object, the design's UI font (Chakra Petch), the
// name in capitals, letters spaced out.

export const FRONT_PAN_DEG = 15; // the ultrasonic sensor looks ahead: only with the camera this near the centre

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

export const HUD_FONT = "'Chakra Petch', system-ui, sans-serif"; // the design's UI font (theme.yaml → fonts.family)

/** "#rrggbb" and a see-through amount (0–1) → "rgba(…)". The colours: config/theme.yaml → labels. */
export function seeThrough(hex, a) {
  const n = parseInt(String(hex).replace("#", ""), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
// the theme's numbers, used when a page passes none (config/theme.yaml → labels, colors.primary)
const LOOK = { color: "#29d4ff", bg: seeThrough("#05080b", 0.85), border: seeThrough("#ffffff", 0.45) };

/** Draw the outlines, corner brackets and labels on a canvas `w` × `h` that shows the picture. */
export function drawLabels(g, w, h, found, { front = -1, distanceMm = null, color = LOOK.color, bg = LOOK.bg, font = HUD_FONT, border = LOOK.border } = {}) {
  const size = Math.max(12, Math.round(h * 0.04)), pad = size * 0.4, line = Math.max(1.5, h / 320);
  g.save();
  g.font = `600 ${size}px ${font}`;
  if ("letterSpacing" in g) g.letterSpacing = `${(size * 0.1).toFixed(1)}px`;
  g.textBaseline = "middle";
  g.textAlign = "left";
  found.forEach((f, i) => {
    const x = f.box.x * w, y = f.box.y * h, bw = f.box.w * w, bh = f.box.h * h;
    g.strokeStyle = border; // a thin light outline of the whole object, so the box reads on any picture
    g.lineWidth = Math.max(1, line * 0.6);
    g.strokeRect(x, y, bw, bh);
    g.strokeStyle = color;
    g.lineWidth = line;
    g.lineCap = "square";
    const c = Math.min(bw / 2, bh / 2, Math.max(size * 0.7, Math.min(bw, bh) * 0.22)); // the brackets' arm
    g.beginPath(); // a HUD's corner brackets, not a full box
    for (const [cx, cy, dx, dy] of [[x, y, 1, 1], [x + bw, y, -1, 1], [x, y + bh, 1, -1], [x + bw, y + bh, -1, -1]]) {
      g.moveTo(cx, cy + dy * c);
      g.lineTo(cx, cy);
      g.lineTo(cx + dx * c, cy);
    }
    g.stroke();
    const text = labelText({ ...f, name: f.name.toUpperCase() }, i === front ? distanceMm : null);
    const tw = g.measureText(text).width + pad * 2, th = size + pad * 2;
    const lx = Math.min(Math.max(0, x), w - tw), ly = y - th >= 0 ? y - th : Math.min(h - th, y + bh);
    g.fillStyle = bg;
    g.fillRect(lx, ly, tw, th);
    g.fillStyle = color;
    g.fillText(text, lx + pad, ly + th / 2);
  });
  g.restore();
}

/** A page's Labels button over a camera picture (an <img> under a <canvas> of the same place, object-fit:
 * contain). `send(msg)` goes to /ws/raspbot; `say(text)` tells the person; `status()` is the newest
 * raspbot_status (for the pan and the distance). Returns {message(m), reconnect()}: give it each
 * {"type": "labels"} message, and call reconnect() when the socket opens again. */
export function labelsSwitch({ button, canvas, img, say, send, status, oldMs = 1000 }) {
  const L = { on: false, found: [], t: 0, state: "", why: "" };
  const css = getComputedStyle(document.documentElement);
  const color = css.getPropertyValue("--primary").trim() || LOOK.color;
  const font = css.getPropertyValue("--f-ui").trim() || HUD_FONT;
  let look = { bg: LOOK.bg, border: LOOK.border };
  import("/web/theme.js").then(({ theme }) => {  // config/theme.yaml → labels
    const t = theme.labels || {};
    if (t.background) look.bg = seeThrough(t.background, t.background_opacity ?? 0.85);
    if (t.border) look.border = seeThrough(t.border, t.border_opacity ?? 0.45);
  }).catch(() => { /* the numbers above */ });
  function paint() {
    const r = canvas.getBoundingClientRect(), k = devicePixelRatio || 1;
    const w = Math.round(r.width * k), h = Math.round(r.height * k);
    if (canvas.width !== w || canvas.height !== h) Object.assign(canvas, { width: w, height: h });
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, w, h);
    const fresh = performance.now() - L.t < oldMs;
    if (!L.on || !fresh || img.hidden || !img.naturalWidth || !L.found.length) return;
    const fit = Math.min(w / img.naturalWidth, h / img.naturalHeight); // the picture's place (object-fit: contain)
    const pw = img.naturalWidth * fit, ph = img.naturalHeight * fit, s = status();
    g.save();
    g.translate((w - pw) / 2, (h - ph) / 2);
    drawLabels(g, pw, ph, L.found, {
      front: frontIndex(L.found, s?.pan_deg), distanceMm: s?.distance_mm ?? null,
      color, bg: look.bg, border: look.border, font,
    });
    g.restore();
  }
  function set(on) {
    Object.assign(L, { on, found: [], t: 0, state: "", why: "" });
    send({ type: "labels", on });
    button.setAttribute("aria-pressed", String(on));
    button.textContent = on ? "Labels on" : "Labels off";
    if (!on) say("Labels off.");
    paint();
  }
  button.onclick = () => set(!L.on);
  setInterval(paint, 250); // old boxes go away when no new ones come
  addEventListener("resize", paint);
  return {
    message(m) {
      if (!L.on) return;
      Object.assign(L, { found: m.found || [], t: performance.now() });
      if (m.state !== L.state || m.why !== L.why) {
        Object.assign(L, { state: m.state, why: m.why });
        say(m.state === "loading" ? "Loading the object detector…" : m.state === "failed" ? `No labels: ${m.why}` : m.why || "Labels on.");
      }
      paint();
    },
    reconnect() { if (L.on) send({ type: "labels", on: true }); },
  };
}
