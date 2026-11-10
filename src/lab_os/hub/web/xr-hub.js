// The immersive hub (xr.html): the designed hub's startup in VR/AR, with three.js.
//   wait  → stars barely drifting around you, the place's name ahead: "pull the trigger to jump"
//   jump  → one smooth speed curve: trails stretch first, then the stars race past (theme ramp_s)
//   hold  → full speed (hold_s), then a flash
//   brake → a long ease-out (brake_s): the stars fade, the network around you starts white-hot and
//           dims, the core grows in front of you
//   hub   → the network drifts with pulses along its links, the core breathes in the assistant's real
//           state (/api/status), the title decodes and the brain's greeting types itself out
// The trigger (or a pinch) jumps (again). Units: metres, "local" space (origin = your head at the
// start, -z ahead). "Preview on this screen" runs the same scene without a headset.
import * as THREE from "three";
import { theme, color } from "/web/theme.js";

const $ = (s) => document.querySelector(s);
const params = new URLSearchParams(location.search);
const HY = theme.startup?.hyperspace || {};
const T = { ramp: (HY.ramp_s ?? 2) * 1000, hold: (HY.hold_s ?? 0.7) * 1000, brake: (HY.brake_s ?? 2.6) * 1000 };
const N_STARS = Math.min(HY.stars ?? 3000, 3000); // the Quest draws 3000 lines easily; more buys nothing
const COL = Object.fromEntries(["primary", "hot", "line", "accent", "danger", "offline", "ok"].map((k) => [k, new THREE.Color(color(`colors.${k}`))]));
const BG = new THREE.Color(color("colors.background"));
const FONT_DISPLAY = theme.font?.display || "system-ui, sans-serif";
const FONT_LINES = theme.font?.lines || "system-ui, sans-serif";
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const rand = (a, b) => a + Math.random() * (b - a);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

