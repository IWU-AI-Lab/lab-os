// WebXR input: reads the Quest's controllers (or bare hands) every XR frame and sends them to the
// brain, and renders the session's scene (ghost arm, hand markers, status panel: xr-scene.js).
// Message format: docs/protocol.md.
//   - Controllers: right grip = clutch, trigger = gripper, A/X = stop, right thumbstick up/down =
//     speed. Left grip held = move and turn the 3D arm (e.g. onto the real one), Y = put it back.
//   - Hands (controllers put down): right wrist = the controller, left pinch = clutch, right pinch
//     = gripper. Sent as a "right controller" with grip/trigger from the pinches (source "hands").
//   - Hand positions are sent in the 3D arm's frame (from its base, turned with it; "frame": "arm"):
//     once it sits on the real arm, the gripper moves the way the hand moves in the room, from any
//     side, and in the 1:1 mode it goes exactly where the hand is (grab the 3D gripper to start).
import * as THREE from "three";
import { XRScene } from "./xr-scene.js";
import { getArmFeed } from "./arm/arm-feed.js";

const clamp01 = (v) => Math.min(1, Math.max(0, v || 0));
// Pinch: thumb tip to index tip. Apart (6 cm+) = 0, touching (1.5 cm; the joints' centres) = 1.
const PINCH_OPEN_M = 0.06;
const PINCH_SHUT_M = 0.015;
const SPEED_STEP = 0.05; // per thumbstick flick
const PLACE_KEY = "lab-os.xr-arm-place"; // where the 3D arm was put, kept in this browser
const Y_AXIS = new THREE.Vector3(0, 1, 0);

function loadPlace() {
  try {
    const p = JSON.parse(localStorage.getItem(PLACE_KEY));
    if (p && [p.x, p.y, p.z, p.yaw].every(Number.isFinite)) return p;
  } catch {}
  return { x: 0, y: 0, z: 0, yaw: 0 };
}
function savePlace(p) {
  try {
    localStorage.setItem(PLACE_KEY, JSON.stringify(p));
  } catch {}
}
// The controller's heading around the vertical (radians), for turning the 3D arm.
function yawOf(quat) {
  const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(new THREE.Quaternion().fromArray(quat));
  return Math.atan2(-fwd.x, -fwd.z);
}

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

function jointPose(frame, hand, name, refSpace) {
  const space = hand.get(name);
  return space ? frame.getJointPose(space, refSpace) : null;
}
function pinch(frame, hand, refSpace) {
  const a = jointPose(frame, hand, "thumb-tip", refSpace);
  const b = jointPose(frame, hand, "index-finger-tip", refSpace);
  if (!a || !b) return 0;
  const p = a.transform.position, q = b.transform.position;
  const d = Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
  return clamp01((PINCH_OPEN_M - d) / (PINCH_OPEN_M - PINCH_SHUT_M));
}
// A tracked hand: with finger joints (the "hand-tracking" feature) its wrist and our own pinch;
// without them (the Quest then offers the hand like a controller: profile "oculus-hand" /
// "generic-hand", trigger = its pinch) the controller pose and the Quest's pinch.
const isHand = (src) => !!src.hand || (src.profiles || []).some((p) => p.includes("hand"));
function readHand(src, frame, refSpace) {
  if (!src.hand) {
    const c = readController(src, frame, refSpace);
    return { pos: c.pos, quat: c.quat, pinch: c.trigger };
  }
  const w = jointPose(frame, src.hand, "wrist", refSpace);
  const p = w && w.transform.position;
  const o = w && w.transform.orientation;
  return {
    pos: p ? [p.x, p.y, p.z] : null,
    quat: o ? [o.x, o.y, o.z, o.w] : null,
    pinch: w ? pinch(frame, src.hand, refSpace) : 0,
  };
}
// Bare hands → the message's "right controller": the right wrist moves it, the left pinch is the
// clutch (a dead-man: let go and the arm holds still), the right pinch closes the gripper.
export function handsAsController(h) {
  const none = { buttons: { thumbstick: false, a: false, b: false }, thumbstick: [0, 0] };
  const out = {};
  if (h.left) out.left = { pos: h.left.pos, quat: h.left.quat, trigger: 0, grip: 0, ...none };
  if (h.right) {
    out.right = {
      pos: h.right.pos, quat: h.right.quat,
      trigger: h.right.pinch, grip: h.left && h.left.pos ? h.left.pinch : 0, ...none,
    };
  }
  return out;
}
// Room → the 3D arm's frame: measured from its base, with its turn undone, so "toward the arm's
// front" is forward and the brain knows where the hand is relative to the arm (1:1 mode).
export function toArmFrame(c, yaw, base = new THREE.Vector3()) {
  if (!c.pos) return c;
  const turn = new THREE.Quaternion().setFromAxisAngle(Y_AXIS, -yaw);
  const pos = new THREE.Vector3().fromArray(c.pos).sub(base).applyQuaternion(turn);
  const quat = turn.multiply(new THREE.Quaternion().fromArray(c.quat));
  return { ...c, pos: pos.toArray(), quat: quat.toArray() };
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
  const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor", "hand-tracking"] });
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
  const tele = new TeleopSession(link, { ar, style, refType });
  const camera = new THREE.PerspectiveCamera(70, 1, 0.01, 50); // replaced by the headset's cameras
  await renderer.xr.setSession(session);

  ui.setActive("xr");
  session.addEventListener("end", () => {
    renderer.setAnimationLoop(null);
    tele.end();
    ui.setActive(null);
    ui.showHands({}, "XR session ended");
  });

  renderer.setAnimationLoop((t, frame) => {
    if (!frame) return;
    const { hands, source } = tele.frame(t, frame, renderer.xr.getReferenceSpace());
    ui.showHands(hands, source === "hands" ? "hands: left pinch = move, right pinch = gripper" : source ? "" : "no controllers or hands in view");
    renderer.render(tele.scene, camera);
  });
}

