// Archived scene before the map adopted the hub core. See buildCore(), createMap() and step().
// The System Map's 3D scene (quick job 152): the brain's core in the middle, the devices spread around it
// where they fit (a small force layout, no rings), a trace from the core to each connected device.
// Devices with a 3D model turn on their bases. Screens show the page they have open on a picture that
// always faces you; things in front of it hide it, as in a real room.
//
// Motion follows the hub's look (DESIGN.md → "Quality levels"):
//   maximal / full  idle spin, turning models and core rings, breathing, pulses along live links,
//                   arrivals, devices gliding to new places, flights
//   reduced         the same without the pulses
//   minimal         nothing moves by itself; it draws only after an input or a change
// Idle spin pauses while you use the map and starts again a few seconds after you let go.
// Light on slow screens: at most 30 frames per second while idle, never in a hidden tab or off screen.
//
// Controls: drag to orbit; right-drag, Shift-drag or two fingers to pan; scroll or pinch to zoom (toward
// the pointer); double-click a device to focus it. Keys: arrows orbit, Shift + arrows pan, + and - zoom,
// F focuses the selected device, V or Home resets the view.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { loadArmModel } from "/static/arm/arm-model.js";
import { loadRaspbotModel } from "/web/raspbot-model.js";
import { drawRes } from "/web/screen.js";
import { color, theme } from "/web/theme.js";
import { currentLook } from "/hub/persona-table.js";
import { previewAspect, previewIcon, screenTitle } from "/hub/screen-preview.js";

const primary = color("colors.primary");
const offline = color("colors.offline");
const line = color("colors.line");
const hot = color("colors.hot");
const background = color("colors.background");
const surface = color("colors.surface");
const textColor = color("colors.text");
const textDim = color("colors.text_dim");
const motion = theme.motion || {};
const ringTurns = motion.idle?.ring_turn_s || [25, 40, 70];
const breatheS = theme.assistant?.idle?.breathe_s || 5;
const fireEvery = theme.network?.fire_every_s || [2, 6];
const panelMs = motion.panel_ms || 600;
const staggerMs = motion.stagger_ms || 60;
const SPIN_S = ringTurns[ringTurns.length - 1];  // one turn of the whole map, in seconds
const MODEL_TURN_S = ringTurns[0];               // one turn of a robot on its base, in seconds
const SPIN_AFTER_MS = 5000;                      // idle spin starts again this long after the last input
const IDLE_FRAME_MS = 33;                        // at most 30 frames per second while nothing is touched
const arrive = (t) => 1 - (1 - t) ** 3;          // starts fast, settles slowly (motion.arrive)

const pad = new THREE.CylinderGeometry(0.73, 0.81, 0.13, 6);
const outline = new THREE.EdgesGeometry(pad);
const marker = new THREE.OctahedronGeometry(0.067);
const beam = new THREE.CylinderGeometry(0.52, 0.28, 0.77, 6, 1, true);
const beamMaterial = new THREE.MeshBasicMaterial({
  color: primary, transparent: true, opacity: 0.06, depthWrite: false, side: THREE.DoubleSide,
  blending: THREE.AdditiveBlending,
});
const holo = new THREE.MeshStandardMaterial({
  color: color("colors.line"), emissive: primary, emissiveIntensity: 0.25, roughness: 0.55,
});
const lift = 0.79;
const shapes = {
  screen: new THREE.BoxGeometry(1.05, 0.66, 0.14),
  camera: new THREE.CylinderGeometry(0.31, 0.38, 0.65, 6).rotateX(Math.PI / 2),
  headset: new THREE.CylinderGeometry(0.49, 0.54, 0.42, 6),
  usb: new THREE.BoxGeometry(0.55, 0.4, 0.8),
};
const edges = Object.fromEntries(Object.entries(shapes).map(([kind, g]) => [kind, new THREE.EdgesGeometry(g)]));
const sharedLines = new Set([outline, ...Object.values(edges)]);
// Offline: gray, dim, no glow (DESIGN.md → "How serious is it?"). Only the outline, so it stays quiet.
const dark = new THREE.MeshStandardMaterial({
  color: color("colors.surface"), roughness: 0.75, transparent: true, opacity: 0.45, depthWrite: false,
});
const litPad = new THREE.MeshStandardMaterial({
  color: color("colors.surface"), emissive: line, emissiveIntensity: 0.38,
  roughness: 0.65, transparent: true, opacity: 0.64, depthWrite: false,
});
const wires = {
  on: new THREE.LineBasicMaterial({ color: primary }),
  off: new THREE.LineBasicMaterial({ color: offline, transparent: true, opacity: 0.7 }),
  selected: new THREE.LineBasicMaterial({ color: hot }),
};
const point = new THREE.MeshBasicMaterial({ color: primary });
const crystal = new THREE.MeshStandardMaterial({
  color: primary, emissive: primary, emissiveIntensity: 0.63, roughness: 0.45,
});
const links = {
  usb: new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.55 }),
  network: new THREE.LineDashedMaterial({ color: primary, dashSize: 0.16, gapSize: 0.13, transparent: true, opacity: 0.55 }),
};
// Decorations, on the full and maximal looks only (DESIGN.md → Quality levels): a polar floor grid with
// + marks, a line from each device down to the floor, a turning segmented ring under each connected device,
// a radar ping from the core now and then; maximal adds a satellite ring at the core.
const faint = (opacity) => new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity, depthWrite: false });
const dropLine = faint(0.16), footLine = faint(0.32), plusLine = faint(0.22), tickLine = faint(0.45);
const dropGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, -1, 0)]);
const footGeometry = new THREE.BufferGeometry().setFromPoints(Array.from({ length: 25 }, (_, i) =>
  new THREE.Vector3(Math.cos(i * Math.PI / 12) * 0.28, 0, Math.sin(i * Math.PI / 12) * 0.28)));
