// The immersive hub (xr.html): the designed hub's startup in VR/AR, with three.js. Same look, motion,
// timings and sounds as the hub at / (design.html; numbers from /theme.json), around you instead of on a screen:
//   ignite → the waiting core and its words over a still star field (xr/ignition.js); the trigger or a
//            pinch starts it ("safe to start": it only opens the hub)
//   unlock → ~1.35 s: the bolts pull back, the ring turns and opens, the core bursts (and its sounds)
//   jump   → the same stars stream past on one smooth speed curve (xr/stars.js), then the impact frame
//   boot   → the flash, a long brake: the network streaks in white-hot and cools (xr/network.js), the core
//            arrives big and settles while its rings lock on one by one (xr/core.js), the real checks type
//            out under it, the place's name decodes above it, the brain's greeting types out
//   hub    → the hub around you (xr/hub.js): the title flies to its corner, the core settles, the
//            callouts unfold out from it; the strip, the log, the frame; the network drifts with pulses
//            and the core shows the assistant's real state (/api/status)
// The trigger (or a pinch) starts it and skips the startup while it plays; on the hub it presses what
// the controller or hand points at (xr/pointer.js). ⏻ in the strip goes back to the start (and the
// jump), B or Y closes a page. Units: metres; the stage (everything) is placed where your head is,
// facing where you look, at the start and at each jump.
// "Preview on this screen" runs the same scene without a headset (drag to look around, click to press).
// "Shut down lab-os" (quick job 44): the brain says so first ("brain_off" on /ws); the hub around you goes
// away and a "lab-os is off" card stays in front of you (xr/off.js), as every page's cover does on a screen.
// Quick job 78: the hub in VR doesn't count on that one message. When the brain doesn't answer (when you
// enter VR or AR, at a press on the start screen, or for ~3 s at any time), the same card says "lab-os is
// not reachable" and nothing starts; once the brain answers again, the page reloads by itself. Exit (under the hub on every page, and under the off card) leaves VR or AR, back to the
// browser.
import * as THREE from "three";
import { theme } from "/web/theme.js";
import { Checks, Greeting, Title } from "./xr/boottext.js";
import { Core, RING_ORDER } from "./xr/core.js";
import { C, PASS, arrive, clamp, loadFonts, loadIcons } from "./xr/draw.js";
import { Ignition } from "./xr/ignition.js";
import { Network } from "./xr/network.js";
import { WayOut } from "./xr/modules.js";
import { OffCard } from "./xr/off.js";
import { Sfx } from "./xr/sfx.js";
import { HubView } from "./xr/hub.js";
import { Pointer } from "./xr/pointer.js";
import { FAR, Sky, Stars } from "./xr/stars.js";
import { loadLook, minimal } from "./xr/look.js";
import { getLink } from "/static/link.js";
import { deviceName } from "/web/device.js";

const $ = (s) => document.querySelector(s);
const params = new URLSearchParams(location.search);
const HY = theme.startup?.hyperspace || {};
const T = { ramp: (HY.ramp_s ?? 2) * 1000, hold: (HY.hold_s ?? 0.7) * 1000, brake: (HY.brake_s ?? 2.6) * 1000 };
const IMPACT = HY.impact_frame !== false;
const N_STARS = Math.min(HY.stars ?? 3000, 3000); // the Quest draws 3000 easily; more buys nothing
const BG = new THREE.Color(C.bg);
const D = 2.4; // the core's distance (m)
const V_DRIFT = 0.8, V_MAX = 110; // star speed, m/s (the hub crosses its depth in ~1.2 s; so does this)
const BOOT_SCALE = 1.3; // the core during the startup, as on the screen (then 1 on the hub)
// ?slow=10: everything ten times slower, silent (to look at each moment of the startup, and for tests)
const SLOW = Math.max(1, Number(params.get("slow")) || 1);
let vnow = 0; // the show's clock (ms): frame time, divided by SLOW
const clockNow = () => vnow;
// waits on the show's clock, so the startup's steps stay in step with its frames
const timers = [];
const wait = (ms) => new Promise((r) => timers.push({ at: vnow + ms, r }));
function runTimers() {
  for (let i = timers.length - 1; i >= 0; i--) if (timers[i].at <= vnow) { timers[i].r(); timers.splice(i, 1); }
}
// the hub's arrival curve for the core, cubic-bezier(0.2, 0.9, 0.25, 1), close enough
const settle = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3.4);
// quick job 78: the brain's status is read every 1.5 s; two reads in a row with no answer (~3 s): lab-os
// counts as off. A press after a longer quiet time (the headset slept, so the reads stopped) asks first.
const LOST_MS = 3500, LOST_READS = 2;

