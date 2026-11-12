// Pointing in VR: a ray from each controller (or each hand: the Quest gives hands a pointing ray too),
// a thin beam that fades along its length, and a small reticle where it lands. Things you can point at
// are meshes with userData.hit = an object with hit(u, v) → what's there (or null), where (u, v) is the
// point on the plane (0..1, v up). The trigger or a pinch ("select") presses what that ray is on.
// On a screen (the preview) the mouse is the pointer.
import * as THREE from "three";
import { C } from "./draw.js";

const MAX = 6; // metres
export class Pointer {
  constructor(scene) {
    this.scene = scene;
    this.ray = new THREE.Raycaster();
    this.rays = {}; // per input source (handedness): {beam, reticle, hit}
    this.targets = [];
  }
  /** Things that can be pointed at (visible ones only are tested). */
  setTargets(list) { this.targets = list; }

  _visuals(key) {
    if (this.rays[key]) return this.rays[key];
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 0, 0, -1], 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute([...new THREE.Color(C.primary).toArray(), 0, 0, 0], 3));
    const beam = new THREE.Line(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false }));
    beam.renderOrder = 90; beam.frustumCulled = false;
    const reticle = new THREE.Group();
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.009, 0.012, 32), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.hot), transparent: true, depthTest: false, depthWrite: false }));
    const dot = new THREE.Mesh(new THREE.CircleGeometry(0.003, 16), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, depthTest: false, depthWrite: false }));
    reticle.add(ring, dot);
    for (const o of [ring, dot]) o.renderOrder = 91;
    this.scene.add(beam, reticle);
    return (this.rays[key] = { beam, reticle, ring, hit: null, obj: null });
  }

  /**
   * One pointer's ray this frame (world space). Returns what it's on: {obj, what, point} or null.
   * key: "left" / "right" / "mouse". show: draw the beam (not for the mouse).
   */
  update(key, origin, dir, show = true) {
    const v = this._visuals(key);
    this.ray.set(origin, dir);
    this.ray.far = MAX;
    const hits = this.ray.intersectObjects(this.targets.filter((o) => o.visible && worldVisible(o)), false);
    let found = null;
    for (const h of hits) {
      const what = h.object.userData.hit?.hit(h.uv?.x ?? 0, h.uv?.y ?? 0);
      if (what) { found = { obj: h.object, what, point: h.point, dist: h.distance, normal: h.face?.normal }; break; }
    }
    const len = found ? found.dist : 1.2;
    const end = origin.clone().addScaledVector(dir, len);
    const pos = v.beam.geometry.attributes.position;
    pos.setXYZ(0, origin.x, origin.y, origin.z); pos.setXYZ(1, end.x, end.y, end.z); pos.needsUpdate = true;
    v.beam.visible = show;
    v.reticle.visible = !!found;
    if (found) {
      v.reticle.position.copy(found.point);
      v.reticle.quaternion.copy(found.obj.getWorldQuaternion(new THREE.Quaternion()));
      v.reticle.scale.setScalar(Math.max(0.6, found.dist / 2.2));
    }
    v.hit = found;
    return found;
  }
  hide(key) { const v = this.rays[key]; if (v) { v.beam.visible = false; v.reticle.visible = false; v.hit = null; } }
  hitOf(key) { return this.rays[key]?.hit || null; }
  /** Everything any pointer is on (for hover). */
  all() { return Object.values(this.rays).map((r) => r.hit).filter(Boolean); }
}

function worldVisible(o) {
  for (let p = o; p; p = p.parent) if (!p.visible) return false;
  return true;
}