// A segmented ring: four arcs with gaps between them, as line pairs.
const tickGeometry = new THREE.BufferGeometry().setFromPoints(Array.from({ length: 4 }, (_, q) => {
  const steps = 16, from = q * Math.PI / 2 + 0.12, span = Math.PI / 2 - 0.24;
  return Array.from({ length: steps }, (_, i) => [i, i + 1].map((k) => {
    const a = from + span * k / steps;
    return new THREE.Vector3(Math.cos(a) * 1.08, 0, Math.sin(a) * 1.08);
  })).flat();
}).flat());
const decorLines = [dropGeometry, footGeometry, tickGeometry];
const TRACE_POINTS = 25;  // the trace as a polyline, so it can draw itself in

const modelTypes = { so101: "so101", "so101-leader": "so101", xarm1s: "xarm1s", raspbot: "raspbot" };
const models = new Map();
function modelFor(type) {
  if (!models.has(type)) {
    const load = type === "raspbot" ? loadRaspbotModel() : loadArmModel(type);
    models.set(type, load.then(({ object }) => {
      object.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(object);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      const scale = 1.45 / Math.max(size.x, size.y, size.z);
      object.scale.setScalar(scale);
      object.position.set(-center.x * scale, 0.13 - bounds.min.y * scale, -center.z * scale);
      return object;
    }).catch(() => null));
  }
  return models.get(type);
}

function glowTexture() {
  const image = document.createElement("canvas");
  image.width = image.height = 64;
  const ctx = image.getContext("2d");
  const glow = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  glow.addColorStop(0, "rgba(255,255,255,1)");
  glow.addColorStop(0.25, "rgba(255,255,255,0.35)");
  glow.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(image);
}

function halo(texture, tint, opacity, size) {
  const material = new THREE.SpriteMaterial({
    map: texture, color: tint, opacity, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(size, size, 1);
  return sprite;
}

function arc(radius, start, length, height, material) {
  const segments = Math.max(8, Math.ceil(length * 13));
  const points = Array.from({ length: segments + 1 }, (_, i) => {
    const angle = start + i * length / segments;
    return new THREE.Vector3(Math.cos(angle) * radius, height, Math.sin(angle) * radius);
  });
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
}

function buildCore(texture) {
  const core = new THREE.Group();
  const hub = new THREE.Group();
  hub.position.y = 0.87;
  core.add(hub);

  const jewel = new THREE.Mesh(new THREE.IcosahedronGeometry(0.31), crystal);
  const cage = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(0.57)), wires.on);
  const glow = halo(texture, primary, 0.75, 2.9);
  const centre = halo(texture, hot, 0.52, 0.74);
  hub.add(jewel, cage, glow, centre);

  const quiet = new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.3 });
  // Each ring turns in its own frame (spin), inside a tilted frame (the tilt stays put).
  const ring = (radius, parts, tilt) => {
    const spin = new THREE.Group();
    for (const [start, length, material] of parts) spin.add(arc(radius, start, length, 0, material));
    const frame = new THREE.Group();
    frame.rotation.set(...tilt);
    frame.add(spin);
    hub.add(frame);
    return spin;
  };
  const inner = ring(0.85, [[0.2, 2.15, wires.selected], [3.1, 2.1, quiet]], [0.67, 0, 0.34]);
  const outer = ring(1.03, [[0.25, 2.7, wires.on], [3.35, 2.45, quiet]], [-0.55, 0, -0.78]);

  const floor = new THREE.Group();
  floor.add(arc(1.52, 0, Math.PI * 2, 0.02, quiet), arc(2.0, 0, Math.PI * 2, 0.01, quiet));
  const segments = new THREE.Group();
  for (let i = 0; i < 4; i++) {
    segments.add(arc(1.76, i * Math.PI / 2 + 0.14, 0.96, 0.02, wires.on));
  }
  const ticks = [];
  for (let i = 0; i < 72; i++) {
    const angle = i * Math.PI / 36;
    const edge = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle));
    ticks.push(edge.clone().multiplyScalar(i % 6 === 0 ? 2.19 : 2.1), edge.multiplyScalar(2.04));
  }
  const tickRing = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(ticks), quiet);
  floor.add(segments, tickRing);
  core.add(floor);
  return { core, hub, cage, glow, centre, turning: [[inner, ringTurns[0], 1], [outer, ringTurns[1], -1],
    [segments, ringTurns[2], 1], [tickRing, ringTurns[2] * 1.6, -1]] };
}

// A reticle around the selected device: four corner arcs that close in and turn slowly.
function buildReticle() {
  const reticle = new THREE.Group();
  const material = new THREE.LineBasicMaterial({ color: hot, transparent: true, opacity: 0.85 });
  for (let i = 0; i < 4; i++) reticle.add(arc(1.08, i * Math.PI / 2 + 0.35, 0.85, 0.09, material));
  return reticle;
}

// A number in [0, 1) from a text, the same every time (so a device keeps its place and its turn).
function seed(text) {
  let h = 2166136261;
  for (const c of text) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return (h >>> 0) / 4294967296;
}

