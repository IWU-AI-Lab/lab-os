// Page glue: connects a 3D view to the server and shows exactly what the arm driver receives.
//
// Draws the joints of every `arm_command` (the arguments of Arm.move_joints), unclamped. Before the
// first command it shows the driver's reported joints from `status`. The table flags joints the
// driver clamped (command ≠ driver state) and commands outside the 3D model's limits.
import { createArmView } from "./arm-view.js";
import { loadArmModel, MODEL_CHOICES } from "./arm-model.js";
import { getLink } from "../link.js";

const $ = (id) => document.getElementById(id);
const FROZEN_TINT = 0x7a1d00;

// Pages include <section id="arm-panel" class="panel arm3d" data-role="monitor|input"></section>;
// the markup lives here only. data-role picks which shared connection to listen on.
$("arm-panel").innerHTML = `
  <div class="arm3d-head">
    <span class="label">3D view</span>
    <select id="arm-model" aria-label="3D model"></select>
  </div>
  <div id="arm-view"></div>
  <p id="arm-source" class="hint">Connecting…</p>
  <p id="arm-error" class="hint warn-text"></p>
  <table class="arm-table"><tbody id="arm-joints"></tbody></table>`;

const view = createArmView($("arm-view"));
const select = $("arm-model");
let model = null;
let loading = null;
let userPicked = false;
let shownJoints = {};
let lastCommand = null;
let frozen = false;

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
    model.setTint(frozen ? FROZEN_TINT : null);
    $("arm-error").textContent = "";
    render();
  } catch (e) {
    $("arm-error").textContent = `3D model "${choice.label}" failed to load: ${e.message}`;
  } finally {
    if (loading === key) loading = null;
  }
}

function render() {
  if (!model) return;
  const { unknown, outOfRange } = model.setJoints(shownJoints);
  view.requestRender();
  // Clamping is judged from the driver state reported with the same command (never a later one).
  const after = lastCommand?.driver_joints || {};
  const rows = Object.entries(shownJoints).map(([name, cmd]) => {
    const drv = after[name];
    const flags = [];
    if (drv !== undefined && Math.abs(drv - cmd) > 0.05) flags.push(`clamped by driver → ${drv.toFixed(1)}°`);
    if (outOfRange.includes(name)) flags.push("outside model limits");
    if (unknown.includes(name)) flags.push("not in this model");
    return `<tr class="${flags.length ? "flag" : ""}"><td>${name}</td><td>${cmd >= 0 ? "+" : ""}${cmd.toFixed(1)}°</td><td>${flags.join("; ")}</td></tr>`;
  });
  $("arm-joints").innerHTML = rows.join("");
}

function setSource() {
  $("arm-source").textContent = lastCommand
    ? `Showing driver command #${lastCommand.seq} → ${lastCommand.device} (speed ${Math.round(lastCommand.speed_scale * 100)}%)${frozen ? " · FROZEN (stop sent)" : ""}`
    : `No commands yet: showing the driver's reported joints${frozen ? " · FROZEN" : ""}`;
}

function onMessage(msg) {
  if (msg.type === "status") {
    if (!userPicked && !loading) {
      const choice = MODEL_CHOICES.find((c) => c.kind === msg.arm?.model);
      if (choice && (!model || model.kind !== choice.kind)) useModel(choice);
    }
    if (!lastCommand) {
      lastCommand = msg.last_command;
      shownJoints = lastCommand ? lastCommand.joints : msg.joints;
    }
    setFrozen(msg.frozen);
  } else if (msg.type === "arm_command") {
    lastCommand = msg;
    shownJoints = msg.joints;
  } else if (msg.type === "arm_stop") {
    setFrozen(true);
  } else if (msg.type === "arm_resume") {
    setFrozen(false);
  } else {
    return;
  }
  setSource();
  render();
}

function setFrozen(value) {
  frozen = value;
  if (model) model.setTint(frozen ? FROZEN_TINT : null);
  view.requestRender();
}

const link = getLink($("arm-panel").dataset.role || "monitor");
for (const type of ["status", "arm_command", "arm_stop", "arm_resume"]) link.on(type, onMessage);
