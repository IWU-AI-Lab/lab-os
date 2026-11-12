// The hub in VR after the startup, laid out like the designed hub's launcher (design.html), on a gentle
// curve around you so everything faces you: the core in the middle; the callouts on the far sides
// (Current Project and AI Spend left, Commits and Devices right); the place's name top left, the status
// strip top right with ⏻ (back to the start screen: the jump plays again from there); the typed log
// bottom left; the screen frame (cut corners, tabs, notches) around it all; thin traces from the core
// up to the strip and down to the log. Module buttons go between the core and the callouts.
// Pointing and pressing (xr/pointer.js): a callout opens its details page (it unfolds from the callout,
// the core docks in its corner, Back closes it); its own controls work (7d / 14d / 30d, List all, a
// device opens its card).
// Units: metres in the stage's space (you at the origin, -z ahead).
import * as THREE from "three";
import { C, CanvasPlane, FONT, arrive, clamp, glowText, icon, rgba, spaced } from "./draw.js";
import { Callout, DetailsPage, DeviceCard, REM_M, devicesFrom } from "./panels.js";

const R = 2.4; // the curve's radius = the core's distance
const AZ_COL = 37; // degrees: the callout columns' centres (all of the hub fits the Quest's view)
const DEG = Math.PI / 180;
const CALLOUT_GAP = 1.9 * REM_M;

/** Put `obj` on the curve at azimuth `az` (degrees, + = right), height y, facing you. */
export function onCurve(obj, az, y, r = R) {
  obj.position.set(Math.sin(az * DEG) * r, y, -Math.cos(az * DEG) * r);
  obj.rotation.set(0, -az * DEG, 0);
}

export class HubView {
  /** @param {{core: import("./core.js").Core, sfx: import("./sfx.js").Sfx, D: number}} o */
  constructor({ core, sfx, D }) {
    this.core = core; this.sfx = sfx; this.D = D;
    this.group = new THREE.Group();
    this.group.visible = false;
    this.facts = { title: "", status: null, project: null, spend: null, commits: null, devices: null };
    this.mode = "hub"; // hub | details
    this.t0 = -1e9; // the arrival
    // callouts, each in a pivot at its corner nearest the core (it unfolds from there)
    this.callouts = { project: new Callout("project", "Current Project", "left"), spend: new Callout("spend", "AI Spend", "left"), commits: new Callout("commits", "Commits", "right"), devices: new Callout("devices", "Devices", "right") };
    this.cols = { left: [this.callouts.project, this.callouts.spend], right: [this.callouts.commits, this.callouts.devices] };
    for (const [side, list] of Object.entries(this.cols)) {
      const col = new THREE.Group();
      onCurve(col, side === "left" ? -AZ_COL : AZ_COL, 0);
      this.group.add(col);
      for (const c of list) {
        c.corner = new THREE.Group();
        c.mesh.position.set((side === "left" ? -1 : 1) * c.p.w / 2, -c.p.h / 2, 0);
        c.corner.add(c.mesh);
        col.add(c.corner);
      }
    }
    // the device card, beside the Devices callout toward the core
    this.card = new DeviceCard();
    onCurve(this.card.mesh, AZ_COL - 18, -0.05, R - 0.08);
    this.group.add(this.card.mesh);
    // the place's name (top left) and the strip (top right), ⏻ at its end
    // (lined up with the callout columns' outer edges, like the screen's top row)
    const edge = (13.6 * REM_M) / 2;
    this.brand = new CanvasPlane(1.4, 0.12, 1100);
    const brandHolder = new THREE.Group(); onCurve(brandHolder, -AZ_COL, 0.9); brandHolder.add(this.brand.mesh);
    this.brand.mesh.position.x = -edge + 0.7;
    this.group.add(brandHolder);
    this.strip = new CanvasPlane(1.75, 0.12, 1100);
    this.power = new CanvasPlane(0.11, 0.11, 1100);
    this.power.mesh.userData.hit = { hit: () => ({ kind: "power" }) };
    const stripHolder = new THREE.Group(); onCurve(stripHolder, AZ_COL, 0.9); stripHolder.add(this.strip.mesh, this.power.mesh);
    this.power.mesh.position.x = edge - 0.055;
    this.strip.mesh.position.x = edge - 0.13 - 1.75 / 2;
    this.group.add(stripHolder);
    // the typed log, bottom left
    this.log = new CanvasPlane(1.9, 0.28, 1000);
    const logHolder = new THREE.Group(); onCurve(logHolder, -AZ_COL + 4, -0.9); logHolder.add(this.log.mesh);
    this.group.add(logHolder);
    this.logRows = []; // {time, text, t0}
    this.logIdx = 0; this.nextLog = 0;
    // the frame and the traces
    this.frame = buildFrame();
    this.group.add(this.frame);
    this.traces = new Traces(D);
    this.group.add(this.traces.group);
    // the details page (unfolds from its callout)
    this.page = new DetailsPage(2.7, 1.6);
    this.page.mesh.visible = false;
    this.group.add(this.page.mesh);
    this.pageFrom = new THREE.Vector3();
    this.pageAt = -1e9; this.pageClosing = false;
    this.hovered = [];
  }