// Devices group by kind into clusters (the arms, the robots, the cameras, the screens, …). Each cluster
// is a ball: its devices sit evenly on a sphere around the cluster's centre (a Fibonacci sphere, turned
// by a fixed amount per kind), so the map has depth, not one flat level.
// The groups of two or more spread evenly around the core, the largest first, each at its own height
// (one high, one low, one level, …), so no side or level gets all the big ones. Single devices sit at
// the core's level, in the gaps between the groups. Then the clusters push apart where they overlap.
const KINDS = ["arm", "robot", "camera", "headset", "screen"];
const GAP = 3.6, CORE_GAP = 4.4;
const LEVEL = 1.6;  // how far above or below the core the highest and lowest groups sit (the balls still overlap in height)
const GOLDEN = Math.PI * (3 - Math.sqrt(5));
function place(devices) {
  const groups = new Map();
  for (const device of devices) {
    const kind = KINDS.includes(device.kind) ? device.kind : "other";
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push(device);
  }
  const order = [...KINDS, "other"].filter((kind) => groups.has(kind));
  const clusters = order.map((kind) => {
    const members = groups.get(kind).slice().sort((a, b) => a.id.localeCompare(b.id));
    const n = members.length;
    const spacing = kind === "screen" ? GAP * 1.8 : GAP;
    const radius = n === 1 ? 0 : Math.max(spacing * 0.62, spacing * Math.sqrt(n / (4 * Math.PI)) * 1.2);
    return { kind, members, radius, center: new THREE.Vector3() };
  });
  const big = clusters.filter((c) => c.members.length > 1)
    .sort((a, b) => b.members.length - a.members.length || order.indexOf(a.kind) - order.indexOf(b.kind));
  const single = clusters.filter((c) => c.members.length === 1);
  // Heights from high to low, taken alternately from the top and the bottom: +L, -L, then between.
  const even = big.length < 2 ? [0] : big.map((_, i) => LEVEL * (1 - 2 * i / (big.length - 1)));
  const levels = [];
  while (even.length) levels.push(even.shift(), ...(even.length ? [even.pop()] : []));
  const step = 2 * Math.PI / Math.max(1, big.length);
  big.forEach((cluster, i) => {
    const angle = i * step + 0.55, out = CORE_GAP + cluster.radius + 0.8;
    cluster.center.set(Math.cos(angle) * out, levels[i], Math.sin(angle) * out);
  });
  // Single devices: shared out over the gaps between the groups, at the core's level.
  const gaps = Math.max(1, big.length);
  single.forEach((cluster, i) => {
    const gap = i % gaps, inGap = single.filter((_, k) => k % gaps === gap).length;
    const slot = Math.floor(i / gaps) + 1;
    const angle = 0.55 + (big.length ? (gap + slot / (inGap + 1)) * step : 2 * Math.PI * i / single.length);
    const out = CORE_GAP + 1.6;
    cluster.center.set(Math.cos(angle) * out, 0, Math.sin(angle) * out);
  });
  for (const cluster of clusters) cluster.home = cluster.center.clone();
  // Push clusters apart where they overlap (and off the core); a weak pull holds each near its place.
  const push = new THREE.Vector3();
  for (let round = 0; round < 200; round++) {
    for (let i = 0; i < clusters.length; i++) {
      for (let j = i + 1; j < clusters.length; j++) {
        const a = clusters[i], b = clusters[j];
        push.subVectors(a.center, b.center);
        const d = push.length() || 0.01, need = a.radius + b.radius + GAP;
        if (d >= need) continue;
        push.multiplyScalar((need - d) / d * 0.5);
        a.center.add(push);
        b.center.sub(push);
      }
    }
    for (const cluster of clusters) {
      const d = cluster.center.length() || 0.01, need = CORE_GAP + cluster.radius + 0.8;
      if (d < need) cluster.center.multiplyScalar(need / d);
      cluster.center.lerp(cluster.home, 0.03);
    }
  }
  const spots = new Map();
  for (const { kind, members, radius, center } of clusters) {
    const turn = new THREE.Euler(seed(`${kind}:x`) * Math.PI, seed(`${kind}:y`) * Math.PI * 2, seed(`${kind}:z`) * Math.PI);
    members.forEach((device, k) => {
      const n = members.length;
      const y = n === 1 ? 0 : 1 - 2 * (k + 0.5) / n;
      const ring = Math.sqrt(1 - y * y);
      const point = new THREE.Vector3(Math.cos(k * GOLDEN) * ring, y, Math.sin(k * GOLDEN) * ring);
      spots.set(device.id, point.applyEuler(turn).multiplyScalar(radius).add(center));
    });
  }
  return devices.map((device) => spots.get(device.id));
}

// The icons, drawn into a screen's picture (the same symbols as the pages, in the main color).
let iconSheet;
const hex = (value) => `#${value.toString(16).padStart(6, "0")}`;
function iconImage(id) {
  iconSheet ??= fetch("/web/design/icons.svg").then((r) => r.text())
    .then((text) => new DOMParser().parseFromString(text, "image/svg+xml")).catch(() => null);
  return iconSheet.then((sheet) => {
    const symbol = sheet?.getElementById(id);
    if (!symbol) return null;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${symbol.getAttribute("viewBox")}" width="96" height="96"`
      + ` fill="none" stroke="${hex(primary)}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">`
      + `${symbol.innerHTML}</svg>`;
    return new Promise((resolve) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    });
  });
}

function starField() {
  const points = [];
  let seed = 219;
  const rand = () => {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let i = 0; i < 320; i++) {
    const theta = rand() * Math.PI * 2;
    const height = rand() * 2 - 1;
    const radius = 12 + rand() * 32;
    const flat = Math.sqrt(1 - height * height);
    points.push(new THREE.Vector3(radius * flat * Math.cos(theta), radius * height, radius * flat * Math.sin(theta)));
  }
  return new THREE.Points(new THREE.BufferGeometry().setFromPoints(points),
    new THREE.PointsMaterial({ color: primary, size: 1.8, sizeAttenuation: false, transparent: true, opacity: 0.22 }));
}

