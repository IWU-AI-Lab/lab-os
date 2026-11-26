// Read-only preview for the Raspbot pages. Its input is the existing WebSocket status.
import * as THREE from "three";
import { loadRaspbotModel } from "/web/raspbot-model.js";
import { drawRes } from "/web/screen.js";
import { color } from "/web/theme.js";

const WHEELS = ["l1_Joint", "l2_Joint", "r1_Joint", "r2_Joint"];
const SIGNS = [1, 1, -1, -1];  // the URDF uses opposite axes on the right side
const STOPPED = [0, 0, 0, 0];
const TURN = 2 * Math.PI;
const STATUS_TIMEOUT_MS = 600;  // status arrives every 200 ms

export async function createRaspbotView(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(drawRes(), 1.5));
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(color("arm3d.light_sky"), color("arm3d.light_ground"), 2.2));
  const sun = new THREE.DirectionalLight(color("arm3d.sun"), 1.6);
  sun.position.set(0.6, 1.2, 0.8);
  scene.add(sun);

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 5);
  camera.position.set(0.48, 0.32, 0.38);
  camera.lookAt(0, 0.05, 0);

  let model;
  try {
    model = await loadRaspbotModel();
  } catch (error) {
    renderer.dispose();
    throw error;
  }
  const { robot, object } = model;
  scene.add(object);

  let frame = 0, previous = 0, lastStatus = 0;
  let pan = 0, tilt = 0, speeds = STOPPED;
  const angles = [...STOPPED];

  function schedule() {
    if (!frame) frame = requestAnimationFrame(render);
  }

  function render(now) {
    frame = 0;
    const spinning = now - lastStatus < STATUS_TIMEOUT_MS && speeds.some(Boolean);
    if (spinning && previous) {
      const dt = Math.min(0.1, (now - previous) / 1000);
      WHEELS.forEach((joint, i) => {
        // Use one turn per second at the cap as a visual estimate of the commanded speed.
        angles[i] = (angles[i] + SIGNS[i] * speeds[i] * TURN * dt) % TURN;
        robot.setJointValue(joint, angles[i]);
      });
    }
    renderer.render(scene, camera);
    previous = spinning ? now : 0;
    if (spinning) schedule();
  }

  const size = new ResizeObserver(() => {
    const { clientWidth: width, clientHeight: height } = canvas;
    if (!width || !height) return;
    const aspect = width / height;
    const halfHeight = Math.max(0.10, 0.15 / aspect);
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.left = -halfHeight * aspect;
    camera.right = halfHeight * aspect;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    schedule();
  });
  size.observe(canvas);

  return {
    update(status) {
      const nextPan = status?.pan_deg ?? pan;
      const nextTilt = status?.tilt_deg ?? tilt;
      const changed = nextPan !== pan || nextTilt !== tilt;
      if (changed) {
        pan = nextPan;
        tilt = nextTilt;
        robot.setJointValue("arm1_Joint", THREE.MathUtils.degToRad(pan));
        robot.setJointValue("arm2_Joint", THREE.MathUtils.degToRad(tilt));
      }
      lastStatus = performance.now();
      speeds = status?.connected && status.wheel_speeds?.length === 4 ? status.wheel_speeds : STOPPED;
      if (changed || speeds.some(Boolean)) schedule();
    },
  };
}
