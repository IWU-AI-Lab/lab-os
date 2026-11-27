// The Command Center's start (quick jobs 160, 161): one radar sweep, 1 s, over the whole page. The sweep turns
// first; in its last 0.3 s the page fades in and the sweep fades out (before, each card showed as the sweep passed
// it, so the scan and the page came at the same time). The sweep does not block the page, so nothing ends it.
import { prefs } from "/web/device.js";

const MS = 1000;

function sweepSound() {
  if (prefs().sound === false) return;
  if (parent !== window) {
    parent.postMessage({ type: "lab-os-sfx", name: "sweep" }, location.origin);
    return;
  }
  if (!navigator.userActivation.hasBeenActive || !window.AudioContext) return;
  const ctx = new AudioContext();
  const tone = ctx.createOscillator(), gain = ctx.createGain();
  const now = ctx.currentTime;
  tone.type = "triangle";
  tone.frequency.setValueAtTime(160, now);
  tone.frequency.exponentialRampToValueAtTime(1300, now + .8);
  gain.gain.setValueAtTime(.01, now);
  gain.gain.exponentialRampToValueAtTime(.0001, now + .8);
  tone.connect(gain).connect(ctx.destination);
  tone.onended = () => ctx.close();
  tone.start(); tone.stop(now + .8);
}

const FADE = 300;  // the last part of the sweep: the page in, the sweep out
const START = -40;  // where the sweep's bright edge starts, in degrees clockwise from the top (the .beam's conic-gradient)

// the radar's circular grid (quick job 163): rings that open out, spokes, degree ticks with their numbers, a
// reticle in the middle and blips that light as the sweep passes them. It fades out with the sweep.
function grid() {
  const R = [90, 180, 270, 360, 450], out = [];
  R.forEach((r, i) => out.push(`<circle class="ring${i % 2 ? " dash" : ""}" r="${r}" style="animation-delay:${i * 60}ms"/>`));
  for (let a = 0; a < 360; a += 30) {
    const t = (a * Math.PI) / 180, x = Math.sin(t), y = -Math.cos(t);
    out.push(`<line class="spoke" x1="${x * 40}" y1="${y * 40}" x2="${x * 450}" y2="${y * 450}"/>`);
    out.push(`<text x="${x * 482}" y="${y * 482}">${String(a).padStart(3, "0")}</text>`);
  }
  for (let a = 0; a < 360; a += 5) {
    const t = (a * Math.PI) / 180, x = Math.sin(t), y = -Math.cos(t), l = a % 30 ? 8 : 16;
    out.push(`<line class="tick" x1="${x * 450}" y1="${y * 450}" x2="${x * (450 + l)}" y2="${y * (450 + l)}"/>`);
  }
  out.push('<circle class="ring spin" r="225"/><path class="reticle" d="M-26 0h18M8 0h18M0 -26v18M0 8v18"/><circle class="ring" r="6"/>');
  // blips: each lights when the sweep's edge reaches its angle
  for (const [a, r] of [[35, 140], [110, 310], [160, 220], [215, 390], [290, 120], [330, 260], [70, 420]]) {
    const t = (a * Math.PI) / 180, at = ((((a - START) % 360) + 360) % 360) / 360 * MS;
    out.push(`<circle class="blip" cx="${Math.sin(t) * r}" cy="${-Math.cos(t) * r}" r="5" style="animation-delay:${Math.round(at)}ms"/>`);
  }
  return `<svg class="grid" viewBox="-500 -500 1000 1000">${out.join("")}</svg>`;
}

export function playIntro() {
  const page = document.querySelector(".page");
  page.classList.remove("wait");
  if (document.documentElement.classList.contains("q-minimal") || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    page.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 160 });
    return;
  }
  sweepSound();
  const box = document.createElement("div");
  box.id = "intro";
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = `${grid()}<div class="beam"></div>`;
  document.body.append(box);
  const end = 1 - FADE / MS;
  page.animate([{ opacity: 0, scale: 0.985 }, { opacity: 0, scale: 0.985, offset: end }, { opacity: 1, scale: 1 }],
    { duration: MS, easing: "ease-out" });
  box.animate([{ opacity: 1 }, { opacity: 1, offset: end }, { opacity: 0 }], { duration: MS })
    .finished.then(() => box.remove());
}
