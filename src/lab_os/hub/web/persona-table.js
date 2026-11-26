// The persona chooser as a 3D round table (quick job 151; a first version). The personas sit around a
// virtual table; select one (its name, or its orb) and the table turns it to the front, types its
// greeting and plays it in its own voice (GET /api/personas/{id}/preview, kept by the brain once
// spoken). "Choose" saves it like the Persona row (the row's own control, so one way to save).
// Only on the full and maximal looks (settings.js); reduced and minimal keep the plain row.
// Light on slow screens: it draws only while something moves (a turn, a voice), never off screen or
// in a hidden tab, at most 1.5 pixels per CSS pixel (or This Device → Drawing Resolution), with few
// segments and no glow passes.
import * as THREE from "three";
import { prefs } from "/web/device.js";
import { theme } from "/web/theme.js";

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const TURN_MS = 900;
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);  // slow in, slow out
const col = (name, fallback) => new THREE.Color(theme.colors?.[name] || fallback);

/** The look the hub uses on this screen: the hub around this page, else ?quality=, else this
 * device's own, else the computer's reduced motion, else the theme's default. */
export function currentLook() {
  try {
    if (window.parent !== window) {
      const q = [...window.parent.document.body.classList].find((c) => /^q-(maximal|full|reduced|minimal)$/.test(c));
      if (q) return q.slice(2);
    }
  } catch { /* another origin: the rule below */ }
  const asked = new URLSearchParams(location.search).get("quality");
  if (asked) return asked;
  if (prefs().quality) return prefs().quality;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return "minimal";
  return theme.quality?.default || "full";
}

/**
 * The table, or null when this screen can't draw 3D (the plain row stays).
 * @param {{personas: object[], active: string, look: string, choose: (id: string) => Promise<boolean>, readOnly: boolean}} o
 */
