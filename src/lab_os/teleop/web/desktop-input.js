// Desktop control: drive the arm from a computer, in one of three swappable modes.
//
//   Keys          one key pair per motor (hold to turn it one way or the other)      → joint_input
//   Mouse         hold a motor's number key and move the mouse; mouse buttons = gripper → joint_input
//   Virtual hand  (prototype) a pretend Quest controller moved by keyboard + trackpad  → xr_input
//
// Keys and Mouse jog motors directly (never IK). The virtual hand sends the same messages as the
// Quest, so it goes through the same mapping (IK on arms that have kinematics). Click the button
// to start (the page captures the pointer), Esc to leave: leaving freezes the arm and hands
// control over. Messages are sent at 60 Hz while active, even when nothing is pressed: if they
// stop (tab hidden, page closed), the arm freezes (dead-man). Format: docs/dev/protocol.md.

const SHARED_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"];
const SLOW = 0.3; // Shift held = fine control (keys and mouse modes)

// Keys mode: [key for +, key for −, what + does] per shared joint name (+ directions: docs/GOTCHAS
// "joint directions"; the operator stands behind the arm, opposite the controller board).
const KEY_PAIRS = {
  shoulder_pan: ["KeyD", "KeyA", "base turns right"],
  shoulder_lift: ["KeyW", "KeyS", "shoulder tilts forward"],
  elbow_flex: ["KeyR", "KeyF", "elbow tilts forward"],
  wrist_flex: ["KeyT", "KeyG", "wrist tilts forward"],
  wrist_roll: ["KeyQ", "KeyE", "wrist rolls counter-clockwise"],
  gripper: ["KeyV", "KeyC", "gripper opens"],
};

// Mouse mode: hold the digit, move the mouse along the axis. sign: +1 = right/up is +.
const MOUSE_JOINTS = {
  Digit1: ["shoulder_pan", "x", 1, "base: mouse right = turn right"],
  Digit2: ["shoulder_lift", "y", 1, "shoulder: mouse up = forward"],
  Digit3: ["elbow_flex", "y", 1, "elbow: mouse up = forward"],
  Digit4: ["wrist_flex", "y", 1, "wrist tilt: mouse up = forward"],
  Digit5: ["wrist_roll", "x", -1, "wrist roll: mouse right = clockwise"],
};
const MOUSE_GAIN = 0.02; // rate per pixel per tick, times the sensitivity slider

const keyName = (code) => code.replace(/^Key|^Digit/, "");

function keysMode() {
  return {
    name: "keys",
    help(joints) {
      return joints
        .filter((j) => KEY_PAIRS[j])
        .map((j) => `<tr><td><kbd>${keyName(KEY_PAIRS[j][0])}</kbd> / <kbd>${keyName(KEY_PAIRS[j][1])}</kbd></td><td>${j}: ${KEY_PAIRS[j][2]} / the other way</td></tr>`)
        .concat([`<tr><td><kbd>Shift</kbd> held</td><td>slow (fine control)</td></tr>`])
        .join("");
    },
    handles: (code) => Object.values(KEY_PAIRS).some(([p, m]) => code === p || code === m),
    tick(keys, joints) {
      const k = keys.has("ShiftLeft") || keys.has("ShiftRight") ? SLOW : 1;
      const rates = {};
      for (const j of joints) {
        const pair = KEY_PAIRS[j];
        if (!pair) continue;
        const r = (keys.has(pair[0]) ? 1 : 0) - (keys.has(pair[1]) ? 1 : 0);
        if (r) rates[j] = r * k;
      }
      return { type: "joint_input", t: performance.now(), source: "desktop-keys", rates };
    },
  };
}

function mouseMode(sens) {
  let dx = 0;
  let dy = 0;
  return {
    name: "mouse",
    help(joints) {
      return Object.entries(MOUSE_JOINTS)
        .filter(([, [j]]) => joints.includes(j))
        .map(([code, [, , , text]]) => `<tr><td><kbd>${keyName(code)}</kbd> held + mouse</td><td>${text}</td></tr>`)
        .concat([
          `<tr><td>Left / right button held</td><td>gripper opens / closes</td></tr>`,
          `<tr><td><kbd>Shift</kbd> held</td><td>slow (fine control)</td></tr>`,
        ])
        .join("");
    },
    handles: (code) => code in MOUSE_JOINTS,
    mousemove(e) {
      dx += e.movementX;
      dy += e.movementY;
    },
    tick(keys, joints, buttons) {
      const k = (keys.has("ShiftLeft") || keys.has("ShiftRight") ? SLOW : 1) * MOUSE_GAIN * Number(sens.value);
      const clamp = (v) => Math.max(-1, Math.min(1, v));
      const rates = {};
      for (const [code, [j, axis, sign]] of Object.entries(MOUSE_JOINTS)) {
        if (!keys.has(code) || !joints.includes(j)) continue;
        const r = clamp(sign * (axis === "x" ? dx : -dy) * k); // screen y grows downward
        if (r) rates[j] = r;
      }
      const g = (buttons.has(0) ? 1 : 0) - (buttons.has(2) ? 1 : 0);
      if (g && joints.includes("gripper")) rates.gripper = g * (keys.has("ShiftLeft") || keys.has("ShiftRight") ? SLOW : 1);
      dx = dy = 0;
      return { type: "joint_input", t: performance.now(), source: "desktop-mouse", rates };
    },
  };
}