/* ---------- the stars: each one a line from its tail to its head, plus a dot ---------- */
const FAR = 160; // they start this far ahead...
const BEHIND = 2; // ...and leave this far behind you
const V_DRIFT = 0.8, V_MAX = 150; // m/s
const TRAIL_MAX = 35; // m: complete lines at full speed
class Stars {
  constructor() {
    this.p = new Float32Array(N_STARS * 3);
    this.w = new Float32Array(N_STARS); // brightness of each star
    for (let i = 0; i < N_STARS; i++) this.spawn(i, false);
    this.lineGeo = new THREE.BufferGeometry();
    this.linePos = new Float32Array(N_STARS * 6);
    this.lineCol = new Float32Array(N_STARS * 6); // tail black (invisible when added), head bright
    this.lineGeo.setAttribute("position", new THREE.BufferAttribute(this.linePos, 3).setUsage(THREE.DynamicDrawUsage));
    this.lineGeo.setAttribute("color", new THREE.BufferAttribute(this.lineCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.lines = new THREE.LineSegments(this.lineGeo, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.dotGeo = new THREE.BufferGeometry();
    this.dotGeo.setAttribute("position", new THREE.BufferAttribute(this.p, 3).setUsage(THREE.DynamicDrawUsage));
    this.dots = new THREE.Points(this.dotGeo, new THREE.PointsMaterial({ size: 0.09, map: dotTexture(), color: COL.hot, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    for (const o of [this.lines, this.dots]) o.frustumCulled = false;
    this.group = new THREE.Group();
    this.group.add(this.lines, this.dots);
  }
  spawn(i, far) {
    // around the line of travel, never through your head; denser toward the middle
    const r = 1.5 + 28 * Math.pow(Math.random(), 1.6), a = Math.random() * Math.PI * 2;
    this.p[i * 3] = Math.cos(a) * r;
    this.p[i * 3 + 1] = Math.sin(a) * r * 0.75;
    this.p[i * 3 + 2] = far ? -FAR * rand(0.75, 1) : -rand(3, FAR);
    this.w[i] = rand(0.35, 1);
  }
  /** v: speed (m/s), trail: line length (m), bright: 0..1+, white: how white the heads are */
  step(dt, v, trail, bright, white, dotAlpha) {
    const c = COL.primary, h = new THREE.Color(1, 1, 1);
    for (let i = 0; i < N_STARS; i++) {
      const j = i * 3;
      this.p[j + 2] += v * dt;
      if (this.p[j + 2] > BEHIND) this.spawn(i, true);
      const x = this.p[j], y = this.p[j + 1], z = this.p[j + 2];
      const near = clamp(1.15 - -z / FAR, 0.1, 1), a = bright * near * this.w[i];
      const k = i * 6;
      this.linePos[k] = x; this.linePos[k + 1] = y; this.linePos[k + 2] = z - trail;
      this.linePos[k + 3] = x; this.linePos[k + 4] = y; this.linePos[k + 5] = z;
      this.lineCol[k + 3] = (c.r + (h.r - c.r) * white) * a;
      this.lineCol[k + 4] = (c.g + (h.g - c.g) * white) * a;
      this.lineCol[k + 5] = (c.b + (h.b - c.b) * white) * a;
    }
    this.lineGeo.attributes.position.needsUpdate = true;
    this.lineGeo.attributes.color.needsUpdate = true;
    this.dotGeo.attributes.position.needsUpdate = true;
    this.dots.material.opacity = dotAlpha;
  }
}

/* ---------- the network: nodes on a shell around you, links to their nearest, pulses ---------- */
class Network {
  constructor() {
    const pts = [];
    for (let i = 0; i < 150; i++) {
      const d = new THREE.Vector3().randomDirection();
      if (d.y < -0.45) d.y = -d.y * 0.5; // mostly not under the floor
      pts.push(d.multiplyScalar(rand(6, 11)));
    }
    this.edges = [];
    const seen = new Set();
    pts.forEach((p, i) => {
      pts.map((q, j) => [j, p.distanceTo(q)]).filter(([j]) => j !== i).sort((a, b) => a[1] - b[1]).slice(0, 2).forEach(([j]) => {
        const key = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (!seen.has(key)) { seen.add(key); this.edges.push([i, j]); }
      });
    });
    this.pts = pts;
    const lp = new Float32Array(this.edges.length * 6);
    this.edges.forEach(([a, b], k) => { pts[a].toArray(lp, k * 6); pts[b].toArray(lp, k * 6 + 3); });
    const lg = new THREE.BufferGeometry();
    lg.setAttribute("position", new THREE.BufferAttribute(lp, 3));
    this.lineMat = new THREE.LineBasicMaterial({ color: COL.primary, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const ng = new THREE.BufferGeometry().setFromPoints(pts);
    this.dotMat = new THREE.PointsMaterial({ size: 0.16, map: dotTexture(), color: COL.primary, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    this.group = new THREE.Group();
    this.group.add(new THREE.LineSegments(lg, this.lineMat), new THREE.Points(ng, this.dotMat));
    // pulses running along the links, like the hub's traces
    this.pulses = Array.from({ length: 10 }, () => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color: COL.hot, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      s.scale.setScalar(0.25);
      this.group.add(s);
      return { s, e: this.edges[Math.floor(Math.random() * this.edges.length)], t: Math.random(), dir: 1 };
    });
  }
  step(dt, show, heat) {
    this.group.rotation.y += dt * 0.012;
    // it arrives white-hot and cools to the primary color
    this.lineMat.color.copy(COL.primary).lerp(COL.hot, heat);
    this.lineMat.opacity = 0.32 * show;
    this.dotMat.opacity = 0.9 * show;
    for (const p of this.pulses) {
      const [a, b] = p.e, len = this.pts[a].distanceTo(this.pts[b]);
      p.t += (dt * 2.5) / len;
      if (p.t >= 1) { // on to a link from the end it reached
        const end = p.dir > 0 ? b : a, next = this.edges.filter(([x, y]) => x === end || y === end);
        p.e = next[Math.floor(Math.random() * next.length)] || p.e;
        p.dir = p.e[0] === end ? 1 : -1;
        p.t = 0;
      }
      const [from, to] = p.dir > 0 ? [this.pts[p.e[0]], this.pts[p.e[1]]] : [this.pts[p.e[1]], this.pts[p.e[0]]];
      p.s.position.lerpVectors(from, to, p.t);
      p.s.material.opacity = show * Math.sin(Math.PI * p.t);
    }
  }
}

/* ---------- the core: a glowing heart, rings that turn, ticks; colored by the assistant's state ---------- */
class Core {
  constructor() {
    this.group = new THREE.Group();
    this.group.position.set(0, 0, -2.4);
    const add = (o) => (this.group.add(o), o);
    this.glow = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color: COL.primary, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })));
    this.glow.scale.setScalar(1.1);
    this.heart = add(new THREE.Mesh(new THREE.SphereGeometry(0.075, 32, 16), new THREE.MeshBasicMaterial({ color: COL.hot })));
    const mat = () => new THREE.MeshBasicMaterial({ color: COL.primary, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
    this.rings = [
      add(new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.004, 8, 160), mat())),
      add(new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.009, 8, 160, Math.PI * 1.25), mat())),
      add(new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.009, 8, 160, Math.PI * 0.45), mat())),
    ];
    this.rings[2].rotation.z = Math.PI * 1.4;
    const dash = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 180 }, (_, i) => new THREE.Vector3(Math.cos((i / 180) * Math.PI * 2) * 0.32, Math.sin((i / 180) * Math.PI * 2) * 0.32, 0))),
      new THREE.LineDashedMaterial({ color: COL.primary, dashSize: 0.035, gapSize: 0.02, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    dash.computeLineDistances();
    this.rings.push(add(dash));
    const tp = [];
    for (let i = 0; i < 90; i++) {
      const a = (i / 90) * Math.PI * 2, r0 = i % 5 ? 0.47 : 0.45;
      tp.push(Math.cos(a) * r0, Math.sin(a) * r0, 0, Math.cos(a) * 0.5, Math.sin(a) * 0.5, 0);
    }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute("position", new THREE.Float32BufferAttribute(tp, 3));
    this.ticks = add(new THREE.LineSegments(tg, new THREE.LineBasicMaterial({ color: COL.primary, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false })));
    this.state = "idle";
    this.group.scale.setScalar(0.001);
  }
  step(dt, now, grow) {
    const look = theme.assistant?.[this.state] || {};
    const col = COL[look.color] || COL.primary, bright = look.brightness ?? 0.7;
    const breathe = look.breathe_s ? 1 + 0.035 * Math.sin((now / 1000 / look.breathe_s) * Math.PI * 2) : 1;
    const spin = this.state === "thinking" ? 3 : this.state === "offline" ? 0.2 : 1;
    this.group.scale.setScalar(Math.max(0.001, grow * breathe));
    const speeds = [0.25, -0.4, 0.55, -0.15];
    this.rings.forEach((r, i) => { r.rotation.z += dt * speeds[i] * spin; r.material.color.copy(col); r.material.opacity = 0.35 + 0.65 * bright; });
    this.ticks.rotation.z -= dt * 0.05 * spin;
    this.ticks.material.color.copy(col);
    this.glow.material.color.copy(col);
    this.glow.material.opacity = 0.25 + 0.5 * bright;
    this.heart.material.color.copy(this.state === "offline" ? COL.offline : COL.hot);
  }
}

