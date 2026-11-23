// Webcam teleop (preview 2): hand landmarks from one camera → the Quest's bare-hands `xr_input`.
// Only plain maths here (no camera, no DOM), so node can test it (tests/test_webcam_teleop.py).
// The page that runs the camera and MediaPipe: webcam.js. Message format: docs/dev/protocol.md.
//
// The same mapping as the Quest's bare hands (xr.js → handsAsController): the right wrist moves the
// gripper, a left pinch is the clutch (or Space held), a right pinch closes the gripper. Sent as the
// "right controller", in the room's frame (+x right, +y up, −z forward), relative mode only (no
// "frame": "arm": the page doesn't know where the real arm is, so 1:1 isn't possible). The hand's
// turn is sent too (quick job 88), so the brain maps it as the Quest's: tilt → wrist_flex,
// roll → wrist_roll.
//
// Safety, on top of the brain's (the dead-man's 250 ms, the clutch, STOP, the limits):
//   - The moving hand out of view (or a jump too big to be real) = tracking lost: the arm holds.
//   - After that the arm stays frozen until the clutch is let go and pinched again, like the brain's
//     own "release the grip" after a freeze. A hand that comes back never moves the arm by itself.
//   - A hand counts only after STEADY_FRAMES frames in a row on its side (quick job 88: a left hand
//     that wasn't there showed for a few seconds; as the clutch hand it could start a move).

// MediaPipe's 21 hand landmarks: the ones used here.
const WRIST = 0, THUMB_TIP = 4, INDEX_MCP = 5, INDEX_TIP = 8, MIDDLE_MCP = 9, PINKY_MCP = 17;
// Palm segments for the hand's distance: the palm is flat, so at least one of them faces the camera.
const PALM = [[WRIST, INDEX_MCP], [WRIST, PINKY_MCP], [INDEX_MCP, PINKY_MCP], [WRIST, MIDDLE_MCP]];

export const DIAG_FOV_DEG = 78; // the Logitech C615's diagonal field of view (most webcams: 70–90)
// Pinch from MediaPipe's world landmarks (metres): tips 5 cm apart = 0, 2 cm (touching) = 1. The
// clutch engages above 0.6 (under 3.2 cm), so a relaxed open hand (its thumb near the index finger)
// doesn't hold it by accident (7 cm gave 72–87 % for open hands on MediaPipe's sample photo).
export const PINCH_OPEN_M = 0.05;
export const PINCH_SHUT_M = 0.02;
export const GRIP_OFF = 0.4; // the brain's clutch lets go below this (mapping.py grip_off)
export const JUMP_M = 0.12; // the wrist moving further than this between two frames isn't a real hand
// The picture is only about 50 cm high at 60 cm from the camera, less than the arm's reach, so the
// hand's moves count 1.5 times (quick job 88: the arm couldn't reach down to the table).
export const REACH = 1.5;
export const STEADY_FRAMES = 5; // about 170 ms at 30 frames a second
const REST = { buttons: { a: false, b: false, thumbstick: false }, thumbstick: [0, 0] };

const clamp01 = (v) => Math.min(1, Math.max(0, v || 0));
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0));

/** Thumb tip to index tip, 0 (apart) … 1 (touching), from world landmarks (metres). */
export function pinchAmount(world) {
  const d = dist(world[THUMB_TIP], world[INDEX_TIP]);
  return clamp01((PINCH_OPEN_M - d) / (PINCH_OPEN_M - PINCH_SHUT_M));
}

/** The camera's focal length in pixels, from its diagonal field of view. */
export function focalPx(width, height, diagFovDeg = DIAG_FOV_DEG) {
  return Math.hypot(width, height) / 2 / Math.tan((diagFovDeg * Math.PI) / 360);
}

/**
 * The wrist in metres, in the room's frame as the person sees it, for a camera that faces them.
 * Left/right and up/down come from where the wrist is in the picture; toward/away from the palm's
 * size in the picture against its real size (MediaPipe's world landmarks): rough, ±a few cm.
 * `image`: normalized landmarks (0..1 of the picture), `world`: metres; the picture is not mirrored.
 */
