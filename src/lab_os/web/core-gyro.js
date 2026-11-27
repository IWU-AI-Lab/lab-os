// The 3D core (quick job 159, a first version): each ring of the assistant's core is tilted on its own axis,
// like a gyroscope, and the axis turns slowly. The state shows in the shape: listening lines every ring up flat
// (focused), thinking tilts them further and turns them fast, speaking moves them with the voice. Each persona
// has its own ring set (its tilts and turns). The hub (design.html, an SVG core) and the VR hub (xr/core.js,
// three.js) both use it; minimal keeps a flat core.

const RINGS = ["bars", "cross", "ticks", "seg", "sat", "arcs", "tri", "thin"];

// per ring: [tilt (degrees), the axis's start angle (degrees), how fast the axis turns (degrees a second)]
const SETS = {
  // the Lab Assistant: calm, small tilts, slow turns, all one way
  "lab-assistant": { bars: [8, 0, 4], cross: [16, 40, 5], ticks: [14, 200, 6], seg: [28, 90, 8], sat: [38, 300, 11], arcs: [32, 150, 9], tri: [22, 250, 7], thin: [42, 20, 12] },
  // J.A.R.V.I.S.: a bold gyroscope, larger tilts, the rings turning against each other
  jarvis: { bars: [10, 0, -6], cross: [24, 60, 9], ticks: [18, 180, -8], seg: [34, 90, 13], sat: [48, 270, -17], arcs: [40, 135, 15], tri: [28, 225, -11], thin: [55, 315, 19] },
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
  RINGS.forEach((id, i) => { out[id] = [8 + r() * 36, r() * 360, (5 + r() * 12) * (i % 2 ? -1 : 1)]; });
  return out;
}

// per state: how far the rings tilt (1 = the set's tilts) and how fast their axes turn
const STATES = {
  idle: { k: 1, turn: 1 },
  listening: { k: 0, turn: 0.3 },   // lined up flat: it focuses on you
  thinking: { k: 1.35, turn: 4 },   // tilted further, turning fast
  speaking: { k: 0.55, turn: 1.6 }, // plus the voice's loudness (step)
  offline: { k: 1, turn: 0 },
  error: { k: 1, turn: 0 },
};

export class Gyro {
  constructor(personaId = "") { this.k = 1; this.turn = 1; this.setPersona(personaId); }
  setPersona(id) {
    if (id === this.persona) return;
    this.persona = id; this.set = ringSet(id);
    this.phi = Object.fromEntries(RINGS.map((r) => [r, this.set[r][1]]));
  }
  /** Advance by dt seconds. loud: 0..1 while speaking. */
  step(dt, state, loud = 0) {
    const s = STATES[state] || STATES.idle;
    const k = s.k + (state === "speaking" ? loud * 0.7 : 0);
    this.k += (k - this.k) * Math.min(1, dt * (state === "listening" ? 5 : 2.5));
    this.turn += (s.turn - this.turn) * Math.min(1, dt * 2);
    for (const r of RINGS) this.phi[r] = (this.phi[r] + this.set[r][2] * this.turn * dt) % 360;
  }
  /** A ring's tilt and its axis's angle, in radians (null: a ring the set doesn't tilt). */
  of(id) {
    const t = this.set[id];
    if (!t) return null;
    return { tilt: (t[0] * this.k * Math.PI) / 180, phi: (this.phi[id] * Math.PI) / 180 };
  }
  /** The SVG transform that shows a ring tilted (a circle seen tilted is an ellipse). */
  svg(id) {
    const g = this.of(id);
    if (!g) return "";
    const deg = (g.phi * 180) / Math.PI;
    return `rotate(${deg.toFixed(2)}) scale(1 ${Math.cos(g.tilt).toFixed(4)}) rotate(${(-deg).toFixed(2)}) `;
  }
}
