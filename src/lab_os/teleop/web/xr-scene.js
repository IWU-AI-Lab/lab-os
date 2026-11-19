// What the headset (or the WebXR emulator) shows during a session:
//   - the arm, driven by exactly what the driver receives (ArmFeed); a see-through "ghost" in AR
//   - a marker on each controller (green while the clutch is held) and a line from where you grabbed
//   - a floating status panel (connected / following / frozen, gripper, speed, hint)
//   - 1:1 mode: a see-through ball around the 3D gripper, where the hand grabs it to start
//   - VR only: a dim room with a floor grid and a table, so there's something to stand in
//   - two arms at once (a left feed with a status): the left arm too, in its own place, with its own
//     clutch line from the left hand; each 3D arm can be moved (setPlacement(place, "left"); xr.js)
// The arm stands on the table in front of you, facing away (you operate it from behind), until it's
// moved (setPlacement: e.g. onto the real arm, with the left grip; xr.js).
// Units: metres, WebXR local-floor space (+x right, +y up, -z forward).
import * as THREE from "three";
import { loadArmModel } from "./arm/arm-model.js";
import { color, theme } from "/web/theme.js";
import { panelText } from "./status-text.js";

const TABLE_TOP = 0.75;
const ARM_BASE = new THREE.Vector3(0, TABLE_TOP, -0.45);
// Arm/marker colors from config/theme.yaml. (The VR room below is not themed yet: design phase.)
const FROZEN_TINT = color("colors.frozen");
const CLUTCH_COLOR = color("colors.ok");
const IDLE_COLOR = color("arm3d.idle_marker");

export class XRScene {
  /**
   * @param {import("./arm/arm-feed.js").ArmFeed} feed  the brain's first arm (the right hand's)
   * @param {{ar: boolean, style?: string}} opts  style: "stick" for a light model (default: mesh/boxes)
   * @param {import("./arm/arm-feed.js").ArmFeed} [leftFeed]  the left hand's arm (two arms at once)
   */
  constructor(feed, { ar, style }, leftFeed = null) {
    this.feed = feed;
    this.leftFeed = leftFeed;
    this.ar = ar;
    this.style = style;
    this.scene = new THREE.Scene();
    this.root = new THREE.Group(); // shifted down if the headset has no floor-level space
    this.scene.add(this.root);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x666660, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(0.5, 2.5, 1.0);
    this.scene.add(sun);

    if (!ar) this._addRoom();
    this._addArmStand();
    this.hands = { left: this._handMarker(), right: this._handMarker() };
    for (const h of Object.values(this.hands)) this.root.add(h);
    this.clutchLine = this._clutchLine();
    this.root.add(this.clutchLine);
    this.leftLine = this._clutchLine(); // two arms: from where the left hand grabbed
    this.root.add(this.leftLine);
    this._leftWas = false;
    this._leftAnchor = null;
    this.panel = new StatusPanel();
    this.panel.mesh.position.set(0.48, 1.12, -0.62);
    this.panel.mesh.rotation.y = -0.35; // turned toward the user
    this.root.add(this.panel.mesh);

    this.arm = null;
    this._clutchWas = false;
    this._anchor = null;
    this.armLeft = null;
    feed.onChange(() => this._applyFeed());
    leftFeed?.onChange(() => this._applyLeft());
    this._loadArm(feed.modelKind || "so101");
  }

  /** Move a 3D arm ("right": the first arm; "left": two arms' left one) from its usual spot by
   * {x, y, z} metres and turn it by `yaw` radians. */
  setPlacement({ x, y, z, yaw }, slot = "right") {
    const holder = slot === "left" ? this.leftHolder : this.armHolder;
    holder.position.set(ARM_BASE.x + x, ARM_BASE.y + y, ARM_BASE.z + z);
    holder.rotation.y = Math.PI / 2 + yaw;
  }

