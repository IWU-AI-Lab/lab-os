// Desktop 3D view: scene, camera, orbit controls, lights, floor grid. Holds one ArmModel for each arm:
// the "right" one (the brain's first arm) where it always was, and with two arms at once the "left"
// one LEFT_OFFSET_M to its left (a fixed spot: the desktop doesn't know where the real arms stand),
// on a floor grid that is under both arms.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { drawRes } from "/web/screen.js";
import { color } from "/web/theme.js";

const DEG = Math.PI / 180;
export const LEFT_OFFSET_M = 0.4;

export function createArmView(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(drawRes()); // this screen's drawing resolution (Settings → This device, ?res=)
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a84, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(0.6, 1.2, 0.8);
  scene.add(sun);
  // the floor grid: 0.6 m under one arm; with two arms a wider one under both (quick job 119), 5 cm cells
  let grid = null;
  function setGrid(two) {
    if (grid && grid.userData.two === two) return;
    if (grid) scene.remove(grid);
    const size = two ? 1.2 : 0.6;
    grid = new THREE.GridHelper(size, size / 0.05, color("arm3d.grid_center"), color("arm3d.grid"));
    grid.material.transparent = true;
    grid.material.opacity = 0.6;
    grid.position.z = two ? -LEFT_OFFSET_M / 2 : 0; // the middle between the two arms
    grid.userData.two = two;
    scene.add(grid);
  }
  setGrid(false);

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

  const models = {}; // slot ("right" / "left") → ArmModel
  renderer.setAnimationLoop(() => {
    controls.update(); // fires "change" while damping settles
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, camera);
  });

  /** Keep the viewing direction, but frame the models' reach (a sphere around their bases). */
  function frame() {
    const box = new THREE.Box3();
    for (const m of Object.values(models)) box.expandByObject(m.object);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const reach = Math.max(size.x, size.y, size.z, 0.25);
    const middle = box.getCenter(new THREE.Vector3());
    const target = new THREE.Vector3(0.08, Math.min(size.y, reach) * 0.4, models.left ? middle.z : 0);
    const dir = camera.position.clone().sub(controls.target).normalize();
    const dist = (reach * 0.75) / Math.sin((camera.fov * DEG) / 2);
    controls.target.copy(target);
    camera.position.copy(target).addScaledVector(dir, dist);
    controls.update();
  }

  return {
    scene,
    /** Show `model` for the arm in `slot` ("right", or "left" with two arms); null removes it. */
    setModel(model, slot = "right") {
      const old = models[slot];
      // frame again only when an arm type changes or an arm comes or goes, so user orbiting is kept
      const reframe = !old !== !model || (old && model && old.kind !== model.kind);
      if (old) scene.remove(old.object);
      if (model) {
        models[slot] = model;
        model.object.position.z = slot === "left" ? -LEFT_OFFSET_M : 0; // the robot's left is −z here
        scene.add(model.object);
      } else delete models[slot];
      setGrid(!!models.left);
      if (reframe) frame();
      dirty = true;
    },
    /** Call after changing the model (joints, tint, opacity). */
    requestRender() {
      dirty = true;
    },
  };
}
