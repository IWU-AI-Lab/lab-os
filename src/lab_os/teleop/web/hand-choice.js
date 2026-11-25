// Controllers or bare hands in VR and AR Teleop (quick job 114, the builder 2026-11-24: "HUGE issue").
// Before, putting the controllers down switched to the hands by itself. Now only the choice drives:
//   hands: false  the controllers drive; put down, the arm holds still (the Quest's hands do nothing)
//   hands: true   the bare hands drive (Hands in the Teleop options); controllers do nothing
//   auto:  true   the old way: the controllers win, the hands drive while the controllers are down
// Kept in this browser, set in the hub's Teleop options. No imports, so the tests run it with node.

export const HANDS_KEY = "lab-os.xr-hands"; // "1": Hands chosen
export const AUTO_HANDS_KEY = "lab-os.xr-auto-hands"; // "1": switch to Hands by itself

/** This browser's choice: {hands, auto}; both false when nothing was chosen. */
export function loadHandChoice(store = globalThis.localStorage) {
  try {
    return { hands: store?.getItem(HANDS_KEY) === "1", auto: store?.getItem(AUTO_HANDS_KEY) === "1" };
  } catch {
    return { hands: false, auto: false }; // private window
  }
}

export function saveHandChoice(c, store = globalThis.localStorage) {
  try {
    store?.setItem(HANDS_KEY, c.hands ? "1" : "0");
    store?.setItem(AUTO_HANDS_KEY, c.auto ? "1" : "0");
  } catch { /* private window: this session only */ }
}

/** Which input drives this frame: "controllers", "hands" or null (auto, and nothing in view). */
export function pickSource(controllersSeen, handsSeen, { hands, auto }) {
  if (auto) return controllersSeen ? "controllers" : handsSeen ? "hands" : null;
  return hands ? "hands" : "controllers";
}
