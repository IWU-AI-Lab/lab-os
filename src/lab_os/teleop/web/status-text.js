// What the headset's teleop status panel says (xr-scene.js draws it; quick job 37): the state and how
// serious it is, the gripper's opening, the speed, and the hint. No imports, so tests run it with node.
//   level: normal (cyan) | following (green) | warning (amber) | held (rust, pause icon) | offline (gray)
// Plain words, no dot separators (docs/design/DESIGN.md → "Don't").

// Two arms at once (status.left_arm, preview 3): `left` is the left arm's {state, level}, and `state`
// says "Right …"; the panel draws the left one on the left. Bare hands drive only the right arm.

/** The left arm's state (two arms at once), from status.left_arm. */
function leftText(l) {
  return l.connected === false ? ["Left disconnected", "offline"]
    : l.frozen ? [l.needs_release ? "Left stopped: let go" : "Left stopped", "held"]
    : l.clutch ? [l.one_to_one ? "Left following 1:1" : "Left following", "following"]
    : l.mode === "one_to_one" && l.hand_gap_cm != null && l.hand_gap_cm > l.capture_cm
      ? [`Left: reach the gripper ${Math.round(l.hand_gap_cm)} cm`, "normal"]
      : ["Left holding", "normal"];
}

/** From the teleop status (an ArmFeed): {state, level, gripper (% open or null), speed, hint: [parts],
 * left: {state, level} or null}. `moving`: two arms, Y held (the grips move the 3D arms). `off`: the
 * brain_off message once lab-os was shut down or restarts (quick job 44: the page's cover isn't seen in
 * the headset, so the panel says it). */
export function panelText(feed, noController, source, moving = false, off = null) {
  if (off) {
    return off.restart
      ? { state: "lab-os is restarting", level: "offline", gripper: null, speed: null, hint: ["It comes back by itself"], left: null }
      : { state: "lab-os is off", level: "offline", gripper: null, speed: null, hint: ["The arm was let go", "Start it from its icon"], left: null };
  }
  const one = oneArmText(feed, noController, source);
  const l = feed?.status?.left_arm;
  if (!l || noController) {
    delete one.release;
    return { ...one, left: null };
  }
  const [state, level] = leftText(l);
  const hands = source === "hands";
  const oneToOne = feed.status.mode === "one_to_one";
  const hint = hands ? ["Two arms: controllers only", "now: right arm", "left pinch = move"]
    : moving ? ["Y held: a grip moves its 3D arm", "the arms hold", "tap Y = put back"]
      : oneToOne ? ["1:1: each hand in its ball", "hold grip = move", "Y + grip = move 3D arm", "A/X = stop both"]
        : ["Grip = move its arm", "trigger = gripper", "Y + grip = move 3D arm", "A/X = stop both"];
  const right = one.release ? "Stopped: let go" : one.state;
  const words = right.startsWith("Reach the gripper: ")
    ? `Right: reach the gripper ${right.slice("Reach the gripper: ".length)}`
    : `Right ${right.charAt(0).toLowerCase()}${right.slice(1)}`;
  delete one.release;
  return { ...one, state: words, hint, left: { state, level } };
}

function oneArmText(feed, noController, source) {
  const s = feed?.status, hands = source === "hands";
  const [state, level] = noController ? [hands ? "No right hand" : "No controller", "warning"]
    : !s ? ["Connecting…", "offline"]
    : s.arm?.connected === false ? ["Arm disconnected", "offline"]
    // one page drives at a time (quick jobs 76, 97): this one can't now, so it says who can
    : s.may_drive === false ? ["View only", "warning"]
    : s.control === "ai" ? ["The AI tools have control", "warning"]
    : s.control === "other" ? [s.driver ? `${s.driver} has control` : "Another page has control", "warning"]
    : feed.frozen ? ["Stopped", "held"] // what happened; what to do is the hint (quick job 66)
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
  // stopped, and it waits for the grip (or the pinch) to be let go: say what to do (quick job 66; it
  // said "frozen: release grip", which didn't say either)
  const release = !noController && !!s && s.arm?.connected !== false && feed.frozen && !!s.needs_release;
  const taken = !noController && !!s && s.arm?.connected !== false && (s.may_drive === false || s.control === "ai" || s.control === "other");
  const hint = taken ? s.may_drive === false ? ["Driven from the brain's computer", "drive_from in place.yaml allows it"] : ["It must stop first"]
    : release ? [hands ? "Let go of the pinch" : "Let go of the grip", hands ? "then pinch again" : "then grab again"]
    : oneToOne && !noController
    ? hands ? ["1:1: right wrist in the ball", "left pinch = move"] : ["1:1: hand in the ball", "hold grip = move", "A/X = stop"]
    : hands ? ["Hold left pinch = move", "right pinch = gripper"]
      : noController ? ["Pick up the controllers", "leave: palm up + pinch"]
        : ["Hold grip = move", "trigger = gripper", "A/X = stop"];
  return { state, level, gripper, speed, hint, release: release && !taken };
}