export function personaTable({ personas, active, look, choose, readOnly }) {
  if (!personas.length) return null;
  const canvas = document.createElement("canvas");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: devicePixelRatio <= 1, alpha: true, powerPreference: "low-power" });
  } catch (e) {
    console.warn(`persona table: no 3D on this screen (${e.message}); the plain chooser stays`);
    return null;
  }
  const maximal = look === "maximal";
  const res = Number(prefs().res) || 0;
  renderer.setPixelRatio(Math.min(devicePixelRatio, res || 1.5));

  const box = document.createElement("div");
  box.className = "ptable";
  box.innerHTML = `<div class="stage"><div class="names"></div></div>
    <div class="pside" aria-live="polite">
      <div class="who"></div>
      <p class="greet"></p>
      <div class="acts"><button type="button" class="btn hear">Hear It Again</button><button type="button" class="btn primary pick"></button></div>
      <p class="why"></p>
    </div>`;
  box.querySelector(".stage").prepend(canvas);
  const names = box.querySelector(".names"), who = box.querySelector(".who"), greet = box.querySelector(".greet");
  const hear = box.querySelector(".hear"), pick = box.querySelector(".pick"), why = box.querySelector(".why");

  /* ---------- the scene ---------- */
  const primary = col("primary", "#29d4ff"), hot = col("hot", "#e8fbff"), lineC = col("line", "#1d3a4a"), surface = col("surface", "#0b1620");
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 2, 0.1, 50);
  camera.position.set(0, 3.2, 6.9);
  camera.lookAt(0, -0.05, 0.2);
  const lines = (geo, color, opacity = 1) => new THREE.LineSegments(new THREE.EdgesGeometry(geo, 20), new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity }));
  const table = new THREE.Group();
  scene.add(table);
  const R = 1.55;  // the table's radius
  // the top: a dark disc with a bright rim and a faint inner ring (the design: lines, not shading)
  const top = new THREE.Mesh(new THREE.CylinderGeometry(R, R, 0.08, 48, 1), new THREE.MeshBasicMaterial({ color: surface, transparent: true, opacity: 0.85 }));
  table.add(top, lines(new THREE.CylinderGeometry(R, R, 0.08, 48, 1), primary, 0.9));
  const ring = (r, color, opacity, y = 0.045) => {
    const pts = [];
    for (let i = 0; i <= 96; i++) pts.push(new THREE.Vector3(Math.cos((i / 96) * Math.PI * 2) * r, y, Math.sin((i / 96) * Math.PI * 2) * r));
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  };
  table.add(ring(R * 0.62, primary, 0.35), ring(R * 0.3, primary, 0.5));
  // ticks on the rim: the full and maximal looks decorate the line (DESIGN.md); maximal has more
  const tickN = maximal ? 72 : 36, ticks = [];
  for (let i = 0; i < tickN; i++) {
    const a = (i / tickN) * Math.PI * 2, r0 = R * (i % 6 === 0 ? 0.86 : 0.92);
    ticks.push(new THREE.Vector3(Math.cos(a) * r0, 0.046, Math.sin(a) * r0), new THREE.Vector3(Math.cos(a) * R * 0.97, 0.046, Math.sin(a) * R * 0.97));
  }
  table.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(ticks), new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.45 })));
  // the leg and its foot
  const leg = lines(new THREE.CylinderGeometry(0.12, 0.12, 0.9, 8, 1), lineC);
  leg.position.y = -0.45;
  table.add(leg);
  table.add(ring(0.7, lineC, 0.8, -0.9));
  // the core in the middle: the brain they all share (rings, as on the hub)
  const core = new THREE.Group();
  core.position.y = 0.32;
  const coreRing = (r, tilt) => {
    const c = ring(r, primary, 0.7, 0);
    c.rotation.x = tilt;
    return c;
  };
  core.add(coreRing(0.16, 0), coreRing(0.22, Math.PI / 2.4), new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), new THREE.MeshBasicMaterial({ color: hot })));
  table.add(core);

  // a seat for each persona: a chair in lines, the persona's orb above it
  const seats = personas.map((p, i) => {
    const a = (i / personas.length) * Math.PI * 2;  // seat 0 at the back (-z), across from the viewer
    const g = new THREE.Group();
    g.position.set(-Math.sin(a) * (R + 0.42), 0, -Math.cos(a) * (R + 0.42));
    g.rotation.y = a + Math.PI;
    const chair = new THREE.Group();
    const seat = lines(new THREE.BoxGeometry(0.46, 0.06, 0.42), lineC);
    seat.position.y = -0.28;
    const back = lines(new THREE.BoxGeometry(0.46, 0.62, 0.05), lineC);
    back.position.set(0, 0.03, 0.22);
    chair.add(seat, back);
    const c = col(p.picture?.color || "primary", "#29d4ff");
    const orb = new THREE.Mesh(new THREE.SphereGeometry(0.19, 20, 14), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.55 }));
    orb.position.y = 0.42;
    orb.userData.id = p.id;
    const halo = ring(0.27, c, 0.5, 0);
    halo.rotation.x = Math.PI / 2;
    halo.position.y = 0.42;
    const extra = new THREE.Group();  // the persona's picture style: "calm-ring" adds a tilted ring
    if (p.picture?.style && p.picture.style !== "plain") {
      const r2 = ring(0.34, c, 0.6, 0);
      r2.rotation.set(Math.PI / 2.6, 0, Math.PI / 7);
      extra.add(r2);
      extra.position.y = 0.42;
    }
    g.add(chair, orb, halo, extra);
    table.add(g);
    return { p, angle: a, group: g, orb, halo, extra, chairLines: [seat, back] };
  });

  /* ---------- the names: buttons over the canvas (crisp words, and keys and screen readers) ---------- */
  const tags = seats.map((s) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "pname";
    b.innerHTML = `<span>${esc(s.p.display_name)}</span>`;
    b.addEventListener("click", () => select(s.p.id, true));
    names.append(b);
    return b;
  });

  /* ---------- drawing on demand ---------- */
  let spin = 0, from = 0, to = 0, turnStart = 0, frame = 0, visible = true, speaking = 0, analyser = null, level = new Uint8Array(32);
  let chosen = null, activeId = active, typing = 0, ctx = null, source = null;
  const tmp = new THREE.Vector3();
  function size() {
    const w = canvas.clientWidth || 600, h = canvas.clientHeight || 300;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    wake();
  }
  function draw(now) {
    frame = 0;
    let moving = false;
    if (turnStart) {
      const t = Math.min(1, (now - turnStart) / TURN_MS);
      spin = from + (to - from) * ease(t);
      if (t >= 1) turnStart = 0; else moving = true;
    }
    table.rotation.y = spin;
    core.rotation.y = spin * -2;
    let loud = 0;
    if (analyser) {
      analyser.getByteTimeDomainData(level);
      loud = Math.min(1, Math.sqrt(level.reduce((a, v) => a + ((v - 128) / 128) ** 2, 0) / level.length) * 5);
      moving = true;
    }
    speaking += (loud - speaking) * 0.35;
    for (const s of seats) {
      const on = s.p.id === chosen;
      const k = on ? 1 + speaking * 0.35 : 1;
      s.orb.scale.setScalar(k);
      s.orb.material.opacity = on ? 0.85 : 0.4;
      s.orb.material.color.copy(on && speaking > 0.05 ? hot : col(s.p.picture?.color || "primary", "#29d4ff"));
      s.halo.material.opacity = on ? 0.9 : 0.3;
      s.halo.scale.setScalar(on ? 1 + speaking * 0.5 : 1);
      if (on && maximal) s.extra.rotation.y = now / 1400;  // maximal: the selected one's ring turns
      for (const l of s.chairLines) l.material.color.copy(on ? primary : lineC);
    }
    if (maximal && chosen) moving = true;
    renderer.render(scene, camera);
    // the names follow their orbs; the one at the back is dimmed
    const w = canvas.clientWidth, h = canvas.clientHeight;
    seats.forEach((s, i) => {
      s.orb.getWorldPosition(tmp);
      const near = tmp.z > 0.3;  // a seat on the viewer's side: its name under the chair, off the table
      tmp.y += near ? -0.85 : 0.38;
      tmp.project(camera);
      const tag = tags[i];
      // kept inside the stage, so a name is never cut off
      const th = tag.offsetHeight, y = ((1 - tmp.y) / 2) * h;
      const top = Math.max(4, Math.min(h - th - 4, near ? y : y - th));
      tag.style.transform = `translate(-50%, 0) translate(${((tmp.x + 1) / 2) * w}px, ${top}px)`;
      tag.style.opacity = String(s.p.id === chosen ? 1 : 0.7);
      tag.setAttribute("aria-pressed", String(s.p.id === chosen));
      tag.classList.toggle("active", s.p.id === activeId);
    });
    if (moving && visible) wake();
  }
  function wake() {
    if (!frame && visible) frame = requestAnimationFrame(draw);
  }
  new ResizeObserver(size).observe(canvas);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting && !document.hidden; wake(); }).observe(box);
  document.addEventListener("visibilitychange", () => { visible = !document.hidden; wake(); });

  // a tap on an orb selects it too
  const ray = new THREE.Raycaster(), pt = new THREE.Vector2();
  canvas.addEventListener("click", (e) => {
    const r = canvas.getBoundingClientRect();
    pt.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(pt, camera);
    const hit = ray.intersectObjects(seats.map((s) => s.orb))[0];
    if (hit) select(hit.object.userData.id, true);
  });

  /* ---------- select, hear, choose ---------- */
  const shown = (id) => personas.find((p) => p.id === id);
  function typeOut(text) {
    clearInterval(typing);
    let n = 0;
    greet.textContent = "";
    typing = setInterval(() => {
      n += 2;
      greet.textContent = text.slice(0, n);
      if (n >= text.length) clearInterval(typing);
    }, 28);
  }
  function stopVoice() {
    try { source?.stop(); } catch { /* already ended */ }
    source = null;
    analyser = null;
  }
  async function play(id) {
    stopVoice();
    why.textContent = "";
    if (prefs().sound === false) {
      why.textContent = "Sound is off on this device (This Device → Sound).";
      return;
    }
    hear.disabled = true;
    try {
      const res = await fetch(`/api/personas/${encodeURIComponent(id)}/preview`, { cache: "no-store" });
      if (!res.ok) {
        const out = res.headers.get("Content-Type")?.includes("json") ? await res.json() : null;
        why.textContent = out?.message || "No voice preview now. The brain's log has the details.";
        return;
      }
      const data = await res.arrayBuffer();
      if (id !== chosen) return;  // another one was selected meanwhile
      ctx ||= new AudioContext();
      if (ctx.state === "suspended") await ctx.resume();
      const buf = await ctx.decodeAudioData(data);
      source = ctx.createBufferSource();
      source.buffer = buf;
      analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      level = new Uint8Array(analyser.fftSize);
      source.connect(analyser).connect(ctx.destination);
      const mine = source;
      source.onended = () => { if (source === mine) { analyser = null; source = null; wake(); } };
      source.start();
      wake();
    } catch (e) {
      why.textContent = `No voice preview: ${e.message}.`;
    } finally {
      hear.disabled = false;
    }
  }
  function select(id, withVoice) {
    const s = seats.find((x) => x.p.id === id);
    if (!s) return;
    const changed = id !== chosen;
    chosen = id;
    // turn the table the short way so this seat sits across from the viewer, facing them
    let target = -s.angle;
    while (target - spin > Math.PI) target -= Math.PI * 2;
    while (target - spin < -Math.PI) target += Math.PI * 2;
    from = spin; to = target; turnStart = performance.now();
    const p = shown(id);
    who.innerHTML = `<span class="pn">${esc(p.display_name)}</span>${id === activeId ? '<span class="pill on">Active</span>' : ""}`;
    if (changed) typeOut(p.greeting || "");
    pick.textContent = id === activeId ? "Chosen" : `Choose ${p.display_name}`;
    pick.disabled = readOnly || id === activeId;
    pick.title = readOnly ? "Settings change only on the brain's computer." : "";
    why.textContent = "";
    wake();
    if (withVoice) play(id);
  }
  hear.addEventListener("click", () => chosen && play(chosen));
  pick.addEventListener("click", async () => {
    if (!chosen || chosen === activeId) return;
    pick.disabled = true;
    const want = chosen;
    if (await choose(want)) {
      // the brain says which one is active now: the venue's own persona may win over this one
      const now = await fetch("/api/personas", { cache: "no-store" }).then((r) => r.json()).catch(() => null);
      activeId = now?.active || want;
    }
    select(want, false);
    if (activeId !== want && !why.textContent) why.textContent = "Saved, but this venue uses its own persona: Persona in This Venue (below) wins.";
  });

  /** The row's value changed another way (its own control): show it as active. */
  box.setActive = (id) => { activeId = id; if (chosen) select(chosen, false); };
  select(active && shown(active) ? active : personas[0].id, false);
  requestAnimationFrame(size);
  return box;
}
