// Webcam teleop (preview 2): hand landmarks from one camera → the Quest's bare-hands `xr_input`.
// Only plain maths here (no camera, no DOM), so node can test it (tests/test_webcam_teleop.py).
// The page that runs the camera and MediaPipe: webcam.js. Message format: docs/dev/protocol.md.
//
// The same mapping as the Quest's bare hands (xr.js → handsAsController): the right wrist moves the
// gripper, a left pinch is the clutch (or Space held), a right pinch closes the gripper. Sent as the
// "right controller", in the room's frame (+x right, +y up, −z forward), relative mode only (no
// "frame": "arm": the page doesn't know where the real arm is, so 1:1 isn't possible). The hand's
// turn is sent too (quick job 88), so the brain maps it as the Quest's: tilt → wrist_flex,
// roll → wrist_roll. The message asks the brain to turn the gripper about the wrist ("pivot":
// "wrist", quick job 120): a turn of the hand moves only the wrist, not the whole arm.
//
// Safety, on top of the brain's (the dead-man's 250 ms, the clutch, STOP, the limits):
//   - The moving hand out of view (or a jump too big to be real) = tracking lost: the arm holds.
//   - After that the arm stays frozen until the clutch is let go and pinched again, like the brain's
//     own "release the grip" after a freeze. A hand that comes back never moves the arm by itself.
//   - A hand counts only after STEADY_FRAMES frames in a row on its side (quick job 88: a left hand
//     that wasn't there showed for a few seconds; as the clutch hand it could start a move).

// MediaPipe's 21 hand landmarks: the ones used here.
const WRIST = 0, THUMB_TIP = 4, INDEX_MCP = 5, INDEX_TIP = 8, MIDDLE_MCP = 9, PINKY_MCP = 17;
const FINGER_TIPS = [8, 12, 16, 20]; // index, middle, ring, little

export const DIAG_FOV_DEG = 78; // the Logitech C615's diagonal field of view (most webcams: 70–90)
// Pinch from MediaPipe's world landmarks (metres): tips 5 cm apart = 0, 2 cm (touching) = 1. The
// clutch engages above 0.6 (under 3.2 cm), so a relaxed open hand (its thumb near the index finger)
// doesn't hold it by accident (7 cm gave 72–87 % for open hands on MediaPipe's sample photo).
export const PINCH_OPEN_M = 0.05;
export const PINCH_SHUT_M = 0.02;
export const GRIP_OFF = 0.4; // the brain's clutch lets go below this (mapping.py grip_off)
export const JUMP_M = 0.12; // the wrist moving further than this between two frames isn't a real hand
// How much the hand's moves count. Quick job 88 made it 1.5 (the arm couldn't reach the table); quick
// job 120: much too sensitive, most of all toward and away (the least sure of the three). To go
// further, grab again (the page says so).
export const REACH = 0.8; // left/right and up/down
export const REACH_DEPTH = 0.4; // toward and away from the camera
// The gripper (quick job 120: it didn't stay closed with the hand closed). It closes above
// GRIP_SHUT and stays fully closed until the hand opens below GRIP_OPEN; a fist counts as closed.
export const GRIP_SHUT = 0.6;
export const GRIP_OPEN = 0.25;
export const STEADY_FRAMES = 5; // about 170 ms at 30 frames a second
const REST = { buttons: { a: false, b: false, thumbstick: false }, thumbstick: [0, 0] };

const clamp01 = (v) => Math.min(1, Math.max(0, v || 0));
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0));

/** Thumb tip to index tip, 0 (apart) … 1 (touching), from world landmarks (metres). */
export function pinchAmount(world) {
  const d = dist(world[THUMB_TIP], world[INDEX_TIP]);
  return clamp01((PINCH_OPEN_M - d) / (PINCH_OPEN_M - PINCH_SHUT_M));
}

/**
 * How closed the hand is, 0 (open) … 1 (a fist): the finger tips' distance from the wrist against
 * the palm's length (wrist → middle knuckle). Open: about 2 palms; a fist: about 1.
 */
export function fistAmount(world) {
  const palm = dist(world[WRIST], world[MIDDLE_MCP]);
  if (!(palm > 1e-4)) return 0;
  const reach = FINGER_TIPS.reduce((s, k) => s + dist(world[k], world[WRIST]), 0) / FINGER_TIPS.length / palm;
  return clamp01((1.6 - reach) / (1.6 - 1.15));
}

/** The right hand's gripper amount: a pinch or a fist, whichever is more closed. */
export const gripAmount = (world) => Math.max(pinchAmount(world), fistAmount(world));

/** The camera's focal length in pixels, from its diagonal field of view. */
export function focalPx(width, height, diagFovDeg = DIAG_FOV_DEG) {
  return Math.hypot(width, height) / 2 / Math.tan((diagFovDeg * Math.PI) / 360);
}

