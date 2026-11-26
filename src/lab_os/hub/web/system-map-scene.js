import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { loadArmModel } from "/static/arm/arm-model.js";
import { loadRaspbotModel } from "/web/raspbot-model.js";
import { drawRes } from "/web/screen.js";
import { color } from "/web/theme.js";
import { screenPreview } from "/hub/screen-preview.js";

const primary = color("colors.primary");
const offline = color("colors.offline");
const line = color("colors.line");
const hot = color("colors.hot");
const pad = new THREE.CylinderGeometry(0.73, 0.81, 0.13, 6);
const outline = new THREE.EdgesGeometry(pad);
const marker = new THREE.OctahedronGeometry(0.067);
const beam = new THREE.CylinderGeometry(0.52, 0.28, 0.77, 6, 1, true);
const beamMaterial = new THREE.MeshBasicMaterial({
  color: primary, transparent: true, opacity: 0.09, depthWrite: false, side: THREE.DoubleSide,
  blending: THREE.AdditiveBlending,
});
const holo = new THREE.MeshStandardMaterial({
  color: color("colors.line"), emissive: primary, emissiveIntensity: 0.25, roughness: 0.55,
});
const lift = 0.79;
const horizon = new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.19 });
const shapes = {
  screen: new THREE.BoxGeometry(1.05, 0.66, 0.14),
  camera: new THREE.CylinderGeometry(0.31, 0.38, 0.65, 6).rotateX(Math.PI / 2),
  headset: new THREE.CylinderGeometry(0.49, 0.54, 0.42, 6),
  usb: new THREE.BoxGeometry(0.55, 0.4, 0.8),
};
const edges = Object.fromEntries(Object.entries(shapes).map(([kind, g]) => [kind, new THREE.EdgesGeometry(g)]));
const sharedLines = new Set([outline, ...Object.values(edges)]);
const dark = new THREE.MeshStandardMaterial({ color: color("colors.surface"), roughness: 0.75 });
const litPad = new THREE.MeshStandardMaterial({
  color: color("colors.surface"), emissive: line, emissiveIntensity: 0.38,
  roughness: 0.65, transparent: true, opacity: 0.64, depthWrite: false,
});
const wires = {
  on: new THREE.LineBasicMaterial({ color: primary }),
  off: new THREE.LineBasicMaterial({ color: offline }),
  selected: new THREE.LineBasicMaterial({ color: hot }),
};
const point = new THREE.MeshBasicMaterial({ color: primary });
const crystal = new THREE.MeshStandardMaterial({
  color: primary, emissive: primary, emissiveIntensity: 0.63, roughness: 0.45,
});
const links = {
  usb: new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.65 }),
  network: new THREE.LineDashedMaterial({ color: primary, dashSize: 0.16, gapSize: 0.13, transparent: true, opacity: 0.65 }),
};

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
  hub.add(jewel, cage, halo(texture, primary, 0.75, 2.9), halo(texture, hot, 0.52, 0.74));

  const quiet = new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.3 });
  const orbit = new THREE.Group();
  orbit.add(arc(0.85, 0.2, 2.15, 0, wires.selected), arc(0.85, 3.1, 2.1, 0, quiet));
  orbit.rotation.set(0.67, 0, 0.34);
  const outer = new THREE.Group();
  outer.add(arc(1.03, 0.25, 2.7, 0, wires.on), arc(1.03, 3.35, 2.45, 0, quiet));
  outer.rotation.set(-0.55, 0, -0.78);
  hub.add(orbit, outer);

  core.add(arc(1.52, 0, Math.PI * 2, 0.02, quiet), arc(2.0, 0, Math.PI * 2, 0.01, quiet));
  for (let i = 0; i < 4; i++) {
    core.add(arc(1.76, i * Math.PI / 2 + 0.14, 0.96, 0.02, wires.on));
  }
  const ticks = [];
  for (let i = 0; i < 72; i++) {
    const angle = i * Math.PI / 36;
    const edge = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle));
    ticks.push(edge.clone().multiplyScalar(i % 6 === 0 ? 2.19 : 2.1), edge.multiplyScalar(2.04));
  }
  core.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(ticks), quiet));
  return { core, hub };
}

