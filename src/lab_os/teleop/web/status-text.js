// What the headset's teleop status panel says (xr-scene.js draws it; quick job 37): the state and how
// serious it is, the gripper's opening, the speed, and the hint. No imports, so tests run it with node.
//   level: normal (cyan) | following (green) | warning (amber) | held (rust, pause icon) | offline (gray)
// Plain words, no dot separators (docs/design/DESIGN.md → "Don't").

// Two arms at once (status.left_arm, preview 3): `left` is the left arm's {state, level}, and `state`
// says "Right …"; the panel draws the left one on the left. Bare hands drive only the right arm.

/** The left arm's state (two arms at once), from status.left_arm. */
function leftText(l) {
  return l.connected === false ? ["Left disconnected", "offline"]
    : l.frozen ? [l.needs_release ? "Left frozen: let go" : "Left frozen", "held"]
    : l.clutch ? ["Left following", "following"]
    : ["Left holding", "normal"];
}

/** From the teleop status (an ArmFeed): {state, level, gripper (% open or null), speed, hint: [parts],
 * left: {state, level} or null}. */
export function panelText(feed, noController, source) {
  const one = oneArmText(feed, noController, source);
  const l = feed?.status?.left_arm;
  if (!l || noController) return { ...one, left: null };
  const [state, level] = leftText(l);
  const hands = source === "hands";
  const oneToOne = feed.status.mode === "one_to_one";
  const hint = hands ? ["Two arms: controllers only", "now: right arm", "left pinch = move"]
    : oneToOne ? ["Right 1:1: hand in the ball", "left relative", "A/X = stop both"]
      : ["Each hand drives its arm", "grip = move", "trigger = gripper", "A/X = stop both"];
  const right = one.state.replace(/^Frozen: let go of the (grip|pinch)$/, "Frozen: let go");
  return { ...one, state: `Right ${right.charAt(0).toLowerCase()}${right.slice(1)}`, hint, left: { state, level } };
}

function oneArmText(feed, noController, source) {
  const s = feed?.status, hands = source === "hands";
  const [state, level] = noController ? [hands ? "No right hand" : "No controller", "warning"]
    : !s ? ["Connecting…", "offline"]
    : s.arm?.connected === false ? ["Arm disconnected", "offline"]
    : feed.frozen ? [s.needs_release ? `Frozen: let go of the ${hands ? "pinch" : "grip"}` : "Frozen", "held"]
    : s.clutch && s.one_to_one && s.servos?.hot ? ["1:1 slowed: servos warm", "warning"]
    : s.clutch ? [s.one_to_one ? "Following 1:1" : "Following", "following"]
    : s.mode === "one_to_one" && s.hand_gap_cm != null && s.hand_gap_cm > s.capture_cm
      ? [`Reach the gripper: ${Math.round(s.hand_gap_cm)} cm`, "normal"]
      : ["Holding", "normal"];
  let gripper = null;
  if (s && feed.joints.gripper !== undefined && s.limits?.gripper) {
    const [lo, hi] = s.limits.gripper;
    gripper = Math.round(((feed.joints.gripper - lo) / (hi - lo)) * 100);
  }
  const oneToOne = s?.mode === "one_to_one";
  const speed = !s ? null
    : oneToOne ? { label: "Speed 1:1", value: s.one_to_one_deg_per_s == null ? null : Math.round(s.one_to_one_deg_per_s), unit: s.one_to_one_deg_per_s == null ? "servo max" : "°/s top" }
    : { label: "Speed", value: Math.round(s.speed_scale * 100), unit: "%" };
  const hint = oneToOne && !noController
    ? hands ? ["1:1: right wrist in the ball", "left pinch = move"] : ["1:1: hand in the ball", "hold grip = move", "A/X = stop"]
    : hands ? ["Hold left pinch = move", "right pinch = gripper"]
      : noController ? ["Pick up the controllers", "leave: palm up + pinch"]
        : ["Hold grip = move", "trigger = gripper", "A/X = stop"];
  return { state, level, gripper, speed, hint };
}

