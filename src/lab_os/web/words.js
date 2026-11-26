// The words every page shows for the same things (quick job 153), so that one thing has one name.
// No imports, so tests run it with node.
//   jointLabel("shoulder_pan")  → "Shoulder Pan" (the code name goes in the tooltip)
//   held(needsRelease, how)     → {text: "Held still", why: what to do} for an arm that holds still
//   cap("connected")            → "Connected": status words start with a capital letter (docs/design/DESIGN.md)

/** "shoulder_pan" → "Shoulder Pan". */
export function jointLabel(name) {
  return String(name ?? "").split(/[_\s]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
}

/** The first letter as a capital ("" stays ""). */
export const cap = (s) => (s ? String(s)[0].toUpperCase() + String(s).slice(1) : "");

/** An arm that holds still (the brain froze it: start, STOP, a lost input). The words stay calm: it is
 * the safety system working, not a fault (docs/design/DESIGN.md → "Held"). `how`: what lets it go. */
export function held(needsRelease, how = "the grip") {
  return {
    text: "Held still",
    why: needsRelease ? `Held still for safety. Let go of ${how}, then take it again to move.` : "Held still for safety.",
  };
}
