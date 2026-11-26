// The Command Center's opening (quick job 140), in the style of the start screen's startup
// (docs/design/DESIGN.md → "Startup" and "Motion"): about 3.5 s, and any press or key skips it.
//
//   0.0 s  a bright line opens the screen like an old TV
//   0.25   corner brackets close in on the middle; the tick ring sweeps around
//   0.6    two rings arrive from their own sides and lock, each with a flash and a thin ring of light
//   1.35   the core ignites (overshoot, a lens flare); a shockwave reveals the grid
//   1.5    the title decodes; the real counts type out under it (scan bar, dotted leader, value)
//   2.5    a radar sweep goes around once
//   2.9    the screen opens from the middle; the reticle flies to the title; the panels unfold outward,
//          one after another, and the workspace's cards arrive one by one
//
// The sounds are the hub's own (SFX in design.html). Inside the hub's module frame the hub plays them
// (it has the press that unlocks sound; the frame has none): the page sends {type: "lab-os-sfx", name,
// arg}. On its own screen the page plays the same recipes itself, when the browser lets it.

const T = { tv: 0, brackets: 250, ticks: 450, ring1: 600, ring2: 800, core: 1350, title: 1500, rows: 1950, sweep: 2500, reveal: 2900, done: 3700 };
const ARRIVE = "cubic-bezier(0.16, 1, 0.3, 1)";
const GLYPHS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789#%&*+<>/\\";

// ---------- sound ----------
let ac = null, master = null;
function audio() {
  if (ac) return ac.state === "running" ? ac : null;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  ac = new AC(); master = ac.createGain(); master.gain.value = 0.5; master.connect(ac.destination);
  ac.resume?.().catch(() => {});
  return ac.state === "running" ? ac : null;
}
function tone({ f = 440, f2 = 0, type = "sine", dur = 0.15, vol = 0.1, attack = 0.005, delay = 0, lp = 0 }) {
  if (!audio()) return;
  const t = ac.currentTime + delay, o = ac.createOscillator(), g = ac.createGain();
  o.type = type; o.frequency.setValueAtTime(f, t);
  if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + dur);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  let node = o;
  if (lp) { const fl = ac.createBiquadFilter(); fl.type = "lowpass"; fl.frequency.value = lp; o.connect(fl); node = fl; }
  node.connect(g); g.connect(master); o.start(t); o.stop(t + dur + 0.05);
}
// the same recipes as the hub's SFX (a whoosh is a filtered tone here: no noise buffer for one page)
const LOCAL = {
  tick: () => tone({ f: 2300, type: "triangle", dur: 0.025, vol: 0.018 }),
  sweep: () => tone({ f: 160, f2: 1300, type: "triangle", dur: 0.9, vol: 0.06, attack: 0.35, lp: 2600 }),
  lock: (i = 0) => { tone({ f: 520 * Math.pow(1.122, i), type: "triangle", dur: 0.09, vol: 0.05 }); tone({ f: 1800, type: "triangle", dur: 0.02, vol: 0.03 }); },
  shock: () => tone({ f: 90, f2: 40, dur: 1.1, vol: 0.3, attack: 0.01 }),
  decode: () => tone({ f: 1200 + Math.random() * 1200, type: "square", dur: 0.02, vol: 0.012, lp: 3000 }),
  title: () => { for (let i = 0; i < 3; i++) tone({ f: [523, 659, 784][i], dur: 1.4, vol: 0.035, attack: 0.08, delay: i * 0.05 }); },
  land: () => tone({ f: 300, f2: 120, type: "triangle", dur: 0.5, vol: 0.06, lp: 1200 }),
};
function cue(name, arg) {
  if (window.self !== window.top) {
    try { parent.postMessage({ type: "lab-os-sfx", name, arg }, location.origin); } catch { /* another origin: silent */ }
  } else LOCAL[name]?.(arg);
}