/* ---------- text on planes (canvas textures) ---------- */
class Label {
  constructor(w, h, px) {
    this.c = document.createElement("canvas");
    this.c.width = Math.round(w * px); this.c.height = Math.round(h * px);
    this.tex = new THREE.CanvasTexture(this.c);
    this.tex.colorSpace = THREE.SRGBColorSpace;
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: this.tex, transparent: true, depthWrite: false }));
    this.last = null;
  }
  draw(text, font, fill, glow = 0) {
    const key = `${text}|${font}|${fill}|${glow}`;
    if (key === this.last) return;
    this.last = key;
    const g = this.c.getContext("2d");
    g.clearRect(0, 0, this.c.width, this.c.height);
    g.font = font; g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = fill;
    g.shadowColor = fill; g.shadowBlur = glow;
    g.fillText(text, this.c.width / 2, this.c.height / 2, this.c.width * 0.96);
    this.tex.needsUpdate = true;
  }
}
const css = (c) => `#${c.getHexString()}`;
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+<>/";
function decoded(text, t) { // the title decoding, left to right
  const n = Math.floor(text.length * clamp(t, 0, 1));
  return text.slice(0, n) + [...text.slice(n)].map((ch) => (ch === " " ? " " : GLYPHS[Math.floor(Math.random() * GLYPHS.length)])).join("");
}