  get callout() { return this.callouts; }
  /** What the pointer can land on. */
  targets() {
    if (this.mode === "details") return [this.page.mesh];
    return [...Object.values(this.callouts).map((c) => c.mesh), this.power.mesh, this.card.mesh];
  }

  /** The startup is over: everything flies to its place and the panels unfold out from the core. */
  arrive(now, instant = false) {
    this.group.visible = true;
    this.t0 = instant ? now - 5000 : now;
    this.mode = "hub";
    this.page.mesh.visible = false;
    this.card.show(null);
    this.nextLog = now + 1500;
    this.logRows = [];
  }
  hide() { this.group.visible = false; this.mode = "hub"; this.page.mesh.visible = false; }

  /** Lay the callout columns out from their drawn heights (centred around the core's height). */
  _layout() {
    for (const list of Object.values(this.cols)) {
      // an open device list grows downward without moving anything (its closed height lays out the column)
      for (const c of list) if (!c.open) c.closedH = c.h;
      const hOf = (c) => (c.open ? c.closedH ?? c.h : c.h) * REM_M;
      const shown = list.filter((c) => c.available);
      const total = shown.reduce((a, c) => a + hOf(c), 0) + CALLOUT_GAP * Math.max(0, shown.length - 1);
      let y = total / 2;
      for (const c of list) {
        c.corner.visible = c.available;
        if (!c.available) continue;
        c.corner.position.set((c.side === "left" ? 1 : -1) * c.p.w / 2, y, 0);
        y -= hOf(c) + CALLOUT_GAP;
      }
    }
  }

  /** What a press on `hit` does here. Returns "power" when the hub should go back to the start. */
  press(hit, now) {
    if (!hit) return null;
    const w = hit.what;
    if (w.kind === "power") { this.sfx.blip(); return "power"; }
    if (w.kind === "back") { this.closeDetails(now); return null; }
    if (w.kind === "page" || w.kind === "card") return null;
    const c = hit.obj.userData.hit;
    if (w.kind === "control" && c.id === "commits") { c.days = +w.id.slice(4); this.sfx.blip(); return null; }
    if (w.kind === "control" && w.id === "list") { c.open = !c.open; this.card.show(null); this.sfx.blip(); return null; }
    if (w.kind === "device") { this.card.show(this.card.dev?.name === w.dev.name ? null : w.dev); this.sfx.blip(); return null; }
    if (w.kind === "open") { this.openDetails(c, now); return null; }
    return null;
  }
  openDetails(c, now) {
    this.mode = "details";
    this.card.show(null);
    this.page.id = c.id; this.page.title = c.title;
    c.mesh.getWorldPosition(this.pageFrom);
    this.group.worldToLocal(this.pageFrom);
    this.page.mesh.visible = true;
    this.pageAt = now; this.pageClosing = false;
    this.sfx.blip(); this.sfx.open();
  }
  closeDetails(now) {
    if (this.mode !== "details") return;
    this.pageClosing = true; this.pageAt = now;
    this.mode = "hub";
    this.sfx.close();
  }
  /** Where the core should be: in the middle, or docked in the open page's corner. */
  coreTarget() {
    return this.page.mesh.visible && !this.pageClosing ? { pos: new THREE.Vector3(1.18, -0.66, -2.17), scale: 0.26 } : { pos: new THREE.Vector3(0, 0, -this.D), scale: 1 };
  }

