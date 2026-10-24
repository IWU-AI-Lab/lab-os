// Desktop 3D view: scene, camera, orbit controls, lights, floor grid. Holds one ArmModel at a time.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export function createArmView(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a84, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(0.6, 1.2, 0.8);
  scene.add(sun);
  const grid = new THREE.GridHelper(0.6, 12, 0x8a8a84, 0xb8b8b2);
  grid.material.transparent = true;
  grid.material.opacity = 0.6;
  scene.add(grid);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 10);
  camera.position.set(0.5, 0.36, 0.5);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.1, 0);
  controls.enableDamping = true;
  controls.update();

  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  let current = null;
  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  return {
    scene,
    setModel(model) {
      if (current) scene.remove(current.object);
      current = model;
      if (model) scene.add(model.object);
    },
  };
}