let DOT = null;
function dotTexture() { // a soft round dot for points, glows and pulses
  if (DOT) return DOT;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d"), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.25, "rgba(255,255,255,0.6)"); r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  return (DOT = new THREE.CanvasTexture(c));
}

/* ---------- sound: a rising rush, a boom at the flash, a chime on arrival (WebAudio, no files) ---------- */
class Sound {
  constructor() {
    this.on = params.get("sound") !== "0";
    if (!this.on) return;
    this.ctx = new AudioContext();
    const n = this.ctx.sampleRate * 2, buf = this.ctx.createBuffer(1, n, this.ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    this.noise = buf;
  }
  rush(ms) {
    if (!this.on) return;
    const c = this.ctx, t = c.currentTime, src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = this.noise; src.loop = true;
    f.type = "bandpass"; f.Q.value = 0.8;
    f.frequency.setValueAtTime(180, t); f.frequency.exponentialRampToValueAtTime(2600, t + ms / 1000);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.45, t + ms / 1000);
    g.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000 + 0.25);
    src.connect(f).connect(g).connect(c.destination);
    src.start(t); src.stop(t + ms / 1000 + 0.3);
  }
  boom() {
    if (!this.on) return;
    const c = this.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(32, t + 1.4);
    g.gain.setValueAtTime(0.9, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.8);
    o.connect(g).connect(c.destination); o.start(t); o.stop(t + 1.9);
  }
  chime() {
    if (!this.on) return;
    const c = this.ctx, t = c.currentTime;
    [660, 990].forEach((hz, i) => {
      const o = c.createOscillator(), g = c.createGain();
      o.type = "sine"; o.frequency.value = hz;
      g.gain.setValueAtTime(0.0001, t + i * 0.12); g.gain.exponentialRampToValueAtTime(0.18, t + i * 0.12 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.12 + 1.2);
      o.connect(g).connect(c.destination); o.start(t + i * 0.12); o.stop(t + i * 0.12 + 1.3);
    });
  }
}

