// The 3D core as an armillary sphere (quick job 159, remade in quick job 160 after the builder's references in
// docs/design/references/: armillary_sphere.jpg, jarvis_sphere1.jpeg, jarvis_sphere2.jpg).
// Every ring is a circle in 3D on a gimbal: it turns about its own axis, and that axis is fixed to its parent
// ring, so the inner rings tumble with the outer ones and cross through the middle. Some rings also sit at a
// fixed slant in their gimbal (like the armillary's wide band). The state shows in the motion: listening lines
// every ring up flat (it focuses on you), thinking turns them fast, speaking moves them with the voice.
// Each persona has its own set. The hub (design.html, SVG with perspective) and the VR hub (xr/core.js,
// three.js) both use it; minimal keeps a flat core.
//
// Coordinates: x right, y up, z toward the viewer; a ring lies in its own x–y plane before it turns.

export const RINGS = ["bars", "cross", "ticks", "merid", "band", "seg", "sat", "arcs", "tri", "thin"];

// per ring: p = the parent ring (its gimbal turns with it), ax = the axis it turns about (in the parent's frame),
// v = degrees a second (or with amp: a swing of ±amp degrees, v = swings a minute), ph = the start angle,
// slant = [the direction in its plane (degrees), how far (degrees)]: a fixed slant inside its gimbal
const SETS = {
  // the Lab Assistant: calm; the outer rings stay near the front, the inner ones turn slowly, all one way
  "lab-assistant": {
    bars: { ax: [0, 1, 0], amp: 10, v: 2, ph: 0 },
    cross: { p: "bars", ax: [1, 0, 0], amp: 6, v: 3, ph: 90 },
    ticks: { ax: [0, 1, 0], v: 9, ph: 35 },
    merid: { ax: [1, 0, 0], v: -6, ph: 200 },
    band: { p: "merid", ax: [0, 1, 0], v: 5, ph: 60, slant: [0, 24] },
    seg: { p: "ticks", ax: [1, 0, 0], v: 13, ph: 120 },
    sat: { p: "seg", ax: [0, 1, 0], v: -17, ph: 10, slant: [90, 20] },
    arcs: { ax: [0.7, 0.7, 0], v: 21, ph: 300 },
    tri: { p: "sat", ax: [1, 0, 0], v: 0, ph: 0, slant: [45, 12] },
    thin: { p: "seg", ax: [0.4, 0.9, 0], v: 11, ph: 250 },
  },
  // J.A.R.V.I.S.: a bold gyroscope; larger slants, faster, the rings turning against each other
  jarvis: {
    bars: { ax: [0.2, 1, 0], amp: 14, v: 3, ph: 0 },
    cross: { p: "bars", ax: [1, 0, 0], amp: 10, v: 4, ph: 70 },
    ticks: { ax: [0, 1, 0.15], v: -13, ph: 20 },
    merid: { ax: [1, 0.25, 0], v: 9, ph: 160 },
    band: { p: "ticks", ax: [0, 1, 0], v: -8, ph: 30, slant: [20, 32] },
    seg: { p: "merid", ax: [0, 1, 0], v: 18, ph: 90 },
    sat: { p: "seg", ax: [1, 0, 0], v: -25, ph: 300, slant: [120, 28] },
    arcs: { ax: [0.5, 0.85, 0.2], v: -27, ph: 45 },
    tri: { p: "sat", ax: [0, 1, 0], v: 15, ph: 0, slant: [0, 18] },
    thin: { p: "arcs", ax: [1, 0, 0], v: 22, ph: 200 },
  },
};

function hash(s) {
  let h = 2166136261;
  for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0) / 4294967296);
}

/** The ring set of a persona: its own, or one made from its id (the same every time). */
export function ringSet(personaId = "") {
  if (SETS[personaId]) return SETS[personaId];
  const r = hash(personaId || "default"), out = {};
  const unit = () => { const a = r() * Math.PI * 2; return [Math.cos(a), Math.sin(a), (r() - 0.5) * 0.4]; };
  RINGS.forEach((id, i) => {
    if (i < 2) out[id] = { ...(i ? { p: "bars" } : {}), ax: [0, 1, 0], amp: 6 + r() * 8, v: 2 + r() * 2, ph: r() * 360 };
    else out[id] = { ...(i > 4 && r() < 0.6 ? { p: RINGS[2 + Math.floor(r() * (i - 2))] } : {}), ax: unit(),
      v: (6 + r() * 16) * (i % 2 ? -1 : 1), ph: r() * 360, ...(r() < 0.4 ? { slant: [r() * 360, 10 + r() * 25] } : {}) };
  });
  return out;
}

