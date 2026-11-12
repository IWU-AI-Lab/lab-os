// The hyperspace jump's star field in VR, like the designed hub's (design.html → drawStars):
//   - the waiting stars are the ones that jump: nothing is re-dealt when it starts, so each line grows
//     out of a star you were looking at (its head is the star);
//   - every line is one gradient, a faint cyan tail to a bright head, and brighter is whiter (more so
//     at speed), so color and brightness change together; lines get thicker with speed;
//   - a third of the stars gather around the middle, so the place you look at isn't empty;
//   - recycled stars start far away and fade in; while waiting, they twinkle.
// Each star is one camera-facing quad (instanced), drawn by a small shader: thick, soft lines that the
// Quest draws cheaply. Units: metres in the stage's space (you at the origin, -z ahead); stars travel +z.
// Sky: a sphere around you for the faint blue that grows with the speed, the flash (a burst from the
// middle that clears from the edges first) and the impact frame (dark streaks on white).
import * as THREE from "three";
import { C, clamp, rand } from "./draw.js";

export const FAR = 160; // stars start this far ahead...
const BEHIND = 2; // ...and leave once their tail is this far behind you
const MIN_R = 0.7; // never through your head
// a theme color as its sRGB numbers (the shaders mix in sRGB, like the hub's canvas, then convert)
const srgb = (hex) => { const c = new THREE.Color(hex).convertLinearToSRGB(); return new THREE.Vector3(c.r, c.g, c.b); };

const VERT = /* glsl */ `
  attribute vec2 corner;      // x: 0 tail, 1 head; y: -1 / 1 side
  attribute vec3 iHead;
  attribute float iTrail;
  attribute float iBright;
  attribute float iWide;
  uniform float uAngle;       // half the line's width, as an angle (radians)
  varying vec2 vLocal;
  varying float vL;
  varying float vR;
  varying float vA;
  void main() {
    vec4 h = projectionMatrix * viewMatrix * modelMatrix * vec4(iHead, 1.0);
    vec4 t = projectionMatrix * viewMatrix * modelMatrix * vec4(iHead - vec3(0.0, 0.0, iTrail), 1.0);
    // a line that reaches behind you: cut it where it meets the near plane
    const float EPS = 0.02;
    if (h.w < EPS && t.w < EPS) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    if (h.w < EPS) h = mix(t, h, (EPS - t.w) / (h.w - t.w));
    if (t.w < EPS) t = mix(h, t, (EPS - h.w) / (t.w - h.w));
    float aspect = projectionMatrix[1][1] / projectionMatrix[0][0];
    vec2 hp = h.xy / h.w, tp = t.xy / t.w;
    hp.x *= aspect; tp.x *= aspect;
    vec2 d = hp - tp;
    float L = length(d);
    vec2 dir = L > 1e-6 ? d / L : vec2(1.0, 0.0);
    vec2 n = vec2(-dir.y, dir.x);
    float r = uAngle * projectionMatrix[1][1] * (iWide > 0.5 ? 1.8 : 1.0);
    vec2 p = mix(tp, hp, corner.x) + dir * (corner.x * 2.0 - 1.0) * r + n * corner.y * r;
    float z = mix(t.z / t.w, h.z / h.w, corner.x);
    gl_Position = vec4(p.x / aspect, p.y, z, 1.0);
    vLocal = vec2(corner.x * L + (corner.x * 2.0 - 1.0) * r, corner.y * r);
    vL = L; vR = r; vA = iBright;
  }`;