// ---------- the pieces ----------
function rigSVG() {
  const br = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([x, y]) => `<path class="br" d="M${x * 150} ${y * 112} L${x * 150} ${y * 150} L${x * 112} ${y * 150}"/>`).join("");
  let ticks = "";
  for (let i = 0; i < 72; i++) {
    const a = (i / 72) * Math.PI * 2, r0 = i % 6 ? 128 : 122, r1 = 134;
    ticks += `<line x1="${(Math.cos(a) * r0).toFixed(1)}" y1="${(Math.sin(a) * r0).toFixed(1)}" x2="${(Math.cos(a) * r1).toFixed(1)}" y2="${(Math.sin(a) * r1).toFixed(1)}"/>`;
  }
  return `<svg viewBox="-170 -170 340 340">
    <defs><radialGradient id="ci-core"><stop offset="0" stop-color="var(--hot)"/><stop offset="0.4" stop-color="var(--hot)" stop-opacity="0.9"/>
      <stop offset="0.7" stop-color="var(--c)" stop-opacity="0.5"/><stop offset="1" stop-color="var(--c)" stop-opacity="0"/></radialGradient></defs>
    <g class="brs">${br}</g>
    <g class="ticks">${ticks}</g>
    <circle class="r1" r="108" stroke-dasharray="46 10 6 10"/>
    <circle class="r2" r="84" stroke-dasharray="2 5"/>
    <g class="r3"><circle r="62" stroke-dasharray="120 18 30 18"/><path d="M0 -70 L5 -62 L-5 -62 Z"/></g>
    <circle class="core" r="38" fill="url(#ci-core)"/>
    <rect class="flare" x="-170" y="-1.2" width="340" height="2.4"/>
  </svg>`;
}
function decode(el, text, start, dur) {
  // each letter flickers through random glyphs and settles, left to right
  el.innerHTML = [...text].map((ch) => `<span>${ch === " " ? "&nbsp;" : ""}</span>`).join("");
  const spans = [...el.children];
  const t0 = performance.now() + start;
  let last = 0;
  return new Promise((done) => {
    (function step(now) {
      if (!el.isConnected) return done();
      let settled = 0;
      spans.forEach((s, i) => {
        if (text[i] === " ") { settled++; return; }
        const at = t0 + (i / text.length) * dur * 0.7, end = at + dur * 0.3;
        if (now < at) s.textContent = "";
        else if (now < end) s.textContent = GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        else { s.textContent = text[i]; settled++; }
      });
      if (now - last > 55 && now > t0) { cue("decode"); last = now; }
      if (settled < spans.length) requestAnimationFrame(step); else done();
    })(performance.now());
  });
}

// ---------- the opening ----------
let running = null;
/** Play the opening. `counts()` gives the real numbers when the rows type out ([[label, value], …]).
 *  `panels` unfold at the end, `items()` gives the cards and rows that arrive one by one. */