class Show {
  constructor(ar) {
    this.ar = ar;
    PASS.ar = ar; // a stronger panel fill over the room (quick job 157)
    this.scene = new THREE.Scene();
    if (!ar) this.scene.background = BG;
    this.stage = new THREE.Group(); // you at its origin, -z ahead
    this.scene.add(this.stage);
    this.sky = new Sky();
    this.stars = new Stars(N_STARS);
    this.net = new Network();
    this.net.core.set(0, 0, -D);
    this.core = new Core();
    this.core.group.position.set(0, 0, -D);
    this.ign = new Ignition();
    this.ign.group.position.set(0, 0, -D);
    this.title = new Title();
    this.title.mesh.position.set(0, 1.02, -D);
    this.greet = new Greeting();
    this.greet.mesh.position.set(0, 0.84, -D);
    this.checks = new Checks();
    this.checks.mesh.position.set(0, -1.02, -D);
    this.sfx = new Sfx(T);
    this.hub = new HubView({ core: this.core, sfx: this.sfx, D });
    this.hub.clock = () => this.clock();
    this.hub.scene = this.scene; this.hub.ar = ar;
    this.stage.add(this.sky.mesh, this.stars.group, this.net.group, this.ign.group, this.hub.group, this.core.group, this.title.mesh, this.greet.mesh, this.checks.mesh, this.hub.tab.mesh, this.hub.menu.mesh);
    this.pointer = new Pointer(this.scene);
    // the way out (quick job 157): ⏻, EXIT and × (while a page is open) under the core and the ask line, on
    // the hub, a details page and Settings; an open module has the same buttons on its tab, Teleop on its bar
    this.exit = new WayOut(0.13);
    this.exit.mesh.position.set(0, -1.22, -D + 0.1);
    this.exit.mesh.visible = false;
    this.stage.add(this.exit.mesh);
    this.leave = () => {}; // start() sets it: end the VR or AR session, or close the preview
    this.facts = { title: "Lab", greeting: "", status: null, arm: null, display: "" };
    this.seenAt = Date.now(); this.misses = 0; // the brain's last answer, and the failed reads since (quick job 78)
    this.phase = "ignite";
    this.t0 = 0;
    this.skip = false;
    this.toIgnite();
  }

  /** Put the stage where the head is, facing where it looks (level). */
  placeAt(camera) {
    const p = new THREE.Vector3(), q = new THREE.Quaternion();
    camera.getWorldPosition(p); camera.getWorldQuaternion(q);
    const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    this.stage.position.copy(p);
    this.stage.rotation.set(0, Math.atan2(-fwd.x, -fwd.z), 0);
  }

  toIgnite() {
    this.phase = "ignite";
    this.ign.reset(); this.ign.group.visible = true;
    this.core.group.visible = false;
    this.hub.hide();
    this.flyAt = null;
    this.title.reset(); this.greet.reset(); this.checks.reset();
    this.hub.ask.syncWake(false);
    this.title.mesh.position.set(0, 1.02, -D); this.title.mesh.scale.setScalar(1); this.title.mesh.rotation.set(0, 0, 0);
    this.greet.mesh.position.set(0, 0.84, -D);
    this.checks.mesh.position.set(0, -1.02, -D); this.checks.mesh.scale.setScalar(1);
    this.stars.visible = true;
  }