  /** Where the 3D arm's base is, in the same space as the hands' positions (WebXR space; the
   * hands are drawn under `root` as they come), for hand positions relative to it. Not the world
   * position: with a "local" space `root` is shifted down 1.4 m, and the hand would look 1.4 m
   * from the gripper to the brain (found 2026-11-16, quick job 13). */
  armBase(slot = "right") {
    const holder = slot === "left" ? this.leftHolder : this.armHolder;
    holder.updateWorldMatrix(true, false);
    return this.root.worldToLocal(holder.getWorldPosition(new THREE.Vector3()));
  }

  /** "local" reference spaces put y = 0 at the head; move the content down to roughly the floor. */
  setFloorOffset(y) {
    this.root.position.y = y;
  }

  async _loadArm(kind) {
    this.armKind = kind;
    const style = this.style === "stick" ? "stick" : kind === "so101" ? "mesh" : "boxes";
    const arm = await loadArmModel(kind, { style });
    if (this.armKind !== kind) return;
    if (this.arm) this.armHolder.remove(this.arm.object);
    this.arm = arm;
    if (this.ar) arm.setOpacity(0.55);
    this.armHolder.add(arm.object);
    this._applyFeed();
  }

  /** Two arms at once: the left arm's model, shown only while the brain drives a left arm. */
  async _loadLeft(kind) {
    this.leftKind = kind;
    const style = this.style === "stick" ? "stick" : kind === "so101" ? "mesh" : "boxes";
    const arm = await loadArmModel(kind, { style });
    if (this.leftKind !== kind) return;
    if (this.armLeft) this.leftHolder.remove(this.armLeft.object);
    this.armLeft = arm;
    if (this.ar) arm.setOpacity(0.55);
    this.leftHolder.add(arm.object);
    this._applyLeft();
  }

  _applyLeft() {
    const f = this.leftFeed;
    this.leftHolder.visible = !!f?.status;
    if (!f?.status) return;
    if (f.modelKind && f.modelKind !== this.leftKind) this._loadLeft(f.modelKind);
    if (this.armLeft) {
      this.armLeft.setJoints(f.joints);
      this.armLeft.setTint(f.frozen ? FROZEN_TINT : null);
    }
  }

  _applyFeed() {
    const f = this.feed;
    if (f.modelKind && f.modelKind !== this.armKind) this._loadArm(f.modelKind);
    if (this.arm) {
      this.arm.setJoints(f.joints);
      this.arm.setTint(f.frozen ? FROZEN_TINT : null);
    }
    this.panel.update(f);
  }

  /** Called every XR frame with the controller states (in room space), their source
   * ("controllers" / "hands" / null) and, for hands, each one's pinch (0..1). */
  /** 1:1 mode, not holding: a ball around the 3D gripper point, green once the hand is in it. */
  _updateGrabZone(clutch) {
    const s = this.feed.status;
    const tip = this.arm?.object.getObjectByName("gripper_frame_link");
    const show = !!(s && s.mode === "one_to_one" && s.hand_gap_cm != null && !clutch && tip);
    this.grabZone.visible = show;
    if (!show) return;
    this.grabZone.position.copy(this.root.worldToLocal(tip.getWorldPosition(new THREE.Vector3())));
    this.grabZone.scale.setScalar((s.capture_cm || 8) / 100);
    this.grabZone.material.color.setHex(s.hand_gap_cm <= s.capture_cm ? CLUTCH_COLOR : IDLE_COLOR);
  }

