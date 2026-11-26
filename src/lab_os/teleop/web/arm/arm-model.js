// 3D arm models, independent of any page: build one, add `model.object` to any three.js scene
// (the desktop views and the Quest's ghost arm), and call `model.setJoints({...degrees})`.
//
//   loadArmModel("so101", { style: "mesh" | "stick" })   real SO-101 URDF (models/so101/)
//   loadArmModel("xarm1s", { style: "boxes" | "stick" }) xArm 1S from simple boxes/cylinders
//
// Joint names are shared across arms (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex,
// wrist_roll, gripper), angles in degrees, exactly as the Python `Arm` driver receives them.
// Models never clamp: a command outside the model's limits is drawn as-is and reported.
import * as THREE from "three";
import { loadRobotUrdf, queueModelLoad, zUp } from "/web/robot-urdf.js";
import { color } from "/web/theme.js";

const DEG = Math.PI / 180;
const SO101_URDF = "/models/so101/so101_new_calib.urdf";
// All colors come from config/theme.yaml (design tokens).
const COLORS = {
  body: color("arm3d.body"),
  joint: color("colors.primary"),
  stick: color("arm3d.stick"),
  jaw: color("colors.accent"),
};
const HELD_RING = color("colors.frozen_text"); // the "held still" ring around the base

export class ArmModel {
  /** @param {THREE.Object3D} object  @param {Record<string, {set(deg:number):void, lower:number, upper:number}>} joints */
  constructor(kind, style, object, joints) {
    this.kind = kind;
    this.style = style;
    this.object = object;
    this.joints = joints;
    this.jointNames = Object.keys(joints);
    this._materials = [];
    object.traverse((o) => {
      if (o.isMesh) {
        o.material = o.material.clone(); // own materials, so ghost/tint never leak between models
        o.material.userData.baseOpacity = o.material.opacity;
        this._materials.push(o.material);
      }
    });
  }

  /** Apply joint angles (degrees). Returns {unknown: [...names], outOfRange: [...names]}. */
  setJoints(degrees) {
    const unknown = [];
    const outOfRange = [];
    for (const [name, value] of Object.entries(degrees)) {
      const j = this.joints[name];
      if (!j) {
        unknown.push(name);
        continue;
      }
      j.set(value);
      if (value < j.lower - 0.01 || value > j.upper + 0.01) outOfRange.push(name); // 0.01° slack for float noise
    }
    return { unknown, outOfRange };
  }

  /** Ghost look for overlays: 1 = solid, e.g. 0.35 = see-through. */
  setOpacity(alpha) {
    for (const m of this._materials) {
      m.transparent = alpha < 1;
      m.opacity = m.userData.baseOpacity * alpha;
      m.depthWrite = alpha >= 1;
    }
  }

  /** Tint the whole arm; null = normal colors. */
  setTint(hex) {
    for (const m of this._materials) if (m.emissive) m.emissive.setHex(hex ?? 0x000000);
  }

  /** Held still (the brain froze it): the body keeps its steel, and a muted rust ring lies on the floor
   * around the base (docs/design/DESIGN.md → "Held"; quick job 153: a rust tint made the arm salmon pink). */
  setHeld(on) {
    if (!this._heldRing) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.075, 0.085, 48),
        new THREE.MeshBasicMaterial({ color: HELD_RING, transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthWrite: false }),
      );
      ring.rotation.x = -Math.PI / 2; // flat on the floor: the scenes are y-up
      ring.position.y = 0.002;
      ring.renderOrder = 1;
      this._heldRing = ring;
    }
    if (on && !this._heldRing.parent) this.object.add(this._heldRing);
    else if (!on && this._heldRing.parent) this.object.remove(this._heldRing);
  }
}

// ---- Shared helpers --------------------------------------------------------------------
function material(color) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.05 });
}

/** A cylinder from point a to point b (local coordinates of whatever it's added to). */
function stick(a, b, radius, color) {
  const from = new THREE.Vector3(...a);
  const to = new THREE.Vector3(...b);
  const length = from.distanceTo(to);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 12), material(color));
  mesh.position.copy(from).add(to).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), to.clone().sub(from).normalize());
  return mesh;
}

function ball(radius, color) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 16, 12), material(color));
}

// ---- SO-101 from its URDF -----------------------------------------------------------------
async function loadSo101(style) {
  const robot = await loadRobotUrdf(SO101_URDF, { parseVisual: style === "mesh" });

  if (style === "stick") addSkeleton(robot);
  robot.traverse((o) => {
    if (o.isMesh && style === "mesh") o.material = new THREE.MeshStandardMaterial({ color: COLORS.body, roughness: 0.7 });
  });

  const joints = {};
  for (const [name, j] of Object.entries(robot.joints)) {
    if (j.jointType === "fixed") continue;
    j.ignoreLimits = true; // draw exactly what was commanded, even outside the limits
    joints[name] = {
      set: (deg) => robot.setJointValue(name, deg * DEG),
      lower: j.limit.lower / DEG,
      upper: j.limit.upper / DEG,
    };
  }
  return new ArmModel("so101", style, zUp(robot), joints);
}