  /** The trigger or a pinch (or a click on a screen); `hit`: what that pointer is on. */
  press(now, hit) {
    if (hit?.what.kind === "exit") return this.leave(); // Exit: back to the browser, from any page
    if (this.off) return; // lab-os is off: nothing else to press
    if (this.asking) return; // still asking the brain (below)
    if (this.unsure()) { // a shutdown this page didn't hear about? Ask the brain before anything starts
      this.sfx.unlockAudio();
      this.asking = true;
      getJSON("/api/status").then((st) => {
        this.asking = false;
        if (!st) return this.turnOff({ lost: true });
        this.heard();
        this.press(clockNow(), hit);
      });
      return;
    }
    this.sfx.unlockAudio();
    if (this.phase === "ignite" && minimal()) {
      // minimal (quick job 157): no unlock, no jump, no flash: the hub is there at once
      this.hub.ask.greet();
      this.placeAt(this.camera);
      this.bootAt = now - T.brake;
      this.phase = "boot";
      this.finishBoot();
      wait(1500).then(() => this.hub.ask.playGreeting()); // once the greeting has come
    } else if (this.phase === "ignite") {
      this.ign.unlock(now); this.sfx.unlock();
      this.hub.ask.greet(); // the spoken greeting: asked for now, played as it's typed
      this.phase = "unlock";
      this.wantPlace = true;
    } else if (this.phase === "jump" || this.phase === "boot") this.finishBoot();
    else if (this.phase === "hub" && now > this.hubAt + 600) {
      const r = this.hub.press(hit, now); // ⏻ opens its menu; the menu says which
      if (r === "power") this.toIgnite(); // back to the start screen
      else if (r === "exit") this.leave(); // leave VR or AR (the menu's Exit)
    }
  }
  /** lab-os was shut down (or restarts): the hub goes, the microphone closes, the card stays. */
  /** The brain answered a status read. */
  heard() { this.seenAt = Date.now(); this.misses = 0; }
  /** No recent answer from the brain (a read failed, or none for a while): ask before a press acts. */
  unsure() { return this.misses > 0 || Date.now() - this.seenAt > LOST_MS; }
  turnOff(msg) {
    if (this.off) return;
    this.off = new OffCard(msg);
    this.off.lost = !!msg.lost;
    this.hub.closeModule(); // Teleop's room (outside the stage) goes too: only the card
    this.scene.add(this.off.mesh);
    this.stage.visible = false;
    this.pointer.setTargets([this.off.exit.mesh]); // only Exit, under the card
    for (const k of ["left", "right", "mouse"]) this.pointer.hide(k);
    this.hub.ask.V?.off();
    this.sfx.close?.();
  }
  /** B or Y: back (closes an open page or module; in Teleop only B, Y is teleop's). */
  back(now, key) { if (this.phase === "hub") this.hub.back(now, key); }

  startJump(now) {
    this.phase = "jump";
    this.t0 = now;
    this.ign.group.visible = false;
    this.sfx.hyper();
  }

  async boot(now) {
    // the flash: the core arrives big and settles; the network streaks in; the rings lock on
    this.phase = "boot";
    this.bootAt = now;
    this.skip = false;
    if (!this.ar) this.sky.flash(now); // AR: no white flash over the real room (quick job 157)
    this.sfx.arrive();
    this.core.group.visible = true;
    this.core.setRingsOn(false);
    this.core.spinBoost = 12;
    this.core.lockOn(now);
    for (let i = 0; i < RING_ORDER.length; i++) {
      this.core.lockRing(RING_ORDER[i], clockNow());
      this.sfx.lock(i);
      await wait(75);
      if (this.skip) return;
    }
    this.core.ignite(clockNow()); this.sfx.sweep();
    // real checks only: each line reads something the brain just reported
    const st = this.facts.status, ai = st?.ai, arm = this.facts.arm;
    const checks = [
      ["Theme", theme.colors ? "loaded" : "defaults", !!theme.colors],
      ["Sound", this.sfx.ready ? "unlocked" : "muted", this.sfx.ready],
      ["Display", this.facts.display, true],
      ["Internet", st?.internet === true ? "online" : st?.internet === false ? "offline" : "checking", st?.internet === true],
      ["AI", !ai ? "brain not reachable" : ai.paused ? "paused" : ai.connected ? ai.setup : "not connected", !!ai?.connected && !ai.paused],
      ["Assistant", st?.persona?.display_name || "unknown", !!st],
      ["Arm", arm?.connected ? arm.name : "disconnected", !!arm?.connected],
    ];
    const typing = (async () => {
      for (const [k, v, ok] of checks) {
        this.checks.add(k, v, ok, clockNow());
        await wait(70 + k.length * 10 + 90 + v.length * 10 + 40);
        if (this.skip) return;
      }
    })();
    await wait(650);
    if (this.skip) return;
    this.title.start(clockNow());
    await wait(24 * 34);
    if (this.skip) return;
    this.sfx.title();
    this.greet.text = this.facts.greeting || this.greetingWord();
    this.greet.start(clockNow());
    this.hub.ask.playGreeting();
    await wait(this.greet.text.length * 22);
    await typing;
    if (this.skip) return;
    await wait(800);
    this.finishBoot();
  }
  greetingWord() { const h = new Date().getHours(); return h < 5 ? "Good evening." : h < 12 ? "Good morning." : h < 18 ? "Good afternoon." : "Good evening."; }