  /** `moving`: two arms, Y held (the grips move the 3D arms; the panel says so). */
  updateHands(hands, source = "controllers", pinches = null, moving = false) {
    // No right controller or hand: say so, and how to leave, instead of looking broken
    // (2026-10-29: the builder got stuck in the page).
    const missing = !hands.right?.pos;
    if (missing !== this.panel.noController || source !== this.panel.source || moving !== this.panel.moving) {
      this.panel.noController = missing;
      this.panel.source = source;
      this.panel.moving = moving;
      this.panel.update(this.feed);
    }
    const clutch = !!this.feed.status?.clutch && !this.feed.frozen;
    const lf = this.leftFeed?.status ? this.leftFeed : null; // two arms at once
    const leftClutch = !!lf?.status.clutch && !lf.frozen;
    this._updateGrabZone(clutch);
    for (const [side, marker] of Object.entries(this.hands)) {
      const c = hands[side];
      marker.visible = !!(c && c.pos);
      if (!marker.visible) continue;
      marker.position.fromArray(c.pos);
      marker.quaternion.fromArray(c.quat);
      // hands: the ball grows as the fingers close; the left one is green while its pinch holds the
      // clutch (the server engages above 0.6), the right one while the arm follows
      const p = pinches ? pinches[side] : 0;
      marker.userData.ball.scale.setScalar(1 + 1.5 * p);
      const on = side === "right" ? clutch : lf && !pinches ? leftClutch : !!pinches && p > 0.6;
      marker.userData.ball.material.color.setHex(on ? CLUTCH_COLOR : IDLE_COLOR);
    }
    const right = hands.right;
    if (clutch && right?.pos) {
      if (!this._clutchWas || !this._anchor) this._anchor = new THREE.Vector3().fromArray(right.pos);
      const pts = this.clutchLine.geometry.attributes.position;
      pts.setXYZ(0, this._anchor.x, this._anchor.y, this._anchor.z);
      pts.setXYZ(1, right.pos[0], right.pos[1], right.pos[2]);
      pts.needsUpdate = true;
      this.clutchLine.visible = true;
    } else {
      this.clutchLine.visible = false;
      this._anchor = null;
    }
    this._clutchWas = clutch;
    const left = hands.left;
    if (leftClutch && left?.pos) {
      if (!this._leftWas || !this._leftAnchor) this._leftAnchor = new THREE.Vector3().fromArray(left.pos);
      const pts = this.leftLine.geometry.attributes.position;
      pts.setXYZ(0, this._leftAnchor.x, this._leftAnchor.y, this._leftAnchor.z);
      pts.setXYZ(1, left.pos[0], left.pos[1], left.pos[2]);
      pts.needsUpdate = true;
      this.leftLine.visible = true;
    } else {
      this.leftLine.visible = false;
      this._leftAnchor = null;
    }
    this._leftWas = leftClutch;
  }

