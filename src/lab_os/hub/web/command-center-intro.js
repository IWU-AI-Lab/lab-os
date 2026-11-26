// One radar return for each card. Each return travels to the card it represents.
import { prefs } from "/web/device.js";

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
  box.innerHTML = '<h2>Command Center</h2><div class="radar"></div><button class="btn" type="button">Skip</button>';
  document.body.append(box);
  const radar = box.querySelector(".radar");
  const timers = [];
  function finish() {
    timers.forEach(clearTimeout);
    box.remove();
    removeEventListener("pointerdown", skip, true);
    removeEventListener("keydown", skip, true);
  }
  function skip(event) {
    event.preventDefault();
    finish();
  }
  addEventListener("pointerdown", skip, true);
  addEventListener("keydown", skip, true);
  box.querySelector("button").onclick = finish;
  const rect = radar.getBoundingClientRect();
  cards.forEach((card, index) => {
    const fraction = (index + 0.5) / cards.length;
    const angle = 2 * Math.PI * fraction;
    const radius = rect.width * (0.25 + (index % 3) * 0.08);
    const x = rect.width / 2 + radius * Math.sin(angle);
    const y = rect.height / 2 - radius * Math.cos(angle);
    const dot = document.createElement("i");
    dot.className = "blip";
    dot.style.left = x + "px";
    dot.style.top = y + "px";
    dot.hidden = true;
    radar.append(dot);
    timers.push(setTimeout(() => { dot.hidden = false; }, fraction * 2000));
    timers.push(setTimeout(() => {
      const target = card.getBoundingClientRect();
      const dx = target.left + target.width / 2 - rect.left - x;
      const dy = target.top + target.height / 2 - rect.top - y;
      dot.animate([{ translate: "0 0" }, { translate: `${dx}px ${dy}px` }], { duration: 400, fill: "forwards" });
      card.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500 });
    }, 2000));
  });
  timers.push(setTimeout(() => {
    box.animate([{ backgroundColor: "var(--bg)" }, { backgroundColor: "transparent" }], { duration: 450, fill: "forwards" });
  }, 2000));
  timers.push(setTimeout(finish, 2500));
}