// ---------- quaternions [x, y, z, w] ----------
export function qAxis(ax, deg) {
  const n = Math.hypot(ax[0], ax[1], ax[2]) || 1, h = (deg * Math.PI) / 360, s = Math.sin(h) / n;
  return [ax[0] * s, ax[1] * s, ax[2] * s, Math.cos(h)];
}
export function qMul(a, b) {
  return [
    a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
    a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
    a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
  ];
}
/** From no turn (t = 0) to q (t = 1), the short way. */
function qToward(q, t) {
  const w = Math.min(1, Math.abs(q[3])), sg = q[3] < 0 ? -1 : 1, th = Math.acos(w);
  if (th < 1e-5) return [0, 0, 0, 1];
  const a = Math.sin((1 - t) * th) / Math.sin(th), b = (Math.sin(t * th) / Math.sin(th)) * sg;
  return [q[0] * b, q[1] * b, q[2] * b, a + q[3] * b];
}
/** The rotation as 3 rows of 3. */
export function qMat([x, y, z, w]) {
  return [
    1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
    2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
    2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y),
  ];
}

// per state: how far the rings turn away from flat (1 = the set's) and how fast the gimbals turn
const STATES = {
  idle: { k: 1, turn: 1 },
  listening: { k: 0, turn: 0.3 },   // lined up flat: it focuses on you
  thinking: { k: 1, turn: 4 },      // the gimbals turn fast
  speaking: { k: 0.75, turn: 1.6 }, // plus the voice's loudness (step)
  offline: { k: 1, turn: 0 },
  error: { k: 1, turn: 0 },
};

export class Gyro {
  constructor(personaId = "") { this.k = 1; this.turn = 1; this.t = 0; this.persona = null; this.setPersona(personaId); }
  setPersona(id) {
    if (id === this.persona) return;
    this.persona = id; this.set = ringSet(id);
    this.ang = Object.fromEntries(RINGS.map((r) => [r, this.set[r]?.ph || 0]));
    this.q = {};
    this._pose();
  }
  /** Advance by dt seconds. loud: 0..1 while speaking. */
  step(dt, state, loud = 0) {
    const s = STATES[state] || STATES.idle;
    const k = s.k + (state === "speaking" ? loud * 0.5 : 0);
    this.k += (k - this.k) * Math.min(1, dt * (state === "listening" ? 5 : 2.5));
    this.turn += (s.turn - this.turn) * Math.min(1, dt * 2);
    this.t += dt * this.turn;
    for (const r of RINGS) {
      const g = this.set[r];
      if (!g) continue;
      this.ang[r] = g.amp ? g.ph + g.amp * Math.sin((this.t * g.v * Math.PI * 2) / 60) : (this.ang[r] + g.v * this.turn * dt) % 360;
    }
    this._pose();
  }
  _pose() {
    const full = {};
    const of = (r) => {
      if (full[r]) return full[r];
      const g = this.set[r];
      if (!g) return [0, 0, 0, 1];
      let q = qAxis(g.ax, this.ang[r]);
      if (g.p && g.p !== r) q = qMul(of(g.p), q);
      if (g.slant) {
        const d = (g.slant[0] * Math.PI) / 180;
        q = qMul(q, qAxis([Math.cos(d), Math.sin(d), 0], g.slant[1]));
      }
      return (full[r] = q);
    };
    for (const r of RINGS) this.q[r] = this.set[r] ? qToward(of(r), Math.max(0, this.k)) : null;
  }
  /** A ring's turn as a quaternion [x, y, z, w] (null: a ring the set doesn't turn). */
  quat(id) { return this.q[id] || null; }
  /** A ring's turn as 3 rows of 3, with its own spin in its plane (degrees, counterclockwise) after it. */
  mat(id, spin = 0) {
    const q = this.q[id];
    if (!q) return null;
    return qMat(spin ? qMul(q, qAxis([0, 0, 1], spin)) : q);
  }
}
