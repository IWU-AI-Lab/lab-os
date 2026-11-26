// The hub's VR and AR Raspbot (quick job 107): drive raspbot1 with its camera as your eyes.
//   - The left stick drives (forward, back, turn), through the Raspbot page's socket (/ws/raspbot): the
//     same brain path, STOP and freeze as the Raspbot page (quick job 72). Let go: the car stops.
//   - The window opens in front of you. Point at it and hold a grip to move it.
//     The head and the right stick turn the camera's servos. HEAD turns head control on or off.
//   - The direction you look when the module opens is the camera's centre. CENTRE (or a press on the
//     right stick) sets it again. The Raspbot keeps each servo inside its own limits.
//   - PICTURE saves one picture and RECORD starts and stops a recording, on the brain's computer; the
//     status line says where. STOP (or A / X) stops the car. B or Y closes the module, as do Back and Exit.
import * as THREE from "three";
import { C, CanvasPlane, FONT, arrive, icon, rgba, spaced } from "./draw.js";

const PX = 900;
const DEAD = 0.15; // stick dead zone
const DRIVE_MS = 100; // a held stick is sent again this often (the brain's freeze is 300 ms)
const LOOK_MS = 50;
const STICK_DEG_S = 60; // the right stick turns the camera this fast
const LOOK_MAX = 90;
const DIST = 1.2; // initial viewing distance, in metres
const RAD = Math.PI / 180;
const BAR = [
  { kind: "stop", label: "STOP", ico: "i-stop", danger: true },
  { kind: "rasp", op: "head", label: "HEAD", ico: "i-hand" },
  { kind: "rasp", op: "centre", label: "CENTRE", ico: "i-target" },
  { kind: "rasp", op: "picture", label: "PICTURE", ico: "i-cam" },
  { kind: "rasp", op: "record", label: "RECORD", ico: "i-hist" },
];
const clampDeg = (v) => Math.max(-LOOK_MAX, Math.min(LOOK_MAX, v));

/** Your head's turn (yaw, + = left) and tilt (pitch, + = up), in degrees, from its orientation. */
export function headAngles(q) {
  const f = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
  return { yaw: (Math.atan2(-f.x, -f.z) * 180) / Math.PI, pitch: (Math.asin(Math.max(-1, Math.min(1, f.y))) * 180) / Math.PI };
}
const wrap180 = (d) => ((((d + 180) % 360) + 360) % 360) - 180;

export class RaspbotModule {
  constructor() {
    this.group = new THREE.Group();
    this.video = new CanvasPlane(1.2, 0.9, 640 / 1.2);
    this.video.mesh.position.set(0, -0.08, 0);
    this.video.mesh.userData.hit = { hit: () => ({ kind: "page" }) };
    this.group.add(this.video.mesh);
    this.bar = new CanvasPlane(1.2, 0.12, PX);
    this.bar.mesh.userData.hit = this;
    this.bar.mesh.position.set(0, -0.62, 0);
    this.group.add(this.bar.mesh);
    this.line = new CanvasPlane(1.2, 0.07, PX);
    this.line.mesh.position.set(0, -0.74, 0);
    this.group.add(this.line.mesh);
    this.tally = new CanvasPlane(0.26, 0.07, PX);
    this.tally.mesh.position.set(-0.45, 0.31, 0.01);
    this.tally.mesh.visible = false;
    this.group.add(this.tally.mesh);
    this.hover = null;
    this.link = { send: (m) => this._send(m) }; // STOP from the bar (hub.js sends it)
  }
  targets() { return [this.bar.mesh, this.video.mesh]; }
  hit(u) { const b = BAR[Math.min(BAR.length - 1, Math.floor(u * BAR.length))]; return b.op ? { kind: b.kind, op: b.op } : { kind: b.kind }; }