export function createMap(canvas, labels, onSelect) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(41, 1, 0.1, 300);
  const controls = new OrbitControls(camera, canvas);
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  controls.zoomToCursor = true;
  controls.minDistance = 2.4;
  controls.minPolarAngle = 0.03;
  controls.maxPolarAngle = Math.PI - 0.03;
  controls.rotateSpeed = 0.72;
  controls.dampingFactor = 0.16;
  scene.add(new THREE.HemisphereLight(hot, color("colors.surface"), 2.5));
  const light = new THREE.DirectionalLight(hot, 2);
  light.position.set(-4, 10, 6);
  scene.add(light);

  const graph = new THREE.Group();
  const signals = new THREE.Group();
  const texture = glowTexture();
  const { core, hub, cage, glow, centre, turning } = buildCore(texture);
  const reticle = buildReticle();
  const pulsePool = Array.from({ length: 16 }, () => halo(texture, hot, 0.95, 0.52));
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  scene.add(graph, core, signals, starField());
  // The decorations that don't belong to one device (rebuilt floor, the ping, maximal's extras).
  const stage = new THREE.Group(), floor = new THREE.Group(), extras = new THREE.Group();
  const ping = new THREE.LineLoop(footGeometry, faint(0.5));
  ping.visible = false;
  stage.add(floor, ping);
  const satellite = new THREE.Group();
  const satelliteSpin = new THREE.Group();
  satelliteSpin.add(arc(2.75, 0, 1.4, 0, tickLine), arc(2.75, 2.1, 1.4, 0, tickLine), arc(2.75, 4.2, 1.4, 0, tickLine));
  for (let i = 0; i < 3; i++) {
    const bead = new THREE.Mesh(marker, point);
    bead.scale.setScalar(1.6);
    bead.position.set(Math.cos(i * 2.1 + 1.4) * 2.75, 0, Math.sin(i * 2.1 + 1.4) * 2.75);
    satelliteSpin.add(bead);
  }
  satellite.add(satelliteSpin);
  satellite.position.y = 0.87;
  satellite.rotation.set(1.05, 0, 0.35);
  extras.add(satellite);
  scene.add(stage, extras);
  let floorY = -3, nextPing = 0;
  scene.fog = new THREE.FogExp2(color("colors.background"), 0.0105);
  const nodes = new Map();
  const project = new THREE.Vector3();
  const viewPoint = new THREE.Vector3();
  const ray = new THREE.Raycaster();
  const viewOffset = new THREE.Vector3(0.28, 0.89, 1).normalize();
  const previousPointer = new THREE.Vector2();
  const highlightedLink = new THREE.LineBasicMaterial({ color: hot, transparent: true, opacity: 0.91 });
  const highlightedNetwork = links.network.clone();
  highlightedNetwork.color.setHex(hot);
  highlightedNetwork.opacity = 0.91;
  let edge = 2.2, fitDistance = 0, points = [new THREE.Vector3()];
  let selected = "", frame = 0, lastDraw = 0, lastTick = 0;
  let seen = new Set(), pulses = [], nextFire = 0, flight = null;
  let spin = 0, lastInput = -Infinity, holding = false, onScreen = true, introduced = false;
  let lookNow = "", lookRead = -Infinity;
  let spots = new Map();               // where each device sits now (id → position)
  const screenPictures = new Map();    // a screen's picture, kept while it shows the same page
  reticle.userData.from = 0;

  // What may move by itself on this screen (the hub's look, then the computer's reduced motion).
  // Read again once a second, so a change in Settings reaches an open map.
  const look = () => {
    const now = performance.now();
    if (now - lookRead > 1000) {
      lookNow = reducedMotion.matches ? "minimal" : currentLook();
      lookRead = now;
    }
    return lookNow;
  };
  const moving = () => look() !== "minimal";
  const firing = () => ["full", "maximal"].includes(look());
  controls.enableDamping = moving();
  reducedMotion.addEventListener("change", () => {
    lookRead = -Infinity;
    controls.enableDamping = moving();
    render();
  });

  // One loop: it keeps going while something moves, at most 30 frames per second unless you're dragging.
  function render() {
    if (frame) return;
    frame = requestAnimationFrame(draw);
  }
  function draw(time) {
    frame = 0;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height || renderer.getContext().isContextLost()) return;
    const busy = holding || flight || pulses.length || hub.userData.born || arriving(time) || time - lastInput < 1200;
    if (!busy && time - lastDraw < IDLE_FRAME_MS) {
      if (alive()) render();
      return;
    }
    const dt = Math.min(0.1, (time - (lastTick || time)) / 1000);
    lastTick = time;
    lastDraw = time;
    step(time, dt);
    controls.update(dt);
    renderer.render(scene, camera);
    layoutLabels(width, height);
    if (alive() || busy) render();
    else lastTick = 0;
  }
  // Keep the loop running? Only on screen, in a visible tab, and when something may move.
  const alive = () => onScreen && !document.hidden && (moving() || flight || holding);

  function step(time, dt) {
    const still = !moving();
    // The core settles in once, on the first draw (it grows and turns into place).
    if (hub.userData.born) {
      const k = arrive(Math.min(1, (time - hub.userData.born) / 1050));
      hub.rotation.y = (k - 1) * Math.PI * 0.85;
      hub.scale.setScalar(0.72 + k * 0.28);
      if (k >= 1) hub.userData.born = 0;
    }
    // Idle spin: eases out on input, eases back in a few seconds after the last one.
    const want = still || holding || flight || time - lastInput < SPIN_AFTER_MS ? 0 : 1;
    spin += (want - spin) * Math.min(1, dt * (want ? 0.9 : 6));
    controls.autoRotate = spin > 0.002;
    controls.autoRotateSpeed = spin * 60 / SPIN_S;
    const fancy = firing(), most = look() === "maximal";
    stage.visible = fancy;
    extras.visible = most;
    for (const node of nodes.values()) for (const d of node.decor) d.visible = fancy;
    if (fancy) {
      for (const node of nodes.values()) if (node.ticks) node.ticks.rotation.y += dt * 2 * Math.PI / ringTurns[1];
      // The ping: a ring that runs out from the core along the core's level and fades.
      if (time > nextPing) {
        ping.userData.start = time;
        const [a, b] = motion.idle?.event_every_s || [8, 20];
        nextPing = time + 1000 * (a + Math.random() * (b - a));
      }
      const t = (time - (ping.userData.start ?? -Infinity)) / 2600;
      ping.visible = t >= 0 && t < 1;
      if (ping.visible) {
        ping.scale.setScalar((2.3 + arrive(t) * (edge - 2.3)) / 0.28);
        ping.material.opacity = 0.45 * (1 - t);
      }
    }
    if (most) {
      satelliteSpin.rotation.y -= dt * 2 * Math.PI / ringTurns[0];
    }
    glow.visible = centre.visible = !still;
    if (!still) {
      const s = time / 1000;
      for (const [object, period, direction] of turning) object.rotation.y = direction * s * 2 * Math.PI / period;
      cage.rotation.y = -s * 2 * Math.PI / (ringTurns[2] * 1.3);
      const breath = 0.5 - 0.5 * Math.cos(s * 2 * Math.PI / breatheS);
      glow.material.opacity = 0.6 + breath * 0.25;
      glow.scale.setScalar(2.7 + breath * 0.4);
      centre.material.opacity = 0.42 + breath * 0.2;
      reticle.rotation.y = s * 2 * Math.PI / ringTurns[1];
      for (const node of nodes.values()) {
        if (node.spinner) node.spinner.rotation.y += dt * 2 * Math.PI / MODEL_TURN_S;
      }
    }
    // Devices glide to their new places when others arrive or leave.
    for (const node of nodes.values()) {
      if (!node.moveStart) continue;
      const k = arrive(Math.min(1, Math.max(0, (time - node.moveStart) / (panelMs * 1.6))));
      node.group.position.lerpVectors(node.moveFrom, node.to, k);
      if (node.trace) retrace(node);
      dropTo(node);
      if (k >= 1) node.moveStart = 0;
    }
    // The reticle closes in on the selected device.
    const r = Math.min(1, (time - reticle.userData.from) / panelMs);
    const size = reticle.userData.size || 1;
    reticle.scale.setScalar(size * (still ? 1 : 1 + 0.45 * (1 - arrive(r))));
    reticle.children[0].material.opacity = 0.85 * (still ? 1 : arrive(r));
    arrivals(time);
    firePulses(time);
    if (flight) fly(time);
  }

  // Devices arrive one after another, outward from the centre; their traces draw themselves in.
  function arriving(time) {
    for (const node of nodes.values()) if (node.moveStart || (node.born && time < node.born + panelMs)) return true;
    return false;
  }
  function arrivals(time) {
    for (const node of nodes.values()) {
      if (!node.born) continue;
      const t = Math.min(1, Math.max(0, (time - node.born) / panelMs));
      const k = arrive(t);
      node.group.scale.setScalar(0.001 + k * 0.999);
      node.label.style.opacity = String(k);
      if (node.trace) node.trace.geometry.setDrawRange(0, Math.max(2, Math.ceil(k * TRACE_POINTS)));
      if (node.tip) node.tip.visible = t >= 1;
      if (t >= 1) node.born = 0;
    }
  }

  // Now and then a pulse runs along a live link, out from the core or in to it.
  function firePulses(time) {
    pulses = pulses.filter((p) => {
      const t = (time - p.start) / p.ms;
      if (t >= 1) {
        p.sprite.visible = false;
        signals.remove(p.sprite);
        return false;
      }
      p.sprite.visible = t > 0;
      if (t > 0) {
        p.curve.getPoint(p.out ? t : 1 - t, p.sprite.position);
        p.sprite.material.opacity = Math.sin(t * Math.PI) * 0.95;
      }
      return true;
    });
    if (!firing() || time < nextFire) return;
    const live = [...nodes.values()].filter((n) => n.curve);
    if (nextFire && live.length) {
      const node = live[Math.floor(Math.random() * live.length)];
      pulse(node.curve, time, Math.random() < 0.6);
    }
    nextFire = time + 1000 * (fireEvery[0] + Math.random() * (fireEvery[1] - fireEvery[0]));
  }
  function pulse(curve, start, out = true) {
    const sprite = pulsePool.find((s) => !s.parent);
    if (!sprite) return;
    sprite.visible = false;
    signals.add(sprite);
    pulses.push({ curve, sprite, start, ms: 1100, out });
  }

  // Camera flights (reset, focus): one curve that starts fast and settles; any drag cancels one.
  function flyTo(target, position) {
    if (!moving()) {
      controls.target.copy(target);
      camera.position.copy(position);
      controls.update();
      render();
      return;
    }
    flight = { start: performance.now(), from: [controls.target.clone(), camera.position.clone()], to: [target, position] };
    render();
  }
  function fly(time) {
    const k = arrive(Math.min(1, (time - flight.start) / panelMs));
    controls.target.lerpVectors(flight.from[0], flight.to[0], k);
    camera.position.lerpVectors(flight.from[1], flight.to[1], k);
    if (k >= 1) {
      flight = null;
      lastInput = performance.now();
    }
  }

  // Project the callouts in screen coordinates, so the text never turns edge-on. The selected device
  // goes first, then the connected ones, nearest first; a name that would cover another one waits.
  function layoutLabels(width, height) {
    const placed = [];
    const covers = (box) => placed.some((p) => box.x0 < p.x1 && box.x1 > p.x0 && box.y0 < p.y1 && box.y1 > p.y0);
    const list = [...nodes.values()].map((node) => {
      viewPoint.copy(node.group.position).applyMatrix4(camera.matrixWorldInverse);
      return { node, depth: -viewPoint.z };
    });
    const rank = ({ node }) => (node.device.id === selected ? 0 : node.device.connected ? 1 : 2);
    list.sort((a, b) => rank(a) - rank(b) || a.depth - b.depth);
    for (const { node, depth } of list) {
      const { device, label, group } = node;
      const inFront = depth > camera.near;
      project.copy(group.position).project(camera);
      const x = (project.x + 1) * width / 2;
      const baseY = (1 - project.y) * height / 2;
      project.copy(group.position);
      project.y += node.height;
      project.project(camera);
      const y = (1 - project.y) * height / 2 - 4;
      const priority = device.id === selected;
      const half = Math.min(75, 5 + device.name.length * 3.6);
      const left = Math.max(half + 5, Math.min(width - half - 5, x));
      const inView = inFront && x > 0 && x < width && baseY > 0 && baseY < height && y > 26;
      const box = { x0: left - half - 2, x1: left + half + 2, y0: y - 20, y1: y };
      label.hidden = !inView || (covers(box) && !priority);
      if (label.hidden) continue;
      label.style.left = `${left}px`;
      label.style.top = `${y}px`;
      label.style.zIndex = priority ? "1200" : "1100";
      placed.push(box);
    }
  }

  // The distance at which every device stays in view from any side at the starting angle, so the
  // idle spin never cuts one off and the map fills the view (a disc, not a ball).
  function fitFor(aspect) {
    const tanY = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.96;
    const tanX = tanY * aspect;
    const forward = new THREE.Vector3(), right = new THREE.Vector3(), up = new THREE.Vector3();
    const look = new THREE.Matrix4();
    let need = 0;
    for (let i = 0; i < 12; i++) {
      const from = viewOffset.clone().applyAxisAngle(THREE.Object3D.DEFAULT_UP, i * Math.PI / 6);
      look.lookAt(from, new THREE.Vector3(), THREE.Object3D.DEFAULT_UP);
      look.extractBasis(right, up, forward);  // forward points from the target back to the camera
      for (const p of points) {
        const toward = p.dot(forward);
        need = Math.max(need, toward + Math.abs(p.dot(right)) / tanX, toward + Math.abs(p.dot(up)) / tanY);
      }
    }
    return Math.max(need, 6);
  }

  function resize() {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    const next = fitFor(camera.aspect);
    if (fitDistance && !flight) camera.position.sub(controls.target).multiplyScalar(next / fitDistance).add(controls.target);
    fitDistance = next;
    controls.maxDistance = fitDistance * 2.2;
    controls.maxTargetRadius = edge;
    controls.update();
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(drawRes(), 1.5));  // sharp on a laptop's screen, light on a big one
    renderer.setSize(width, height, false);
    render();
  }

  function reset() {
    lastInput = performance.now();
    flyTo(new THREE.Vector3(), viewOffset.clone().multiplyScalar(fitDistance || 10));
  }

  function focus(id = selected) {
    const node = nodes.get(id);
    if (!node) return;
    lastInput = performance.now();
    const target = node.group.position.clone();
    target.y += node.height * 0.45;
    const away = camera.position.clone().sub(controls.target).normalize();
    flyTo(target, target.clone().addScaledVector(away, id ? 7 : 10));
  }

  // A screen's picture: what its window shows, drawn once per page shown, on a sprite that always
  // faces you. It is part of the scene, so a device in front of it hides it.
  function screenPicture(preview) {
    const key = JSON.stringify(preview);
    if (screenPictures.has(key)) return screenPictures.get(key);
    const aspect = previewAspect(preview);
    const W = 768, H = Math.round(W * aspect), P = 40;  // P: room for the glow around the frame
    const image = document.createElement("canvas");
    image.width = W + 2 * P;
    image.height = H + 2 * P;
    const texture = new THREE.CanvasTexture(image);
    texture.colorSpace = THREE.SRGBColorSpace;
    const picture = { texture, aspect: image.height / image.width };
    const paint = (icon) => {
      const ctx = image.getContext("2d");
      ctx.clearRect(0, 0, image.width, image.height);
      ctx.save();
      ctx.shadowColor = `${hex(primary)}88`;
      ctx.shadowBlur = moving() ? 38 : 0;
      ctx.fillStyle = hex(background);
      ctx.fillRect(P, P, W, H);
      ctx.restore();
      const fill = ctx.createRadialGradient(P + W / 2, P + H / 2, 0, P + W / 2, P + H / 2, W * 0.6);
      fill.addColorStop(0, hex(surface));
      fill.addColorStop(1, hex(background));
      ctx.fillStyle = fill;
      ctx.fillRect(P, P, W, H);
      ctx.strokeStyle = hex(primary);
      ctx.lineWidth = 6;
      ctx.strokeRect(P + 3, P + 3, W - 6, H - 6);
      const cx = P + W / 2, cy = P + H * 0.44;
      if (preview.showing) {
        const size = H * 0.34;
        if (icon) ctx.drawImage(icon, cx - size / 2, cy - size / 2, size, size);
      } else if (preview.stage === "start") {
        ctx.strokeStyle = `${hex(primary)}8c`;
        ctx.lineWidth = 4.5;
        ctx.beginPath();
        ctx.arc(cx, cy, W * 0.16 * Math.min(1, aspect / 0.5625), 0, Math.PI * 2);
        ctx.stroke();
      } else {
        const r = W * 0.13 * Math.min(1, aspect / 0.5625);
        ctx.save();
        ctx.shadowColor = hex(primary);
        ctx.shadowBlur = moving() ? 32 : 0;
        ctx.strokeStyle = hex(primary);
        ctx.lineWidth = 9;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
        ctx.strokeStyle = `${hex(primary)}73`;
        ctx.lineWidth = 4.5;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 0.62, 0, Math.PI * 2);
        ctx.stroke();
      }
      const fit = (text, room) => {
        let shown = text;
        while (shown.length > 1 && ctx.measureText(shown).width > room) shown = `${shown.slice(0, -2)}…`;
        return shown;
      };
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      ctx.fillStyle = hex(textColor);
      ctx.font = `500 ${Math.round(H * 0.12)}px "Chakra Petch", system-ui, sans-serif`;
      ctx.fillText(fit(screenTitle(preview), W - 56), cx, P + H - H * 0.08);
      if (preview.showing && preview.from) {
        ctx.textAlign = "right";
        ctx.fillStyle = hex(textDim);
        ctx.font = `300 ${Math.round(H * 0.085)}px Inter, system-ui, sans-serif`;
        ctx.fillText(fit(`From ${preview.from}`, W * 0.7), P + W - 24, P + H * 0.14);
      }
      texture.needsUpdate = true;
      render();
    };
    paint(null);
    // Again once the fonts and the icon are in (the first paint may use a fallback font).
    Promise.all([preview.showing ? iconImage(previewIcon(preview)) : null, document.fonts?.ready])
      .then(([icon]) => paint(icon));
    screenPictures.set(key, picture);
    return picture;
  }

  function add(device, position) {
    const group = new THREE.Group();
    group.position.copy(position);
    graph.add(group);
    const base = new THREE.Mesh(pad, device.connected ? litPad : dark);
    const wire = new THREE.LineSegments(outline, wires[device.connected ? "on" : "off"]);
    group.add(base, wire);
    const node = { group, wire, device, height: device.kind === "brain" ? 1.95 : device.connected ? 1.75 : 0.98 };
    // A line down to the floor (it shows the height) and a small ring where it lands.
    node.drop = new THREE.Line(dropGeometry, dropLine);
    node.foot = new THREE.LineLoop(footGeometry, footLine);
    node.decor = [node.drop, node.foot];
    if (device.connected && device.kind !== "brain") {
      node.ticks = new THREE.LineSegments(tickGeometry, tickLine);
      node.ticks.position.y = 0.02;
      node.decor.push(node.ticks);
    }
    group.add(...node.decor);
    const key = Object.hasOwn(shapes, device.kind) ? device.kind : "usb";
    const simple = device.connected
      ? new THREE.Mesh(shapes[key], holo)
      : new THREE.Group();  // offline: the outline only
    if (device.kind !== "brain") {
      simple.add(new THREE.LineSegments(edges[key], wires[device.connected ? "on" : "off"]));
      simple.position.y = device.connected ? 1.16 : 0.49;
      if (device.preview) {
        const picture = screenPicture(device.preview);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
          map: picture.texture, transparent: true, depthWrite: false,
        }));
        const width = 1.65, tall = width * picture.aspect;
        sprite.scale.set(width, tall, 1);
        sprite.position.y = 0.62 + tall / 2;
        group.add(sprite);
        node.height = 0.62 + tall - 0.05;
      } else {
        group.add(simple);
      }
      if (device.connected) {
        const projection = new THREE.Mesh(beam, beamMaterial);
        projection.position.y = 0.46;
        group.add(projection);
      }
    }
    const label = document.createElement("button");
    label.type = "button";
    label.tabIndex = -1;
    label.className = device.connected ? "map-label" : "map-label off";
    label.textContent = device.name;
    label.title = device.name;
    label.hidden = true;
    label.addEventListener("click", () => onSelect(device.id));
    label.addEventListener("dblclick", () => focus(device.id));
    labels.append(label);
    node.label = label;
    nodes.set(device.id, node);
    const type = Object.hasOwn(modelTypes, device.model) ? modelTypes[device.model] : null;
    if (type) modelFor(type).then((object) => {
      if (!object || nodes.get(device.id) !== node) return;
      // The model turns on its base: it sits in a pivot at the base's centre.
      const pivot = new THREE.Group();
      pivot.add(object.clone(true));
      pivot.rotation.y = seed(device.id) * Math.PI * 2;
      if (device.connected) {
        pivot.position.y = lift;
        node.spinner = pivot;
      }
      group.remove(simple);
      group.add(pivot);
      node.height = 1.62 + (device.connected ? lift : 0);
      render();
    });
    return node;
  }

  // The trace from the core to a device: up and over, then down to the device's base. Updated in place
  // (the pulses ride the same curve) while the device glides to a new place.
  function retrace(node) {
    const position = node.group.position;
    const direction = position.clone().setY(0).normalize();
    const [first, second] = node.curve.curves;
    first.v1.copy(direction).multiplyScalar(0.96);
    first.v1.y += hub.position.y;
    second.v2.copy(position).addScaledVector(direction, -0.7);
    first.v2.copy(first.v1).lerp(second.v2, 0.57);
    first.v2.y += 0.52 + 0.052 * Math.hypot(position.x, position.z);
    second.v1.copy(first.v2);
    node.curve.updateArcLengths();
    node.trace.geometry.setFromPoints(node.curve.getSpacedPoints(TRACE_POINTS - 1));
    node.trace.computeLineDistances();
    node.tip.position.copy(second.v2);
  }

  function setDevices(devices) {
    graph.traverse((child) => {
      if (child.isLine && !sharedLines.has(child.geometry) && !decorLines.includes(child.geometry)) child.geometry.dispose();
      if (child.isSprite) child.material.dispose();
    });
    graph.clear();
    nodes.clear();
    labels.replaceChildren();
    add(devices[0], new THREE.Vector3());
    const now = performance.now();
    const animate = moving();
    const fresh = [];
    const nextSeen = new Set();
    const others = devices.slice(1);
    const targets = place(others);
    points = [new THREE.Vector3(0, 2.2, 0), new THREE.Vector3(2.2, 0, 0), new THREE.Vector3(-2.2, 0, 0)];
    edge = 2.2;
    const nextSpots = new Map();
    others.forEach((device, i) => {
      const target = targets[i];
      const was = spots.get(device.id);
      const node = add(device, animate && was ? was : target);
      node.to = target;
      if (animate && was && was.distanceToSquared(target) > 0.0004) {
        node.moveFrom = was.clone();
        node.moveStart = now;
      }
      nextSpots.set(device.id, target);
      edge = Math.max(edge, target.length() + 1.5);
      points.push(target.clone(), target.clone().setY(target.y + node.height + 0.5));
      const key = `${device.id}:${device.connected}`;
      nextSeen.add(key);
      if (animate && !seen.has(key)) fresh.push(node);
      if (!device.connected) return;
      const curve = new THREE.CurvePath();
      curve.add(new THREE.LineCurve3(new THREE.Vector3(), new THREE.Vector3()));
      curve.add(new THREE.LineCurve3(new THREE.Vector3(), new THREE.Vector3()));
      const tip = new THREE.Mesh(marker, point);
      const material = device.via?.includes("USB") ? links.usb : links.network;
      const trace = new THREE.Line(new THREE.BufferGeometry(), material);
      Object.assign(node, { trace, traceMaterial: material, tip, curve });
      retrace(node);
      graph.add(trace, tip);
    });
    spots = nextSpots;
    buildFloor(targets);
    for (const node of nodes.values()) dropTo(node);
    // New devices (and ones that changed state) arrive one after another, nearest first.
    fresh.sort((a, b) => a.to.length() - b.to.length());
    fresh.forEach((node, i) => {
      node.born = now + i * staggerMs;
      node.group.scale.setScalar(0.001);
      if (node.trace) node.trace.geometry.setDrawRange(0, 2);
      if (node.tip) node.tip.visible = false;
      if (node.curve && firing()) pulse(node.curve, node.born + panelMs * 0.4);
    });
    seen = nextSeen;
    if (!introduced && animate) {
      hub.userData.born = now;
      hub.scale.setScalar(0.72);
    }
    introduced = true;
    resize();
  }

  // The floor sits a little under the lowest device: a polar grid as wide as the map, + marks where
  // its rings meet its spokes.
  function buildFloor(targets) {
    floor.traverse((child) => {
      if (child.isLine) child.geometry.dispose();
      if (child.material && child.material !== plusLine) child.material.dispose();
    });
    floor.clear();
    floorY = Math.min(-2.6, ...targets.map((t) => t.y - 2.6));
    const rings = Math.max(3, Math.round(edge / 3));
    const grid = new THREE.PolarGridHelper(edge, 12, rings, 72, primary, primary);
    grid.material.transparent = true;
    grid.material.opacity = 0.07;
    grid.material.depthWrite = false;
    const plus = [];
    for (let r = 1; r <= rings; r++) {
      for (let k = 0; k < 12; k++) {
        const a = k * Math.PI / 6, at = new THREE.Vector3(Math.cos(a), 0, Math.sin(a)).multiplyScalar(edge * r / rings);
        const across = new THREE.Vector3(-Math.sin(a), 0, Math.cos(a)).multiplyScalar(0.16);
        const along = new THREE.Vector3(Math.cos(a), 0, Math.sin(a)).multiplyScalar(0.16);
        plus.push(at.clone().add(across), at.clone().sub(across), at.clone().add(along), at.clone().sub(along));
      }
    }
    floor.add(grid, new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(plus), plusLine));
    floor.position.y = floorY;
  }

  function dropTo(node) {
    const h = Math.max(0.01, node.group.position.y - floorY);
    node.drop.scale.y = h;
    node.foot.position.y = -h;
  }

  function placeReticle(node, animate) {
    node.group.add(reticle);
    reticle.userData.size = selected ? 1 : 2.2;
    if (animate) reticle.userData.from = performance.now();
  }

  function select(device) {
    const previous = nodes.get(selected);
    if (previous) {
      previous.wire.material = wires[previous.device.connected ? "on" : "off"];
      previous.label.classList.remove("selected");
      if (previous.trace) previous.trace.material = previous.traceMaterial;
    }
    const changed = selected !== device.id;
    selected = device.id;
    const node = nodes.get(selected);
    if (!node) return;
    node.wire.material = wires.selected;
    node.label.classList.add("selected");
    if (node.trace) node.trace.material = node.traceMaterial === links.usb ? highlightedLink : highlightedNetwork;
    if (changed || reticle.parent !== node.group) placeReticle(node, changed);
    render();
  }

  // Input: any touch pauses the idle spin and cancels a flight.
  const input = () => {
    lastInput = performance.now();
    render();
  };
  controls.addEventListener("start", () => {
    holding = true;
    flight = null;
    input();
  });
  controls.addEventListener("end", () => {
    holding = false;
    input();
  });
  controls.addEventListener("change", render);
  canvas.addEventListener("wheel", input, { passive: true });
  canvas.addEventListener("pointerdown", (event) => previousPointer.set(event.clientX, event.clientY));

  canvas.addEventListener("keydown", (event) => {
    const { key, shiftKey } = event;
    // Keys with Cmd, Ctrl or Alt belong to the browser (Cmd+R reloads, Cmd+F finds): the map leaves them.
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (key === "v" || key === "V" || key === "Home") {
      event.preventDefault();
      reset();
      return;
    }
    if (key === "f" || key === "F") {
      event.preventDefault();
      focus();
      return;
    }
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "+", "=", "-"].includes(key)) return;
    event.preventDefault();
    flight = null;
    input();
    const offset = camera.position.clone().sub(controls.target);
    if (shiftKey && key.startsWith("Arrow")) {
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 0);
      const up = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 1);
      const stepSize = offset.length() * 0.06;
      const move = new THREE.Vector3()
        .addScaledVector(right, key === "ArrowLeft" ? -stepSize : key === "ArrowRight" ? stepSize : 0)
        .addScaledVector(up, key === "ArrowDown" ? -stepSize : key === "ArrowUp" ? stepSize : 0);
      controls.target.add(move);
      camera.position.add(move);
    } else {
      const orbit = new THREE.Spherical().setFromVector3(offset);
      if (key === "ArrowLeft") orbit.theta -= 0.17;
      if (key === "ArrowRight") orbit.theta += 0.17;
      if (key === "ArrowUp") orbit.phi -= 0.17;
      if (key === "ArrowDown") orbit.phi += 0.17;
      if (key === "+" || key === "=") orbit.radius *= 0.9;
      if (key === "-") orbit.radius *= 1.11;
      orbit.radius = Math.min(controls.maxDistance, Math.max(controls.minDistance, orbit.radius));
      camera.position.setFromSpherical(orbit.makeSafe()).add(controls.target);
    }
    controls.update();
    render();
  });

  function nodeAt(event) {
    const rect = canvas.getBoundingClientRect();
    ray.setFromCamera({
      x: 2 * (event.clientX - rect.left) / rect.width - 1,
      y: 1 - 2 * (event.clientY - rect.top) / rect.height,
    }, camera);
    // Select using a simple bounding sphere so clicks also work on detailed models.
    const sphere = new THREE.Sphere(new THREE.Vector3(), 0.8);
    let closest, distance = Infinity;
    for (const node of nodes.values()) {
      sphere.center.copy(node.group.position);
      sphere.center.y += node.height * 0.48;
      sphere.radius = Math.max(0.8, node.height * 0.5);
      const hit = ray.ray.intersectSphere(sphere, project);
      if (!hit) continue;
      const depth = ray.ray.origin.distanceToSquared(hit);
      if (depth < distance) {
        closest = node;
        distance = depth;
      }
    }
    return closest;
  }
  canvas.addEventListener("click", (event) => {
    if (Math.hypot(event.clientX - previousPointer.x, event.clientY - previousPointer.y) > 5) return;
    const node = nodeAt(event);
    if (node) onSelect(node.device.id);
  });
  canvas.addEventListener("dblclick", (event) => {
    const node = nodeAt(event);
    if (node) focus(node.device.id);
    else reset();
  });
  // The names and previews sit over the canvas: scroll and drags on them still move the map.
  labels.addEventListener("wheel", (event) => {
    event.preventDefault();
    canvas.dispatchEvent(new WheelEvent("wheel", event));
  }, { passive: false });

  new ResizeObserver(resize).observe(canvas);
  new IntersectionObserver(([entry]) => {
    onScreen = entry.isIntersecting;
    render();
  }).observe(canvas);
  document.addEventListener("visibilitychange", () => {
    lastTick = 0;
    render();
  });
  resize();
  camera.position.copy(viewOffset).multiplyScalar(fitDistance || 10);
  controls.update();
  return { setDevices, select, reset, focus };
}
