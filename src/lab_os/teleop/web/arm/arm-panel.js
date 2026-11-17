// Page glue: connects a 3D view to the server and shows exactly what the arm driver receives.
//
// Draws the joints of every `arm_command` (the arguments of Arm.move_joints), unclamped. Before the
// first command it shows the driver's reported joints from `status`. The joint readout flags joints
// the driver clamped (command ≠ driver state) and joints the driver holds outside its own limits
// (joint-flags.js; the 3D model's limits only until the driver has sent its own).
//
// Layout (quick job 14): the 3D view in its own box, the joint readout in a column beside it with one
// row per joint of the arm, always all of them, in the arm's order, each a fixed height. A command
// that names only some joints (a jog moves one or two) updates those rows; nothing appears,
// disappears or wraps, so the 3D view never resizes.
import { createArmView } from "./arm-view.js";
import { loadArmModel, MODEL_CHOICES } from "./arm-model.js";
import { getLink } from "../link.js";
import { getArmFeed } from "./arm-feed.js";
import { jointFlags } from "./joint-flags.js";
import { color } from "/web/theme.js";

const $ = (id) => document.getElementById(id);
const FROZEN_TINT = color("colors.frozen");

// Pages include <section id="arm-panel" class="panel arm3d" data-role="monitor|input"></section>;
// the markup lives here only. data-role picks which shared connection to listen on.
$("arm-panel").innerHTML = `
  <div class="arm3d-head">
    <span class="label">3D view</span>
    <select id="arm-model" aria-label="3D model"></select>
  </div>
  <div class="arm3d-body">
    <div id="arm-view"></div>
    <div class="arm-readout" aria-label="Joints"><div id="arm-joints" class="arm-joints"></div></div>
  </div>
  <p id="arm-source" class="hint">Connecting…</p>
  <p id="arm-error" class="hint warn-text"></p>`;

const view = createArmView($("arm-view"));
const select = $("arm-model");
const feed = getArmFeed(getLink($("arm-panel").dataset.role || "monitor"));
let model = null;
let loading = null;
let userPicked = false;
// the readout's rows: every joint seen for this arm, in the arm's order, with its latest value
let shown = new Map();
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

for (const [i, c] of MODEL_CHOICES.entries()) select.add(new Option(c.label, String(i)));
select.onchange = () => {
  userPicked = true;
  useModel(MODEL_CHOICES[Number(select.value)]);
};

async function useModel(choice) {
  const key = `${choice.kind}/${choice.style}`;
  if (loading === key || (model && `${model.kind}/${model.style}` === key)) return;
  loading = key;
  select.value = String(MODEL_CHOICES.indexOf(choice));
  try {
    const next = await loadArmModel(choice.kind, { style: choice.style });
    if (loading !== key) return; // another choice won meanwhile
    model = next;
    view.setModel(model);
    $("arm-error").textContent = "";
    render();
  } catch (e) {
    $("arm-error").textContent = `3D model "${choice.label}" failed to load: ${e.message}`;
  } finally {
    if (loading === key) loading = null;
  }
}

function render() {
  const { joints, lastCommand, frozen } = feed;
  $("arm-source").textContent = lastCommand
    ? `Showing driver command #${lastCommand.seq} → ${lastCommand.device} (speed ${Math.round(lastCommand.speed_scale * 100)}%)${frozen ? " · FROZEN (stop sent)" : ""}`
    : `No commands yet: showing the driver's reported joints${frozen ? " · FROZEN" : ""}`;
  if (!model) return;
  model.setTint(frozen ? FROZEN_TINT : null);
  const { unknown, outOfRange } = model.setJoints(joints);
  view.requestRender();
  // Clamping is judged from the driver state reported with the same command (never a later one).
  const after = lastCommand?.driver_joints || {};
  // every joint the driver reports gets its row (with the reported angle until a command names it)
  for (const [name, deg] of Object.entries(feed.status?.joints || {})) {
    if (!shown.has(name) || shown.get(name).cmd == null) shown.set(name, { cmd: deg ?? null, flags: [] });
  }
  const limits = feed.status?.limits || {}; // the driver's limits in force (quick job 24)
  for (const [name, cmd] of Object.entries(joints)) {
    const flags = jointFlags(cmd, after[name], limits[name], {
      outOfModel: outOfRange.includes(name),
      unknown: unknown.includes(name),
    });
    shown.set(name, { cmd, flags });
  }
  $("arm-joints").innerHTML = [...shown].map(([name, { cmd, flags }]) => {
    const value = cmd == null ? "—" : `${cmd >= 0 ? "+" : ""}${cmd.toFixed(1)}°`;
    const note = flags.join("; ");
    return `<div class="jrow${note ? " flag" : ""}"><span class="jn">${esc(name)}</span><span class="jv">${value}</span>` +
      `<span class="jf" title="${esc(note)}">${esc(note)}</span></div>`;
  }).join("");
}

feed.onChange((f, why) => {
  if (why === "arm") {
    userPicked = false; // another arm: show its own model again
    shown = new Map(); // and its own joints
  }
  if ((why === "status" || why === "arm") && !userPicked && !loading) {
    const choice = MODEL_CHOICES.find((c) => c.kind === f.modelKind);
    if (choice && (!model || model.kind !== choice.kind)) useModel(choice);
  }
  render();
});
