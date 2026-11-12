// The far layer in VR: the designed hub's network of dots (design.html → stepNetwork), around you.
// Dots on a shell 6–11 m away, linked when close (the closer, the brighter). After the jump's flash they
// streak in from the middle ahead and settle on the brake's curve, arriving white-hot and cooling to the
// main color. Now and then a pulse runs along a few links; while the assistant thinks the pulses run
// toward the core, while it speaks away from it (faster when it's louder), like the hub.
import * as THREE from "three";
import { theme } from "/web/theme.js";
import { C, clamp, dotTexture, rand } from "./draw.js";

const N = theme.quality?.default === "maximal" ? 200 : 150;
const LINK = 2.6; // metres: dots closer than this are linked

export class Network {
  constructor() {
    this.home = [];
    for (let i = 0; i < N; i++) {
      const d = new THREE.Vector3().randomDirection();
      if (d.y < -0.45) d.y = -d.y * 0.5; // mostly not under the floor
      if (d.z > 0.2 && Math.random() < 0.4) d.z = -d.z; // a few more in front, where you look
      this.home.push(d.normalize().multiplyScalar(rand(6, 11)));
    }
    this.pos = this.home.map((p) => p.clone());
    // links: up to 3 nearest within LINK
    const seen = new Set();
    this.edges = [];
    this.home.forEach((p, i) => {
      this.home.map((q, j) => [j, p.distanceTo(q)]).filter(([j, d]) => j !== i && d < LINK).sort((a, b) => a[1] - b[1]).slice(0, 3).forEach(([j, d]) => {
        const key = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (!seen.has(key)) { seen.add(key); this.edges.push([i, j, 1 - d / LINK]); }
      });
    });
    this.linkPos = new Float32Array(this.edges.length * 6);
    this.linkCol = new Float32Array(this.edges.length * 6);
    const lg = new THREE.BufferGeometry();
    lg.setAttribute("position", new THREE.BufferAttribute(this.linkPos, 3).setUsage(THREE.DynamicDrawUsage));
    lg.setAttribute("color", new THREE.BufferAttribute(this.linkCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.links = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.dotPos = new Float32Array(N * 3);
    const dg = new THREE.BufferGeometry();
    dg.setAttribute("position", new THREE.BufferAttribute(this.dotPos, 3).setUsage(THREE.DynamicDrawUsage));
    this.dotMat = new THREE.PointsMaterial({ size: 0.11, map: dotTexture(), color: new THREE.Color(C.primary), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    this.dots = new THREE.Points(dg, this.dotMat);
    // the arrival's streaks: a short line behind each dot while it flies in
    this.streakPos = new Float32Array(N * 6);
    this.streakCol = new Float32Array(N * 6);
    const sg = new THREE.BufferGeometry();
    sg.setAttribute("position", new THREE.BufferAttribute(this.streakPos, 3).setUsage(THREE.DynamicDrawUsage));
    sg.setAttribute("color", new THREE.BufferAttribute(this.streakCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.streaks = new THREE.LineSegments(sg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.group = new THREE.Group();
    this.group.add(this.links, this.dots, this.streaks);
    for (const o of [this.links, this.dots, this.streaks]) { o.frustumCulled = false; o.renderOrder = -1; } // the far layer: under everything
    this.from = this.home.map(() => new THREE.Vector3(rand(-1.5, 1.5), rand(-1, 1), -rand(30, 60))); // ahead, in the middle
    this.pulses = Array.from({ length: 12 }, () => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color: new THREE.Color(C.hot), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
      s.scale.setScalar(0.28);
      s.renderOrder = -1;
      this.group.add(s);
      return { s, e: null, t: 0, dir: 1, hops: 0, wait: rand(0, 4) };
    });
    this.color = new THREE.Color(C.primary);
    this.hot = new THREE.Color(C.hot);
    this.arriveK = 1;
    this.core = new THREE.Vector3(0, 0, -2.2); // where the core is (set by the hub), for pulse directions
  }

  /**
   * arrive: 0 → 1 over the brake (dots fly in from the middle, white-hot, then cool); show: overall
   * visibility; state: the assistant's (pulses toward / away); loud: 0..1 while speaking.
   */
  step(dt, { arrive = 1, show = 1, state = "idle", loud = 0 }) {
    const heat = 1 - clamp(arrive * 1.15, 0, 1);
    const c = this.color.clone().lerp(this.hot, heat);
    const prev = this.arriveK;
    this.arriveK = arrive;
    for (let i = 0; i < N; i++) {
      // each dot on the brake's curve, a little staggered so they don't all land at once
      const k = clamp(arrive * 1.1 - (i % 10) * 0.01, 0, 1), e = 1 - Math.pow(1 - k, 3);
      const p = this.pos[i].lerpVectors(this.from[i], this.home[i], e);
      p.toArray(this.dotPos, i * 3);
      // its streak: from where it was a moment ago on the same curve
      const kb = clamp(k - 0.05, 0, 1), eb = 1 - Math.pow(1 - kb, 3);
      const q = new THREE.Vector3().lerpVectors(this.from[i], this.home[i], eb);
      const sa = k < 1 && prev < 1 ? 0.8 * show * (1 - k) : 0;
      q.toArray(this.streakPos, i * 6); p.toArray(this.streakPos, i * 6 + 3);
      for (let j = 0; j < 3; j++) { this.streakCol[i * 6 + j] = 0; this.streakCol[i * 6 + 3 + j] = this.hot.toArray()[j] * sa; }
    }
    this.edges.forEach(([a, b, w], k) => {
      this.pos[a].toArray(this.linkPos, k * 6); this.pos[b].toArray(this.linkPos, k * 6 + 3);
      const al = show * clamp(arrive * 1.3 - 0.3, 0, 1) * (0.05 + 0.22 * w) * (1 + 2 * heat);
      for (let j = 0; j < 3; j++) this.linkCol[k * 6 + j] = this.linkCol[k * 6 + 3 + j] = c.toArray()[j] * al;
    });
    const g = this.links.geometry.attributes, sg = this.streaks.geometry.attributes;
    g.position.needsUpdate = g.color.needsUpdate = true;
    sg.position.needsUpdate = sg.color.needsUpdate = true;
    this.dots.geometry.attributes.position.needsUpdate = true;
    this.dotMat.color.copy(c);
    this.dotMat.opacity = 0.9 * show;
    this.streaks.visible = arrive < 1;
    if (arrive >= 1) this.group.rotation.y += dt * 0.01;
    this._pulses(dt, show * (arrive >= 1 ? 1 : 0), state, loud);
  }

  _pulses(dt, show, state, loud) {
    const inward = state === "thinking", outward = state === "speaking";
    const speed = 2.5 * (outward ? 1.5 + 2 * loud : inward ? 1.8 : 1);
    const coreLocal = this.group.worldToLocal(this.group.parent ? this.group.parent.localToWorld(this.core.clone()) : this.core.clone());
    for (const p of this.pulses) {
      if (!p.e) { // waiting to fire (more often while it thinks or speaks)
        p.wait -= dt * (inward || outward ? 3 : 1);
        p.s.material.opacity = 0;
        if (p.wait <= 0 && this.edges.length) {
          p.e = this.edges[Math.floor(Math.random() * this.edges.length)]; p.dir = 1; p.t = 0; p.hops = 3 + Math.floor(Math.random() * 4);
        }
        continue;
      }
      const [a, b] = p.e, from = p.dir > 0 ? this.pos[a] : this.pos[b], to = p.dir > 0 ? this.pos[b] : this.pos[a];
      p.t += (dt * speed) / Math.max(0.3, from.distanceTo(to));
      if (p.t >= 1) {
        const end = p.dir > 0 ? b : a;
        if (--p.hops <= 0) { p.e = null; p.wait = rand(2, 6); continue; }
        let next = this.edges.filter(([x, y]) => (x === end || y === end) && !(x === a && y === b));
        if ((inward || outward) && next.length > 1) { // toward the core while thinking, away while speaking
          const far = (e) => this.pos[e[0] === end ? e[1] : e[0]].distanceTo(coreLocal);
          next.sort((u, v) => (inward ? far(u) - far(v) : far(v) - far(u)));
          next = next.slice(0, 2);
        }
        if (!next.length) { p.e = null; p.wait = rand(2, 6); continue; }
        p.e = next[Math.floor(Math.random() * next.length)];
        p.dir = p.e[0] === end ? 1 : -1;
        p.t = 0;
        continue;
      }
      p.s.position.lerpVectors(from, to, p.t);
      p.s.material.opacity = show * (0.4 + 0.6 * Math.sin(Math.PI * p.t));
    }
  }
}
