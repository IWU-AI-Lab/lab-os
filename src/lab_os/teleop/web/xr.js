// WebXR input: reads Quest controllers every XR frame and sends them to the brain.
// Message format: docs/protocol.md.

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

async function start(mode, link, ui) {
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

  ui.setActive("xr");
  session.addEventListener("end", () => {
    link.send({ type: "session_end" });
    ui.setActive(null);
    ui.showHands({}, "XR session ended");
  });

  const clear = mode === "immersive-ar" ? [0, 0, 0, 0] : [0.1, 0.1, 0.12, 1];

  session.requestAnimationFrame(function onFrame(t, frame) {
    session.requestAnimationFrame(onFrame);
    const hands = {};
    for (const src of session.inputSources) {
      // Hand-tracking sources (src.hand) come in step 6; controllers only for now.
      if ((src.handedness === "left" || src.handedness === "right") && src.gamepad && !src.hand) {
        hands[src.handedness] = readController(src, frame, refSpace);
      }
    }
    link.send({ type: "xr_input", t, hands });
    ui.showHands(hands);

    // Nothing to draw yet (overlay = step 5): just clear. Transparent in AR = passthrough.
    gl.bindFramebuffer(gl.FRAMEBUFFER, session.renderState.baseLayer.framebuffer);
    gl.clearColor(...clear);
    gl.clear(gl.COLOR_BUFFER_BIT);
  });
}