/* ---------- the show ---------- */
class Show {
  constructor(ar) {
    this.ar = ar;
    this.scene = new THREE.Scene();
    if (!ar) this.scene.background = BG;
    this.stars = new Stars();
    this.net = new Network();
    this.core = new Core();
    this.flash = new THREE.Mesh(new THREE.SphereGeometry(3, 24, 16), new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.BackSide, transparent: true, opacity: 0, depthWrite: false }));
    this.title = new Label(2.2, 0.32, 600);
    this.title.mesh.position.set(0, 0.62, -2.4);
    this.line = new Label(2.4, 0.16, 600);
    this.line.mesh.position.set(0, -0.62, -2.4);
    this.hint = new Label(2.0, 0.12, 600);
    this.hint.mesh.position.set(0, -0.32, -3);
    this.scene.add(this.stars.group, this.net.group, this.core.group, this.flash, this.title.mesh, this.line.mesh, this.hint.mesh);
    this.phase = "wait";
    this.t0 = performance.now();
    this.name = "Lab";
    this.greeting = "";
    this.sound = null;
  }
  jump() {
    if (this.phase === "jump" || this.phase === "hold") return;
    this.phase = "jump";
    this.t0 = performance.now();
    this.sound?.rush(T.ramp + T.hold);
    for (let i = 0; i < N_STARS; i++) this.stars.spawn(i, false); // a full field to race through
  }
  step(dt, now) {
    const ms = now - this.t0;
    let v = V_DRIFT, trail = 0.04, bright = 0.6, white = 0.3, dotAlpha = 0.9, starShow = 1, net = 0, heat = 0, grow = 0;
    if (this.phase === "jump" || this.phase === "hold") {
      const p = clamp(ms / T.ramp, 0, 1), rush = (Math.exp(4.2 * p) - 1) / (Math.exp(4.2) - 1);
      v = V_DRIFT + (V_MAX - V_DRIFT) * rush;
      trail = 0.04 + TRAIL_MAX * p * p; // the trails lead: long lines while the dots are still slow
      bright = 0.7 + 0.6 * Math.pow(p, 1.2); white = 0.3 + 0.7 * p; dotAlpha = clamp(1 - trail / 2, 0, 0.9);
      if (ms > T.ramp) this.phase = "hold";
      if (ms > T.ramp + T.hold) {
        this.phase = "brake"; this.t0 = now;
        this.flash.material.opacity = 0.85;
        this.sound?.boom();
      }
    } else if (this.phase === "brake" || this.phase === "hub") {
      const b = clamp(ms / T.brake, 0, 1), e = easeOut(b);
      v = V_DRIFT + (V_MAX - V_DRIFT) * Math.pow(1 - b, 3);
      trail = 0.04 + TRAIL_MAX * Math.pow(1 - b, 2.5);
      starShow = 1 - e; white = 1 - 0.7 * b; bright = 1.2 - 0.6 * b; dotAlpha = 0.9 * b;
      net = e; heat = 1 - e; grow = easeOut(clamp(ms / (T.brake * 0.7), 0, 1));
      if (this.phase === "brake" && b >= 1) { this.phase = "hub"; this.hubAt = now; this.sound?.chime(); }
    }
    this.stars.step(dt, v, trail, bright * starShow, white, dotAlpha * starShow);
    this.stars.group.visible = starShow > 0.01;
    this.flash.material.opacity = Math.max(0, this.flash.material.opacity - dt / 0.9);
    this.net.step(dt, net, heat);
    this.core.step(dt, now, grow);

    const P = css(COL.primary), H = css(COL.hot), D = css(COL.offline);
    if (this.phase === "wait") {
      this.title.draw(this.name.toUpperCase(), `700 120px ${FONT_DISPLAY}`, H, 30);
      this.hint.draw("Pull the trigger or pinch to jump", `400 52px ${FONT_LINES}`, P, 0);
      this.line.draw("", `400 60px ${FONT_LINES}`, H);
    } else if (this.phase === "hub") {
      const t = (now - this.hubAt) / 1000;
      this.title.draw(decoded(this.name.toUpperCase(), t / 1.2), `700 120px ${FONT_DISPLAY}`, H, 30);
      const typed = this.greeting.slice(0, Math.max(0, Math.floor((t - 1) * 40)));
      this.line.draw(typed, `400 58px ${FONT_LINES}`, H, 0);
      this.hint.draw(t > 4 ? "Trigger: jump again" : "", `400 44px ${FONT_LINES}`, D, 0);
    } else {
      this.title.draw("", `700 120px ${FONT_DISPLAY}`, H);
      this.hint.draw("", `400 44px ${FONT_LINES}`, D);
      this.line.draw("", `400 58px ${FONT_LINES}`, H);
    }
    this.title.mesh.position.z = this.phase === "wait" ? -3.2 : -2.4;
    if (this.phase === "wait") this.hint.mesh.position.set(0, -0.32, -3); // under the title
    else this.hint.mesh.position.set(0, -0.82, -2.4); // under the greeting, clear of the core
  }
}

