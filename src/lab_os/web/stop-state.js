// When the hubs show STOP (quick job 43): while a real arm is connected (not a software one), and whether it
// moves now (an AI move, or a teleop page or the Quest driving), from the brain's `status` message
// (docs/dev/protocol.md). Two arms at once: either arm. No imports, so tests run it with node; the button
// itself is /web/hub-stop.js (screens) and hub/web/xr/hub.js (VR).

/** {show, moving} from a `status` message (or null before the first one). */
export function stopState(s) {
  if (!s) return { show: false, moving: false };
  const arms = [s.arm, s.left_arm].filter(Boolean);
  const show = arms.some((a) => a.real && a.connected !== false);
  const driving = (a) => !!a?.clutch && !a.frozen;
  const moving = show && (!!s.ai_motion || driving(s) || driving(s.left_arm));
  return { show, moving };
}
