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
  box.innerHTML = '<div class="beam"></div>';
  document.body.append(box);
  const end = 1 - FADE / MS;
  page.animate([{ opacity: 0, scale: 0.985 }, { opacity: 0, scale: 0.985, offset: end }, { opacity: 1, scale: 1 }],
    { duration: MS, easing: "ease-out" });
  box.animate([{ opacity: 1 }, { opacity: 1, offset: end }, { opacity: 0 }], { duration: MS })
    .finished.then(() => box.remove());
}