// ---- Virtual hand (prototype): a pretend right-hand controller --------------------------------
const HOME = [0.2, 1.0, -0.3]; // a comfortable spot in front of a seated user (WebXR local-floor)
const KEY_SPEED = 0.2; // m/s for W A S D R F
const TURN_SPEED = 30; // °/s for the arrow keys (90 was too twitchy on the real arm)
const GRIPPER_SPEED = 2.0; // trigger units per second (0 → 1 in half a second)
const HAND_KEYS = new Set(["Space", "KeyW", "KeyA", "KeyS", "KeyD", "KeyR", "KeyF", "KeyC", "KeyX", "KeyH",
  "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]);
const DEG = Math.PI / 180;
const qmul = (a, b) => [
  a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
  a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
  a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
  a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
];
const axisQuat = (axis, deg) => {
  const s = Math.sin((deg * DEG) / 2);
  return [axis[0] * s, axis[1] * s, axis[2] * s, Math.cos((deg * DEG) / 2)];
};

function handMode(sens, invert, ui) {
  const home = () => ({ pos: [...HOME], pitch: 0, roll: 0, trigger: 0, closed: false });
  let s = home();
  return {
    name: "hand",
    help: () =>
      [
        ["<kbd>Space</kbd> hold", "clutch (= grip): the arm follows while held"],
        ["Trackpad / mouse", "hand left/right, up/down"],
        ["Two-finger scroll", "hand forward/back"],
        ["<kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> · <kbd>R</kbd><kbd>F</kbd>", "steady move: forward/left/back/right · up/down"],
        ["<kbd>←</kbd><kbd>→</kbd> · <kbd>↑</kbd><kbd>↓</kbd>", "wrist roll · wrist tilt"],
        ["<kbd>C</kbd>", "gripper close / open (toggle; applied while the clutch is held)"],
        ["<kbd>H</kbd>", "re-center your virtual hand (only while the clutch is released)"],
      ]
        .map(([k, t]) => `<tr><td>${k}</td><td>${t}</td></tr>`)
        .join(""),
    handles: (code) => HAND_KEYS.has(code),
    reset() {
      s = home();
    },
    keydown(code, keys) {
      if (code === "KeyC") s.closed = !s.closed;
      if (code === "KeyH" && !keys.has("Space")) s = { ...home(), closed: s.closed, trigger: s.trigger }; // released clutch → the arm doesn't move
    },
    mousemove(e) {
      const k = 0.00025 * Number(sens.value); // metres per pixel
      s.pos[0] += e.movementX * k;
      s.pos[1] -= e.movementY * k;
    },
    wheel(e) {
      // deltaY > 0 (scroll down / swipe toward you) = hand toward you (+z).
      s.pos[2] += e.deltaY * 0.0004 * (invert.checked ? -1 : 1) * (e.deltaMode === 1 ? 16 : 1);
    },
    tick(keys, _joints, _buttons, dt) {
      const held = (code) => (keys.has(code) ? 1 : 0);
      s.pos[0] += (held("KeyD") - held("KeyA")) * KEY_SPEED * dt;
      s.pos[1] += (held("KeyR") - held("KeyF")) * KEY_SPEED * dt;
      s.pos[2] += (held("KeyS") - held("KeyW")) * KEY_SPEED * dt;
      s.roll += (held("ArrowLeft") - held("ArrowRight")) * TURN_SPEED * dt;
      s.pitch += (held("ArrowUp") - held("ArrowDown")) * TURN_SPEED * dt;
      const target = s.closed ? 1 : 0;
      s.trigger += Math.max(-GRIPPER_SPEED * dt, Math.min(GRIPPER_SPEED * dt, target - s.trigger));
      const hand = {
        pos: [...s.pos],
        quat: qmul(axisQuat([1, 0, 0], s.pitch), axisQuat([0, 0, 1], s.roll)),
        trigger: s.trigger,
        grip: held("Space"),
        buttons: { a: false, b: false, thumbstick: false },
        thumbstick: [0, 0],
      };
      ui.showHands({ right: hand }, `virtual hand · gripper ${s.closed ? "closing" : "opening"} (C)`);
      return { type: "xr_input", t: performance.now(), source: "desktop-hand", hands: { right: hand } };
    },
  };
}

// ---- Shared on/off, input events and the 60 Hz sender -----------------------------------------
export function initDesktop(link, ui) {
  const $ = (id) => document.getElementById(id);
  const button = $("desktop");
  const select = $("desk-mode");
  const sens = $("desk-sens");
  const invert = $("desk-invert");
  const modes = { keys: keysMode(), mouse: mouseMode(sens), hand: handMode(sens, invert, ui) };
  const keys = new Set();
  const buttons = new Set();
  let joints = SHARED_JOINTS; // replaced by the connected arm's joints (status), so switching arms works
  let active = false;
  let last = 0;
  let timer = null;

  try {
    const saved = localStorage.getItem("lab-os.desktop-mode");
    if (saved && modes[saved]) select.value = saved;
  } catch {
    // storage blocked: keep the default
  }
  const mode = () => modes[select.value] || modes.keys;
  const showHelp = () => ($("desk-keys").innerHTML = mode().help(joints));
  select.onchange = () => {
    try {
      localStorage.setItem("lab-os.desktop-mode", select.value);
    } catch {
      // not important
    }
    showHelp();
  };
  showHelp();

  link.on("status", (s) => {
    const names = Object.keys(s.joints || {});
    if (names.length && names.join() !== joints.join()) {
      joints = names;
      showHelp();
    }
  });

  button.onclick = async () => {
    try {
      await document.body.requestPointerLock();
    } catch (e) {
      ui.message(`Couldn't capture the pointer: ${e.message}`);
    }
  };
  document.addEventListener("pointerlockerror", () => ui.message("The browser refused to capture the pointer; click the button again."));
  document.addEventListener("pointerlockchange", () => {
    if (document.pointerLockElement === document.body) startControl();
    else stopControl();
  });

  function startControl() {
    active = true;
    keys.clear();
    buttons.clear();
    mode().reset?.();
    select.disabled = true; // no switching modes mid-drive
    document.activeElement?.blur(); // a key on a focused button would click it again
    ui.setActive("desktop");
    $("desk-help").open = true;
    button.textContent = `Desktop control on: ${select.options[select.selectedIndex].text} (Esc to leave)`;
    last = performance.now();
    // A timer, not requestAnimationFrame: input must not stall when rendering is slow. Browsers
    // throttle timers in background tabs, so leaving the tab still freezes the arm (dead-man).
    timer = setInterval(tick, 1000 / 60);
  }

  function stopControl() {
    if (!active) return;
    active = false;
    clearInterval(timer);
    keys.clear();
    buttons.clear();
    select.disabled = false;
    link.send({ type: "session_end" }); // dead-man: the arm freezes, control is handed over
    ui.setActive(null);
    button.textContent = "Desktop control";
  }

  function tick() {
    const now = performance.now();
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    const msg = mode().tick(keys, joints, buttons, dt);
    link.send(msg);
    if (msg.type === "joint_input") {
      const moving = Object.entries(msg.rates).map(([j, r]) => `${j} ${r > 0 ? "+" : ""}${r.toFixed(2)}`);
      $("readout").textContent = `desktop control · ${mode().name}\n${moving.join("\n") || "nothing pressed (holding)"}`;
    }
  }

  document.addEventListener("keydown", (e) => {
    if (!active) return;
    if (e.code === "KeyX") {
      e.preventDefault();
      if (!e.repeat) link.send({ type: "stop" }); // X = STOP in every mode
      return;
    }
    const shift = e.code === "ShiftLeft" || e.code === "ShiftRight";
    if (!shift && !mode().handles(e.code)) return;
    e.preventDefault();
    if (e.repeat) return;
    keys.add(e.code);
    mode().keydown?.(e.code, keys);
  });
  document.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("blur", () => {
    keys.clear();
    buttons.clear();
  });
  document.addEventListener("mousemove", (e) => active && mode().mousemove?.(e));
  document.addEventListener("mousedown", (e) => active && buttons.add(e.button));
  document.addEventListener("mouseup", (e) => buttons.delete(e.button));
  document.addEventListener("contextmenu", (e) => active && e.preventDefault()); // right button = gripper
  document.addEventListener(
    "wheel",
    (e) => {
      if (!active || !mode().wheel) return;
      e.preventDefault();
      mode().wheel(e);
    },
    { passive: false },
  );
}
