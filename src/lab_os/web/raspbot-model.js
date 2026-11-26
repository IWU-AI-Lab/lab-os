// Add model.object to a Three.js scene. Set angles in radians on model.robot.
import * as THREE from "three";
import { loadRobotUrdf, queueModelLoad, zUp } from "/web/robot-urdf.js";
import { color } from "/web/theme.js";

const RASPBOT_URDF = "/models/raspbot/Raspbot-V2.urdf";
const WHEEL_LINKS = new Set(["l1_Link", "l2__Link", "r1_Link", "r2_Link"]);

export function loadRaspbotModel() {
  return queueModelLoad(async () => {
    const robot = await loadRobotUrdf(RASPBOT_URDF);
    const body = new THREE.MeshStandardMaterial({ color: color("raspbot3d.body"), roughness: 0.7 });
    const wheel = new THREE.MeshStandardMaterial({ color: color("raspbot3d.wheel"), roughness: 0.7 });
    for (const [name, link] of Object.entries(robot.links)) {
      const material = WHEEL_LINKS.has(name) ? wheel : body;
      for (const visual of link.children.filter((child) => child.isURDFVisual)) {
        visual.traverse((object) => {
          if (object.isMesh) object.material = material;
        });
      }
    }
    return { object: zUp(robot), robot };
  });
}
