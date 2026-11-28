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
//
// Two arms at once (status.left_arm): both models in the one view, the left arm to the left
// (arm-view.js), and the readout in two parts, "Right arm" then "Left arm". Each arm has its own
// ArmFeed, so each model moves with exactly its own driver's commands.
//
// A Monitor page of one kind of robot (/monitor/so101, /monitor/xarm; quick job 147): only the arms of
// that kind, only that kind's 3D models in the list, and a sentence while no such arm is connected.
import { createArmView } from "./arm-view.js";
import { loadArmModel, MODEL_CHOICES } from "./arm-model.js";
import { getLink } from "../link.js";
import { getArmFeed } from "./arm-feed.js";
import { jointFlags } from "./joint-flags.js";
import { KINDS, kindOf, pageKind } from "./kinds.js";
import { jointLabel } from "/web/words.js";

const $ = (id) => document.getElementById(id);

// Pages include <section id="arm-panel" class="panel arm3d" data-role="monitor|input"></section>;
// the markup lives here only. data-role picks which shared connection to listen on.
$("arm-panel").innerHTML = `
  <div class="arm3d-head">
    <span class="label">3D view</span>
    <select id="arm-model" aria-label="3D model"></select>
  </div>
  <div class="arm3d-body">
    <div id="arm-view"><span id="arm-held" class="arm-held" hidden title="Held still for safety. It moves again when an input takes it."><svg class="ico"><use href="/web/design/icons.svg#i-pause"/></svg>Held still</span><p id="arm-empty" class="arm-empty" hidden></p></div>
    <div class="arm-readout" aria-label="Joints"><div id="arm-joints" class="arm-joints"></div><div id="arm-cams" class="arm-cams" hidden></div></div>
  </div>
  <p id="arm-source" class="hint">Connecting…</p>
  <p id="arm-error" class="hint warn-text"></p>`;

const KIND = pageKind(location.pathname); // null: every arm (Teleop, AI Control)
const view = createArmView($("arm-view"), { fromFront: KIND === "so101" });
const select = $("arm-model");
const link = getLink($("arm-panel").dataset.role || "monitor");
const CHOICES = MODEL_CHOICES.filter((c) => !KIND || kindOf(c.kind) === KIND);
// each arm: its feed, its model, and its readout's rows (every joint seen, in the arm's order)
const arms = ["right", "left"].map((side) => ({ side, feed: getArmFeed(link, side, KIND), model: null, loading: null, shown: new Map() }));
let picked = null; // the model the user chose in the list (both arms), or null: each arm's own
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const twoArms = () => !!arms[1].feed.status;

for (const [i, c] of CHOICES.entries()) select.add(new Option(c.label, String(i)));
select.onchange = () => {
  picked = CHOICES[Number(select.value)];
  for (const arm of arms) if (arm.feed.status) useModel(arm, picked);
};

/** The model for an arm: the user's choice, else the first one of the arm's own kind. */
function choiceFor(arm) {
  return picked || CHOICES.find((c) => c.kind === arm.feed.modelKind);
}

async function useModel(arm, choice) {
  const key = `${choice.kind}/${choice.style}`;
  if (arm.loading === key || (arm.model && `${arm.model.kind}/${arm.model.style}` === key)) return;
  arm.loading = key;
  if (arm.side === "right") select.value = String(CHOICES.indexOf(choice));
  try {
    const next = await loadArmModel(choice.kind, { style: choice.style });
    if (arm.loading !== key) return; // another choice won meanwhile
    arm.model = next;
    view.setModel(next, arm.side);
    $("arm-error").textContent = "";
    render();
  } catch (e) {
    $("arm-error").textContent = `3D model "${choice.label}" failed to load: ${e.message}`;
  } finally {
    if (arm.loading === key) arm.loading = null;
  }
}

function sourceText({ feed: { lastCommand, frozen } }) {
  return lastCommand
    ? `Showing driver command #${lastCommand.seq} → ${lastCommand.device} (speed ${Math.round(lastCommand.speed_scale * 100)}%)${frozen ? ", held still (stop sent)" : ""}`
    : `No commands yet: showing the driver's reported joints${frozen ? ", held still" : ""}`;
}

/** One arm's model and readout rows (HTML). */
function renderArm(arm) {
  const { feed, model, shown } = arm;
  const { joints, lastCommand, frozen } = feed;
  if (!model) return "";
  model.setHeld(frozen);
  const { unknown, outOfRange } = model.setJoints(joints);
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
  return [...shown].map(([name, { cmd, flags }]) => {
    const value = cmd == null ? "—" : `${cmd >= 0 ? "+" : ""}${cmd.toFixed(1)}°`;
    const note = flags.join("; ");
    return `<div class="jrow${note ? " flag" : ""}"><span class="jn" title="${esc(name)}">${esc(jointLabel(name))}</span><span class="jv">${value}</span>` +
      `<span class="jf" title="${esc(note)}">${esc(note)}</span></div>`;
  }).join("");
}

function render() {
  const [right, left] = arms;
  const two = twoArms();
  const none = KIND && !right.feed.status && right.feed.heard;
  // no arm of this page's kind: one message, in the middle of the view (quick job 155: it said so three times)
  $("arm-empty").hidden = !none;
  $("arm-empty").textContent = none ? `No ${KINDS[KIND].robot} is connected to the brain.` : "";
  $("arm-source").textContent = none
    ? ""
    : two
      ? `Right arm: ${sourceText(right)}. Left arm: ${sourceText(left)}.`
      : sourceText(right);
  const rows = renderArm(right);
  const leftRows = two ? renderArm(left) : "";
  const head = (word, arm) => `<div class="jhead">${word} <small>${esc(arm.feed.status?.arm?.name || "")}</small></div>`;
  $("arm-joints").innerHTML = two ? head("Right arm", right) + rows + head("Left arm", left) + leftRows : rows;
  $("arm-held").hidden = !arms.some((a) => a.model && a.feed.frozen);
  view.requestRender();
}

for (const arm of arms) {
  arm.feed.onChange((f, why) => {
    if (why === "arm") {
      arm.shown = new Map(); // another arm (or none): its own joints
      if (!f.status) { // the brain drives one arm now: the left model goes
        arm.model = null;
        arm.loading = null;
        view.setModel(null, arm.side);
      }
    }
    if ((why === "status" || why === "arm") && f.status && !arm.loading) {
      const choice = choiceFor(arm);
      if (choice && (!arm.model || arm.model.kind !== choice.kind)) useModel(arm, choice);
    }
    render();
  });
}
