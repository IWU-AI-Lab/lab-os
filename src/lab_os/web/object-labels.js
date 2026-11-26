// Labels on what a camera sees (quick job 128): a thin box around each object the brain's detector finds,
// and a label with its name, how sure it is and, for the object in front of the car, the ultrasonic distance.
// The detector runs on the brain (lab_os/object_labels.py: YOLOE, the words in config/labels.yaml); a page
// sends {"type": "labels", "on": true} on /ws/raspbot and gets {"type": "labels", "found": [...]} back.
//
//   found                      [{name, score, box: {x, y, w, h}}], the box as fractions of the picture
//   drawLabels(g, w, h, found, {front, distanceMm, color, bg, font})   on the picture's canvas
//   frontIndex(found, panDeg)  which object the ultrasonic sensor measures, or -1

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
