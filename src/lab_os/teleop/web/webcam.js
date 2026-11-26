// Webcam teleop page (preview 2, /webcam): your bare hand in front of a webcam drives the arm.
// MediaPipe's hand landmarker (vendored in /web/vendor/mediapipe/, runs offline in the browser) finds
// the hands in each camera frame; webcam-hands.js turns them into the Quest's bare-hands `xr_input`,
// sent once per camera frame (about 30 a second). If the frames stop (tab hidden, page closed, a
// slow computer), the brain freezes the arm after 250 ms (dead-man).
// The browser gives the camera only to a secure page: open it on the brain's computer
// (http://localhost:8080/webcam) until the lab has its secure address.
import { getLink } from "./link.js";
import { gate } from "./control-gate.js";
import { deviceName } from "/web/device.js";
import { held } from "/web/words.js";
import { FilesetResolver, HandLandmarker } from "/web/vendor/mediapipe/vision_bundle.mjs";
import { WebcamHands, gripAmount, handAxes, pinchAmount, sidesOf, wristPosition } from "./webcam-hands.js";
import { color } from "/web/theme.js";

const $ = (id) => document.getElementById(id);
const link = getLink("input");
const MP = "/web/vendor/mediapipe";
// a new name (quick job 88): the right hand is now right by default, so a box ticked before is cleared
const SWAP_KEY = "lab-os.webcam-swap-2";
const DEPTH_KEY = "lab-os.webcam-depth";
const CAM_KEY = "lab-os.webcam-camera";
// palm and finger lines between MediaPipe's 21 landmarks, for the drawing
const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11],
  [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20]];

const STATES = {
  following: ["Following your right hand", "on"],
  holding: ["Holding: pinch with your left hand (or hold Space) to move", "off"],
  "no hand": ["Holding: show your right hand", "off"],
  frozen: ["Held still: open your left pinch (and let go of Space), then pinch again", "held"],
};