  finishBoot() {
    if (this.phase === "hub") return;
    this.skip = true;
    const now = clockNow();
    if (this.phase === "jump") { if (!this.ar) this.sky.flash(now); this.bootAt = now - T.brake; }
    this.phase = "hub";
    this.hubAt = now;
    this.ign.group.visible = false;
    this.core.group.visible = true;
    this.core.setRingsOn(true);
    if (this.title.t0 == null) this.title.start(now - 2000);
    if (!this.greet.text) this.greet.text = this.facts.greeting || this.greetingWord();
    if (this.greet.t0 == null) this.greet.start(now - 1e5);
    this.sfx.land();
    // the startup's pieces travel to their places on the hub; the panels unfold
    this.flyAt = now;
    this.flyFrom = { title: this.title.mesh.position.clone(), checks: this.checks.mesh.position.clone() };
    this.hub.arrive(now);
  }

  step(dt, now, camera) {
    this.camera = camera;
    if (this.off) return this.off.follow(camera, dt, this.pointer.all().length > 0);
    if (this.wantPlace) { this.placeAt(camera); this.wantPlace = typeof this.wantPlace === "number" && this.wantPlace > 1 ? this.wantPlace - 1 : false; }
    let v = V_DRIFT, trail = 0.04, bright = 0.6, k = 0, tint = 0, starShow = 1, impact = false, arriveK = 0, coreScale = BOOT_SCALE;
    const P = this.phase;
    if (P === "unlock") {
      if (this.ign.step(dt, now, this.clock())) this.startJump(now);
    } else if (P === "ignite") {
      this.ign.paintWords(this.screen, this.hasHands);
      this.ign.step(dt, now, this.clock());
    }
    if (P === "jump") {
      // one smooth curve: exponential speed; the trails lead (they grow with time²); the view brightens
      // and turns faintly blue; then full speed (hold), then the impact frame
      const ms = now - this.t0, p = clamp(ms / T.ramp, 0, 1), rush = (Math.exp(4.2 * p) - 1) / (Math.exp(4.2) - 1);
      k = Math.pow(p, 1.5);
      v = V_DRIFT + (V_MAX - V_DRIFT) * rush;
      trail = 0.04 + FAR * p * p;
      bright = 0.7 + 0.5 * Math.pow(p, 1.2);
      tint = 0.15 * k;
      if (ms > T.ramp + T.hold) {
        if (IMPACT && !this.ar && ms < T.ramp + T.hold + 80) impact = true; // AR: no impact frame
        else this.boot(now);
      }
    } else if (P === "boot" || P === "hub") {
      const b = clamp((now - this.bootAt) / T.brake, 0, 1), e = 1 - Math.pow(1 - b, 3);
      v = V_DRIFT + (V_MAX - V_DRIFT) * Math.pow(1 - b, 3);
      trail = 0.04 + FAR * Math.pow(1 - b, 2.5);
      bright = 1.2 - 0.6 * b; k = 1 - b;
      starShow = 1 - e;
      arriveK = e;
      coreScale = BOOT_SCALE * (2.8 / 1.3 - (2.8 / 1.3 - 1) * settle(b));
    }
    if (P === "hub") this.toPlaces(dt, now);
    this.stars.impact = impact;
    this.stars.step(dt, now, { v, trail, bright: bright * starShow, k, jump: P === "jump" || P === "boot", frozen: impact });
    this.stars.visible = starShow > 0.01;
    this.sky.step(now, tint, impact);
    // the assistant's state: this headset's own voice turn, else the brain's; another screen's turn is idle
    // here (quick job 58: only the screen that has the conversation listens, thinks and speaks)
    const ask = this.hub.ask;
    const a = this.facts.status?.assistant;
    const other = a && ["listening", "thinking", "speaking"].includes(a.state) && (a.device || "") !== deviceName();
    const state = ask.state || (other ? "idle" : a?.state) || "offline";
    this.core.voiceLoud = ask.state === "speaking" ? ask.loud || 0 : null;
    this.core.micLevel = ask.state === "listening" ? ask.level || 0 : null;
    this.core.state = P === "hub" || P === "boot" ? state : "idle";
    if (P === "boot" || P === "hub") this.core.step(dt, now);
    if (P !== "hub") { this.core.group.scale.setScalar(coreScale); this.core.group.position.set(0, 0, -D); }
    this.net.step(dt, { arrive: P === "boot" || P === "hub" ? arriveK : 0, show: P === "boot" || P === "hub" ? 1 : 0, state, loud: this.core.loud });
    if (this.title.step(now)) this.sfx.decode();
    this.greet.step(now);
    if (this.checks.step(now)) this.sfx.line();
    this.checks.fade = P === "hub" ? Math.max(0, 1 - (now - this.hubAt) / 800) : 1;
    // a module has the way out on its tab (Teleop on the bar under its status box, quick job 102)
    this.exit.mesh.visible = P === "hub" && !this.hub.module;
    this.exit.close = this.hub.mode === "details" || this.hub.mode === "settings";
    this.exit.hover = this.pointer.all().find((h) => h.obj === this.exit.mesh)?.what || null;
    if (this.exit.mesh.visible) this.exit.paint();
    this.pointer.setTargets(P === "hub" ? [...this.hub.targets(), this.exit.mesh] : []);
    camera.getWorldPosition(this.hub.cameraPos ||= new THREE.Vector3());
    this.stage.worldToLocal(this.hub.cameraPos);
    // teleop's own room replaces the far layer while it's open
    const teleop = this.hub.module?.id === "teleop";
    this.net.group.visible = !teleop;
    if (teleop) this.stars.visible = false;
    this.hub.step(dt, now, P === "hub" ? this.pointer.all() : []);
  }

