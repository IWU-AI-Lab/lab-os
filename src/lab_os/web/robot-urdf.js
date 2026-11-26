import * as THREE from "three";
import URDFLoader from "/web/vendor/urdf-loader/URDFLoader.js";

// Concurrent loads can share a Three.js request and leave one loading manager unaware of it.
let queue = Promise.resolve();

export function queueModelLoad(load) {
  const next = queue.then(load);
  queue = next.catch(() => {});
  return next;
}

export function loadRobotUrdf(url, { parseVisual = true } = {}) {
  return new Promise((resolve, reject) => {
    const manager = new THREE.LoadingManager();
    const loader = new URDFLoader(manager);
    loader.parseVisual = parseVisual;
    let robot;
    manager.onLoad = () => (robot ? resolve(robot) : reject(new Error(`could not load ${url}`)));
    manager.onError = (failedUrl) => reject(new Error(`could not load ${failedUrl}`));
    loader.load(url, (result) => (robot = result));
  });
}

// URDF is Z-up. The wrapper keeps the robot's joints in their original frames.
export function zUp(object) {
  const group = new THREE.Group();
  object.rotation.x = -Math.PI / 2;
  group.add(object);
  return group;
}
