// Desktop control: a virtual right-hand controller driven by keyboard + trackpad/mouse.
// It sends the same `xr_input` messages as the Quest, so everything downstream is tested as-is.
//
//   Space (hold)      clutch (= grip)                 Trackpad / mouse   hand left/right, up/down
//   Two-finger scroll hand forward/back                W A S D / R F      steady move (fwd/left/back/right, up/down)
//   ← →  /  ↑ ↓       wrist roll / wrist tilt          C                  gripper close/open (toggle, ramped)
//   X (hold)          stop (= A/X button)              H                  re-center the hand (only while released)
//   Esc               leave desktop control (the arm freezes)

const HOME = [0.2, 1.0, -0.3]; // a comfortable spot in front of a seated user (WebXR local-floor)
const KEY_SPEED = 0.2; // m/s for W A S D R F
const TURN_SPEED = 90; // °/s for the arrow keys
const GRIPPER_SPEED = 2.0; // trigger units per second (0 → 1 in half a second)
const HANDLED = new Set(["Space", "KeyW", "KeyA", "KeyS", "KeyD", "KeyR", "KeyF", "KeyC", "KeyX", "KeyH",
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

export function initDesktop(link, ui) {
  const $ = (id) => document.getElementById(id);
  const button = $("desktop");
  const sens = $("desk-sens");
  const invert = $("desk-invert");
  const keys = new Set();
  let active = false;
  let last = 0;
  let timer = null;
  let s = home();

  function home() {
    return { pos: [...HOME], pitch: 0, roll: 0, trigger: 0, closed: false };
  }

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
    document.activeElement?.blur(); // Space on a focused button would click it again
    ui.setActive("desktop");
    $("desk-help").open = true;
    button.textContent = "Desktop control on (Esc to leave)";
    last = performance.now();
    // A timer, not requestAnimationFrame: input must not stall when rendering is slow. Browsers
    // throttle timers in background tabs, so leaving the tab still freezes the arm (dead-man).
    timer = setInterval(() => tick(performance.now()), 1000 / 60);
  }

  function stopControl() {
    if (!active) return;
    active = false;
    clearInterval(timer);
    keys.clear();
    link.send({ type: "session_end" }); // dead-man: the arm freezes
    ui.setActive(null);
    button.textContent = "Desktop control (keyboard + trackpad)";
  }

  // Trackpad / mouse: relative motion while the pointer is captured.
  document.addEventListener("mousemove", (e) => {
    if (!active) return;
    const k = 0.00025 * Number(sens.value); // metres per pixel
    s.pos[0] += e.movementX * k;
    s.pos[1] -= e.movementY * k;
  });
  document.addEventListener(
    "wheel",
    (e) => {
      if (!active) return;
      e.preventDefault();
      // deltaY > 0 (scroll down / swipe toward you) = hand toward you (+z).
      s.pos[2] += e.deltaY * 0.0004 * (invert.checked ? -1 : 1) * (e.deltaMode === 1 ? 16 : 1);
    },
    { passive: false },
  );

  document.addEventListener("keydown", (e) => {
    if (!active || !HANDLED.has(e.code)) return;
    e.preventDefault();
    if (e.repeat) return;
    keys.add(e.code);
    if (e.code === "KeyC") s.closed = !s.closed;
    if (e.code === "KeyH" && !keys.has("Space")) {
      const closed = s.closed;
      const trigger = s.trigger;
      s = { ...home(), closed, trigger }; // released clutch → the arm doesn't move
    }
  });
  document.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("blur", () => keys.clear());

  function tick(now) {
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
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
      buttons: { a: keys.has("KeyX"), b: false, thumbstick: false },
      thumbstick: [0, 0],
    };
    link.send({ type: "xr_input", t: now, source: "desktop", hands: { right: hand } });
    ui.showHands({ right: hand }, `desktop control · gripper ${s.closed ? "closing" : "opening"} (C)`);
  }
}