// Pack devices into inclined orbits with alternating tilt and azimuth.
const radiusOf = (ring) => 4.65 + ring * 3.75;
function orbitRotation(ring) {
  const inclination = [0.3, -0.39, 0.45][ring % 3];
  return new THREE.Euler(inclination, 0, (ring % 2 ? 1 : -1) * 0.19, "YXZ");
}

function galaxy(devices) {
  const result = [];
  let capacity = 0;
  let rings = 0;
  while (capacity < devices.length) capacity += 8 + 6 * rings++;
  let offset = 0;
  for (let ring = 0; ring < rings; ring++) {
    const slots = 8 + ring * 6;
    const count = Math.round((devices.length - offset) * slots / capacity);
    capacity -= slots;
    const radius = radiusOf(ring);
    const tilt = orbitRotation(ring);
    const positions = devices.slice(offset, offset + count).map((device, i) => {
      const angle = 2 * Math.PI * i / count + ring * 1.07 + 0.55;
      const position = new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
      return { device, position: position.applyEuler(tilt) };
    });
    result.push({ radius, tilt, positions });
    offset += count;
  }
  return result;
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
    new THREE.PointsMaterial({ color: primary, size: 1.8, sizeAttenuation: false, transparent: true, opacity: 0.28 }));
}

export function createMap(canvas, labels, onSelect) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(41, 1, 0.1, 300);
  const controls = new OrbitControls(camera, canvas);
  controls.enablePan = false;
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
  const { core, hub } = buildCore(texture);
  const pulsePool = Array.from({ length: 16 }, () => halo(texture, hot, 0.95, 0.52));
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  controls.enableDamping = !reducedMotion.matches;
  reducedMotion.addEventListener("change", () => { controls.enableDamping = !reducedMotion.matches; });
  scene.add(graph, core, signals, starField());
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
  let edge = 2.2, fitDistance = 0;
  let selected = "", frame = 0, started = 0, lastDraw = -Infinity;
  let connected = new Set(), paths = [];

  function animate(time) {
    if (!started) return;
    const progress = Math.min(1, Math.max(0, (time - started) / 1050));
    const settle = 1 - (1 - progress) ** 3;
    hub.rotation.y = (settle - 1) * Math.PI * 0.85;
    hub.scale.setScalar(0.72 + settle * 0.28);
    paths.forEach(({ curve, pulse }, index) => {
      const signal = (progress - index * 0.012) * 1.27;
      pulse.visible = signal > 0 && signal < 1;
      if (!pulse.visible) return;
      curve.getPoint(signal, pulse.position);
      pulse.material.opacity = Math.sin(signal * Math.PI) * 0.95;
    });
    if (progress < 1) render();
    else {
      started = 0;
      signals.clear();
    }
  }

  function reveal(routes) {
    signals.clear();
    paths = routes.slice(0, pulsePool.length).map((curve, i) => {
      const pulse = pulsePool[i];
      pulse.visible = false;
      signals.add(pulse);
      return { curve, pulse };
    });
    if (reducedMotion.matches) {
      hub.rotation.y = 0;
      hub.scale.setScalar(1);
      started = 0;
      return;
    }
    started = performance.now();
    render();
  }
  function render() {
    if (frame) return;
    frame = requestAnimationFrame((time) => {
      frame = 0;
      if (started && time - lastDraw < 30) {
        render();
        return;
      }
      lastDraw = time;
      animate(time);
      controls.update();
      const width = canvas.clientWidth, height = canvas.clientHeight;
      if (!width || !height || renderer.getContext().isContextLost()) return;
      renderer.render(scene, camera);
      layoutLabels(width, height);
    });
  }

  // Project the callouts in screen coordinates, so the text never turns edge-on.
  function layoutLabels(width, height) {
    const placed = [];
    const ordered = [...nodes.values()].sort((a, b) => Number(b.device.id === selected) - Number(a.device.id === selected));
    for (const node of ordered) {
      const { device, label, billboard, group } = node;
      viewPoint.copy(group.position).applyMatrix4(camera.matrixWorldInverse);
      const depth = -viewPoint.z;
      const inFront = depth > camera.near;
      const pixelsPerUnit = height / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * depth);
      project.copy(group.position).project(camera);
      const x = (project.x + 1) * width / 2;
      const baseY = (1 - project.y) * height / 2;
      project.copy(group.position);
      project.y += node.height;
      project.project(camera);
      let y = (1 - project.y) * height / 2 - 4;
      const priority = device.id === selected;
      if (billboard) {
        project.copy(group.position);
        project.y += node.height - 0.46;
        project.project(camera);
        const scale = Math.min(1, Math.max(priority ? 0.58 : 0, pixelsPerUnit * 2.1 / 150));
        const middle = (1 - project.y) * height / 2;
        billboard.hidden = !inFront || Math.abs(project.x) > 0.99 || Math.abs(project.y) > 0.96;
        billboard.style.left = `${(project.x + 1) * 50}%`;
        billboard.style.top = `${middle}px`;
        billboard.style.transform = `translate(-50%, -50%) scale(${scale})`;
        billboard.style.zIndex = priority ? "1150" : String(Math.max(0, Math.round(1000 - depth * 8)));
        y = Math.min(y, middle - node.previewHeight * scale * 0.5 - 4);
      }
      const half = Math.min(75, 5 + device.name.length * 3.6);
      const left = Math.max(half + 5, Math.min(width - half - 5, x));
      const inView = inFront && x > 0 && x < width && baseY > 0 && baseY < height && y > 26;
      const collision = placed.some((p) => Math.abs(left - p.left) < half + p.half + 4 && Math.abs(y - p.y) < 19);
      label.hidden = !inView || (collision && !priority);
      if (label.hidden) continue;
      label.style.left = `${left}px`;
      label.style.top = `${y}px`;
      label.style.zIndex = priority ? "1200" : "1100";
      placed.push({ left, half, y });
    }
  }

  function resize() {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const narrow = Math.atan(Math.tan(halfFov) * Math.min(camera.aspect, 1));
    const next = (edge + 1.1) / Math.sin(narrow);
    if (fitDistance) camera.position.multiplyScalar(next / fitDistance);
    fitDistance = next;
    controls.minDistance = edge * 0.38 + 2;
    controls.maxDistance = fitDistance * 2.1;
    controls.update();
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(drawRes(), 1));
    renderer.setSize(width, height, false);
    render();
  }

  function reset() {
    // Clear any remaining drag before returning to the starting angle.
    const damping = controls.enableDamping;
    controls.enableDamping = false;
    controls.update();
    camera.position.copy(viewOffset).multiplyScalar(fitDistance || 10);
    controls.update();
    controls.enableDamping = damping;
    render();
  }

  function add(device, position) {
    const group = new THREE.Group();
    group.position.copy(position);
    graph.add(group);
    const base = new THREE.Mesh(pad, device.connected ? litPad : dark);
    const wire = new THREE.LineSegments(outline, wires[device.connected ? "on" : "off"]);
    group.add(base, wire);
    const key = Object.hasOwn(shapes, device.kind) ? device.kind : "usb";
    const simple = new THREE.Mesh(shapes[key], device.connected ? holo : dark);
    if (device.kind !== "brain") {
      simple.add(new THREE.LineSegments(edges[key], wires[device.connected ? "on" : "off"]));
      simple.position.y = device.connected ? 1.16 : 0.49;
      if (!device.preview) group.add(simple);
      if (device.connected) {
        const projection = new THREE.Mesh(beam, beamMaterial);
        projection.position.y = 0.46;
        group.add(projection);
        group.add(arc(0.52, 0, Math.PI * 2, 0.08, horizon));
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
    labels.append(label);
    const node = { group, wire, label, height: device.kind === "brain" ? 1.95 : device.connected ? 1.75 : 0.98, device };
    nodes.set(device.id, node);
    if (device.preview) {
      const billboard = document.createElement("button");
      billboard.type = "button";
      billboard.tabIndex = -1;
      billboard.className = "map-screen";
      billboard.hidden = true;
      billboard.innerHTML = screenPreview(device.preview, 150);
      billboard.addEventListener("click", () => onSelect(device.id));
      node.billboard = billboard;
      node.previewHeight = parseFloat(billboard.firstElementChild.style.height);
      labels.append(billboard);
    }
    const type = Object.hasOwn(modelTypes, device.model) ? modelTypes[device.model] : null;
    if (type) modelFor(type).then((object) => {
      if (!object || nodes.get(device.id) !== node) return;
      const model = object.clone(true);
      if (device.connected) model.position.y += lift;
      group.remove(simple);
      group.add(model);
      node.height = 1.62 + (device.connected ? lift : 0);
      render();
    });
    return node;
  }

  function setDevices(devices) {
    graph.traverse((child) => {
      if (child.isLine && !sharedLines.has(child.geometry)) child.geometry.dispose();
    });
    graph.clear();
    nodes.clear();
    labels.replaceChildren();
    add(devices[0], new THREE.Vector3());
    const nextConnected = new Set();
    const newRoutes = [];
    edge = 2.2;
    for (const { radius, tilt, positions } of galaxy(devices.slice(1))) {
      edge = radius + 0.9;
      const track = arc(radius, 0, Math.PI * 2, 0, horizon);
      track.rotation.copy(tilt);
      graph.add(track);
      for (const { device, position } of positions) {
        const node = add(device, position);
        if (!device.connected) continue;
        const direction = position.clone().normalize();
        const start = direction.clone().multiplyScalar(0.96);
        start.y += hub.position.y;
        const end = position.clone().addScaledVector(direction, -0.7);
        const bend = start.clone().lerp(end, 0.57);
        bend.y += 0.52 + 0.052 * radius;
        const geometry = new THREE.BufferGeometry().setFromPoints([start, bend, end]);
        const tip = new THREE.Mesh(marker, point);
        tip.position.copy(end);
        const material = device.via?.includes("USB") ? links.usb : links.network;
        const trace = new THREE.Line(geometry, material);
        node.trace = trace;
        node.traceMaterial = material;
        graph.add(trace, tip);
        trace.computeLineDistances();
        nextConnected.add(device.id);
        if (!connected.has(device.id)) {
          const curve = new THREE.CurvePath();
          curve.add(new THREE.LineCurve3(start, bend));
          curve.add(new THREE.LineCurve3(bend, end));
          newRoutes.push(curve);
        }
      }
    }
    connected = nextConnected;
    if (newRoutes.length) reveal(newRoutes);
    resize();
  }

  function select(device) {
    const previous = nodes.get(selected);
    if (previous) {
      previous.wire.material = wires[previous.device.connected ? "on" : "off"];
      previous.label.classList.remove("selected");
      if (previous.trace) previous.trace.material = previous.traceMaterial;
    }
    selected = device.id;
    const node = nodes.get(selected);
    node.wire.material = wires.selected;
    node.label.classList.add("selected");
    if (node.trace) node.trace.material = node.traceMaterial === links.usb ? highlightedLink : highlightedNetwork;
    render();
  }

  canvas.addEventListener("pointerdown", (event) => previousPointer.set(event.clientX, event.clientY));
  canvas.addEventListener("keydown", (event) => {
    const { key } = event;
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "+", "=", "-"].includes(key)) return;
    event.preventDefault();
    const orbit = new THREE.Spherical().setFromVector3(camera.position);
    if (key === "ArrowLeft") orbit.theta -= 0.17;
    if (key === "ArrowRight") orbit.theta += 0.17;
    if (key === "ArrowUp") orbit.phi -= 0.17;
    if (key === "ArrowDown") orbit.phi += 0.17;
    if (key === "+" || key === "=") orbit.radius *= 0.9;
    if (key === "-") orbit.radius *= 1.11;
    camera.position.setFromSpherical(orbit.makeSafe());
    controls.update();
    render();
  });
  canvas.addEventListener("click", (event) => {
    if (Math.hypot(event.clientX - previousPointer.x, event.clientY - previousPointer.y) > 5) return;
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
    if (closest) onSelect(closest.device.id);
  });
  controls.addEventListener("change", render);
  new ResizeObserver(resize).observe(canvas);
  resize();
  reset();
  return { setDevices, select, reset };
}