  open(now) {
    this.t0 = now;
    this.placed = false;
    this.drag = null;
    this.grips = {};
    this.headOn = true;
    this.lastT = now;
    this.status = null;
    this.said = { text: "", t: -Infinity, bad: false };
    this.btn = {};
    this.group.position.set(0, 0, -DIST);
    this.group.rotation.set(0, 0, 0);
    this.group.scale.setScalar(0.4);
    this.centre = null; // the next head pose is the centre
    this.stick = { pan: 0, tilt: 0 };
    this.look = { ...this.stick };
    this._connect();
    this.img = document.createElement("img");
    this.img.style.cssText = "position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none";
    this.img.onerror = () => { this.imgOk = false; this.retry = setTimeout(() => this._camera(), 3000); };
    this.img.onload = () => { this.imgOk = true; };
    document.body.appendChild(this.img);
    this._camera();
  }
  close() {
    this.closed = true;
    clearTimeout(this.retry);
    if (this.ws) { this._send({ type: "release" }); this.ws.close(); this.ws = null; } // the car stops
    if (this.img) { this.img.onload = this.img.onerror = null; this.img.removeAttribute("src"); this.img.remove(); this.img = null; }
  }
  _camera() { if (this.img) { this.imgOk = false; this.img.src = `/api/raspbot/camera.mjpg?t=${Date.now()}`; } }
  _connect() {
    this.closed = false;
    this.sent = { look: null, lookT: 0, driveT: 0, driving: false };
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/raspbot`);
    ws.onmessage = (e) => this._message(JSON.parse(e.data));
    ws.onclose = () => {
      if (this.ws !== ws || this.closed) return;
      this.status = null;
      setTimeout(() => this.ws === ws && this._connect(), 2000);
    };
    this.ws = ws;
  }
  _send(m) { if (this.ws?.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify(m));
    return true; }
  _say(text, bad = false) { this.said = { text, t: performance.now(), bad }; }
  _message(m) {
    if (m.type === "raspbot_status") {
      const hadCam = this.status?.camera;
      this.status = m;
      if (m.camera && !hadCam && !this.imgOk) this._camera();
    } else if (m.type === "error") this._say(m.message, true);
    else if (m.type === "saved") {
      if (m.what === "picture") this._say(`Picture saved: ${m.path}`);
      else if (m.on) this._say(`Recording to ${m.path}`);
      else this._say(m.path ? `Recording saved: ${m.path}` : "No recording was on.");
    }
  }

  /** A press on the bar (`what`: {kind: "rasp", op}). STOP goes through hub.js. */
  press(what) {
    if (what.op === "centre") {
      this.centre = null;
      this.stick = { pan: 0, tilt: 0 };
      this._say(this.headOn ? "The camera's centre is where you look now." : "Camera centred.");
    } else if (what.op === "head") {
      this.headOn = !this.headOn;
      this.stick = { ...this.look }; // switching modes keeps the camera's current direction
      this.centre = null;
    } else if (what.op === "picture") this._send({ type: "picture" });
    else if (what.op === "record") this._send({ type: "record", on: !this.status?.recording });
  }

  /** Each XR frame (xr-hub.js): the head turns the camera, the sticks drive and turn it, A / X is STOP. */
  input(frame, ref, now, hitOf) {
    const pose = frame.getViewerPose(ref);
    if (!pose) { this.drag = null; return; }
    const o = pose.transform.orientation, p = pose.transform.position;
    const head = headAngles(new THREE.Quaternion(o.x, o.y, o.z, o.w));
    if (!this.placed) {
      const yaw = head.yaw * RAD;
      const at = new THREE.Vector3(p.x - DIST * Math.sin(yaw), p.y, p.z - DIST * Math.cos(yaw));
      this.group.position.copy(this.group.parent.worldToLocal(at));
      this.group.rotation.y = yaw - this.group.parent.rotation.y;
      this.placed = true;
    }
    this.moveWindow(frame, ref, hitOf);
    const dt = Math.min(0.1, (now - (this.lastT || now)) / 1000);
    this.lastT = now;
    let drive = null;
    for (const src of frame.session.inputSources) {
      const gp = src.gamepad, key = src.handedness;
      if (!gp || (key !== "left" && key !== "right")) continue;
      const x = gp.axes[2] || 0, y = gp.axes[3] || 0;
      const a = !!gp.buttons[4]?.pressed; // A (right) / X (left): STOP
      if (a && !this.btn[`a${key}`]) this.link.send({ type: "stop" });
      this.btn[`a${key}`] = a;
      if (key === "left") { if (Math.hypot(x, y) > DEAD) drive = [-y, x]; }
      else {
        if (Math.abs(x) > DEAD) this.stick.pan = clampDeg(this.stick.pan - x * STICK_DEG_S * dt);
        if (Math.abs(y) > DEAD) this.stick.tilt = clampDeg(this.stick.tilt - y * STICK_DEG_S * dt);
        const press = !!gp.buttons[3]?.pressed; // the right stick, pressed: the centre again
        if (press && !this.btn.stick) this.press({ op: "centre" });
        this.btn.stick = press;
      }
    }
    this.centre ||= head;
    this.look = {
      pan: clampDeg(this.stick.pan + (this.headOn ? wrap180(head.yaw - this.centre.yaw) : 0)),
      tilt: clampDeg(this.stick.tilt + (this.headOn ? head.pitch - this.centre.pitch : 0)),
    };
    const s = this.sent;
    const moved = !s.look || Math.abs(s.look.pan - this.look.pan) > 0.5 || Math.abs(s.look.tilt - this.look.tilt) > 0.5;
    if (moved && now - s.lookT > LOOK_MS && this._send({ type: "look", ...this.look })) {
      s.look = { ...this.look }; s.lookT = now;
    }
    if (drive && now - s.driveT > DRIVE_MS) { this._send({ type: "drive", dir: "stick", stick: drive }); s.driveT = now; s.driving = true; }
    else if (!drive && s.driving) { this._send({ type: "release" }); s.driving = false; }
  }

  /** Like the 3D arm, the window follows the grip's translation and turn from the grab pose. */
  moveWindow(frame, ref, hitOf) {
    const grips = {};
    let held = false;
    for (const src of frame.session.inputSources) {
      const key = src.handedness;
      if (!src.gripSpace || (key !== "left" && key !== "right")) continue;
      const down = (src.gamepad?.buttons[1]?.value ?? 0) > 0.6;
      grips[key] = down;
      if (!down || (this.drag && this.drag.key !== key)) continue;
      const pose = frame.getPose(src.gripSpace, ref);
      if (!pose) continue;
      const hit = hitOf(key);
      if (!this.drag && (this.grips?.[key] || hit?.obj.parent !== this.group)) continue;
      const { position: p, orientation: q } = pose.transform;
      const pos = this.group.parent.worldToLocal(new THREE.Vector3(p.x, p.y, p.z));
      const yaw = headAngles(new THREE.Quaternion(q.x, q.y, q.z, q.w)).yaw;
      this.drag ||= { key, pos, yaw, start: this.group.position.clone(), turn: this.group.rotation.y };
      this.group.position.copy(pos).sub(this.drag.pos).add(this.drag.start);
      this.group.rotation.y = this.drag.turn + wrap180(yaw - this.drag.yaw) * RAD;
      held = true;
    }
    if (!held) this.drag = null;
    this.grips = grips;
  }

  step(dt, now, cameraPos, hits) {
    const k = arrive((now - this.t0) / 600);
    this.group.scale.setScalar(0.4 + 0.6 * k);
    this._paintVideo(now);
    this.hover = hits.find((h) => h.obj === this.bar.mesh)?.what || null;
    this._paintBar();
    this._paintTally();
    this._paintLine();
  }
  _paintVideo(now) {
    if (now - (this.vidT || 0) < 90) return;
    this.vidT = now;
    const g = this.video.g, w = this.video.canvas.width, h = this.video.canvas.height;
    if (this.imgOk && this.img?.naturalWidth) {
      try { g.drawImage(this.img, 0, 0, w, h); this.video.tex.needsUpdate = true; this.video.key = null; return; } catch { /* not decoded yet */ }
    }
    this.video.paint((g2) => {
      g2.fillStyle = rgba(C.bg, 0.9); g2.fillRect(0, 0, w, h);
      g2.strokeStyle = rgba(C.primary, 0.5); g2.lineWidth = 3; g2.strokeRect(2, 2, w - 4, h - 4);
      icon(g2, "i-cam", w / 2, h / 2 - 30, 60, C.dim, 1.6);
      g2.font = `${FONT.linesW} 22px ${FONT.lines}`; g2.fillStyle = C.dim; g2.textAlign = "center"; g2.textBaseline = "middle";
      g2.fillText(this.status && !this.status.camera ? "This Raspbot sends no camera picture." : "Waiting for the camera's picture…", w / 2, h / 2 + 40);
    }, `none|${this.status?.camera}`);
  }
  _paintBar() {
    const over = this.hover ? `${this.hover.kind}${this.hover.op || ""}` : "", rec = !!this.status?.recording;
    this.bar.paint((g, w, h) => {
      const bw = w / BAR.length, gap = h * 0.1;
      BAR.forEach((b, i) => {
        const x = i * bw + gap / 2, on = over === `${b.kind}${b.op || ""}`, lit = b.op === "record" && rec;
        const head = b.op === "head", active = lit || (head && this.headOn);
        const col = b.danger || lit ? C.danger : C.primary, cut = h * 0.22, width = bw - gap;
        g.save(); g.translate(x, 0);
        g.beginPath(); g.moveTo(cut, 0); g.lineTo(width, 0); g.lineTo(width, h - cut); g.lineTo(width - cut, h); g.lineTo(0, h); g.lineTo(0, cut); g.closePath();
        g.fillStyle = rgba(C.bg, 0.92); g.fill();
        if (on || active || b.danger) { g.fillStyle = rgba(col, on ? 0.4 : 0.2); g.fill(); }
        g.strokeStyle = on || active ? col : rgba(col, 0.7); g.lineWidth = 3; g.stroke();
        icon(g, b.ico, h * 0.45, h / 2, h * 0.36, on ? C.hot : col, 1.6);
        g.font = `700 ${h * 0.23}px ${FONT.ui}`; spaced(g, 0.1);
        g.fillStyle = on ? C.hot : C.text; g.textAlign = "left"; g.textBaseline = "middle";
        g.fillText(lit ? "END REC" : head ? `HEAD ${this.headOn ? "ON" : "OFF"}` : b.label, h * 0.72, h / 2); spaced(g, 0);
        g.restore();
      });
    }, `${over}|${rec}|${this.headOn}`);
  }
  _paintTally() {
    this.tally.mesh.visible = !!this.status?.recording;
    if (!this.tally.mesh.visible) return;
    const seconds = this.status.recording_seconds ?? 0;
    this.tally.paint((g, w, h) => {
      g.fillStyle = rgba(C.bg, 0.92); g.fillRect(0, 0, w, h);
      g.fillStyle = C.danger;
      g.beginPath(); g.arc(h / 2, h / 2, h * 0.14, 0, Math.PI * 2); g.fill();
      g.font = `${FONT.linesW} ${h * 0.48}px ${FONT.lines}`;
      g.fillStyle = C.text; g.textBaseline = "middle";
      g.fillText(`${seconds} s`, h * 0.95, h / 2);
    }, seconds);
  }
  _paintLine() {
    const s = this.status, fresh = performance.now() - this.said.t < 6000;
    let text, bad = false;
    if (fresh) ({ text, bad } = this.said);
    else if (!s) text = "Connecting to the brain…";
    else if (!s.connected) { text = s.message || `${s.name} is not connected.`; bad = true; }
    else if (!s.may_drive) { text = `View only: ${s.address || "this headset"} is not in drive_from.`; bad = true; }
    else {
      const who = { free: "control: free", you: "control: you", other: "control: another page" }[s.control];
      const pan = Math.round(this.look.pan), tilt = Math.round(this.look.tilt);
      text = `${s.name}   ${s.moving ? "driving" : "stopped"}   ${who}   camera ${pan}°, ${tilt}°`;
    }
    this.line.paint((g, w, h) => {
      g.fillStyle = rgba(C.bg, 0.85); g.fillRect(0, 0, w, h);
      g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = bad ? C.accent : C.text;
      let size = h * 0.42;
      g.font = `${FONT.linesW} ${size}px ${FONT.lines}`;
      const tw = g.measureText(text).width;
      if (tw > w * 0.96) { size *= (w * 0.96) / tw; g.font = `${FONT.linesW} ${size}px ${FONT.lines}`; }
      g.fillText(text, w / 2, h / 2);
    }, `${text}|${bad}`);
  }
}
