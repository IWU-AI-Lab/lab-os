// WebXR input page: reads Quest controllers every XR frame and sends them to the
// Python server over a WebSocket. Message format: docs/protocol.md.
"use strict";

const $ = (id) => document.getElementById(id);
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

// ---- WebSocket (reconnects automatically) ---------------------------------
let ws = null;

function connect() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    setPill($("conn"), "connected", "on");
    send({ type: "hello", agent: navigator.userAgent });
  };
  ws.onclose = () => {
    setPill($("conn"), "disconnected", "off");
    setTimeout(connect, 1000);
  };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "status") showStatus(msg);
    else if (msg.type === "error") $("xr-msg").textContent = msg.message;
  };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

// ---- Status panel -----------------------------------------------------------
function setPill(el, text, cls) {
  el.textContent = text;
  el.className = `pill ${cls}`;
}

function showStatus(s) {
  if (s.frozen) setPill($("state"), s.needs_release ? "frozen: release grip" : "frozen", "warn");
  else if (s.clutch) setPill($("state"), "following (clutch)", "on");
  else setPill($("state"), "holding", "off");
  const g = s.joints.gripper;
  const [lo, hi] = s.limits.gripper || [0, 1];
  $("gripper").textContent = g === undefined ? "—" : `${Math.round(((g - lo) / (hi - lo)) * 100)}% open`;
  $("speed").textContent = `${Math.round(s.speed_scale * 100)}%`;
}

// ---- Reading the controllers ------------------------------------------------
const clamp01 = (v) => Math.min(1, Math.max(0, v || 0));

function readController(src, frame, refSpace) {
  const pose = frame.getPose(src.gripSpace || src.targetRaySpace, refSpace);
  const gp = src.gamepad;
  // "xr-standard" mapping: 0 trigger, 1 squeeze (grip), 3 thumbstick press, 4 A/X, 5 B/Y.
  const btn = (i) => (gp && gp.buttons[i]) || { pressed: false, value: 0 };
  const p = pose && pose.transform.position;
  const o = pose && pose.transform.orientation;
  return {
    pos: p ? [p.x, p.y, p.z] : null,
    quat: o ? [o.x, o.y, o.z, o.w] : null,
    trigger: clamp01(btn(0).value),
    grip: clamp01(btn(1).value),
    buttons: { thumbstick: btn(3).pressed, a: btn(4).pressed, b: btn(5).pressed },
    thumbstick: gp && gp.axes.length >= 4 ? [gp.axes[2], gp.axes[3]] : [0, 0],
  };
}

function fmt(c) {
  if (!c.pos) return "tracking lost";
  const n = (v) => (v >= 0 ? "+" : "") + v.toFixed(2);
  const b = Object.entries(c.buttons).filter(([, on]) => on).map(([k]) => k).join(",") || "-";
  return `pos ${c.pos.map(n).join(" ")}  grip ${c.grip.toFixed(2)}  trig ${c.trigger.toFixed(2)}  btn ${b}`;
}

// ---- XR session -----------------------------------------------------------------
let mode = null;
let lastReadout = 0;

async function init() {
  const button = $("enter");
  if (!navigator.xr) {
    button.textContent = "WebXR not available";
    $("xr-msg").textContent =
      "On the Quest, open this page at http://localhost:8080 (see docs/quest-setup.md). " +
      "On a desktop, install the Immersive Web Emulator extension and reload.";
    return;
  }
  if (await navigator.xr.isSessionSupported("immersive-ar")) mode = "immersive-ar";
  else if (await navigator.xr.isSessionSupported("immersive-vr")) mode = "immersive-vr";
  if (!mode) {
    button.textContent = "No immersive XR on this device";
    return;
  }
  button.textContent = mode === "immersive-ar" ? "Enter AR (passthrough)" : "Enter VR";
  button.disabled = false;
  button.onclick = start;
}

async function start() {
  const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor"] });
  const canvas = document.createElement("canvas");
  const gl = canvas.getContext("webgl2", { xrCompatible: true }) || canvas.getContext("webgl", { xrCompatible: true });
  await session.updateRenderState({ baseLayer: new XRWebGLLayer(session, gl) });
  let refSpace;
  try {
    refSpace = await session.requestReferenceSpace("local-floor");
  } catch {
    refSpace = await session.requestReferenceSpace("local");
  }

  $("enter").disabled = true;
  session.addEventListener("end", () => {
    send({ type: "session_end" });
    $("enter").disabled = false;
    $("readout").textContent = "XR session ended";
  });

  const clear = mode === "immersive-ar" ? [0, 0, 0, 0] : [0.1, 0.1, 0.12, 1];

  session.requestAnimationFrame(function onFrame(t, frame) {
    session.requestAnimationFrame(onFrame);
    const hands = {};
    for (const src of session.inputSources) {
      // Hand-tracking sources (src.hand) come in step 6; controllers only for now.
      if (src.handedness === "left" || src.handedness === "right") {
        if (src.gamepad && !src.hand) hands[src.handedness] = readController(src, frame, refSpace);
      }
    }
    send({ type: "xr_input", t, hands });

    if (t - lastReadout > 100) {
      lastReadout = t;
      $("readout").textContent =
        Object.entries(hands).map(([side, c]) => `${side.padEnd(5)} ${fmt(c)}`).join("\n") || "no controllers";
    }

    // Nothing to draw yet (overlay = step 5): just clear. Transparent in AR = passthrough.
    gl.bindFramebuffer(gl.FRAMEBUFFER, session.renderState.baseLayer.framebuffer);
    gl.clearColor(...clear);
    gl.clear(gl.COLOR_BUFFER_BIT);
  });
}

connect();
init();
