// WebXR input: reads Quest controllers every XR frame and sends them to the brain, and renders the
// session's scene (ghost arm, hand markers, status panel: xr-scene.js) with three.js.
// Message format: docs/protocol.md.
import * as THREE from "three";
import { XRScene } from "./xr-scene.js";
import { getArmFeed } from "./arm/arm-feed.js";

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

export async function initXR(link, ui) {
  const button = document.getElementById("enter");
  const unavailable = (text, hint) => {
    button.textContent = text;
    button.dataset.unavailable = "1";
    button.disabled = true;
    if (hint) ui.message(hint);
  };
  if (!navigator.xr) {
    return unavailable(
      "WebXR not available",
      "On the Quest, open http://localhost:8080 (docs/quest-setup.md). On a desktop, use Desktop control below, or the Immersive Web Emulator extension.",
    );
  }
  let mode = null;
  if (await navigator.xr.isSessionSupported("immersive-ar")) mode = "immersive-ar";
  else if (await navigator.xr.isSessionSupported("immersive-vr")) mode = "immersive-vr";
  if (!mode) return unavailable("No immersive XR on this device");

  button.textContent = mode === "immersive-ar" ? "Enter AR (passthrough)" : "Enter VR";
  button.dataset.unavailable = "";
  button.disabled = false;
  button.onclick = () => start(mode, link, ui);
}

let renderer = null; // one WebGL renderer for every session on this page

async function start(mode, link, ui) {
  const ar = mode === "immersive-ar";
  const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor"] });
  // Floor-level space if the device has one; otherwise "local" (origin at the head) and shift the
  // scene down so the table is still at table height.
  let refType = "local-floor";
  try {
    await session.requestReferenceSpace("local-floor");
  } catch {
    refType = "local";
  }

  if (!renderer) {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.xr.enabled = true;
  }
  renderer.setClearColor(0x000000, ar ? 0 : 1); // transparent in AR = passthrough
  renderer.xr.setReferenceSpaceType(refType);
  // ?xrarm=stick on the page URL = light arm model in the headset (testing, or if frames drop)
  const style = new URLSearchParams(location.search).get("xrarm") || undefined;
  const xrScene = new XRScene(getArmFeed(link), { ar, style });
  if (refType === "local") xrScene.setFloorOffset(-1.4);
  const camera = new THREE.PerspectiveCamera(70, 1, 0.01, 50); // replaced by the headset's cameras
  await renderer.xr.setSession(session);

  ui.setActive("xr");
  session.addEventListener("end", () => {
    renderer.setAnimationLoop(null);
    link.send({ type: "session_end" });
    ui.setActive(null);
    ui.showHands({}, "XR session ended");
  });

  renderer.setAnimationLoop((t, frame) => {
    if (!frame) return;
    const refSpace = renderer.xr.getReferenceSpace();
    const hands = {};
    for (const src of session.inputSources) {
      // Hand-tracking sources (src.hand) come in step 6; controllers only for now.
      if ((src.handedness === "left" || src.handedness === "right") && src.gamepad && !src.hand) {
        hands[src.handedness] = readController(src, frame, refSpace);
      }
    }
    link.send({ type: "xr_input", t, hands });
    ui.showHands(hands);
    xrScene.updateHands(hands);
    renderer.render(xrScene.scene, camera);
  });
}