/**
 * The wrist in metres, in the room's frame as the person sees it, for a camera that faces them.
 * Left/right and up/down come from where the wrist is in the picture; toward/away from the hand's
 * size in the picture against its real size (MediaPipe's world landmarks): rough, ±a few cm.
 * `image`: normalized landmarks (0..1 of the picture), `world`: metres; the picture is not mirrored.
 *
 * The distance: the hand's 3D shape (MediaPipe's world landmarks, in metres, with the camera's
 * axes) is placed where the camera sees it, by least squares over all 21 landmarks (each landmark's
 * picture point = the camera's projection of its 3D point; the unknowns are where the hand is).
 * A turn of the hand turns its 3D shape the same way, so the wrist's distance stays (quick job 120:
 * before, a few palm lines gave it, and a turn of the hand moved the arm).
 */
export function wristPosition(image, world, width, height, { depth = true, diagFovDeg = DIAG_FOV_DEG } = {}) {
  const f = focalPx(width, height, diagFovDeg);
  // Each landmark k (picture point u, v from the middle; 3D point X, Y, Z) gives two lines of
  // f·Tx − u·Tz = u·Z − f·X and f·Ty − v·Tz = v·Z − f·Y, with T where the hand's 3D origin is.
  const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], b = [0, 0, 0];
  const add = (row, rhs) => {
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) A[i][j] += row[i] * row[j];
      b[i] += row[i] * rhs;
    }
  };
  const n = Math.min(image.length, world.length);
  for (let k = 0; k < n; k++) {
    const u = image[k].x * width - width / 2, v = image[k].y * height - height / 2;
    const { x, y, z } = world[k];
    add([f, 0, -u], u * (z || 0) - f * x);
    add([0, f, -v], v * (z || 0) - f * y);
  }
  const T = solve3(A, b);
  if (!T || !(T[2] > 0.05)) return null; // no sure answer (a hand drawn under a few pixels)
  const wr = world[WRIST];
  const cam = [T[0] + wr.x, T[1] + wr.y, T[2] + (wr.z || 0)]; // the wrist, x right, y down, z away
  // The camera faces the person: their right is the picture's left, so x flips. Picture y grows
  // down. Toward the camera (smaller z) is the person's forward (−z), so z works as it is. Depth
  // off: a fixed half metre, so the hand moves in a flat plane.
  const z = depth ? cam[2] : 0.5;
  return [(-cam[0] / cam[2]) * z, (-cam[1] / cam[2]) * z, z];
}

/** Solve A·x = b for a 3×3 A (Cramer's rule); null when A is (nearly) singular. */
function solve3(A, b) {
  const det = (m) =>
    m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
    m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
    m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const d = det(A);
  if (!(Math.abs(d) > 1e-9 * Math.abs(A[0][0] * A[1][1] * A[2][2]))) return null;
  return [0, 1, 2].map((c) => det(A.map((row, i) => row.map((v, j) => (j === c ? b[i] : v)))) / d);
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
    this.filters = [new OneEuro(0.3, 5, 0.2), new OneEuro(0.3, 5, 0.2), new OneEuro(0.15, 2, 0.2)];
    this.turnFilters = Array.from({ length: 6 }, () => new OneEuro(0.3, 1, 0.2));
    this.pinchFilter = new OneEuro(3.0, 0.0);
    this.steady = { left: 0, right: 0 }; // frames in a row each side was seen
    this.last = null; // the moving hand's last position (filtered) and time
    this.held = false; // frozen until the clutch is let go
    this.trigger = 0;
    this.shut = false; // the gripper is held closed (GRIP_SHUT … GRIP_OPEN)
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
   *   frame's hands (`pinch`: pinchAmount() for the left hand, gripAmount() for the right; `axes`:
   *   handAxes(); without them the wrist's turn holds)
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
        pos = raw.map((v, i) => this.filters[i].filter(v, t) * (i === 2 ? REACH_DEPTH : REACH));
        this.last = { raw, t };
        if (right.axes) {
          const v = [...right.axes.along, ...right.axes.across].map((x, i) => this.turnFilters[i].filter(x, t));
          quat = axesQuat({ along: v.slice(0, 3), across: v.slice(3) });
        }
        const amount = clamp01(this.pinchFilter.filter(right.pinch, t));
        if (amount >= GRIP_SHUT) this.shut = true;
        else if (amount < GRIP_OPEN) this.shut = false;
        this.trigger = this.shut ? 1 : amount;
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
      msg: { type: "xr_input", t: t * 1000, source: "webcam", pivot: "wrist", hands: { right: c } },
      state,
      clutch,
      trigger: this.trigger,
    };
  }
}