  step(dt, now, hits) {
    if (!this.group.visible) return;
    const f = this.facts, t = now - this.t0;
    // data into the callouts
    this.callouts.project.data = f.project;
    this.callouts.spend.data = f.spend;
    this.callouts.commits.data = f.commits;
    this.callouts.devices.data = devicesFrom(f.devices?.devices);
    // hover: what any pointer is on
    for (const c of Object.values(this.callouts)) c.hover = null;
    this.page.hover = null;
    let powerHover = false;
    for (const h of hits) {
      const o = h.obj.userData.hit;
      if (o instanceof Callout) o.hover = h.what;
      else if (o === this.page) this.page.hover = h.what;
      else if (h.what.kind === "power") powerHover = true;
    }
    const hoverKey = hits.map((h) => `${h.obj.id}:${h.what.kind}:${h.what.id || ""}`).join("|");
    if (hoverKey !== this._hoverKey) { if (hoverKey) this.sfx.hover(); this._hoverKey = hoverKey; }
    for (const c of Object.values(this.callouts)) c.paint(now);
    this._layout();
    // the panels unfold one after another, spreading out from the core (their delay grows with distance)
    const dim = this.mode === "details" || (this.page.mesh.visible && !this.pageClosing) ? 0.12 : 1;
    this._dim = (this._dim ?? 1) + (dim - (this._dim ?? 1)) * Math.min(1, dt * 8);
    for (const c of Object.values(this.callouts)) {
      const delay = 450 + (c === this.callouts.project || c === this.callouts.commits ? 380 : 470);
      const k = arrive((t - delay) / 600);
      c.corner.scale.set(Math.max(0.001, k), Math.max(0.001, k), 1);
      c.p.opacity = clamp((t - delay) / 300, 0, 1) * this._dim;
    }
    const early = clamp((t - 300) / 600, 0, 1) * this._dim;
    this.paintBrand(); this.brand.opacity = clamp((t - 900) / 300, 0, 1) * this._dim;
    this.paintStrip(now); this.strip.opacity = early;
    this.paintPower(powerHover); this.power.opacity = early;
    this.stepLog(now); this.log.opacity = early;
    this.card.p.opacity = this.card.dev ? this._dim : 0;
    this.frame.userData.set(clamp(t / 700, 0, 1) * (0.4 + 0.6 * this._dim));
    this.traces.step(dt, now, clamp((t - 450) / 800, 0, 1) * this._dim, this.core.state);
    // the details page: unfolds from its callout (0.6 s), closes back toward it quickly (0.25 s)
    if (this.page.mesh.visible) {
      const k = this.pageClosing ? 1 - clamp((now - this.pageAt) / 250, 0, 1) : arrive((now - this.pageAt) / 600);
      const at = new THREE.Vector3(0, 0.02, -2.2);
      this.page.mesh.position.lerpVectors(this.pageFrom, at, k);
      this.page.mesh.scale.setScalar(Math.max(0.01, 0.2 + 0.8 * k));
      this.page.p.opacity = this.pageClosing ? k : clamp(k * 1.6, 0, 1);
      this.page.paint(this.page.id, { ...f, devices: devicesFrom(f.devices?.devices) }, this.page.title || "", now);
      if (this.pageClosing && k <= 0) { this.page.mesh.visible = false; this.pageClosing = false; }
    }
  }