  // ---- building blocks -------------------------------------------------------------------
  _addRoom() {
    this.scene.background = new THREE.Color(0x17191c);
    this.scene.fog = new THREE.Fog(0x17191c, 3, 14); // hides the floor edge
    const floor = new THREE.Mesh(new THREE.CircleGeometry(40, 64), new THREE.MeshStandardMaterial({ color: 0x24272b, roughness: 1 }));
    floor.rotation.x = -Math.PI / 2;
    this.root.add(floor);
    const grid = new THREE.GridHelper(8, 32, 0x4a4f57, 0x33373d);
    grid.position.y = 0.001;
    this.root.add(grid);
    // table: top + four legs
    const wood = new THREE.MeshStandardMaterial({ color: 0x8a7458, roughness: 0.8 });
    const top = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.03, 0.55), wood);
    top.position.set(ARM_BASE.x, TABLE_TOP - 0.015, ARM_BASE.z - 0.05);
    this.root.add(top);
    for (const [x, z] of [[-0.37, -0.24], [0.37, -0.24], [-0.37, 0.24], [0.37, 0.24]]) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(0.04, TABLE_TOP - 0.03, 0.04), wood);
      leg.position.set(ARM_BASE.x + x, (TABLE_TOP - 0.03) / 2, ARM_BASE.z - 0.05 + z);
      this.root.add(leg);
    }
  }

  _addArmStand() {
    this.armHolder = new THREE.Group();
    this.armHolder.position.copy(ARM_BASE);
    this.armHolder.rotation.y = Math.PI / 2; // robot +x (its forward) → away from the user (-z)
    this.root.add(this.armHolder);
    this.leftHolder = new THREE.Group(); // two arms at once: placed by xr.js, hidden until then
    this.leftHolder.position.copy(ARM_BASE);
    this.leftHolder.rotation.y = Math.PI / 2;
    this.leftHolder.visible = false;
    this.root.add(this.leftHolder);
    // 1:1 mode: the grab zone around the gripper point (the brain's capture distance)
    this.grabZone = new THREE.Mesh(
      new THREE.SphereGeometry(1, 24, 16),
      new THREE.MeshBasicMaterial({ color: CLUTCH_COLOR, transparent: true, opacity: 0.18, depthWrite: false }),
    );
    this.grabZone.visible = false;
    this.root.add(this.grabZone);
    if (this.ar) {
      // a faint footprint, so the floating ghost arm reads as "standing" somewhere
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.06, 0.07, 48),
        new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5, side: THREE.DoubleSide }),
      );
      ring.rotation.x = -Math.PI / 2;
      this.armHolder.add(ring);
      this.leftHolder.add(ring.clone());
    }
  }

  _handMarker() {
    const g = new THREE.Group();
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.014, 20, 14), new THREE.MeshStandardMaterial({ color: IDLE_COLOR }));
    g.add(ball);
    g.userData.ball = ball;
    // little axes: red = right, green = up, blue = back (the controller's own frame)
    const axes = new THREE.AxesHelper(0.06);
    axes.material.depthTest = false;
    g.add(axes);
    // a short pointer showing where the controller faces
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.008, 0.035, 12), new THREE.MeshStandardMaterial({ color: color("colors.primary") }));
    tip.rotation.x = -Math.PI / 2;
    tip.position.z = -0.04;
    g.add(tip);
    g.visible = false;
    return g;
  }

  _clutchLine() {
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 0, 0, 0], 3));
    const line = new THREE.Line(geom, new THREE.LineDashedMaterial({ color: CLUTCH_COLOR, dashSize: 0.01, gapSize: 0.006 }));
    line.frustumCulled = false;
    line.visible = false;
    return line;
  }
}

/* ---------- the status panel, in the hub's design (quick job 37; docs/design/DESIGN.md) ----------
   A cut-corner box like the hub's panels: dark see-through fill, a hairline frame with a bright lead-in in
   the state's colour. The state first, as a chip (its colour says how serious: cyan normal, green following,
   amber waiting or warm, rust held still with a pause icon, gray offline); then Gripper and Speed, small CAPS
   labels over numbers in the digit font; then the hint in the light font. Colours and fonts from the theme.
   The fill stays nearly opaque so it reads over a bright room in AR as well as in VR. */
const TC = theme.colors || {};
const PC = {
  bg: TC.background || "#05080b", line: TC.line || "#1f3d48", text: TC.text || "#d4eef5",
  dim: TC.text_dim || "#6d8c96", primary: TC.primary || "#29d4ff", accent: TC.accent || "#ff9a2e",
  offline: TC.offline || "#56636a", ok: TC.ok || "#3ee07f", frozen: TC.frozen || "#7a1d00",
};
const TF = theme.font || {};
const PF = {
  ui: TF.family || "'Chakra Petch', system-ui, sans-serif",
  lines: TF.lines || "Inter, system-ui, sans-serif",
  linesW: TF.lines_weight || 300,
  digits: TF.digits || "DSEG7, monospace",
  spacing: theme.font?.label_spacing_em ?? 0.12,
};
const BLANK = /DSEG/.test(PF.digits) ? "!" : " "; // a digit-wide blank, so numbers don't shift
const W = 960, H = 450; // canvas pixels for the 0.42 × 0.197 m panel
const LEVEL = { // state → colour, chip text colour, icon
  normal: [PC.primary, PC.primary, null], following: [PC.ok, PC.ok, "dot"], warning: [PC.accent, PC.accent, "warn"],
  held: [PC.frozen, PC.text, "pause"], offline: [PC.offline, PC.offline, null],
};