export function wristPosition(image, world, width, height, { depth = true, diagFovDeg = DIAG_FOV_DEG } = {}) {
  const f = focalPx(width, height, diagFovDeg);
  const px = (p) => ({ x: p.x * width, y: p.y * height });
  // the least foreshortened palm segment: its real length over its length in the picture
  let d = Infinity;
  for (const [a, b] of PALM) {
    const inPicture = dist(px(image[a]), px(image[b]));
    if (inPicture > 1) d = Math.min(d, (f * dist(world[a], world[b])) / inPicture);
  }
  if (!Number.isFinite(d)) return null;
  const z = depth ? d : 0.5; // depth off: a fixed half metre, so the hand moves in a flat plane
  const w = px(image[WRIST]);
  // The camera faces the person: their right is the picture's left, so x flips. Picture y grows down.
  // Toward the camera (smaller d) is the person's forward (−z), so z = d works as it is.
  return [(-(w.x - width / 2) / f) * z, (-(w.y - height / 2) / f) * z, z];
}

/**
 * Which of the person's hands each detection is: MediaPipe's own label. (Its documents say the label
 * assumes a mirrored picture, but on a real webcam's plain picture the label is right: lab check W,
 * 2026-11-21, quick job 88. The opposite label was chosen from a sample photo.) Two hands with the
 * same label: by where they are in the picture instead (the person's right hand is on the picture's
 * left). `swap` flips the result (a mirrored camera, or a camera that shows them the wrong way).
 */
export function sidesOf(hands, swap = false) {
  const flip = (s) => (swap ? (s === "left" ? "right" : "left") : s);
  if (hands.length >= 2 && hands[0].label === hands[1].label) {
    const [a, b] = hands[0].image[WRIST].x <= hands[1].image[WRIST].x ? [0, 1] : [1, 0];
    const out = [];
    out[a] = flip("right");
    out[b] = flip("left");
    return out.concat(hands.slice(2).map(() => null));
  }
  return hands.map((h) => flip(h.label === "Right" ? "right" : "left"));
}

const sub = (a, b) => [a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0)];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const unit = (v) => {
  const n = Math.hypot(...v);
  return n > 1e-9 ? v.map((x) => x / n) : null;
};
// MediaPipe's world axes (the picture's: x right, y down, z away from the camera) → the room's as the
// person sees it, facing the camera: their right is the picture's left (x flips), up is −y, and
// toward the camera is their forward (−z), so z stays. A turn of 180° about z: still a rotation.
const toRoom = (v) => [-v[0], -v[1], v[2]];

/**
 * The hand's two axes in the room: `along` (wrist → middle finger's knuckle) and `across` (index
 * knuckle → little finger's knuckle, at right angles to `along`). From world landmarks (metres).
 */
export function handAxes(world) {
  const along = unit(toRoom(sub(world[MIDDLE_MCP], world[WRIST])));
  const rough = toRoom(sub(world[PINKY_MCP], world[INDEX_MCP]));
  if (!along) return null;
  const normal = unit(cross(along, rough));
  if (!normal) return null;
  return { along, across: cross(normal, along) };
}

/** The hand's turn as a quaternion [x, y, z, w] (the brain uses only its change since the grab). */
export function axesQuat({ along, across }) {
  const a = unit(along), n = unit(cross(a || [0, 0, 0], across)); // smoothing bends them a little:
  if (!a || !n) return null;
  const c = cross(n, a); // at right angles again. Columns of the rotation: c (x), n (y), a (z)
  const [m00, m10, m20] = c, [m01, m11, m21] = n, [m02, m12, m22] = a;
  const tr = m00 + m11 + m22;
  let x, y, z, w;
  if (tr > 0) {
    const k = 0.5 / Math.sqrt(tr + 1);
    [w, x, y, z] = [0.25 / k, (m21 - m12) * k, (m02 - m20) * k, (m10 - m01) * k];
  } else if (m00 > m11 && m00 > m22) {
    const k = 2 * Math.sqrt(1 + m00 - m11 - m22);
    [w, x, y, z] = [(m21 - m12) / k, 0.25 * k, (m01 + m10) / k, (m02 + m20) / k];
  } else if (m11 > m22) {
    const k = 2 * Math.sqrt(1 + m11 - m00 - m22);
    [w, x, y, z] = [(m02 - m20) / k, (m01 + m10) / k, 0.25 * k, (m12 + m21) / k];
  } else {
    const k = 2 * Math.sqrt(1 + m22 - m00 - m11);
    [w, x, y, z] = [(m10 - m01) / k, (m02 + m20) / k, (m12 + m21) / k, 0.25 * k];
  }
  return [x, y, z, w];
}