  paintBrand() {
    const title = this.facts.title || "";
    this.brand.paint((g, w, h) => {
      g.textBaseline = "middle"; g.textAlign = "left";
      g.font = `700 ${h * 0.5}px ${FONT.title}`; spaced(g, 0.16);
      glowText(g, title.toUpperCase(), h * 0.1, h / 2, C.hot, rgba(C.primary, 0.6), h * 0.15);
    }, title);
  }
  paintStrip(now) {
    const st = this.facts.status, ai = st?.ai, clock = this.clock?.() || "";
    const items = [];
    if (st?.venue) items.push(["i-pin", st.venue, true]);
    if (st?.persona?.display_name) items.push(["i-user", st.persona.display_name, true]);
    if (st) items.push(["i-globe", st.internet ? "online" : "offline", !!st.internet]);
    if (ai) items.push(["i-chip", ai.paused ? "AI paused" : ai.connected ? `AI: ${ai.setup}` : "AI not connected", !!ai.connected && !ai.paused]);
    const key = JSON.stringify([items, clock]);
    this.strip.paint((g, w, h) => {
      g.textBaseline = "middle";
      // right to left: the clock, then the facts
      g.font = `${h * 0.42}px ${FONT.digits}`; g.textAlign = "right"; g.fillStyle = C.primary;
      g.fillText(clock, w - h * 0.2, h / 2);
      let x = w - h * 0.2 - g.measureText(clock).width - h * 0.75;
      g.font = `${FONT.linesW} ${h * 0.4}px ${FONT.lines}`;
      for (const [ico, text, ok] of items.reverse()) {
        const tw = g.measureText(text).width;
        g.fillStyle = ok ? C.text : C.offline; g.textAlign = "right"; g.fillText(text, x, h / 2);
        icon(g, ico, x - tw - h * 0.3, h / 2, h * 0.36, ok ? C.primary : C.offline, 1.6);
        x -= tw + h * 0.45 + h * 0.62;
      }
    }, key);
  }
  paintPower(hover) {
    this.power.paint((g, w, h) => {
      if (hover) { g.fillStyle = rgba(C.primary, 0.16); g.fillRect(0, 0, w, h); g.strokeStyle = C.primary; g.lineWidth = 3; g.strokeRect(1.5, 1.5, w - 3, h - 3); }
      icon(g, "i-power", w / 2, h / 2, w * 0.5, hover ? C.hot : C.dim, 1.8);
    }, hover);
  }
  /** The typed log: real lines (the latest commits, the current step), one every ~9 s. */
  stepLog(now) {
    const lines = this.logLines();
    if (lines.length && now > this.nextLog) {
      this.logRows.push({ time: this.clock?.() || "", text: lines[this.logIdx++ % lines.length], t0: now });
      while (this.logRows.length > 4) this.logRows.shift();
      this.nextLog = now + 9000;
    }
    const last = this.logRows[this.logRows.length - 1], typed = last ? Math.min(last.text.length, Math.floor((now - last.t0) / 22)) : 0;
    this.log.paint((g, w, h) => {
      const rh = h / 4;
      this.logRows.forEach((r, i, all) => {
        const y = h - (all.length - i - 0.5) * rh, cur = i === all.length - 1;
        g.globalAlpha = 0.35 + (0.65 * (i + 1)) / all.length;
        g.textBaseline = "middle"; g.textAlign = "left";
        g.font = `${rh * 0.42}px ${FONT.digits}`; g.fillStyle = rgba(C.primary, 0.8); g.fillText(r.time, 0, y);
        g.font = `${FONT.linesW} ${rh * 0.48}px ${FONT.lines}`; g.fillStyle = cur ? C.text : C.dim;
        g.fillText(cur ? r.text.slice(0, typed) : r.text, rh * 2.9, y);
      });
    }, `${this.logRows.length}|${last?.t0}|${typed}`);
  }
  logLines() {
    const c = this.facts.commits, p = this.facts.project;
    const lines = (c?.recent || []).map((x) => `git ${x.hash} ${x.subject}`);
    if (p?.available) {
      const now = p.steps.find((s) => !s.done), done = [...p.steps].reverse().find((s) => s.done);
      if (now) lines.splice(1, 0, `focus  Step ${now.n}: ${now.title}`);
      if (done) lines.splice(4, 0, `focus  Step ${done.n} done: ${done.title}`);
    }
    return lines;
  }
}