/** A canvas-textured plane with the teleop status, redrawn only when what it says changes. */
export class StatusPanel {
  constructor() {
    this.canvas = document.createElement("canvas");
    this.canvas.width = W;
    this.canvas.height = H;
    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.anisotropy = 4;
    this.mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(0.42, 0.197), // bigger text than a screen's (DESIGN.md: Quest headset)
      new THREE.MeshBasicMaterial({ map: this.texture, transparent: true }),
    );
    this.key = "";
    this.last = null;
    this.update(null);
    // the bundled fonts may still be loading: draw again once they're there
    const want = [`600 40px ${PF.ui}`, `500 40px ${PF.ui}`, `${PF.linesW} 40px ${PF.lines}`, `40px ${PF.digits}`];
    Promise.all(want.map((f) => document.fonts?.load(f).catch(() => null))).then(() => { this.key = ""; this.update(this.last); });
  }

  update(feed) {
    this.last = feed;
    const t = panelText(feed, this.noController, this.source, this.moving);
    const key = JSON.stringify(t);
    if (key === this.key) return;
    this.key = key;
    const g = this.canvas.getContext("2d");
    const [col] = LEVEL[t.level];
    g.clearRect(0, 0, W, H);
    // the box: cut corners top left and bottom right, a nearly opaque fill, a hairline frame
    cutPath(g, 3, 3, W - 6, H - 6, 34);
    g.fillStyle = rgba(PC.bg, 0.9); g.fill();
    g.lineWidth = 2; g.strokeStyle = rgba(PC.line, 1); g.stroke();
    // the lead-in: the frame's first stretch in the state's colour (glows only while following)
    g.save();
    if (t.level === "following") { g.shadowColor = PC.ok; g.shadowBlur = 12; }
    g.strokeStyle = col; g.lineWidth = 4; g.beginPath();
    g.moveTo(3, 3 + 34 + 70); g.lineTo(3, 3 + 34); g.lineTo(3 + 34, 3); g.lineTo(3 + 34 + 220, 3); g.stroke();
    g.restore();
    // the state, as a chip; two arms at once: the left arm's chip on the left, the right arm's after it
    if (t.left) {
      const half = (W - 88 - 24) / 2;
      chip(g, 44, half, t.left.state, t.left.level);
      chip(g, 44 + half + 24, half, t.state, t.level);
    } else chip(g, 44, W - 88, t.state, t.level);
    // gripper and speed: a small CAPS label over a number in the digit font, its unit after it
    fact(g, 44, 176, t.left ? "Right gripper" : "Gripper", t.gripper, t.gripper == null ? "" : "% open");
    if (t.speed) fact(g, 500, 176, t.speed.label, t.speed.value, t.speed.unit);
    else fact(g, 500, 176, "Speed", null, "");
    // a hairline, then the hint in the light font, its parts apart (no dot separators)
    g.strokeStyle = rgba(PC.line, 1); g.lineWidth = 2;
    g.beginPath(); g.moveTo(44, 352); g.lineTo(W - 44, 352); g.stroke();
    hintLine(g, t.hint, 44, 398, W - 88);
    this.texture.needsUpdate = true;
  }
}

/** The state as a chip at x (at most `width` wide): its level's colour and icon, the words in CAPS,
 * shrunk to fit. */
function chip(g, x0, width, state, level) {
  const [col, chipText, ico] = LEVEL[level];
  const chipH = 92, y0 = 40;
  g.textBaseline = "middle";
  g.font = `600 52px ${PF.ui}`; spaced(g, PF.spacing);
  const word = state.toUpperCase();
  const iconW = ico ? 56 : 0;
  let tw = g.measureText(word).width;
  const maxW = width - 48 - iconW;
  if (tw > maxW) { g.font = `600 ${Math.floor((52 * maxW) / tw)}px ${PF.ui}`; tw = g.measureText(word).width; }
  cutPath(g, x0, y0, tw + 48 + iconW, chipH, 14);
  g.fillStyle = level === "held" ? PC.frozen : rgba(col, 0.16); g.fill();
  g.lineWidth = 2; g.strokeStyle = rgba(col, level === "held" ? 1 : 0.7); g.stroke();
  if (ico) drawIcon(g, ico, x0 + 24 + 20, y0 + chipH / 2, chipText);
  g.fillStyle = chipText; g.textAlign = "left";
  g.fillText(word, x0 + 24 + iconW, y0 + chipH / 2 + 2);
  spaced(g, 0);
}

