// The control buttons only when control is possible (quick job 76). When another page drives the arm,
// the AI tools do, or this page may only watch, the buttons that would take control are grey and can't
// be pressed, and a line under them says who has control. The brain's status says it for each page:
// `control`, `driver` (the device name of the page that drives) and `may_drive` (docs/dev/protocol.md).
//   gate(status, [buttons], lineElement)   on every status; a button this page is using stays as it is

/** Why this page can't take control now, or null when it can (control free, or its own). */
export function whoHasControl(s) {
  if (s.may_drive === false) return "View only: the arm is driven from the brain's computer.";
  if (s.control === "ai") return "The AI tools have control until their move ends.";
  if (s.control === "other") {
    return s.driver ? `The page on ${s.driver} has control. It must stop first.` : "Another page has control. It must stop first.";
  }
  return null;
}

/** Grey the buttons (and say why), or let them be pressed again. Buttons keep their other reasons to be
 *  off: `data-blocked` (another of this page's inputs runs) and `data-unavailable` (no WebXR here). */
export function gate(s, buttons, line) {
  const why = whoHasControl(s);
  for (const b of buttons) {
    if (!b) continue;
    b.dataset.taken = why ? "1" : "";
    b.disabled = !!why || b.dataset.blocked === "1" || b.dataset.unavailable === "1" || b.dataset.busy === "1";
    if (b.dataset.ownTitle === undefined) b.dataset.ownTitle = b.title; // its own hint comes back after
    b.title = why || b.dataset.ownTitle;
  }
  if (line) {
    line.textContent = why || "";
    line.hidden = !why;
  }
  return why;
}
