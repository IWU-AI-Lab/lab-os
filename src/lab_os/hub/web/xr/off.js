// "lab-os is off" in the headset (quick job 44). The page's own cover (/web/off.js) is HTML, and a VR or AR
// session doesn't show the page, so the hub in VR draws the same words on a card in front of you, in the
// offline look (DESIGN.md: gray, dim, no glow). The hub around you goes away; the card follows your head.
// Under the card, Exit leaves VR or AR (quick job 78): card.exit.mesh is what the pointer can press.
//   const card = new OffCard(msg);  scene.add(card.mesh);  card.follow(camera, dt) every frame
// msg: the brain_off message ({from, time_ms, restart}), or {lost: true}: the brain stopped answering and
// this page wasn't told why (quick job 78).
import * as THREE from "three";
import { C, CanvasPlane, FONT, cutPath, icon, rgba, spaced } from "./draw.js";
import { ExitButton } from "./modules.js";
import { wrap } from "./panels.js";

const W = 0.9, H = 0.42, DIST = 1.4; // metres
const hhmm = (ms) => new Date(ms || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

/** The words, as on the page's cover (/web/off.js). */
export function offWords(msg = {}) {
  if (msg.lost) {
    return {
      title: "lab-os is not reachable",
      lines: [
        "The brain does not answer. It was shut down, or the network is down.",
        'Start it with the "Start lab-os" icon on the brain\'s computer. This view comes back by itself when it answers.',
      ],
    };
  }
  const restart = !!msg.restart, who = msg.from ? ` from ${msg.from}` : "";
  return {
    title: restart ? "lab-os is restarting" : "lab-os is off",
    lines: [
      `It was ${restart ? "restarted" : "shut down"}${who} at ${hhmm(msg.time_ms)}. The arm was let go, and the cameras and microphones are closed.`,
      restart ? "It starts again by itself in a few seconds." : 'To start it again, use the "Start lab-os" icon on the brain\'s computer.',
    ],
  };
}

export class OffCard {
  constructor(msg) {
    this.p = new CanvasPlane(W, H, 1400);
    this.mesh = this.p.mesh;
    this.mesh.renderOrder = 10;
    this.p.mat.depthTest = false; // nothing of the hub may cover it
    this.placed = false;
    this.exit = new ExitButton();
    this.exit.mesh.position.set(0, -H / 2 - 0.1, 0.001);
    this.mesh.add(this.exit.mesh);
    const words = offWords(msg);
    this.p.paint((g, w, h) => {
      const pad = w * 0.06, c = h * 0.08;
      cutPath(g, 2, 2, w - 4, h - 4, c);
      g.fillStyle = rgba(C.bg, 0.94); g.fill();
      g.strokeStyle = C.offline; g.lineWidth = 3; g.stroke();
      icon(g, "i-power", w / 2, h * 0.19, h * 0.17, C.offline, 1.5);
      g.textAlign = "center"; g.textBaseline = "middle";
      g.fillStyle = C.offline;
      g.font = `700 ${Math.round(h * 0.09)}px ${FONT.title}`;
      spaced(g, 0.18);
      g.fillText(words.title.toUpperCase(), w / 2, h * 0.39);
      spaced(g, 0);
      g.fillStyle = C.dim;
      g.font = `${FONT.linesW} ${Math.round(h * 0.06)}px ${FONT.lines}`;
      let y = h * 0.55;
      for (const para of words.lines) {
        for (const line of wrap(g, para, w - 2 * pad, 3)) { g.fillText(line, w / 2, y); y += h * 0.085; }
        y += h * 0.03;
      }
    });
  }

  /** Keep the card in front of the head, level, at reading distance; it catches up gently. */
  follow(camera, dt, exitHover = false) {
    this.exit.hover = exitHover;
    this.exit.paint();
    const p = new THREE.Vector3(), q = new THREE.Quaternion();
    camera.getWorldPosition(p); camera.getWorldQuaternion(q);
    const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    fwd.y = 0;
    if (fwd.lengthSq() < 1e-6) fwd.set(0, 0, -1);
    fwd.normalize();
    const want = p.clone().addScaledVector(fwd, DIST);
    const k = this.placed ? Math.min(1, dt * 3) : 1;
    this.placed = true;
    this.mesh.position.lerp(want, k);
    this.mesh.lookAt(p.x, this.mesh.position.y, p.z);
  }
}
