// What the Teleop options panel in the hub's VR and AR Teleop shows and sends (quick job 102): the Teleop
// page's options for the headset (/teleop → Controls), from the brain's status. No imports, so the tests
// run it with node; xr/teleop-panel.js draws it.
//   speed    − and +, 5 % a step, up to the venue's cap (the page's slider)        → set_speed
//   mode     Relative, 1:1 (only where the brain offers it) or Hands              → set_mode
//            (Hands: the bare hands drive, relative; kept in this browser, quick job 114)
//   auto     Switch to Hands by Itself: off (the default) = the controllers put down, the arm holds
//            still; on = the hands drive while the controllers are down (kept in this browser)
//   style    the 3D arm: the full model or the light one (kept in this browser, like the page's)
//   place    put the 3D arm back at its first place (both 3D arms with two arms)

export const SPEED_STEP = 0.05;
const MODES = [["relative", "Relative"], ["one_to_one", "1:1"], ["hands", "Hands"]];
const OFF_ON = [["off", "Off"], ["on", "On"]];
const STYLES = [["", "Full Model"], ["stick", "Light"]];

/** The panel's rows from the brain's status `s` (or null), this headset's 3D-arm look (`style`) and
 * its controllers-or-hands choice (`input`: {hands, auto}, xr.js's hand-choice.js). */
export function optionRows(s, style = "", input = { hands: false, auto: false }) {
  const hands = !!input.hands && !input.auto;
  const pct = s ? Math.round(s.speed_scale * 100) : null;
  const max = Math.round((s?.max_speed_scale ?? 1) * 100);
  const modes = s?.modes || ["relative"];
  const oneToOne = modes.includes("one_to_one");
  const top = s?.one_to_one_deg_per_s == null ? "the servos' own top speed" : `${s.one_to_one_deg_per_s}°/s`;
  const modeHelp = hands
    ? "Hands: hold a left pinch to move, a right pinch = gripper. Controllers do nothing."
    : !oneToOne
    ? "1:1 is off in this venue (Settings → Robots → Teleop 1:1 Top Joint Speed)."
    : s?.mode === "one_to_one"
      ? `1:1 follows as fast as ${top}. Line the 3D arm up on the real one first.`
      : "Relative: half scale. Grab again to recenter.";
  return [
    {
      key: "speed", label: "Speed", kind: "number", value: pct == null ? "—" : `${pct}%`,
      can: { minus: pct != null && pct > 5, plus: pct != null && pct < max },
      help: s?.mode === "one_to_one" ? "For relative only. 1:1 has its own top speed." : "",
    },
    {
      key: "mode", label: "Hand → Arm", kind: "choice", value: hands ? "hands" : s?.mode || "relative",
      choices: MODES.map(([value, label]) => ({
        value, label, enabled: !!s && (value === "hands" ? !input.auto : modes.includes(value)),
      })),
      help: hands && s?.left_arm ? `${modeHelp} Right arm only.` : s?.left_arm ? `${modeHelp} Both arms use it.` : modeHelp,
    },
    {
      key: "auto", label: "Switch to Hands by Itself", kind: "choice", value: input.auto ? "on" : "off",
      choices: OFF_ON.map(([value, label]) => ({ value, label, enabled: true })),
      help: input.auto
        ? "On: put the controllers down and the hands drive."
        : "Off: put the controllers down and the arm holds still.",
    },
    {
      key: "style", label: "3D Arm", kind: "choice", value: style === "stick" ? "stick" : "",
      choices: STYLES.map(([value, label]) => ({ value, label, enabled: true })),
      help: "Light is a stick figure. Use it if frames drop.",
    },
    {
      key: "place", label: "Put the 3D Arm Back", kind: "action", value: "",
      help: s?.left_arm ? "Both 3D arms go to their first places." : "It goes to its first place. Left Grip moves it.",
    },
  ];
}

/** This headset's new {hands, auto} after a press, or null (the press does not change it). */
export function handChoiceAfter(key, op, value, input) {
  if (op !== "pick") return null;
  if (key === "mode") return { hands: value === "hands", auto: !!input.auto };
  if (key === "auto") return { hands: false, auto: value === "on" };
  return null;
}

/** The message to the brain for a press (`op`: "minus" / "plus" / "pick"), or null (nothing to send). */
export function optionMessage(key, op, value, s) {
  if (!s) return null;
  if (key === "speed" && (op === "minus" || op === "plus")) {
    const max = s.max_speed_scale ?? 1;
    const next = Math.round((s.speed_scale + (op === "plus" ? SPEED_STEP : -SPEED_STEP)) * 100) / 100;
    const speed = Math.min(max, Math.max(SPEED_STEP, next));
    return speed === s.speed_scale ? null : { type: "set_speed", speed_scale: speed };
  }
  // Hands drive relative: the brain goes to relative if it is in 1:1
  if (key === "mode" && op === "pick" && value === "hands") {
    return s.mode === "relative" ? null : { type: "set_mode", mode: "relative" };
  }
  if (key === "mode" && op === "pick" && value !== s.mode && (s.modes || ["relative"]).includes(value)) {
    return { type: "set_mode", mode: value };
  }
  return null;
}