let landmarker = null;
let stream = null;
let running = false;
let space = false;
const hands = new WebcamHands();
const video = $("cam");
const canvas = $("overlay");
const ctx = canvas.getContext("2d");

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // storage blocked: the choice lasts until the page closes
  }
}
function stored(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function setPill(el, text, cls, why = "") {
  el.textContent = text;
  el.className = `pill ${cls}`;
  el.title = why;
}
const say = (text) => ($("msg").textContent = text);

// ---- the brain's status (same chips as the teleop page) ----------------------------------------
const CONTROL = {
  you: ["This page", "on"],
  other: ["Another page (it must leave first)", "warn"],
  free: ["Free", "off"],
  ai: ["The AI tools (until their move ends)", "warn"],
};
link.on("open", () => {
  setPill($("conn"), "Connected", "on");
  link.send({ type: "hello", agent: `webcam teleop; ${navigator.userAgent}`, device: deviceName() });
});
link.on("close", () => setPill($("conn"), "Disconnected", "off"));
link.on("error", (m) => say(m.message));
let brain = null; // the brain's last status: its own freeze wins over the page's "following"
link.on("status", (s) => {
  brain = s;
  const [text, cls] = CONTROL[s.control] || ["—", "off"];
  setPill($("control"), s.control === "other" && s.driver ? `The page on ${s.driver} (it must leave first)` : text, cls);
  // quick job 76: Start is grey while control can't be taken (Stop, while running, always works)
  if (!running) gate(s, [$("start")], $("control-why"));
  else $("control-why").hidden = true;
  if (s.arm?.connected === false) setPill($("state"), "Arm disconnected (USB)", "warn");
  else if (s.frozen) { const h = held(s.needs_release, "the clutch"); setPill($("state"), h.text, "held", h.why); }
  else if (s.clutch) setPill($("state"), "Following (clutch)", "on");
  else setPill($("state"), "Holding", "off");
  $("speed").textContent = `${Math.round(s.speed_scale * 100)}%`;
  const sp = $("speed-set");
  sp.disabled = false;
  sp.max = Math.round((s.max_speed_scale ?? 1) * 100);
  if (document.activeElement !== sp) sp.value = Math.round(s.speed_scale * 100);
  // the webcam drives relative only (the page doesn't know where the real arm is)
  if (s.mode && s.mode !== "relative" && running) link.send({ type: "set_mode", mode: "relative" });
});
$("speed-set").oninput = (e) => link.send({ type: "set_speed", speed_scale: e.target.value / 100 });
$("stop").onclick = () => link.send({ type: "stop" });

// ---- choices kept in this browser -----------------------------------------------------------------
$("swap").checked = stored(SWAP_KEY) === "1";
$("depth").checked = stored(DEPTH_KEY) !== "0";
$("swap").onchange = (e) => store(SWAP_KEY, e.target.checked ? "1" : "0");
$("depth").onchange = (e) => store(DEPTH_KEY, e.target.checked ? "1" : "0");

async function listCameras() {
  const sel = $("camera");
  const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
  const want = stored(CAM_KEY);
  sel.innerHTML = devices.map((d, i) => `<option value="${d.deviceId}">${d.label || `Camera ${i + 1}`}</option>`).join("");
  // the C615 by name, the first time (the arms' cameras are Innomaker ones: one program per camera)
  const pick = devices.find((d) => d.deviceId === want) || devices.find((d) => /C615/i.test(d.label));
  if (pick) sel.value = pick.deviceId;
  sel.disabled = running || devices.length === 0;
}
$("camera").onchange = async (e) => {
  store(CAM_KEY, e.target.value);
  if (running) {
    stopControl("Changing the camera.");
    await startControl();
  }
};

// ---- start and stop -------------------------------------------------------------------------------
async function loadModel() {
  if (landmarker) return landmarker;
  say("Loading the hand tracker (the first time takes a few seconds)…");
  const files = await FilesetResolver.forVisionTasks(`${MP}/wasm`);
  const options = (delegate) => ({
    baseOptions: { modelAssetPath: `${MP}/hand_landmarker.task`, delegate },
    runningMode: "VIDEO",
    numHands: 2,
    // stricter than MediaPipe's 0.5 (quick job 88: a left hand that wasn't there); webcam-hands.js
    // also wants a hand in several frames in a row
    minHandDetectionConfidence: 0.7,
    minHandPresenceConfidence: 0.7,
    minTrackingConfidence: 0.6,
  });
  try {
    landmarker = await HandLandmarker.createFromOptions(files, options("GPU"));
  } catch {
    landmarker = await HandLandmarker.createFromOptions(files, options("CPU")); // no WebGL2 here
  }
  return landmarker;
}

async function startControl() {
  if (!navigator.mediaDevices?.getUserMedia) {
    say("This page can't use a camera here. Open http://localhost:8080/webcam on the brain's computer.");
    return;
  }
  $("start").disabled = true;
  $("start").dataset.busy = "1"; // starting: the status doesn't enable it meanwhile
  try {
    await loadModel();
    const id = $("camera").value;
    stream = await navigator.mediaDevices.getUserMedia({
      video: { ...(id ? { deviceId: { exact: id } } : {}), width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
    });
  } catch (e) {
    $("start").disabled = false;
    $("start").dataset.busy = "";
    say(e.name === "NotReadableError"
      ? "Another program uses this camera. Close it, or pick another camera."
      : `Couldn't start the camera: ${e.message}`);
    return;
  }
  video.srcObject = stream;
  await video.play();
  $("cam-empty").hidden = true;
  running = true;
  hands.held = false;
  await listCameras(); // labels appear once the browser has the camera
  link.send({ type: "set_mode", mode: "relative" });
  $("start").disabled = false;
  $("start").dataset.busy = "";
  $("start").title = "";
  $("start").textContent = "Stop webcam control (` key)";
  $("stop-key").hidden = false;
  document.activeElement?.blur(); // Space on a focused button would click it
  say("");
  nextFrame();
}

function stopControl(why = "") {
  if (!running) return;
  running = false;
  link.send({ type: "session_end" }); // dead-man: the arm freezes, control is handed over
  stream?.getTracks().forEach((tr) => tr.stop());
  stream = null;
  video.srcObject = null;
  $("cam-empty").hidden = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  $("start").textContent = "Start webcam control";
  $("stop-key").hidden = true;
  $("camera").disabled = false;
  setPill($("hand-state"), "Off", "off");
  say(why);
}
$("start").onclick = () => (running ? stopControl() : startControl());

// ---- each camera frame --------------------------------------------------------------------------
let lastVideoTime = -1;
let fps = 0;
let lastFrameAt = 0;
function nextFrame() {
  if (!running) return;
  if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(onFrame);
  else requestAnimationFrame(onFrame);
}

function onFrame() {
  if (!running) return;
  const now = performance.now();
  if (video.currentTime !== lastVideoTime && video.videoWidth) {
    lastVideoTime = video.currentTime;
    const result = landmarker.detectForVideo(video, now);
    const w = video.videoWidth, h = video.videoHeight;
    const found = (result.landmarks || []).map((image, i) => ({
      image,
      world: result.worldLandmarks[i],
      label: result.handedness[i]?.[0]?.categoryName,
    }));
    const sides = sidesOf(found, $("swap").checked);
    const seen = found.map((f, i) => ({
      side: sides[i],
      pos: wristPosition(f.image, f.world, w, h, { depth: $("depth").checked }),
      // the left hand's pinch is the clutch; the right hand closes the gripper with a pinch or a
      // fist (quick job 120)
      pinch: sides[i] === "right" ? gripAmount(f.world) : pinchAmount(f.world),
      axes: handAxes(f.world), // the hand's turn → the wrist (quick job 88)
    }));
    const out = hands.step(seen, now / 1000, space);
    link.send(out.msg);
    if (lastFrameAt) fps += (1000 / (now - lastFrameAt) - fps) * 0.1;
    lastFrameAt = now;
    draw(found, sides, out);
    show(out, seen);
  }
  nextFrame();
}

function draw(found, sides, out) {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const css = (path) => `#${color(path).toString(16).padStart(6, "0")}`;
  // the moving hand cyan, the clutch hand amber (as on the teleop page's hints)
  const cols = { right: css("colors.primary"), left: css("colors.accent") };
  found.forEach((f, i) => {
    const c = cols[sides[i]] || css("colors.text_dim");
    const p = (k) => [f.image[k].x * canvas.width, f.image[k].y * canvas.height];
    ctx.strokeStyle = c;
    ctx.fillStyle = c;
    ctx.lineWidth = 3;
    for (const [a, b] of BONES) {
      ctx.beginPath();
      ctx.moveTo(...p(a));
      ctx.lineTo(...p(b));
      ctx.stroke();
    }
    for (let k = 0; k < 21; k++) {
      ctx.beginPath();
      ctx.arc(...p(k), k === 0 ? 9 : 4, 0, 2 * Math.PI);
      ctx.fill();
    }
  });
  canvas.dataset.state = out.state;
}

let lastShown = 0;
function show(out, seen) {
  const now = performance.now();
  if (now - lastShown < 100) return;
  lastShown = now;
  // The brain starts frozen and after any freeze (STOP, a dropped connection) wants the clutch let go
  let st = out.state;
  if (st === "following" && brain?.frozen) st = "frozen";
  else if (st === "following" && brain && brain.control !== "you") st = "holding";
  const [text, cls] = STATES[st];
  setPill($("hand-state"), text, cls);
  if (out.state === "frozen" && hands.why) say(`Held still because ${hands.why}.`);
  else if ($("msg").textContent.startsWith("Held still")) say("");
  $("clutch").textContent = `${Math.round(out.clutch * 100)}%${space ? " (Space)" : ""}`;
  $("pinch").textContent = `${Math.round(out.trigger * 100)}%`;
  const r = seen.find((s) => s.side === "right" && s.pos);
  $("dist").textContent = r && $("depth").checked ? `${Math.round(r.pos[2] * 100)} cm` : "—";
  $("fps").textContent = `${Math.round(fps)}`;
  const c = out.msg.hands.right;
  const n = (v) => (v >= 0 ? "+" : "") + v.toFixed(2);
  $("readout").textContent = `Webcam, ${seen.length} hand(s) seen\nright ${c.pos ? `pos ${c.pos.map(n).join(" ")}` : "tracking lost"}  grip ${c.grip.toFixed(2)}  trig ${c.trigger.toFixed(2)}`;
}

// ---- keys: Space = clutch, X = STOP, ` = leave (as on the other pages, quick job 120) ------------
document.addEventListener("keydown", (e) => {
  if (!running) return;
  if (e.code === "Space") {
    e.preventDefault();
    space = true;
  } else if (e.code === "KeyX" && !e.repeat) {
    e.preventDefault();
    link.send({ type: "stop" });
  } else if (e.code === "Backquote") {
    e.preventDefault();
    stopControl("Webcam control stopped. The arm holds.");
  }
});
document.addEventListener("keyup", (e) => e.code === "Space" && (space = false));
window.addEventListener("blur", () => (space = false));
document.addEventListener("visibilitychange", () => document.hidden && stopControl("The page was hidden, so webcam control stopped."));
window.addEventListener("pagehide", () => stopControl());

listCameras().catch(() => {});