/** Stick figure from the URDF's own joint frames, so it matches the mesh model exactly. */
function addSkeleton(robot) {
  robot.updateMatrixWorld(true);
  for (const link of Object.values(robot.links)) {
    for (const child of link.children) {
      if (!child.isURDFJoint) continue;
      link.add(stick([0, 0, 0], child.position.toArray(), 0.006, COLORS.stick));
      if (child.jointType !== "fixed") child.add(ball(0.011, COLORS.joint));
    }
  }
  // The moving jaw is a leaf link: draw it toward the fixed fingertip (as seen with all joints at 0).
  const jaw = robot.links.moving_jaw_so101_v1_link;
  const tip = robot.links.gripper_frame_link;
  if (jaw && tip) {
    const tipInJaw = jaw.worldToLocal(tip.getWorldPosition(new THREE.Vector3()));
    jaw.add(stick([0, 0, 0], tipInJaw.toArray(), 0.005, COLORS.jaw));
  }
  robot.links.base_link.add(new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.01, 32), material(COLORS.stick)).rotateX(Math.PI / 2));
}

// ---- xArm 1S from primitives --------------------------------------------------------------
// Dimensions from Hiwonder's xArm 1S drawing (mm): shoulder axis 65 above the table, shoulder→elbow
// 101, elbow→wrist 95, wrist→fingertips 168 (364 − 101 − 95), base plate 154 × 140, gripper 96 wide
// when open, both fingers move. Z-up, arm faces +x, upright at all-zero (like the drawing).
// Same joint conventions as the SO-101 (so the teleop signs carry over): +pan swings the arm to its
// right, +lift / +elbow / +wrist_flex tilt forward-down. Limits are placeholders (servos ±120°)
// until the xarm1 driver is measured; gripper 0 = closed, 90 = open.
const XARM_COLORS = Object.fromEntries(
  ["metal", "servo", "plate", "cup", "board"].map((part) => [part, color(`arm3d.xarm.${part}`)]),
);
const XARM = {
  pan: { z: 0.039, limits: [-120, 120] },
  lift: { z: 0.065, limits: [-120, 120] }, // absolute height of the shoulder axis
  upper: 0.101,
  fore: 0.095,
  wristToRoll: 0.045,
  rollToPivot: 0.05,
  finger: 0.07,
  pivotY: 0.012,
  maxOpenDeg: 35, // each finger's swing at gripper = 90
};

/** A box from point a to point b (like stick(), but square-ish in section). */
function beam(a, b, w, d, color) {
  const from = new THREE.Vector3(...a);
  const to = new THREE.Vector3(...b);
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, from.distanceTo(to), d), material(color));
  mesh.position.copy(from).add(to).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), to.clone().sub(from).normalize());
  return mesh;
}

function box(size, color, pos) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(...size), material(color));
  m.position.set(...pos);
  return m;
}

function zCylinder(r, h, color, pos) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 28), material(color));
  m.rotation.x = Math.PI / 2;
  m.position.set(...pos);
  return m;
}

