import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { loadArmModel } from "/static/arm/arm-model.js";
import { loadRaspbotModel } from "/web/raspbot-model.js";
import { drawRes } from "/web/screen.js";
import { color } from "/web/theme.js";

const primary = color("colors.primary");
const offline = color("colors.offline");
const line = color("colors.line");
const hot = color("colors.hot");
const pad = new THREE.CylinderGeometry(0.73, 0.81, 0.13, 6);
const outline = new THREE.EdgesGeometry(pad);
const shapes = {
  brain: new THREE.IcosahedronGeometry(0.63),
  screen: new THREE.BoxGeometry(1.05, 0.66, 0.14),
  camera: new THREE.CylinderGeometry(0.31, 0.38, 0.65, 6).rotateX(Math.PI / 2),
  headset: new THREE.BoxGeometry(0.95, 0.42, 0.53),
  usb: new THREE.BoxGeometry(0.55, 0.4, 0.8),
};
const edges = Object.fromEntries(Object.entries(shapes).map(([kind, g]) => [kind, new THREE.EdgesGeometry(g)]));
const dark = new THREE.MeshStandardMaterial({ color: color("colors.surface"), roughness: 0.75 });
const wires = {
  on: new THREE.LineBasicMaterial({ color: primary }),
  off: new THREE.LineBasicMaterial({ color: offline }),
  selected: new THREE.LineBasicMaterial({ color: hot }),
};
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

// Separate the screens and devices into two halves. Add rows when a half fills.
function place(index, count, side) {
  const columns = Math.ceil(Math.sqrt(count));
  const row = Math.floor(index / columns);
  const col = index % columns;
  const x = side * (2.8 + 2.75 * col);
  const z = (row - (Math.ceil(count / columns) - 1) / 2) * 3.05 + (col % 2) * 0.35;
  return new THREE.Vector3(x, 0, z);
}