const FRAG = /* glsl */ `
  uniform vec3 uPrimary;
  uniform vec3 uWhite;
  uniform float uWhiten;      // how white the bright parts get (more at speed)
  uniform float uImpact;      // 1 = the impact frame: dark streaks
  varying vec2 vLocal;
  varying float vL;
  varying float vR;
  varying float vA;
  void main() {
    float s = vLocal.x, q = vLocal.y;
    float d = s < 0.0 ? length(vec2(s, q)) : s > vL ? length(vec2(s - vL, q)) : abs(q);
    float x = d / vR;
    if (x > 1.0) discard;
    float sharp = smoothstep(0.55, 0.15, x), halo = (1.0 - x) * (1.0 - x) * 0.3;
    float along = vL > 1e-5 ? clamp(s / vL, 0.0, 1.0) : 1.0;
    float f = vA * pow(along, 1.8);           // faint tail → bright head
    if (uImpact > 0.5) { gl_FragColor = vec4(0.02, 0.03, 0.045, sharp * 0.85 * step(0.03, vA)); return; } // whole lines, dark on white
    float m = f * f * uWhiten;
    vec3 c = mix(uPrimary, uWhite, clamp(m, 0.0, 1.0));      // sRGB, like the hub's canvas
    gl_FragColor = vec4(pow(c * f * (sharp + halo), vec3(2.2)), 1.0);
    #include <colorspace_fragment>
  }`;

export class Stars {
  constructor(count) {
    this.n = count;
    this.p = new Float32Array(count * 3); // head positions
    this.trail = new Float32Array(count);
    this.bright = new Float32Array(count);
    this.wide = new Float32Array(count);
    this.w = new Float32Array(count); // each star's own brightness
    this.ph = new Float32Array(count); // twinkle phase
    this.age = new Float32Array(count); // fades in after a respawn
    for (let i = 0; i < count; i++) this.spawn(i, false, true);

    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute("corner", new THREE.BufferAttribute(new Float32Array([0, -1, 1, -1, 1, 1, 0, 1]), 2));
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(12), 3)); // unused, three wants one
    g.setIndex([0, 1, 2, 0, 2, 3]);
    const inst = (arr, size) => new THREE.InstancedBufferAttribute(arr, size).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute("iHead", inst(this.p, 3));
    g.setAttribute("iTrail", inst(this.trail, 1));
    g.setAttribute("iBright", inst(this.bright, 1));
    g.setAttribute("iWide", inst(this.wide, 1));
    g.instanceCount = count;
    this.geo = g;
    this.uniforms = {
      uAngle: { value: 0.0009 }, uWhiten: { value: 0.3 }, uImpact: { value: 0 },
      uPrimary: { value: srgb(C.primary) }, uWhite: { value: new THREE.Vector3(225 / 255, 248 / 255, 1) },
    };
    this.mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, uniforms: this.uniforms,
      transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
    });
    this.mesh = new THREE.Mesh(g, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -2;
    this.group = new THREE.Group();
    this.group.add(this.mesh);
  }

  /** A new star: a random spot over the whole view (and past it), at a random depth; a third bunched
   *  around the middle. `far`: a recycled one, far away, fading in. */
  spawn(i, far, shown = false) {
    const z = far ? -FAR * rand(0.7, 1) : -rand(4, FAR), mid = Math.random() < 0.3;
    const spot = () => (mid ? (Math.random() + Math.random() + Math.random() - 1.5) * 0.2 : rand(-0.56, 0.56));
    // the designed hub spreads stars over a 16:10 screen; here, a bit wider (you can look around)
    let x = spot() * 2.2 * -z, y = spot() * 1.6 * -z;
    const r = Math.hypot(x, y);
    if (r < MIN_R) { const a = Math.random() * Math.PI * 2; x = Math.cos(a) * MIN_R * rand(1, 1.6); y = Math.sin(a) * MIN_R * rand(1, 1.6); }
    this.p[i * 3] = x; this.p[i * 3 + 1] = y; this.p[i * 3 + 2] = z;
    this.w[i] = rand(0.3, 1);
    this.wide[i] = this.w[i] > 0.75 ? 1 : 0;
    this.ph[i] = rand(0, Math.PI * 2);
    this.age[i] = shown ? 1 : 0;
  }

  /**
   * One frame. v: speed (m/s); trail: line length (m); bright: overall 0..1+; k: 0 waiting … 1 full
   * speed (whiter, thicker); jump: twinkle off while jumping; frozen: the impact frame (nothing moves).
   */
  step(dt, now, { v, trail, bright, k, jump, frozen = false }) {
    this.uniforms.uWhiten.value = 0.3 + 0.7 * k;
    this.uniforms.uAngle.value = 0.0011 * (1 + 1.3 * k);
    if (frozen) return;
    for (let i = 0; i < this.n; i++) {
      const j = i * 3;
      this.p[j + 2] += v * dt;
      this.age[i] = Math.min(1, this.age[i] + dt / (0.6 - 0.45 * k)); // at speed they'd never finish fading in
      const z = this.p[j + 2], tr = Math.min(trail, FAR + z); // the tail stops at the far end
      // a star leaves when its tail is behind you, so lines sweep all the way past
      if (z - tr > BEHIND) { this.spawn(i, true); this.trail[i] = 0; this.bright[i] = 0; continue; }
      const near = clamp(1.25 - -z / FAR, 0.15, 1), twinkle = jump ? 1 : 0.8 + 0.2 * Math.sin(now * 0.0016 + this.ph[i]);
      this.trail[i] = Math.max(0, tr);
      this.bright[i] = bright * near * (0.55 + 0.45 * this.w[i]) * this.age[i] * twinkle;
    }
    const a = this.geo.attributes;
    a.iHead.needsUpdate = a.iTrail.needsUpdate = a.iBright.needsUpdate = true;
  }
  set impact(on) {
    this.uniforms.uImpact.value = on ? 1 : 0;
    this.mat.blending = on ? THREE.NormalBlending : THREE.AdditiveBlending;
    this.mat.needsUpdate = true;
  }
  set visible(v) { this.group.visible = v; }
}

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const SKY_FRAG = /* glsl */ `
  uniform vec3 uPrimary;
  uniform vec3 uHot;
  uniform float uTint;    // the faint blue that grows with the speed
  uniform float uMid;     // the flash in the middle...
  uniform float uEdge;    // ...and at the edges (they clear first)
  uniform float uImpact;
  varying vec3 vDir;
  void main() {
    float c = dot(normalize(vDir), vec3(0.0, 0.0, -1.0));   // 1 straight ahead
    float k = clamp(acos(clamp(c, -1.0, 1.0)) / 1.2, 0.0, 1.0); // 0 ahead … 1 at the edge of the view
    vec3 tint = uPrimary * uTint * mix(1.0, 0.35, k);
    float fa = mix(uMid, uEdge, smoothstep(0.0, 1.0, k));
    vec3 flash = mix(uHot, mix(vec3(0.78, 0.94, 1.0), uPrimary, smoothstep(0.35, 1.0, k)), smoothstep(0.0, 0.35, k)) * fa;
    vec3 col = tint + flash + uHot * uImpact;            // sRGB amounts, like the hub's canvas
    gl_FragColor = vec4(pow(min(col, vec3(1.0)), vec3(2.2)), 1.0);
    #include <colorspace_fragment>
  }`;