  /** On the hub: the title flies into its corner, the checks toward the strip, the greeting leaves, and
   *  the core settles from the startup's size to the hub's (or docks beside an open page). */
  toPlaces(dt, now) {
    const k = arrive((now - this.flyAt) / 1000);
    const brand = this.hub.brand.mesh, to = new THREE.Vector3(), q = new THREE.Quaternion();
    brand.getWorldPosition(to); this.stage.worldToLocal(to);
    brand.getWorldQuaternion(q);
    // the title's text starts at the brand's left edge: line their left ends up
    const titleW = this.title.p.w * 0.46, brandLeft = to.clone().add(new THREE.Vector3(-this.hub.brand.w / 2 + titleW / 2 + 0.01, 0, 0).applyQuaternion(q));
    this.title.mesh.position.lerpVectors(this.flyFrom.title, brandLeft, k);
    this.title.mesh.scale.setScalar(1 - 0.54 * k);
    this.title.mesh.quaternion.slerpQuaternions(new THREE.Quaternion(), q.premultiply(this.stage.quaternion.clone().invert()), k);
    this.title.fade = k >= 1 ? 0 : 1;
    this.greet.fade = Math.max(0, 1 - (now - this.flyAt) / 500);
    this.greet.mesh.position.y = 0.84 + 0.05 * clamp((now - this.flyAt) / 500, 0, 1);
    const sk = clamp((now - this.flyAt) / 800, 0, 1);
    this.checks.mesh.position.lerpVectors(this.flyFrom.checks, new THREE.Vector3(0.9, 0.9, -D), arrive(sk));
    this.checks.mesh.scale.setScalar(1 - 0.6 * arrive(sk));
    const tgt = this.hub.coreTarget(), start = BOOT_SCALE + (1 - BOOT_SCALE) * k;
    const s = this.flyAt != null && now - this.flyAt < 1000 ? start * tgt.scale : tgt.scale;
    const cur = this.core.group.scale.x;
    this.core.group.scale.setScalar(now - this.flyAt < 1000 ? s : cur + (s - cur) * Math.min(1, dt * 6));
    this.core.group.position.lerp(tgt.pos, Math.min(1, dt * 6));
  }
  clock() {
    const d = new Date(Date.now() + (this.facts.offset || 0));
    const twelve = theme.clock === "12h", h = d.getHours();
    return `${String(twelve ? h % 12 || 12 : h).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
}

/* ---------- the brain's facts ---------- */
async function getJSON(url) {
  // a time limit, so a read can't hang (quick job 78). Generous: a busy headset's first reads take ~2.5 s,
  // and a brain that's gone fails at once ("connection refused"), not by this limit
  try { const r = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(6000) }); return r.ok ? await r.json() : null; } catch { return null; }
}
async function loadFacts(show) {
  const [hub, hello, st, arm] = await Promise.all([getJSON("/api/hub"), getJSON("/api/greeting"), getJSON("/api/status"), getJSON("/api/arm")]);
  if (hub?.title) { show.facts.title = hub.title; show.title.text = hub.title; }
  // the Raspbot module is in VR and AR only (quick job 107): the screen hub has the Raspbot page in All Pages
  show.hub.setModules([...(hub?.modules || []).map((m) => m.id), "raspbot"]);
  if (hello?.text) show.facts.greeting = hello.text;
  show.facts.status = st; show.facts.arm = arm;
  if (st) show.heard();
  if (st?.time_ms) show.facts.offset = st.time_ms - Date.now();
  show.ign.place = st?.venue || "";
}
async function pollPanels(show) {
  const [project, spend, commits, devices] = await Promise.all([getJSON("/api/project"), getJSON("/api/spend"), getJSON("/api/commits?days=30"), getJSON("/api/live-devices")]);
  Object.assign(show.hub.facts, { project, spend, commits, devices, title: show.facts.title });
}
async function poll(show) {
  if (show.off) { // not reachable: reload once the brain answers again (after a shutdown, /web/off.js does it)
    if (show.off.lost && (await getJSON("/api/status"))) location.reload();
    return;
  }
  show.hub.ask.syncWake(show.phase === "hub"); // in a module or a page too: the wake word, then "back to the hub"
  if (show.phase === "hub") show.hub.ask.pollChat(clockNow());
  const [st, arm] = await Promise.all([getJSON("/api/status"), getJSON("/api/arm")]);
  if (show.off) return;
  if (st) show.heard();
  else if (++show.misses >= LOST_READS) return show.turnOff({ lost: true }); // shut down, and this page missed the message
  if (st) show.facts.status = st; else if (show.facts.status) show.facts.status = { ...show.facts.status, assistant: { state: "offline" } };
  if (arm) show.facts.arm = arm;
  show.hub.facts.status = show.facts.status;
  show.hub.ask.setStatus(show.facts.status);
}

/* ---------- pointing in the headset: each controller's (or hand's) ray, B / Y = back ---------- */
const FWD = new THREE.Vector3();
const backWas = {};
function xrPointers(show, frame, r, now) {
  const ref = r.xr.getReferenceSpace(), on = show.phase === "hub" || !!show.off; // off: Exit on the card
  const teleop = on && !show.off && show.hub.module?.id === "teleop";
  // Teleop open (quick job 97, as before 2026-11-21): its own session reads the controllers and drives the
  // arm; only the right ray can reach the buttons beside the status box (STOP, Options, Back, Exit; quick job
  // 102), its beam drawn only while it is on one, so it isn't in the way (its trigger or pinch only grips while
  // the clutch is held)
  if (teleop) show.hub.module.view.frame(performance.now(), frame, ref);
  for (const src of frame.session.inputSources) {
    const key = src.handedness;
    if (key !== "left" && key !== "right") continue;
    const pose = src.targetRaySpace && frame.getPose(src.targetRaySpace, ref);
    if (!pose || !on || (teleop && key === "left")) { show.pointer.hide(key); continue; }
    const p = pose.transform.position, o = pose.transform.orientation;
    FWD.set(0, 0, -1).applyQuaternion(new THREE.Quaternion(o.x, o.y, o.z, o.w));
    show.pointer.update(key, new THREE.Vector3(p.x, p.y, p.z), FWD.clone(), teleop ? "on-hit" : true);
    const b = !!src.gamepad?.buttons[5]?.pressed; // B (right) / Y (left)
    if (b && !backWas[key]) show.back(now, key);
    backWas[key] = b;
  }
  if (on && !show.off && show.hub.module?.id === "raspbot") {
    show.hub.module.view.input(frame, ref, now, (key) => show.pointer.hitOf(key));
  }
}

/* ---------- running it: in the headset, or on this screen ---------- */
let renderer = null;
function makeRenderer(ar) {
  renderer ||= new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.setClearColor(BG, ar ? 0 : 1);
  return renderer;
}
async function start(mode) {
  await loadLook(); // this headset's Level of Detail, before the scene is made (quick job 157)
  const ar = mode === "immersive-ar" || params.has("passthrough"), show = new Show(ar); // ?preview&passthrough: the AR way, see-through (quick job 10)
  window.__xrShow = show; // for tests and the console
  window.__xrNow = clockNow;
  show.hub.ask.now = clockNow;
  await Promise.all([loadFacts(show), loadFonts(), loadIcons()]);
  show.title.text = show.facts.title;
  await pollPanels(show);
  show.hub.facts.status = show.facts.status;
  const link = getLink("monitor"); // a watcher's link: it drives nothing
  link.on("brain_off", (m) => show.turnOff(m));
  if (!show.facts.status) show.turnOff({ lost: true }); // entered VR or AR with no brain to answer
  const timer = setInterval(() => poll(show), 1500), timer2 = setInterval(() => pollPanels(show), 20000);
  const r = makeRenderer(ar);
  const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.05, 400);
  let last = performance.now();
  vnow = 0;
  const frame = (time, xrFrame) => {
    const real = performance.now(), dt = Math.min(0.05, (real - last) / 1000) / SLOW;
    last = real;
    vnow += dt * 1000;
    runTimers();
    const now = vnow;
    if (xrFrame) xrPointers(show, xrFrame, r, now);
    show.step(dt, now, camera); // in the headset, three keeps `camera` on the head's pose
    r.render(show.scene, camera);
  };
  if (mode === "screen") { // no headset: the same scene full window; click or a key starts / skips
    show.facts.display = `${screen.width}×${screen.height}`;
    show.screen = true;
    show.leave = () => location.reload(); // Exit in the preview: back to the page
    camera.position.set(0, 1.6, 0);
    show.placeAt(camera);
    document.body.append(r.domElement);
    Object.assign(r.domElement.style, { position: "fixed", inset: 0, width: "100%", height: "100%", zIndex: 50, cursor: "grab" });
    const size = () => { r.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); };
    size(); addEventListener("resize", size);
    // drag to look around; a click without a drag presses what the mouse is on
    let drag = null, yaw = 0, pitch = 0, holding = false;
    const mouse = new THREE.Vector2(), rc = new THREE.Raycaster();
    const aim = (e) => {
      mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
      rc.setFromCamera(mouse, camera);
      show.pointer.update("mouse", rc.ray.origin, rc.ray.direction, false);
    };
    r.domElement.addEventListener("pointerdown", (e) => {
      aim(e);
      if (show.phase === "hub" && show.pointer.hitOf("mouse")?.what.kind === "ask") { holding = true; show.hub.ask.pressStart(clockNow()); return; }
      drag = { x: e.clientX, y: e.clientY, yaw, pitch, moved: false };
    });
    addEventListener("pointermove", (e) => {
      aim(e);
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      yaw = drag.yaw + dx * 0.004; pitch = clamp(drag.pitch + dy * 0.004, -1.2, 1.2);
      camera.rotation.set(pitch, yaw, 0, "YXZ");
    });
    addEventListener("pointerup", (e) => { if (holding) { holding = false; show.hub.ask.pressEnd(); return; } if (drag && !drag.moved) { aim(e); show.press(clockNow(), show.pointer.hitOf("mouse")); } drag = null; });
    addEventListener("keydown", (e) => {
      if (e.key === "Escape") return show.hub.mode !== "hub" || show.hub.menu.mesh.visible ? show.back(clockNow(), "right") : location.reload();
      if (show.phase !== "hub") show.press(clockNow());
    });
    r.setAnimationLoop(frame);
    return;
  }
  r.xr.enabled = true;
  r.xr.setFoveation?.(1);
  const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor", "hand-tracking"] });
  let refType = "local-floor";
  try { await session.requestReferenceSpace("local-floor"); } catch { refType = "local"; }
  r.xr.setReferenceSpaceType(refType);
  show.hub.refType = refType;
  await r.xr.setSession(session);
  show.leave = () => { session.end().catch(() => {}); }; // Exit: the browser shows the page again
  const bl = session.renderState.baseLayer;
  show.facts.display = bl ? `${Math.round(bl.framebufferWidth / 2)}×${bl.framebufferHeight} per eye` : "headset";
  show.wantPlace = 30; // in front of you, at your height: for the first frames, until the headset reports where that is
  const hands = () => { show.hasHands = [...session.inputSources].some((s) => s.hand || (s.profiles || []).some((p) => p.includes("hand"))); };
  session.addEventListener("inputsourceschange", hands);
  hands();
  // trigger, or a pinch: presses what that controller or hand points at
  // hold the trigger (or a pinch) on the ask line: push-to-talk
  const holds = new Set();
  session.addEventListener("selectstart", (e) => {
    const key = e.inputSource.handedness;
    if (show.phase === "hub" && show.hub.mode === "hub" && show.pointer.hitOf(key)?.what.kind === "ask") { holds.add(key); show.hub.ask.pressStart(clockNow()); }
  });
  session.addEventListener("selectend", (e) => { if (holds.delete(e.inputSource.handedness)) show.hub.ask.pressEnd(); });
  session.addEventListener("select", (e) => {
    const key = e.inputSource.handedness;
    if (show.hub.module?.id === "teleop" && key === "left") return; // the left hand is teleop's clutch
    show.press(clockNow(), show.pointer.hitOf(key));
  });
  session.addEventListener("end", () => {
    r.setAnimationLoop(null); clearInterval(timer); clearInterval(timer2);
    show.hub.closeModule(clockNow()); // Teleop open (Exit, or the headset taken off): the arm freezes
    $("#msg").textContent = `Left ${ar ? "AR" : "VR"}. Press a button to go back in.`;
  });
  r.setAnimationLoop(frame);
}

async function init() {
  const vr = $("#vr"), ar = $("#ar");
  const device = params.get("device");
  $("#flat").href = `/?flat=1${device ? `&device=${encodeURIComponent(device)}` : ""}`; // the hub in the browser
  getJSON("/api/hub").then((h) => h?.title && ($("#place").textContent = h.title));
  const preview = () => start("screen").catch((e) => ($("#msg").textContent = `Couldn't start: ${e.message}`));
  const can = async (m) => !!navigator.xr && (await navigator.xr.isSessionSupported(m).catch(() => false));
  const [hasVR, hasAR] = await Promise.all([can("immersive-vr"), can("immersive-ar")]);
  vr.disabled = !hasVR;
  vr.querySelector(".label").textContent = hasVR ? "Enter VR" : "No VR here";
  ar.hidden = !hasAR;
  const headset = /OculusBrowser/.test(navigator.userAgent);
  if (!hasVR && !hasAR && headset && !window.isSecureContext) {
    // over Wi-Fi the address isn't "secure", and the browser offers no VR there (GOTCHAS 2026-10-24)
    $("#msg").textContent = `VR needs a secure address. In the Quest's browser, open chrome://flags, find "Insecure origins treated as secure", add ${location.origin}, select Enabled, then Relaunch. Over a USB cable, http://localhost:8080 works as it is.`;
  }
  const go = (m) => () => start(m).catch((e) => ($("#msg").textContent = `Couldn't start: ${e.message}`));
  vr.onclick = go("immersive-vr");
  ar.onclick = go("immersive-ar");
  if (!hasVR && !hasAR && !headset) {
    // a computer (quick job 157): Preview is the main button, in the place of Enter VR ("No VR here" was on top)
    vr.disabled = false;
    vr.querySelector(".label").textContent = "Preview on this screen";
    vr.querySelector("small").textContent = "The hub in VR, here. Drag to look around.";
    vr.onclick = preview;
    $("#msg").textContent = "In the Quest, open the hub's address in its browser to enter VR.";
  }
  if (params.has("preview")) preview();
  micButton();
}
// Talking in VR needs the microphone; a browser's question about it inside VR is easy to miss, so it's
// asked here, on the page, once (the browser remembers). Only where voice works at the brain.
async function micButton() {
  const st = await getJSON("/api/status");
  if (!st?.voice?.available || !window.isSecureContext || !navigator.mediaDevices?.getUserMedia) return;
  const state = await navigator.permissions?.query({ name: "microphone" }).then((p) => p.state).catch(() => "prompt");
  if (state === "granted") return;
  const b = document.createElement("button");
  b.className = "btn"; b.type = "button"; b.textContent = "Allow the microphone (to talk in VR)";
  b.onclick = async () => {
    try {
      (await navigator.mediaDevices.getUserMedia({ audio: true })).getTracks().forEach((t) => t.stop());
      b.remove();
    } catch {
      $("#msg").textContent = "The browser didn't allow the microphone: in VR, the ask line says why. Typing on a screen still works.";
    }
  };
  $(".actions").append(b);
}
init();
