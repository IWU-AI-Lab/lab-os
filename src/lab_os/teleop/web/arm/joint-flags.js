// The joint readout's notes for one joint (quick job 24). Kept apart from the page so a test can
// run it (tests/test_joint_flags.py, with node).
//
// "outside" is judged against the limit actually in force: the driver's own limits from `status`
// (the URDF narrowed by the arm's calibration), at the angle the driver really holds. Before, it
// used the 3D model's limits and the command: a command of 97.4° that the driver held at its limit
// of 96.8° read "clamped by driver → 96.8°; outside model limits" though the arm was inside
// (lab check 8.9). The model's limits are only used when the driver hasn't sent its own.

const SLACK = 0.05; // degrees: the same slack as "clamped"

/**
 * @param {number} cmd       the commanded angle (what the readout shows)
 * @param {number|undefined} drv  the driver's angle reported with the same command
 * @param {[number, number]|undefined} limit  the driver's limit in force [low, high]
 * @param {{outOfModel: boolean, unknown: boolean}} model  what the 3D model said
 * @returns {string[]}
 */
export function jointFlags(cmd, drv, limit, model = { outOfModel: false, unknown: false }) {
  const flags = [];
  if (drv !== undefined && Math.abs(drv - cmd) > SLACK) flags.push(`clamped by driver → ${drv.toFixed(1)}°`);
  const held = drv ?? cmd;
  if (limit) {
    const [lo, hi] = limit;
    if (held < lo - SLACK || held > hi + SLACK) flags.push(`outside the arm's limits (${lo.toFixed(1)}…${hi.toFixed(1)}°)`);
  } else if (model.outOfModel) {
    flags.push("outside model limits");
  }
  if (model.unknown) flags.push("not in this model");
  return flags;
}