/* ---------- the brain's facts ---------- */
async function getJSON(url) {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch { return null; }
}
async function facts(show) {
  const [hub, hello] = await Promise.all([getJSON("/api/hub"), getJSON("/api/greeting")]);
  if (hub?.title) show.name = hub.title;
  if (hello?.text) show.greeting = hello.text;
}
async function pollState(show) {
  const st = await getJSON("/api/status");
  show.core.state = st?.assistant?.state || "offline";
}

/* ---------- running it: in the headset, or on this screen ---------- */
let renderer = null;
function makeRenderer(ar) {
  renderer ||= new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.setClearColor(BG, ar ? 0 : 1);
  return renderer;
}
async function start(mode) {
  const ar = mode === "immersive-ar", show = new Show(ar);
  show.sound = new Sound(); // made on the press: browsers allow sound only after one
  await Promise.all([facts(show), document.fonts?.ready]);
  pollState(show);
  const timer = setInterval(() => pollState(show), 3000);
  const r = makeRenderer(ar);
  const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.05, 400);
  let last = performance.now();
  const frame = () => {
    const now = performance.now(), dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    show.step(dt, now);
    r.render(show.scene, camera);
  };
  if (mode === "screen") { // no headset: the same scene full window; click or a key jumps
    document.body.append(r.domElement);
    Object.assign(r.domElement.style, { position: "fixed", inset: 0, width: "100%", height: "100%", zIndex: 50 });
    const size = () => { r.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); };
    size(); addEventListener("resize", size);
    r.domElement.addEventListener("pointerdown", () => show.jump());
    addEventListener("keydown", (e) => (e.key === "Escape" ? location.reload() : show.jump()));
    r.setAnimationLoop(frame);
    window.__xrShow = show; // for tests and the console
    return;
  }
  r.xr.enabled = true;
  r.xr.setReferenceSpaceType("local");
  r.xr.setFoveation?.(1);
  const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor"] });
  await r.xr.setSession(session);
  session.addEventListener("select", () => show.jump()); // trigger, or a pinch with bare hands
  session.addEventListener("end", () => { r.setAnimationLoop(null); clearInterval(timer); $("#msg").textContent = "Left VR. Press a button to go back in."; });
  r.setAnimationLoop(frame);
}

async function init() {
  const vr = $("#vr"), ar = $("#ar");
  const preview = document.createElement("button");
  preview.className = "btn"; preview.type = "button"; preview.textContent = "Preview on this screen";
  preview.onclick = () => start("screen").catch((e) => ($("#msg").textContent = `Couldn't start: ${e.message}`));
  vr.after(preview);
  const can = async (m) => !!navigator.xr && (await navigator.xr.isSessionSupported(m).catch(() => false));
  const [hasVR, hasAR] = await Promise.all([can("immersive-vr"), can("immersive-ar")]);
  vr.disabled = !hasVR;
  vr.textContent = hasVR ? "Enter VR" : "No VR on this device";
  ar.hidden = !hasAR;
  if (!hasVR && !hasAR) $("#msg").textContent = "Open this page in the Quest's browser: http://localhost:8080/xr (with adb reverse, docs/quest-setup.md). Here you can watch it on the screen.";
  const go = (m) => () => start(m).catch((e) => ($("#msg").textContent = `Couldn't start: ${e.message}`));
  vr.onclick = go("immersive-vr");
  ar.onclick = go("immersive-ar");
  if (params.has("preview")) preview.click();
}
init();