export function playIntro({ counts = () => [], panels = [], items = () => [], title = "Command Center", flyTo = null } = {}) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return Promise.resolve();
  const box = document.createElement("div");
  box.id = "intro";
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = `<div class="bg"></div><canvas></canvas><div class="tv"></div><div class="rig">${rigSVG()}</div><div class="ttl"></div><div class="rows"></div><p class="skip">Press any key to skip</p>`;
  document.body.append(box);
  document.body.classList.add("intro");
  const $ = (s) => box.querySelector(s);
  const anims = [], timers = [];
  const anim = (el, frames, opts) => { const a = el.animate(frames, { fill: "both", easing: ARRIVE, ...opts }); anims.push(a); return a; };
  const at = (ms, fn) => timers.push(setTimeout(fn, ms));

  // the canvas: the grid the shockwave reveals, the thin rings of light, the radar sweep
  const cv = $("canvas"), g = cv.getContext("2d"), dpr = Math.min(2, devicePixelRatio || 1);
  let W = 0, H = 0;
  const size = () => { W = innerWidth; H = innerHeight; cv.width = W * dpr; cv.height = H * dpr; g.setTransform(dpr, 0, 0, dpr, 0, 0); };
  size();
  const css = getComputedStyle(document.documentElement);
  const C = css.getPropertyValue("--c").trim() || "#29d4ff", HOT = css.getPropertyValue("--hot").trim() || "#eafcff";
  const rings = [];  // {t0, r}
  const t0 = performance.now();
  let raf = 0;
  function draw(now) {
    const t = now - t0, cx = W / 2, cy = H / 2, maxR = Math.hypot(W, H) / 2;
    g.clearRect(0, 0, W, H);
    // the grid, inside the shockwave's radius, brightest at its edge
    if (t > T.core) {
      const k = Math.min(1, (t - T.core) / 900), r = maxR * (1 - Math.pow(1 - k, 3));
      g.save();
      g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.clip();
      g.fillStyle = C;
      const step = 32;
      for (let x = cx % step; x < W; x += step) {
        for (let y = cy % step; y < H; y += step) {
          const d = Math.hypot(x - cx, y - cy), edge = Math.max(0, 1 - Math.abs(r - d) / 90);
          g.globalAlpha = 0.12 + edge * 0.7;
          g.fillRect(x - 0.75, y - 0.75, 1.5 + edge * 1.5, 1.5 + edge * 1.5);
        }
      }
      g.restore();
      // the shockwave's ring
      if (k < 1) { g.globalAlpha = 1 - k; g.strokeStyle = HOT; g.lineWidth = 2 + 8 * (1 - k); g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke(); }
    }
    // a thin ring of light from each ring as it locks
    for (const ring of rings) {
      const k = (now - ring.t0) / 650;
      if (k < 0 || k > 1) continue;
      g.globalAlpha = 0.8 * (1 - k); g.strokeStyle = C; g.lineWidth = 1.2;
      g.beginPath(); g.arc(cx, cy, ring.r + k * 160, 0, Math.PI * 2); g.stroke();
    }
    // the radar sweep: a bright arm with a fading wedge behind it
    if (t > T.sweep && t < T.sweep + 800) {
      const k = (t - T.sweep) / 800, a = -Math.PI / 2 + k * Math.PI * 2;
      for (let i = 0; i < 24; i++) {
        const b = a - i * 0.035;
        g.globalAlpha = 0.22 * (1 - i / 24) * (1 - k * 0.5);
        g.fillStyle = C;
        g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, maxR, b - 0.035, b); g.closePath(); g.fill();
      }
      g.globalAlpha = 0.9; g.strokeStyle = HOT; g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a) * maxR, cy + Math.sin(a) * maxR); g.stroke();
    }
    g.globalAlpha = 1;
    raf = requestAnimationFrame(draw);
  }
  raf = requestAnimationFrame(draw);

  // 1. the TV line
  anim($(".tv"), [{ transform: "scaleX(0)", opacity: 1 }, { transform: "scaleX(1)", opacity: 1, offset: 0.4 }, { transform: "scaleX(1) scaleY(60)", opacity: 0 }], { duration: 560, easing: "ease-out" });
  cue("tick");
  // 2. the brackets close in; the tick ring sweeps around
  const rig = $(".rig");
  anim(rig.querySelector(".brs"), [{ transform: "scale(2.6)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], { duration: 520, delay: T.brackets });
  anim(rig.querySelector(".ticks"), [{ transform: "rotate(-200deg)", opacity: 0 }, { transform: "rotate(0)", opacity: 0.8 }], { duration: 800, delay: T.ticks });
  at(T.ticks, () => cue("sweep"));
  // 3. two rings arrive from their own sides and lock with a flash
  const lock = (el, i, r, delay) => {
    at(delay, () => { cue("lock", i); rings.push({ t0: performance.now(), r }); });
    anim(el, [{ filter: "brightness(1)" }, { filter: "brightness(3) drop-shadow(0 0 8px var(--c))" }, { filter: "brightness(1)" }], { duration: 420, delay, easing: "ease-out", fill: "none" });
  };
  anim(rig.querySelector(".r1"), [{ transform: "scale(0.1) rotate(120deg)", opacity: 0 }, { transform: "scale(1) rotate(0)", opacity: 1 }], { duration: 480, delay: T.ring1 });
  lock(rig.querySelector(".r1"), 0, 108, T.ring1 + 450);
  anim(rig.querySelector(".r2"), [{ transform: "scale(2.4) rotate(-90deg)", opacity: 0 }, { transform: "scale(1) rotate(0)", opacity: 1 }], { duration: 480, delay: T.ring2 });
  lock(rig.querySelector(".r2"), 1, 84, T.ring2 + 450);
  anim(rig.querySelector(".r3"), [{ transform: "rotate(-300deg) scale(0.6)", opacity: 0 }, { transform: "rotate(0) scale(1)", opacity: 1 }], { duration: 700, delay: T.ring2 + 100 });
  lock(rig.querySelector(".r3"), 2, 62, T.ring2 + 760);
  // 4. the core ignites (overshoot), a lens flare across it, the shockwave
  anim(rig.querySelector(".core"), [{ transform: "scale(0)", opacity: 0 }, { transform: "scale(1.5)", opacity: 1, offset: 0.45 }, { transform: "scale(1)", opacity: 1 }], { duration: 650, delay: T.core });
  anim(rig.querySelector(".flare"), [{ transform: "scaleX(0)", opacity: 0 }, { transform: "scaleX(1.3)", opacity: 1, offset: 0.3 }, { transform: "scaleX(0.5)", opacity: 0 }], { duration: 900, delay: T.core + 60, fill: "none" });
  at(T.core, () => cue("shock"));
  // 5. the title decodes; the real counts type out
  const ttl = $(".ttl");
  anim(ttl, [{ opacity: 0 }, { opacity: 1 }], { duration: 200, delay: T.title });
  at(T.title, () => decode(ttl, title.toUpperCase(), 0, 600).then(() => ttl.isConnected && cue("title")));
  at(T.rows, () => {
    const rows = $(".rows");
    counts().forEach(([label, value], i) => {
      const r = document.createElement("div");
      r.className = "ln";  // not "row": the page's list rows have that class
      r.innerHTML = `<span>${label}</span><i></i><b>${value}</b>`;
      rows.append(r);
      anim(r, [{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }], { duration: 260, delay: i * 140 });
      anim(r.querySelector("i"), [{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 260, delay: i * 140 + 180 });
      anim(r.querySelector("b"), [{ opacity: 0, filter: "brightness(3)" }, { opacity: 1, filter: "brightness(1)" }], { duration: 300, delay: i * 140 + 380 });
      at(i * 140 + 380, () => cue("tick"));
    });
  });
  // 6. the reveal: the screen opens from the middle, the reticle and title fly to the page's title
  at(T.reveal, () => {
    cue("land");
    anim($(".bg"), [{ "--hole": "0px" }, { "--hole": `${Math.hypot(W, H)}px` }], { duration: 800, easing: "cubic-bezier(0.7, 0, 0.3, 1)" });
    const to = flyTo?.getBoundingClientRect?.();
    const r = rig.getBoundingClientRect();
    const move = to && to.width
      ? `translate(${to.left + to.width / 2 - (r.left + r.width / 2)}px, ${to.top + to.height / 2 - (r.top + r.height / 2)}px) scale(${Math.max(0.05, to.width / r.width)})`
      : "scale(0.2)";
    anim(rig, [{ transform: "none", opacity: 1 }, { transform: move, opacity: 0.0 }], { duration: 700 });
    anim(ttl, [{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(-1rem) scale(0.9)" }], { duration: 400 });
    anim($(".rows"), [{ opacity: 1 }, { opacity: 0 }], { duration: 300 });
    anim($(".skip"), [{ opacity: 1 }, { opacity: 0 }], { duration: 200 });
    document.body.classList.remove("intro");
    unfold(panels, items());
  });
  const finish = () => {
    if (!box.isConnected) return;
    cancelAnimationFrame(raf);
    timers.forEach(clearTimeout);
    anims.forEach((a) => a.cancel());
    box.remove();
    document.body.classList.remove("intro");
    removeEventListener("pointerdown", skip, true); removeEventListener("keydown", skip, true);
    running?.done();
    running = null;
  };
  const skip = () => finish();
  addEventListener("pointerdown", skip, true);
  addEventListener("keydown", skip, true);
  addEventListener("resize", size);
  return new Promise((done) => {
    running = { done };
    at(T.done, finish);
  });
}

// the panels unfold outward from the middle, one after another; then the cards and rows arrive one by one
function unfold(panels, items) {
  const cx = innerWidth / 2;
  for (const p of panels) {
    const r = p.getBoundingClientRect(), mid = r.left + r.width / 2;
    const from = Math.abs(mid - cx) < 40 ? "inset(50% 50% 50% 50%)" : mid < cx ? "inset(0 0 0 100%)" : "inset(0 100% 0 0)";
    p.animate([{ clipPath: from, opacity: 0 }, { clipPath: "inset(0 0 0 0)", opacity: 1 }],
      { duration: 700, delay: Math.round(Math.abs(mid - cx) / 3), easing: ARRIVE, fill: "backwards" });
  }
  items.forEach((el, i) => {
    el.animate([{ opacity: 0, transform: "translateY(10px)", filter: "brightness(2.2)" }, { opacity: 1, transform: "none", filter: "none" }],
      { duration: 500, delay: 350 + i * 70, easing: ARRIVE, fill: "backwards" });
  });
}