export function createMap(canvas, labels, onSelect) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false });
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 250);
  const controls = new OrbitControls(camera, canvas);
  controls.enablePan = false;
  controls.minPolarAngle = 0.12;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.minZoom = 0.65;
  controls.maxZoom = 4;
  scene.add(new THREE.HemisphereLight(hot, color("colors.surface"), 2.5));
  const light = new THREE.DirectionalLight(hot, 2);
  light.position.set(-4, 10, 6);
  scene.add(light);

  const graph = new THREE.Group();
  scene.add(graph);
  const tile = new THREE.GridHelper(80, 80, line, line);
  tile.position.y = -0.08;
  tile.material.transparent = true;
  tile.material.opacity = 0.21;
  scene.add(tile);

  const nodes = new Map();
  const project = new THREE.Vector3();
  const ray = new THREE.Raycaster();
  const bounds = new THREE.Box3();
  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  const viewOffset = new THREE.Vector3(0, 29, 26);
  let selected = "", frame = 0;
  function render() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const width = canvas.clientWidth, height = canvas.clientHeight;
      if (!width || !height || renderer.getContext().isContextLost()) return;
      renderer.render(scene, camera);
      const showNames = width >= 650 && nodes.size <= 12 && camera.zoom >= 0.95;
      for (const node of nodes.values()) {
        const { label } = node;
        if (!showNames && node.device.id !== selected) {
          label.hidden = true;
          continue;
        }
        project.copy(node.group.position);
        project.y += node.height;
        project.project(camera);
        label.hidden = Math.abs(project.x) > 0.88 || Math.abs(project.y) > 0.86;
        label.style.left = `${(project.x + 1) * 50}%`;
        label.style.top = `${(1 - project.y) * 50}%`;
      }
    });
  }

  function resize() {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    const aspect = width / height;
    const half = Math.max(2.5, size.x * 0.63 / aspect, size.z * 0.55 + 1);
    camera.left = -half * aspect;
    camera.right = half * aspect;
    camera.top = half;
    camera.bottom = -half;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(drawRes(), 1));
    renderer.setSize(width, height, false);
    render();
  }

  function reset() {
    controls.target.copy(center);
    camera.position.copy(center).add(viewOffset);
    camera.zoom = 1;
    controls.update();
    resize();
  }

  function add(device, position) {
    const group = new THREE.Group();
    group.position.copy(position);
    graph.add(group);
    const base = new THREE.Mesh(pad, dark);
    const wire = new THREE.LineSegments(outline, wires[device.connected ? "on" : "off"]);
    group.add(base, wire);
    const key = Object.hasOwn(shapes, device.kind) ? device.kind : "usb";
    const simple = new THREE.Mesh(shapes[key], dark);
    simple.add(new THREE.LineSegments(edges[key], wires[device.connected ? "on" : "off"]));
    simple.position.y = device.kind === "brain" ? 0.83 : 0.49;
    group.add(simple);
    const label = document.createElement("span");
    label.className = device.connected ? "map-label" : "map-label off";
    label.textContent = device.name;
    label.hidden = true;
    labels.append(label);
    const node = { group, wire, label, height: device.kind === "brain" ? 1.65 : 0.98, device };
    nodes.set(device.id, node);
    const type = Object.hasOwn(modelTypes, device.model) ? modelTypes[device.model] : null;
    if (type) modelFor(type).then((object) => {
      if (!object || nodes.get(device.id) !== node) return;
      group.remove(simple);
      group.add(object.clone(true));
      node.height = 1.62;
      render();
    });
  }

  function setDevices(devices) {
    for (const child of graph.children) if (child.isLine) child.geometry.dispose();
    graph.clear();
    nodes.clear();
    labels.replaceChildren();
    bounds.setFromPoints([new THREE.Vector3(-0.8, 0, -0.8), new THREE.Vector3(0.8, 0, 0.8)]);
    add(devices[0], new THREE.Vector3());
    const screens = devices.slice(1).filter((device) => device.kind === "screen");
    const hardware = devices.slice(1).filter((device) => device.kind !== "screen");
    for (const [entries, side] of [[screens, -1], [hardware, 1]]) {
      entries.forEach((device, index) => {
        const target = place(index, entries.length, side);
        bounds.expandByPoint(target);
        add(device, target);
        if (!device.connected) return;
        const direction = target.clone().normalize();
        const start = direction.clone().multiplyScalar(0.8);
        const end = target.clone().addScaledVector(direction, -0.8);
        start.y = end.y = 0.04;
        // Raise longer traces above the nearer pads so each connection reaches the brain.
        const arch = start.clone().lerp(end, 0.5);
        arch.y = 0.22 * target.length();
        const geometry = new THREE.BufferGeometry().setFromPoints([start, arch, end]);
        const trace = new THREE.Line(geometry, device.via?.includes("USB") ? links.usb : links.network);
        graph.add(trace);
        trace.computeLineDistances();
      });
    }
    const previousCenter = center.clone();
    bounds.getCenter(center);
    bounds.getSize(size);
    size.addScalar(1.5);
    camera.position.add(center.clone().sub(previousCenter));
    controls.target.copy(center);
    controls.update();
    resize();
  }

  function select(device) {
    const previous = nodes.get(selected);
    if (previous) {
      previous.wire.material = wires[previous.device.connected ? "on" : "off"];
      previous.label.classList.remove("selected");
    }
    selected = device.id;
    const node = nodes.get(selected);
    node.wire.material = wires.selected;
    node.label.classList.add("selected");
    render();
  }

  let down;
  canvas.addEventListener("pointerdown", (event) => { down = [event.clientX, event.clientY]; });
  canvas.addEventListener("click", (event) => {
    if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 5) return;
    const rect = canvas.getBoundingClientRect();
    ray.setFromCamera({
      x: 2 * (event.clientX - rect.left) / rect.width - 1,
      y: 1 - 2 * (event.clientY - rect.top) / rect.height,
    }, camera);
    // Select using a simple bounding sphere so clicks also work on detailed models.
    const sphere = new THREE.Sphere(new THREE.Vector3(), 0.8);
    let closest, distance = Infinity;
    for (const node of nodes.values()) {
      sphere.center.copy(node.group.position).y = 0.55;
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
  reset();
  return { setDevices, select, reset };
}
