// What the headset (or the WebXR emulator) shows during a session:
//   - the arm, driven by exactly what the driver receives (ArmFeed); a see-through "ghost" in AR
//   - a marker on each controller (green while the clutch is held) and a line from where you grabbed
//   - a floating status panel (connected / following / frozen, gripper, speed, hint)
//   - VR only: a dim room with a floor grid and a table, so there's something to stand in
// The arm stands on the table in front of you, facing away (you operate it from behind).
// Units: metres, WebXR local-floor space (+x right, +y up, -z forward).
import * as THREE from "three";
import { loadArmModel } from "./arm/arm-model.js";
import { color, theme } from "./theme.js";

const TABLE_TOP = 0.75;
const ARM_BASE = new THREE.Vector3(0, TABLE_TOP, -0.45);
// Arm/marker colors from config/theme.yaml. (The VR room below is not themed yet: design phase.)
const FROZEN_TINT = color("colors.frozen");
const CLUTCH_COLOR = color("colors.ok");
const IDLE_COLOR = color("arm3d.idle_marker");
const FONT = theme.font?.family || "system-ui, sans-serif";

export class XRScene {
  /**
   * @param {import("./arm/arm-feed.js").ArmFeed} feed
   * @param {{ar: boolean, style?: string}} opts  style: "stick" for a light model (default: mesh/boxes)
   */
  constructor(feed, { ar, style }) {
    this.feed = feed;
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
    this.panel = new StatusPanel();
    this.panel.mesh.position.set(0.42, 1.12, -0.62);
    this.panel.mesh.rotation.y = -0.35; // turned toward the user
    this.root.add(this.panel.mesh);

    this.arm = null;
    this._clutchWas = false;
    this._anchor = null;
    feed.onChange(() => this._applyFeed());
    this._loadArm(feed.modelKind || "so101");
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

  _applyFeed() {
    const f = this.feed;
    if (f.modelKind && f.modelKind !== this.armKind) this._loadArm(f.modelKind);
    if (this.arm) {
      this.arm.setJoints(f.joints);
      this.arm.setTint(f.frozen ? FROZEN_TINT : null);
    }
    this.panel.update(f);
  }

  /** Called every XR frame with the controller states this page just sent. */
  updateHands(hands) {
    // No right controller (asleep, off, or the headset switched to hand tracking): say so, and how
    // to leave, instead of looking broken (2026-10-29: the builder got stuck in the page).
    const missing = !hands.right?.pos;
    if (missing !== this.panel.noController) {
      this.panel.noController = missing;
      this.panel.update(this.feed);
    }
    const clutch = !!this.feed.status?.clutch && !this.feed.frozen;
    for (const [side, marker] of Object.entries(this.hands)) {
      const c = hands[side];
      marker.visible = !!(c && c.pos);
      if (!marker.visible) continue;
      marker.position.fromArray(c.pos);
      marker.quaternion.fromArray(c.quat);
      marker.userData.ball.material.color.setHex(side === "right" && clutch ? CLUTCH_COLOR : IDLE_COLOR);
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
    if (this.ar) {
      // a faint footprint, so the floating ghost arm reads as "standing" somewhere
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.06, 0.07, 48),
        new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5, side: THREE.DoubleSide }),
      );
      ring.rotation.x = -Math.PI / 2;
      this.armHolder.add(ring);
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

/** A canvas-textured plane with the teleop status, redrawn only when the text changes. */
class StatusPanel {
  constructor() {
    this.canvas = document.createElement("canvas");
    this.canvas.width = 640;
    this.canvas.height = 300;
    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(0.32, 0.15),
      new THREE.MeshBasicMaterial({ map: this.texture, transparent: true }),
    );
    this.key = "";
    this.update(null);
  }

  update(feed) {
    const s = feed?.status;
    const state = this.noController ? ["NO CONTROLLER", "#e0662e"]
      : !s ? ["CONNECTING…", "#8a8a84"]
      : feed.frozen ? [s.needs_release ? "FROZEN · release grip" : "FROZEN", "#e0662e"]
      : s.clutch ? ["FOLLOWING", "#2fbf71"]
      : ["HOLDING", "#b8b8b2"];
    let gripper = "—";
    if (s && feed.joints.gripper !== undefined && s.limits?.gripper) {
      const [lo, hi] = s.limits.gripper;
      gripper = `${Math.round(((feed.joints.gripper - lo) / (hi - lo)) * 100)}% open`;
    }
    const speed = s ? `${Math.round(s.speed_scale * 100)}%` : "—";
    const key = `${state[0]}|${gripper}|${speed}|${this.noController}`;
    if (key === this.key) return;
    this.key = key;

    const g = this.canvas.getContext("2d");
    g.clearRect(0, 0, 640, 300);
    g.fillStyle = "rgba(20, 22, 25, 0.82)";
    roundRect(g, 4, 4, 632, 292, 28);
    g.fill();
    g.strokeStyle = state[1];
    g.lineWidth = 6;
    g.stroke();
    fitText(g, state[0], 36, 92, 568, "bold", 58, state[1]);
    fitText(g, `Gripper ${gripper}   ·   Speed ${speed}`, 36, 168, 568, "", 40, "#ececea");
    const hint = this.noController
      ? "Pick up the controllers · Leave: palm up + pinch"
      : "Hold grip = move · Trigger = gripper · A/X = stop";
    fitText(g, hint, 36, 246, 568, "", 32, "#9a9a94");
    this.texture.needsUpdate = true;
  }
}

/** Draw text at up to `size` px, shrinking it until it fits `maxWidth`. */
function fitText(g, text, x, y, maxWidth, weight, size, color) {
  let px = size;
  do {
    g.font = `${weight} ${px}px ${FONT}`;
    px -= 2;
  } while (g.measureText(text).width > maxWidth && px > 12);
  g.fillStyle = color;
  g.fillText(text, x, y);
}

function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}
