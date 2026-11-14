// Desktop 3D view: scene, camera, orbit controls, lights, floor grid. Holds one ArmModel at a time.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { drawRes } from "/web/screen.js";
import { color } from "/web/theme.js";

const DEG = Math.PI / 180;

export function createArmView(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(drawRes()); // this screen's drawing resolution (Settings → This device, ?res=)
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a84, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(0.6, 1.2, 0.8);
  scene.add(sun);
  const grid = new THREE.GridHelper(0.6, 12, color("arm3d.grid_center"), color("arm3d.grid"));
  grid.material.transparent = true;
  grid.material.opacity = 0.6;
  scene.add(grid);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 10);
  // Operator view: behind and above the arm (robots face +x), so screen left/right = hand left/right.
  camera.position.set(-0.46, 0.44, 0.32);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0.1, 0.13, 0);
  controls.enableDamping = true;
  controls.update();
  let dirty = true; // render only when something changed (saves CPU/GPU, keeps the page responsive)
  controls.addEventListener("change", () => (dirty = true));

  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    dirty = true;
  }
  new ResizeObserver(resize).observe(container);
  resize();

  let current = null;
  renderer.setAnimationLoop(() => {
    controls.update(); // fires "change" while damping settles
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, camera);
  });

  /** Keep the viewing direction, but frame the model's reach (a sphere around its base). */
  function frame(model) {
    const box = new THREE.Box3().setFromObject(model.object);
    const size = box.getSize(new THREE.Vector3());
    const reach = Math.max(size.x, size.y, size.z, 0.25);
    const target = new THREE.Vector3(0.08, Math.min(size.y, reach) * 0.4, 0);
    const dir = camera.position.clone().sub(controls.target).normalize();
    const dist = (reach * 0.75) / Math.sin((camera.fov * DEG) / 2);
    controls.target.copy(target);
    camera.position.copy(target).addScaledVector(dir, dist);
    controls.update();
  }

  return {
    scene,
    setModel(model) {
      const first = !current || current.kind !== model?.kind;
      if (current) scene.remove(current.object);
      current = model;
      if (model) {
        scene.add(model.object);
        if (first) frame(model); // only when the arm type changes, so user orbiting is kept
      }
      dirty = true;
    },
    /** Call after changing the model (joints, tint, opacity). */
    requestRender() {
      dirty = true;
    },
  };
}