export class Sky {
  constructor() {
    this.uniforms = {
      uPrimary: { value: srgb(C.primary) }, uHot: { value: srgb(C.hot) },
      uTint: { value: 0 }, uMid: { value: 0 }, uEdge: { value: 0 }, uImpact: { value: 0 },
    };
    this.mesh = new THREE.Mesh(
      new THREE.SphereGeometry(200, 32, 16),
      new THREE.ShaderMaterial({ vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, uniforms: this.uniforms, side: THREE.BackSide, depthWrite: false, depthTest: false, transparent: true, blending: THREE.AdditiveBlending }),
    );
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -3;
    this.flashAt = -1e9;
  }
  flash(now) { this.flashAt = now; }
  /** tint: 0..0.15 with the speed; impact: the impact frame */
  step(now, tint, impact) {
    const k = (now - this.flashAt) / 900; // the hub's flash: 0.9 s, the middle lasts longer than the edges
    const u = this.uniforms;
    u.uTint.value = tint;
    u.uImpact.value = impact ? 1 : 0;
    u.uMid.value = k >= 0 && k < 1 ? 0.9 * Math.pow(1 - k, 1.6) : 0;
    u.uEdge.value = k >= 0 && k < 1 ? 0.85 * Math.pow(1 - k, 4) : 0;
    this.mesh.visible = tint > 0.001 || impact || u.uMid.value > 0.001;
  }
}