/* ---------- the screen frame, on the curve: cut corners, a raised tab top and bottom, notches ---------- */
function buildFrame() {
  const A = 52, Y = 1.08, cut = 0.07, tab = 14, tabH = 0.035, notch = 0.025, nY = 0.32;
  const pt = (az, y, r = R + 0.25) => new THREE.Vector3(Math.sin(az * DEG) * r, y, -Math.cos(az * DEG) * r);
  const arc = (a0, a1, y, n = 24) => Array.from({ length: n + 1 }, (_, i) => pt(a0 + ((a1 - a0) * i) / n, y));
  const cutA = (cut / R) / DEG, tabS = (tabH / R) / DEG;
  const top = [pt(-A, Y - cut), ...arc(-A + cutA, -tab - tabS, Y), ...arc(-tab, tab, Y + tabH, 16), ...arc(tab + tabS, A - cutA, Y), pt(A, Y - cut)];
  const bottom = top.map((p) => new THREE.Vector3(p.x, -p.y, p.z));
  const side = (s) => [pt(s * A, Y - cut), pt(s * A, nY + notch), pt(s * (A - 0.6), nY), pt(s * (A - 0.6), -nY), pt(s * A, -nY - notch), pt(s * A, -Y + cut)];
  const toSegs = (pts) => pts.slice(1).flatMap((p, i) => [pts[i], p]);
  const base = [...toSegs(top), ...toSegs(bottom), ...toSegs(side(-1)), ...toSegs(side(1))];
  const lineMat = new THREE.LineBasicMaterial({ color: new THREE.Color(C.line), transparent: true, depthWrite: false });
  const hiMat = new THREE.LineBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const g = new THREE.Group();
  g.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(base), lineMat));
  // bright brackets on the corners and the tabs
  const hi = [];
  for (const s of [-1, 1]) for (const v of [-1, 1]) {
    const c = [pt(s * (A - 6), v * Y), pt(s * (A - cutA), v * Y), pt(s * A, v * (Y - cut)), pt(s * A, v * (Y - 0.22))];
    hi.push(...toSegs(c));
  }
  for (const v of [-1, 1]) hi.push(...toSegs(arc(-tab, tab, v * (Y + tabH), 16)));
  for (const s of [-1, 1]) hi.push(...toSegs([pt(s * (A - 0.6), nY), pt(s * (A - 0.6), -nY)]));
  g.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(hi), hiMat));
  g.userData.set = (k) => { lineMat.opacity = k; hiMat.opacity = k; g.visible = k > 0.01; };
  return g;
}

/* ---------- traces: from the core to what you can press, ending on its edge with a dot; pulses run along ---------- */
export class Traces {
  constructor(D) {
    this.D = D;
    this.group = new THREE.Group();
    this.paths = []; // each: array of Vector3 (stage space)
    this.mat = new THREE.LineBasicMaterial({ color: new THREE.Color(C.line), transparent: true, depthWrite: false });
    this.dotMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.line), transparent: true, depthWrite: false });
    this.pulseMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.hot), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    this.pulses = [];
    this.next = 0;
    // up to the strip, down to the log: the hub's vertical line through the core
    this.set([[new THREE.Vector3(0, 0.56, -D), new THREE.Vector3(0, 0.98, -D)], [new THREE.Vector3(0, -0.56, -D), new THREE.Vector3(0, -0.98, -D)]]);
  }
  /** Replace the traces with these polylines (stage space). */
  set(paths, extra = []) {
    for (const o of [...this.group.children]) this.group.remove(o);
    this.paths = [...paths, ...extra];
    const segs = this.paths.flatMap((p) => p.slice(1).flatMap((q, i) => [p[i], q]));
    this.lines = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(segs), this.mat);
    this.group.add(this.lines);
    const dot = new THREE.CircleGeometry(0.008, 12);
    for (const p of this.paths) for (const e of [p[0], p[p.length - 1]]) { const m = new THREE.Mesh(dot, this.dotMat); m.position.copy(e); this.group.add(m); }
    this.pulses = [];
  }
  step(dt, now, show, state) {
    this.group.visible = show > 0.01;
    this.mat.opacity = show; this.dotMat.opacity = show;
    // a pulse now and then; toward the core while it thinks, away while it speaks
    if (now > this.next && this.paths.length && show > 0.5) {
      const p = this.paths[Math.floor(Math.random() * this.paths.length)];
      const m = new THREE.Mesh(new THREE.CircleGeometry(0.006, 10), this.pulseMat);
      this.group.add(m);
      this.pulses.push({ m, p, k: 0, inward: state !== "speaking" });
      this.next = now + (state === "thinking" || state === "speaking" ? 600 : 2500 + Math.random() * 4000);
    }
    for (const u of [...this.pulses]) {
      u.k += dt * 0.9;
      if (u.k >= 1) { this.group.remove(u.m); this.pulses.splice(this.pulses.indexOf(u), 1); continue; }
      const k = u.inward ? 1 - u.k : u.k, pts = u.p, seg = k * (pts.length - 1), i = Math.min(pts.length - 2, Math.floor(seg));
      u.m.position.lerpVectors(pts[i], pts[i + 1], seg - i);
      this.pulseMat.opacity = show;
    }
  }
}