/** One fact: label (small CAPS, dim), then the value (digits, padded to 3 places) and its unit. */
function fact(g, x, y, label, value, unit) {
  g.textAlign = "left"; g.textBaseline = "alphabetic";
  g.font = `500 28px ${PF.ui}`; spaced(g, PF.spacing); g.fillStyle = PC.dim;
  g.fillText(label.toUpperCase(), x, y + 24);
  spaced(g, 0);
  let vx = x;
  if (value != null) {
    const digits = String(value);
    g.font = `76px ${PF.digits}`; g.fillStyle = PC.text;
    const shown = BLANK.repeat(Math.max(0, 3 - digits.length)) + digits;
    g.fillText(shown, x, y + 120);
    vx += g.measureText(shown).width + 14;
  } else if (!unit) {
    g.font = `500 40px ${PF.ui}`; g.fillStyle = PC.offline;
    g.fillText("none yet", x, y + 112);
    return;
  }
  g.font = `500 34px ${PF.ui}`; g.fillStyle = PC.text;
  g.fillText(unit, vx, y + 116);
}

/** The hint's parts on one line, apart, shrunk to fit. */
function hintLine(g, parts, x, y, maxW) {
  let px = 34, gap;
  for (;;) {
    g.font = `${PF.linesW} ${px}px ${PF.lines}`;
    gap = px * 1.4;
    const w = parts.reduce((a, p) => a + g.measureText(p).width, 0) + gap * (parts.length - 1);
    if (w <= maxW || px <= 18) break;
    px -= 2;
  }
  g.textAlign = "left"; g.textBaseline = "middle"; g.fillStyle = PC.dim;
  let cx = x;
  parts.forEach((p, i) => {
    g.fillText(p, cx, y);
    cx += g.measureText(p).width;
    if (i < parts.length - 1) { // a short vertical tick between parts
      g.fillStyle = rgba(PC.line, 1); g.fillRect(cx + gap / 2 - 1, y - px * 0.35, 2, px * 0.7); g.fillStyle = PC.dim;
      cx += gap;
    }
  });
}

/** The state's icon, line-drawn: a dot (following), a warning triangle, a pause sign (held). */
function drawIcon(g, kind, cx, cy, color) {
  g.save();
  g.strokeStyle = color; g.fillStyle = color; g.lineWidth = 4; g.lineJoin = "round"; g.lineCap = "round";
  if (kind === "dot") { g.beginPath(); g.arc(cx, cy, 11, 0, Math.PI * 2); g.fill(); }
  else if (kind === "warn") {
    g.beginPath(); g.moveTo(cx, cy - 20); g.lineTo(cx + 22, cy + 18); g.lineTo(cx - 22, cy + 18); g.closePath(); g.stroke();
    g.beginPath(); g.moveTo(cx, cy - 6); g.lineTo(cx, cy + 5); g.stroke();
    g.beginPath(); g.arc(cx, cy + 11, 2, 0, Math.PI * 2); g.fill();
  } else if (kind === "pause") { g.fillRect(cx - 12, cy - 16, 8, 32); g.fillRect(cx + 4, cy - 16, 8, 32); }
  g.restore();
}

/** A box with 45° cut corners, top left and bottom right (the hub's panels). */
function cutPath(g, x, y, w, h, c) {
  g.beginPath();
  g.moveTo(x + c, y); g.lineTo(x + w, y); g.lineTo(x + w, y + h - c);
  g.lineTo(x + w - c, y + h); g.lineTo(x, y + h); g.lineTo(x, y + c);
  g.closePath();
}

function spaced(g, em) {
  if ("letterSpacing" in g) g.letterSpacing = `${em}em`;
}

function rgba(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