function buildXarm(style) {
  const C = XARM_COLORS;
  const stickMode = style === "stick";
  const root = new THREE.Group();
  const frame = (parent, pos, axis) => {
    const g = new THREE.Group();
    g.position.set(...pos);
    g.userData.axis = new THREE.Vector3(...axis);
    parent.add(g);
    return g;
  };
  const pan = frame(root, [0, 0, XARM.pan.z], [0, 0, -1]);
  const lift = frame(pan, [0, 0, XARM.lift.z - XARM.pan.z], [0, 1, 0]);
  const elbow = frame(lift, [0, 0, XARM.upper], [0, 1, 0]);
  const wrist = frame(elbow, [0, 0, XARM.fore], [0, 1, 0]);
  const roll = frame(wrist, [0, 0, XARM.wristToRoll], [0, 0, 1]);
  const fingers = [1, -1].map((side) => frame(roll, [0, side * XARM.pivotY, XARM.rollToPivot], [1, 0, 0]));

  // Finger outline (in its own frame): out-and-up, then the tip curls back in, like the claw.
  const fingerPts = (side) => [
    [0, 0, 0],
    [0, side * 0.014, 0.045],
    [0, side * -0.01, XARM.finger], // tips meet near the middle when closed
  ];

  if (stickMode) {
    const r = 0.006;
    root.add(new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.01, 32), material(COLORS.stick)).rotateX(Math.PI / 2));
    root.add(stick([0, 0, 0], [0, 0, XARM.pan.z], r, COLORS.stick));
    pan.add(stick([0, 0, 0], lift.position.toArray(), r, COLORS.stick));
    lift.add(stick([0, 0, 0], elbow.position.toArray(), r, COLORS.stick));
    elbow.add(stick([0, 0, 0], wrist.position.toArray(), r, COLORS.stick));
    wrist.add(stick([0, 0, 0], roll.position.toArray(), r, COLORS.stick));
    roll.add(stick([0, -XARM.pivotY, XARM.rollToPivot], [0, XARM.pivotY, XARM.rollToPivot], 0.004, COLORS.stick));
    roll.add(stick([0, 0, 0], [0, 0, XARM.rollToPivot], r, COLORS.stick));
    for (const [i, side] of [1, -1].entries()) {
      const [a, b, c] = fingerPts(side);
      fingers[i].add(stick(a, b, 0.004, COLORS.jaw), stick(b, c, 0.004, COLORS.jaw));
    }
    for (const f of [pan, lift, elbow, wrist, roll]) f.add(ball(0.011, COLORS.joint));
  } else {
    // Base: suction cups, two acrylic plates with standoffs, controller board, pan servo.
    for (const [x, y] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      root.add(zCylinder(0.013, 0.012, C.cup, [x * 0.0715, y * 0.0635, 0.006]));
      root.add(zCylinder(0.003, 0.014, C.metal, [x * 0.06, y * 0.055, 0.029]));
    }
    root.add(box([0.154, 0.14, 0.003], C.plate, [0, 0, 0.0215]));
    root.add(box([0.154, 0.14, 0.003], C.plate, [0, 0, 0.0365]));
    root.add(box([0.05, 0.045, 0.004], C.board, [0.045, 0, 0.026]));
    root.add(box([0.04, 0.02, 0.012], C.servo, [0, 0, 0.029]));
    // Turntable + U-bracket up to the shoulder servo.
    pan.add(zCylinder(0.032, 0.006, C.servo, [0, 0, 0.003]));
    for (const y of [0.025, -0.025]) pan.add(box([0.03, 0.003, 0.03], C.metal, [0, y, 0.02]));
    pan.add(box([0.022, 0.042, 0.04], C.servo, [0, 0, XARM.lift.z - XARM.pan.z]));
    // Upper arm and forearm: paired side brackets, servo at the far end.
    for (const [link, len] of [[lift, XARM.upper], [elbow, XARM.fore]]) {
      for (const y of [0.025, -0.025]) link.add(box([0.026, 0.003, len], C.metal, [0, y, len / 2]));
      link.add(box([0.022, 0.042, 0.04], C.servo, [0, 0, len]));
    }
    // Wrist: short bracket + roll servo (shaft along the arm).
    for (const y of [0.022, -0.022]) wrist.add(box([0.026, 0.003, 0.03], C.metal, [0, y, 0.015]));
    wrist.add(box([0.04, 0.02, 0.03], C.servo, [0, 0, 0.028]));
    // Gripper base: palm, gear plate, gripper servo sticking out the back.
    roll.add(box([0.022, 0.056, 0.012], C.metal, [0, 0, 0.012]));
    roll.add(box([0.006, 0.044, 0.04], C.metal, [0.01, 0, 0.034]));
    roll.add(box([0.03, 0.02, 0.04], C.servo, [-0.022, 0, 0.032]));
    for (const [i, side] of [1, -1].entries()) {
      const [a, b, c] = fingerPts(side);
      fingers[i].add(beam(a, b, 0.008, 0.004, C.metal), beam(b, c, 0.008, 0.004, C.metal));
      fingers[i].add(zCylinder(0.006, 0.004, C.servo, [0, 0, 0]).rotateY(Math.PI / 2));
    }
  }

  const rotate = (g, deg) => g.quaternion.setFromAxisAngle(g.userData.axis, deg * DEG);
  const revolute = (g, limits) => ({ set: (deg) => rotate(g, deg), lower: limits[0], upper: limits[1] });
  const servo = [-120, 120];
  const joints = {
    shoulder_pan: revolute(pan, XARM.pan.limits),
    shoulder_lift: revolute(lift, XARM.lift.limits),
    elbow_flex: revolute(elbow, servo),
    wrist_flex: revolute(wrist, servo),
    wrist_roll: revolute(roll, servo),
    gripper: {
      // both fingers swing out symmetrically: 0 = closed, 90 = fully open
      set: (deg) => {
        const a = (deg / 90) * XARM.maxOpenDeg;
        rotate(fingers[0], -a); // +y finger opens toward +y
        rotate(fingers[1], a);
      },
      lower: 0,
      upper: 90,
    },
  };
  return new ArmModel("xarm1s", style, zUp(root), joints);
}

// ---- Entry point ----------------------------------------------------------------------------
export const MODEL_CHOICES = [
  { kind: "so101", style: "mesh", label: "SO-101 (URDF meshes)" },
  { kind: "so101", style: "stick", label: "SO-101 (stick figure)" },
  { kind: "xarm1s", style: "boxes", label: "xArm 1S (boxes)" },
  { kind: "xarm1s", style: "stick", label: "xArm 1S (stick figure)" },
];

export function loadArmModel(kind, { style } = {}) {
  return queueModelLoad(() => {
    if (kind === "so101") return loadSo101(style || "mesh");
    if (kind === "xarm1s") return buildXarm(style || "boxes");
    throw new Error(`no 3D model for arm kind "${kind}"`);
  });
}
