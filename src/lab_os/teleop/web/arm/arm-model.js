// 3D arm models, independent of any page: build one, add `model.object` to any three.js scene
// (the desktop view today, the Quest "ghost arm" later), and call `model.setJoints({...degrees})`.
//
//   loadArmModel("so101", { style: "mesh" | "stick" })   real SO-101 URDF (models/so101/)
//   loadArmModel("xarm1s", { style: "boxes" | "stick" }) xArm 1S from simple boxes/cylinders
//
// Joint names are shared across arms (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex,
// wrist_roll, gripper), angles in degrees, exactly as the Python `Arm` driver receives them.
// Models never clamp: a command outside the model's limits is drawn as-is and reported.
import * as THREE from "three";
import URDFLoader from "/static/vendor/urdf-loader/URDFLoader.js";

const DEG = Math.PI / 180;
const SO101_URDF = "/models/so101/so101_new_calib.urdf";
const COLORS = { body: 0xd2cfc5, joint: 0x2f6fde, stick: 0x3b3b38, jaw: 0xe0782f };

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

  /** Tint the whole arm (e.g. red when frozen); null = normal colors. */
  setTint(hex) {
    for (const m of this._materials) if (m.emissive) m.emissive.setHex(hex ?? 0x000000);
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

/** Robot descriptions are Z-up (URDF convention); three.js is Y-up. */
function zUp(object) {
  const g = new THREE.Group();
  object.rotation.x = -Math.PI / 2;
  g.add(object);
  return g;
}

// ---- SO-101 from its URDF -----------------------------------------------------------------
async function loadSo101(style) {
  // Wait for the URDF *and* every mesh it references (the manager fires onLoad when all are in).
  const robot = await new Promise((resolve, reject) => {
    const manager = new THREE.LoadingManager();
    const loader = new URDFLoader(manager);
    loader.parseVisual = style === "mesh";
    let result = null;
    manager.onLoad = () => (result ? resolve(result) : reject(new Error("URDF did not load")));
    manager.onError = (url) => reject(new Error(`could not load ${url}`));
    loader.load(SO101_URDF, (r) => (result = r));
  });

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
// Approximate dimensions (m), Z-up. Limits are placeholders until the xarm1 driver is measured.
const XARM1S = [
  { joint: "shoulder_pan", axis: [0, 0, 1], offset: [0, 0, 0.06], link: [0, 0, 0.035], size: [0.06, 0.05, 0.035], limits: [-120, 120] },
  { joint: "shoulder_lift", axis: [0, 1, 0], offset: [0, 0, 0.035], link: [0, 0, 0.1], size: [0.04, 0.03, 0.1], limits: [-120, 120] },
  { joint: "elbow_flex", axis: [0, 1, 0], offset: [0, 0, 0.1], link: [0, 0, 0.095], size: [0.035, 0.03, 0.095], limits: [-120, 120] },
  { joint: "wrist_flex", axis: [0, 1, 0], offset: [0, 0, 0.095], link: [0, 0, 0.04], size: [0.035, 0.03, 0.04], limits: [-120, 120] },
  { joint: "wrist_roll", axis: [0, 0, 1], offset: [0, 0, 0.04], link: [0, 0, 0.03], size: [0.05, 0.02, 0.03], limits: [-120, 120] },
  { joint: "gripper", axis: [1, 0, 0], offset: [0, 0.012, 0.03], link: [0, 0, 0.06], size: [0.012, 0.008, 0.06], limits: [0, 90] },
];

function buildXarm(style) {
  const root = new THREE.Group();
  root.add(style === "stick" ? stick([0, 0, 0], [0, 0, 0.06], 0.006, COLORS.stick) : boxAlong([0, 0, 0.06], [0.11, 0.09, 0.06]));
  const joints = {};
  let parent = root;
  for (const seg of XARM1S) {
    const frame = new THREE.Group();
    frame.position.set(...seg.offset);
    parent.add(frame);
    const axis = new THREE.Vector3(...seg.axis);
    joints[seg.joint] = {
      set: (deg) => frame.quaternion.setFromAxisAngle(axis, deg * DEG),
      lower: seg.limits[0],
      upper: seg.limits[1],
    };
    const color = seg.joint === "gripper" ? COLORS.jaw : COLORS.body;
    frame.add(style === "stick" ? stick([0, 0, 0], seg.link, 0.006, seg.joint === "gripper" ? COLORS.jaw : COLORS.stick) : boxAlong(seg.link, seg.size, color));
    frame.add(ball(style === "stick" ? 0.011 : 0.014, COLORS.joint));
    if (seg.joint === "gripper") {
      // fixed finger, mirrored on the other side of the palm
      const fixed = style === "stick" ? stick([0, 0, 0], seg.link, 0.005, COLORS.stick) : boxAlong(seg.link, seg.size, COLORS.body);
      fixed.position.y -= 2 * seg.offset[1];
      parent.add(fixed.translateZ(seg.offset[2]));
    }
    parent = frame;
  }
  return new ArmModel("xarm1s", style, zUp(root), joints);
}

function boxAlong(end, size, color = COLORS.body) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material(color));
  mesh.position.set(end[0] / 2, end[1] / 2, end[2] / 2);
  return mesh;
}

// ---- Entry point ----------------------------------------------------------------------------
export const MODEL_CHOICES = [
  { kind: "so101", style: "mesh", label: "SO-101 (URDF meshes)" },
  { kind: "so101", style: "stick", label: "SO-101 (stick figure)" },
  { kind: "xarm1s", style: "boxes", label: "xArm 1S (boxes)" },
  { kind: "xarm1s", style: "stick", label: "xArm 1S (stick figure)" },
];

export async function loadArmModel(kind, { style } = {}) {
  if (kind === "so101") return loadSo101(style || "mesh");
  if (kind === "xarm1s") return buildXarm(style || "boxes");
  throw new Error(`no 3D model for arm kind "${kind}"`);
}