/**
 * One teleop session's work per XR frame: read the controllers (or hands), move the 3D arm with the
 * left grip, speed with the right thumbstick, send `xr_input` to the brain, update the scene. Used by
 * this page and by the hub in VR (its Teleop button), which renders `scene` inside its own session.
 */
export class TeleopSession {
  /** @param {{ar: boolean, style?: string, refType: string}} opts */
  constructor(link, { ar, style, refType }) {
    this.link = link;
    this.feed = getArmFeed(link);
    this.xrScene = new XRScene(this.feed, { ar, style });
    if (refType === "local") this.xrScene.setFloorOffset(-1.4);
    this.place = loadPlace();
    this.xrScene.setPlacement(this.place);
    this.drag = null; // while the left grip moves the 3D arm: where it and the controller started
    this.yWas = false;
    this.flick = 0;
  }
  get scene() {
    return this.xrScene.scene;
  }
  /** The session is over (or the hub's Teleop closed): the arm freezes and control is free again. */
  end() {
    this.link.send({ type: "session_end" });
  }
  /** Returns {hands, source} (what was read, for a readout). */
  frame(t, frame, refSpace) {
    const { link, feed, xrScene } = this;
    let hands = {};
    const bare = {};
    for (const src of frame.session.inputSources) {
      if (src.handedness !== "left" && src.handedness !== "right") continue;
      if (isHand(src)) bare[src.handedness] = readHand(src, frame, refSpace);
      else if (src.gamepad) hands[src.handedness] = readController(src, frame, refSpace);
    }
    // controllers win; hands only when no controller is in use (the Quest switches by itself)
    const source = hands.right || hands.left ? "controllers" : bare.right || bare.left ? "hands" : null;
    if (source === "hands") hands = handsAsController(bare);

    const left = hands.left, right = hands.right;
    if (source === "controllers") {
      // left grip: drag and turn the 3D arm (not while the right clutch is held: no jumps)
      if (left?.pos && left.grip > 0.6 && !(right && right.grip > 0.4)) {
        if (!this.drag) this.drag = { place: { ...this.place }, pos: left.pos, yaw: yawOf(left.quat) };
        const d = this.drag;
        this.place = {
          x: d.place.x + left.pos[0] - d.pos[0],
          y: d.place.y + left.pos[1] - d.pos[1],
          z: d.place.z + left.pos[2] - d.pos[2],
          yaw: d.place.yaw + yawOf(left.quat) - d.yaw,
        };
        xrScene.setPlacement(this.place);
      } else if (this.drag) {
        this.drag = null;
        savePlace(this.place);
      }
      const y = !!left?.buttons.b;
      if (y && !this.yWas) {
        this.place = { x: 0, y: 0, z: 0, yaw: 0 };
        xrScene.setPlacement(this.place);
        savePlace(this.place);
      }
      this.yWas = y;
      // right thumbstick up/down: speed, one step per flick
      const sy = right ? right.thumbstick[1] : 0;
      const dir = sy < -0.7 ? 1 : sy > 0.7 ? -1 : 0; // pushed up = negative y
      if (dir && dir !== this.flick && feed.status) {
        link.send({ type: "set_speed", speed_scale: feed.status.speed_scale + dir * SPEED_STEP });
      }
      this.flick = dir;
    }

    const sent = {};
    const base = xrScene.armBase();
    for (const [side, c] of Object.entries(hands)) sent[side] = toArmFrame(c, this.place.yaw, base);
    link.send({ type: "xr_input", t, frame: "arm", hands: sent, ...(source === "hands" ? { source } : {}) });
    xrScene.updateHands(hands, source, source === "hands" ? { left: bare.left?.pinch || 0, right: bare.right?.pinch || 0 } : null);
    return { hands, source };
  }
}
