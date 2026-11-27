// The Command Center's start (quick job 160): one radar sweep, 1 s, over the whole page. Each card shows
// when the sweep passes it. The sweep does not block the page, so nothing needs to end it.
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

export function playIntro(cards) {
  const page = document.querySelector(".page");
  if (document.documentElement.classList.contains("q-minimal") || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    page.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 160 });
    return;
  }
  sweepSound();
  const box = document.createElement("div");
  box.id = "intro";
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = '<div class="beam"></div>';
  document.body.append(box);
  const cx = innerWidth / 2, cy = innerHeight / 2;
  for (const card of cards) {
    const r = card.getBoundingClientRect();
    // the sweep starts at the top (12 o'clock) and turns clockwise
    const a = Math.atan2(r.left + r.width / 2 - cx, cy - r.top - r.height / 2);
    const at = (((a / (2 * Math.PI)) + 1) % 1) * MS;
    card.animate([{ opacity: 0 }, { opacity: 0, offset: Math.max(0.001, at / (at + 250)) }, { opacity: 1 }],
      { duration: at + 250, easing: "ease-out" });
  }
  box.animate([{ opacity: 1 }, { opacity: 1, offset: 0.8 }, { opacity: 0 }], { duration: MS + 150 })
    .finished.then(() => box.remove());
}