/** The 1€ filter (Casiez et al. 2012): smooth when the hand is still, little lag when it moves. */
export class OneEuro {
  constructor(minCutoff = 1.0, beta = 2.0, dCutoff = 1.0) {
    Object.assign(this, { minCutoff, beta, dCutoff });
    this.reset();
  }
  reset() {
    this.x = null;
    this.dx = 0;
    this.t = null;
  }
  static alpha(cutoff, dt) {
    const tau = 1 / (2 * Math.PI * cutoff);
    return 1 / (1 + tau / dt);
  }
  /** `t` in seconds. */
  filter(x, t) {
    if (this.x === null || t <= this.t) {
      this.x = x;
      this.t = t;
      return x;
    }
    const dt = t - this.t;
    const dx = (x - this.x) / dt;
    this.dx += OneEuro.alpha(this.dCutoff, dt) * (dx - this.dx);
    const cutoff = this.minCutoff + this.beta * Math.abs(this.dx);
    this.x += OneEuro.alpha(cutoff, dt) * (x - this.x);
    this.t = t;
    return this.x;
  }
}

/**
 * One webcam frame's hands → the `xr_input` message, with the freeze rules above. Keeps the filters
 * and the freeze between frames. `step()` gets the detected hands already as
 * {side: "left"|"right", pos: [x, y, z] metres | null, pinch: 0..1}.
 */
export class WebcamHands {
  constructor() {
    // Stronger smoothing than the 1€ defaults (quick job 88: the 3D arm shook with the hand still),
    // for about the same delay while it moves (~80 ms); toward/away (from the palm's size) is the
    // noisiest, so it gets the most (~110 ms). Checked with simulated noise, not yet on a real hand.
    this.filters = [new OneEuro(0.3, 5, 0.2), new OneEuro(0.3, 5, 0.2), new OneEuro(0.2, 3, 0.2)];
    this.turnFilters = Array.from({ length: 6 }, () => new OneEuro(0.3, 1, 0.2));
    this.pinchFilter = new OneEuro(3.0, 0.0);
    this.steady = { left: 0, right: 0 }; // frames in a row each side was seen
    this.last = null; // the moving hand's last position (filtered) and time
    this.held = false; // frozen until the clutch is let go
    this.trigger = 0;
    this.why = "";
  }
  _lost(why, clutch) {
    this.last = null;
    this.filters.forEach((f) => f.reset());
    this.turnFilters.forEach((f) => f.reset());
    this.pinchFilter.reset();
    // a lost hand with the clutch let go needs nothing: the next pinch starts cleanly
    if (clutch >= GRIP_OFF) {
      this.held = true;
      this.why = why;
    }
  }
  /**
   * @param {{side: string, pos: number[]|null, pinch: number, axes?: object|null}[]} hands this
   *   frame's hands (`axes`: handAxes(); without them the wrist's turn holds)
   * @param {number} t seconds
   * @param {boolean} space Space held (the keyboard clutch)
   * @returns {{msg: object, state: string, clutch: number, trigger: number}}
   */
  step(hands, t, space = false) {
    for (const side of ["left", "right"]) {
      this.steady[side] = hands.some((h) => h.side === side && h.pos) ? this.steady[side] + 1 : 0;
    }
    const ok = (side) => this.steady[side] >= STEADY_FRAMES;
    const right = ok("right") ? hands.find((h) => h.side === "right" && h.pos) : undefined;
    const left = ok("left") ? hands.find((h) => h.side === "left") : undefined;
    const clutch = Math.max(left ? left.pinch : 0, space ? 1 : 0);
    let pos = null;
    let quat = null;
    if (!right) {
      this._lost("your right hand left the picture", clutch);
    } else {
      const raw = right.pos;
      if (this.last && t - this.last.t < 0.25 && Math.hypot(...raw.map((v, i) => v - this.last.raw[i])) > JUMP_M) {
        this._lost("the hand tracking jumped", clutch);
      } else {
        pos = raw.map((v, i) => this.filters[i].filter(v, t) * REACH);
        this.last = { raw, t };
        if (right.axes) {
          const v = [...right.axes.along, ...right.axes.across].map((x, i) => this.turnFilters[i].filter(x, t));
          quat = axesQuat({ along: v.slice(0, 3), across: v.slice(3) });
        }
        this.trigger = clamp01(this.pinchFilter.filter(right.pinch, t));
      }
    }
    if (this.held && clutch < GRIP_OFF) {
      this.held = false;
      this.why = "";
    }
    const grip = this.held || !pos ? 0 : clutch;
    const state = this.held ? "frozen" : !pos ? "no hand" : grip > 0.6 ? "following" : "holding";
    // no turn measured: a fixed one, so the wrist holds its angle
    const c = { pos, quat: pos ? quat || [0, 0, 0, 1] : null, trigger: this.trigger, grip, ...REST };
    return {
      msg: { type: "xr_input", t: t * 1000, source: "webcam", hands: { right: c } },
      state,
      clutch,
      trigger: this.trigger,
    };
  }
}
