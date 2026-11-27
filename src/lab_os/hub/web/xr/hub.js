// The hub in VR after the startup, laid out like the designed hub's launcher (design.html), on a gentle
// curve around you so everything faces you: the core in the middle; the callouts on the far sides
// (Current Project and AI Spend left, Commits and Devices right); the place's name top left, the status
// strip top right with ⚙ (Settings: xr/settings.js) and ⏻ (back to the start screen: the jump plays again); the typed log
// bottom left; the screen frame (cut corners, tabs, notches) around it all; thin traces from the core
// up to the strip and down to the log. Module buttons (xr/modules.js) between the core and the
// callouts, alternating left and right in the theme's order (hub.modules), traces running to them:
// Teleop opens the arm scene without leaving VR or AR (quick job 97); Monitor and AI Control their
// holograms; Back (or B) closes them and the hub comes back.
// Pointing and pressing (xr/pointer.js): a callout opens its details page (it unfolds from the callout,
// the core docks in its corner, Back closes it); its own controls work (7d / 14d / 30d, List all, a
// device opens its card).
// Units: metres in the stage's space (you at the origin, -z ahead).
import * as THREE from "three";
import { C, GLOW, CanvasPlane, FONT, arrive, clamp, glowText, icon, rgba, spaced } from "./draw.js";
import { Ask } from "./ask.js";
import { RaspbotModule } from "./raspbot.js";
import { ArmHologram, ModuleButton, ModuleTab, PowerMenu, TeleopModule, VR_MODULES } from "./modules.js";
import { Callout, DetailsPage, DeviceCard, REM_M, devicesFrom } from "./panels.js";
import { SettingsPage } from "./settings.js";

const R = 2.4; // the curve's radius = the core's distance
const AZ_COL = 39; // degrees: the callout columns' centres (all of the hub fits the Quest's view)
const DEG = Math.PI / 180;
const CALLOUT_GAP = 1.9 * REM_M;
// The whole hub ~15 % larger (quick job 60): easier to read and to point at. Scaled about your head and
// moved back toward you so the core stays at its distance: the panels grow and spread a little wider.
export const HUB_SCALE = 1.15;
const CORE_AHEAD = 0.3 / HUB_SCALE; // metres in front of the panels, in the hub's own space

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
    this.group.scale.setScalar(HUB_SCALE);
    this.group.position.z = D * (HUB_SCALE - 1); // the core's place stays D ahead
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
    this.gear = new CanvasPlane(0.11, 0.11, 1100); // ⚙ Settings, like the screens' (quick job 60)
    this.gear.mesh.userData.hit = { hit: () => ({ kind: "settings" }) };
    const stripHolder = new THREE.Group(); onCurve(stripHolder, AZ_COL, 0.9); stripHolder.add(this.strip.mesh, this.gear.mesh, this.power.mesh);
    this.power.mesh.position.x = edge - 0.055;
    this.gear.mesh.position.x = edge - 0.055 - 0.13;
    this.strip.mesh.position.x = edge - 0.26 - 1.75 / 2;
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
    // the ask line just under the core's ring, the answer under it (xr/ask.js)
    this.ask = new Ask({ sfx });
    this.ask.line.mesh.position.set(0, -0.66, -D + 0.01);
    this.ask.reply.mesh.position.set(0, -0.9, -D + 0.01);
    this.group.add(this.ask.line.mesh, this.ask.reply.mesh);
    // the assistant opens pages here when asked (decision 2026-11-14)
    this.ask.pages = () => this.pagesHere();
    this.ask.onOpen = (id) => this.showPage(id, this.ask.now?.() ?? performance.now());
    // the details page (unfolds from its callout)
    this.page = new DetailsPage(2.7, 1.6);
    this.page.mesh.visible = false;
    this.group.add(this.page.mesh);
    this.pageFrom = new THREE.Vector3();
    this.pageAt = -1e9; this.pageClosing = false;
    // Settings (quick job 60): unfolds from ⚙ where the details pages open
    this.settings = new SettingsPage(2.7, 1.6);
    this.settings.mesh.visible = false;
    this.group.add(this.settings.mesh);
    this.setFrom = new THREE.Vector3();
    this.setAt = -1e9; this.setClosing = false;
    this.hovered = [];
    // module buttons: the ones with a VR version, in the theme's order (/api/hub)
    this.buttons = [];
    this.tab = new ModuleTab();
    this.tab.mesh.visible = false;
    this.tab.mesh.position.set(-0.62, 0.42, -1.35); // the stage adds it (it stays when the hub hides)
    this.tab.mesh.rotation.y = 0.4;
    this.menu = new PowerMenu(); // ⏻'s menu: the stage adds it (it shows over a module too)
    this.module = null; // {id, view}
    this.views = {};
  }

  /** The module buttons, from the hub's list (Training has no VR version). */
  setModules(ids) {
    for (const b of this.buttons) this.group.remove(b.mesh);
    const ids2 = (ids || []).filter((id) => VR_MODULES[id]);
    this.buttons = ids2.map((id) => new ModuleButton(id));
    const cols = { left: [], right: [] };
    this.buttons.forEach((b, i) => { b.side = i % 2 ? "right" : "left"; cols[b.side].push(b); });
    const paths = [];
    for (const [side, list] of Object.entries(cols)) {
      const s = side === "left" ? -1 : 1, gap = 0.07, total = list.length * 0.2 + (list.length - 1) * gap;
      list.forEach((b, i) => {
        const y = total / 2 - 0.1 - i * (0.2 + gap);
        onCurve(b.mesh, s * 20.5, y, R - 0.02);
        this.group.add(b.mesh);
        // a trace from the core's ring: out, a 45° bend, then into the button's inner edge
        const edge = b.mesh.position.clone().add(new THREE.Vector3(-s * (b.w / 2 + 0.005), 0, 0).applyEuler(b.mesh.rotation));
        const x0 = s * 0.56, x1 = s * 0.62, x2 = x1 + s * Math.abs(y) * 0.9;
        paths.push([new THREE.Vector3(x0, 0, -this.D), new THREE.Vector3(x1, 0, -this.D), new THREE.Vector3(x2, y, (edge.z - this.D) / 2), edge]);
      });
    }
    this.traces.setModules(paths);
  }

  get callout() { return this.callouts; }
  /** What the assistant may open here: the hub, the module buttons, the callouts' pages. */
  pagesHere() {
    const out = { hub: "the hub" };
    for (const b of this.buttons) out[b.id] = b.title;
    for (const c of Object.values(this.callouts)) out[c.id] = c.title;
    return out;
  }
  /** The assistant opened a page ("pull up teleop", "go back to the hub"): like pointing at it. */
  showPage(id, now) {
    const shown = this.mode === "module" ? this.module?.id : this.mode === "details" ? this.page.id : this.mode;
    if (shown === id) return;
    if (this.mode === "module") this.closeModule(now);
    else if (this.mode === "details") this.closeDetails(now);
    else if (this.mode === "settings") this.closeSettings(now);
    if (this.buttons.some((b) => b.id === id)) this.openModule(id, now);
    else if (this.callouts[id]) this.openDetails(this.callouts[id], now);
  }
  /** What the pointer can land on. */
  targets() {
    if (this.menu.mesh.visible) return [this.menu.mesh]; // ⏻'s menu: choose, or press beside it
    if (this.mode === "details") return [this.page.mesh, this.power.mesh];
    if (this.mode === "settings") return [this.settings.mesh, this.power.mesh];
    // Teleop has its own Back and Exit beside its status box (quick job 102), so no tab
    if (this.mode === "module") return [...(this.module?.id === "teleop" ? [] : [this.tab.mesh]), ...(this.module?.view.targets?.() || [])];
    return [...Object.values(this.callouts).map((c) => c.mesh), ...this.buttons.map((b) => b.mesh), this.power.mesh, this.gear.mesh, this.card.mesh, this.ask.mesh];
  }

  /** The startup is over: everything flies to its place and the panels unfold out from the core. */
  arrive(now, instant = false) {
    this.group.visible = true;
    this.t0 = instant ? now - 5000 : now;
    this.mode = "hub";
    this.page.mesh.visible = false;
    this.settings.mesh.visible = false;
    this.card.show(null);
    this.nextLog = now + 1500;
    this.logRows = [];
  }
  hide() { this.closeMenu(); this.closeModule(); this.group.visible = false; this.mode = "hub"; this.page.mesh.visible = false; this.settings.mesh.visible = false; }

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

  /** ⏻'s menu, opened beside the ⏻ that was pressed (the strip's, or a module tab's), facing you. */
  openMenu(from) {
    const p = new THREE.Vector3(), stage = this.group.parent;
    from.getWorldPosition(p); stage.worldToLocal(p);
    const toYou = p.clone().setY(0).normalize();
    p.addScaledVector(toYou, -0.25); // a little nearer than the button
    p.y -= this.menu.p.h / 2 + 0.1; // under it, so the button stays in view
    p.x -= Math.sign(p.x) * Math.min(0.6, Math.abs(p.x)); // and toward the middle
    this.menu.mesh.position.copy(p);
    this.menu.mesh.rotation.set(0, Math.atan2(-p.x, -p.z), 0);
    this.menu.mesh.visible = true;
  }
  closeMenu() { this.menu.mesh.visible = false; this.menu.hover = null; }
  /** What a press on `hit` does here. Returns "power" when the hub should go back to the start,
   *  "exit" when it should leave VR or AR (⏻'s menu). */
  press(hit, now) {
    if (this.menu.mesh.visible) { // the menu is open: an item, or a press beside it closes it
      this.closeMenu(); this.sfx.blip();
      const id = hit?.what.kind === "menu" ? hit.what.id : null;
      return id === "start" ? "power" : id === "exit" ? "exit" : null;
    }
    if (!hit) return null;
    const w = hit.what;
    if (w.kind === "power") { this.sfx.blip(); this.openMenu(hit.obj); return null; }
    if (w.kind === "settings") { this.openSettings(now); return null; }
    if (w.kind === "set") { this.sfx.blip(); this.settings.press(w); return null; }
    if (w.kind === "back") { if (this.mode === "module") this.closeModule(now); else if (this.mode === "settings") this.closeSettings(now); else this.closeDetails(now); return null; }
    if (w.kind === "module") { this.openModule(w.id, now); return null; }
    if (w.kind === "tele" || w.kind === "rasp") { this.sfx.blip(); this.module?.view.press?.(w); return null; } // Teleop's options, the Raspbot's bar
    if (w.kind === "stop") { this.module?.view.link?.send({ type: "stop" }); this.sfx.error(); return null; }
    if (w.kind === "tab" || w.kind === "ask") return null; // the ask line is held, not pressed
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
  openSettings(now) {
    this.mode = "settings";
    this.card.show(null);
    this.gear.mesh.getWorldPosition(this.setFrom);
    this.group.worldToLocal(this.setFrom);
    this.settings.mesh.visible = true;
    this.setAt = now; this.setClosing = false;
    this.settings.load();
    this.sfx.blip(); this.sfx.open();
  }
  closeSettings(now) {
    if (this.mode !== "settings") return;
    this.setClosing = true; this.setAt = now;
    this.mode = "hub";
    this.sfx.close();
  }
  closeDetails(now) {
    if (this.mode !== "details") return;
    this.pageClosing = true; this.pageAt = now;
    this.mode = "hub";
    this.sfx.close();
  }
  /** A module opens: the hub steps back, the module's view comes forward, the core docks small. */
  async openModule(id, now) {
    if (this.module) return;
    this.sfx.blip(); this.sfx.open();
    this.mode = "module";
    this.card.show(null);
    this.tab.title = VR_MODULES[id][0]; this.tab.ico = VR_MODULES[id][1];
    let view;
    if (id === "teleop") {
      // the teleop page's own session inside this one (quick job 97: as before 2026-11-21, PR #204)
      view = this.views.teleop ||= new TeleopModule({ ar: this.ar, refType: this.refType });
      this.module = { id, view, at: now };
      const scene = await view.open();
      if (this.module?.view !== view) return view.close(); // closed meanwhile
      this.module.scene = scene;
      this.scene.add(scene);
    } else {
      view = this.views[id] ||= id === "raspbot" ? new RaspbotModule() : new ArmHologram(id);
      if (id === "raspbot") {
        view.group.add(this.tab.mesh);
        this.tab.mesh.position.set(0, 0.46, 0);
        this.tab.mesh.rotation.y = 0;
      } else view.group.position.set(0, -0.62, -1.55);
      this.group.parent.add(view.group);
      view.open(now);
      this.module = { id, view, at: now };
    }
  }
  closeModule(now) {
    const m = this.module;
    if (!m) return;
    this.module = null;
    this.mode = "hub";
    if (m.scene) this.scene.remove(m.scene);
    if (m.id === "raspbot") {
      this.group.parent.add(this.tab.mesh);
      this.tab.mesh.position.set(-0.62, 0.42, -1.35);
      this.tab.mesh.rotation.y = 0.4;
    }
    if (m.view.group) m.view.group.parent?.remove(m.view.group);
    m.view.close();
    this.sfx.close();
    this.t0 = Math.min(this.t0, (now ?? 0) - 5000); // the hub comes straight back
  }
  /** B (or Y, but not while teleop uses Y) closes what's open. */
  back(now, key) {
    if (this.menu.mesh.visible) return this.closeMenu();
    if (this.mode === "module") { if (!(this.module.id === "teleop" && key === "left")) this.closeModule(now); }
    else if (this.mode === "settings") this.closeSettings(now);
    else this.closeDetails(now);
  }

  /** Where the core should be: in the middle, docked in the open page's corner, or small beside a module. */
  coreTarget() {
    if (this.mode === "module") return { pos: new THREE.Vector3(0.62, -0.42, -1.3), scale: 0.13 };
    const open = (this.page.mesh.visible && !this.pageClosing) || (this.settings.mesh.visible && !this.setClosing);
    // on the hub the core floats about 0.3 m in front of the panels, at the same size to the eye (quick job 158)
    const near = (this.D - CORE_AHEAD) / this.D;
    const t = open ? { pos: new THREE.Vector3(1.18, -0.66, -2.17), scale: 0.26 } : { pos: new THREE.Vector3(0, 0, -this.D * near), scale: near };
    // in the hub's own space, which is HUB_SCALE larger (quick job 60): the same place on the page
    t.pos.multiplyScalar(HUB_SCALE); t.pos.z += this.D * (HUB_SCALE - 1);
    t.scale *= HUB_SCALE;
    return t;
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
    this.tab.hover = null;
    this.settings.hover = null;
    this.menu.hover = null;
    for (const b of this.buttons) b.hover = false;
    let powerHover = false, askHover = false, gearHover = false;
    for (const h of hits) {
      const o = h.obj.userData.hit;
      if (o instanceof Callout) o.hover = h.what;
      else if (o === this.page) this.page.hover = h.what;
      else if (o === this.settings) this.settings.hover = h.what;
      else if (o === this.menu) this.menu.hover = h.what;
      else if (h.what.kind === "settings") gearHover = true;
      else if (o === this.tab) this.tab.hover = h.what;
      else if (h.what.kind === "module") o.hover = true;
      else if (h.what.kind === "power") powerHover = true;
      else if (h.what.kind === "ask") askHover = true;
    }
    // a module: the hub steps back (hidden), the module's view and its tab come forward
    if (this.menu.mesh.visible) this.menu.paint();
    const inModule = this.mode === "module";
    this.tab.mesh.visible = inModule && this.module?.id !== "teleop";
    if (inModule) {
      this.tab.paint();
      const v = this.module?.view;
      if (v?.step) v.step(dt, now, this.cameraPos || new THREE.Vector3(), hits);
      this.traces.group.visible = false;
      for (const o of this.group.children) o.visible = false;
      this.group.visible = true;
      return;
    }
    for (const o of this.group.children) if (o !== this.page.mesh && o !== this.settings.mesh) o.visible = true;
    const hoverKey = hits.map((h) => `${h.obj.id}:${h.what.kind}:${h.what.id || ""}`).join("|");
    if (hoverKey !== this._hoverKey) { if (hoverKey) this.sfx.hover(); this._hoverKey = hoverKey; }
    for (const c of Object.values(this.callouts)) c.paint(now);
    this._layout();
    // the panels unfold one after another, spreading out from the core (their delay grows with distance)
    const dim = this.mode === "details" || this.mode === "settings" || (this.page.mesh.visible && !this.pageClosing) || (this.settings.mesh.visible && !this.setClosing) ? 0.12 : 1;
    this._dim = (this._dim ?? 1) + (dim - (this._dim ?? 1)) * Math.min(1, dt * 8);
    for (const c of Object.values(this.callouts)) {
      const delay = 450 + (c === this.callouts.project || c === this.callouts.commits ? 380 : 470);
      const k = arrive((t - delay) / 600);
      c.corner.scale.set(Math.max(0.001, k), Math.max(0.001, k), 1);
      c.p.opacity = clamp((t - delay) / 300, 0, 1) * this._dim;
      c.back.opacity = c.p.opacity; // its fill, 4 cm behind (quick job 158)
    }
    const early = clamp((t - 300) / 600, 0, 1) * this._dim;
    this.buttons.forEach((b, i) => { // the buttons unfold after the core settles, nearest first
      const k = arrive((t - 600 - i * 60) / 600);
      b.mesh.scale.set(Math.max(0.001, k), Math.max(0.001, k), 1);
      b.p.opacity = clamp((t - 600 - i * 60) / 300, 0, 1) * this._dim;
      b.step(dt);
    });
    this.paintBrand(); this.brand.opacity = clamp((t - 900) / 300, 0, 1) * this._dim;
    this.paintStrip(now); this.strip.opacity = early;
    this.paintPower(powerHover); this.power.opacity = clamp((t - 300) / 600, 0, 1); // never dimmed: ⏻'s menu is on every page
    this.paintGear(gearHover); this.gear.opacity = early;
    this.stepLog(now); this.log.opacity = early;
    this.ask.step(now, askHover);
    this.ask.line.opacity = clamp((t - 700) / 400, 0, 1) * this._dim;
    if (this._dim < 1) this.ask.reply.opacity = Math.min(this.ask.reply.opacity, this._dim);
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
    // Settings: the same unfolding, from ⚙
    if (this.settings.mesh.visible) {
      const k = this.setClosing ? 1 - clamp((now - this.setAt) / 250, 0, 1) : arrive((now - this.setAt) / 600);
      this.settings.mesh.position.lerpVectors(this.setFrom, new THREE.Vector3(0, 0.02, -2.2), k);
      this.settings.mesh.scale.setScalar(Math.max(0.01, 0.2 + 0.8 * k));
      this.settings.p.opacity = this.setClosing ? k : clamp(k * 1.6, 0, 1);
      this.settings.paint(now);
      if (this.setClosing && k <= 0) { this.settings.mesh.visible = false; this.setClosing = false; }
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
    const wake = this.ask.wakeOn; // listening for the wake word: a small dot, separate from the core
    const key = JSON.stringify([items, clock, wake, wake && Math.floor(now / 250)]);
    this.strip.paint((g, w, h) => {
      g.textBaseline = "middle";
      // right to left: the clock, then the facts
      g.font = `${h * 0.42}px ${FONT.digits}`; g.textAlign = "right"; g.fillStyle = C.primary;
      g.fillText(clock, w - h * 0.2, h / 2);
      let x = w - h * 0.2 - g.measureText(clock).width - h * 0.75;
      if (wake) {
        g.fillStyle = rgba(C.primary, 0.15 + 0.35 * (0.5 + 0.5 * Math.cos((now / 4000) * Math.PI * 2)));
        g.beginPath(); g.arc(x - h * 0.1, h / 2, h * 0.09, 0, Math.PI * 2); g.fill();
        x -= h * 0.6;
      }
      g.font = `${FONT.linesW} ${h * 0.4}px ${FONT.lines}`;
      for (const [ico, text, ok] of items.reverse()) {
        const tw = g.measureText(text).width;
        g.fillStyle = ok ? C.text : C.offline; g.textAlign = "right"; g.fillText(text, x, h / 2);
        icon(g, ico, x - tw - h * 0.3, h / 2, h * 0.36, ok ? C.primary : C.offline, 1.6);
        x -= tw + h * 0.45 + h * 0.62;
      }
    }, key);
  }
  paintGear(hover) {
    this.gear.paint((g, w, h) => {
      if (hover) { g.fillStyle = rgba(C.primary, 0.16); g.fillRect(0, 0, w, h); g.strokeStyle = C.primary; g.lineWidth = 3; g.strokeRect(1.5, 1.5, w - 3, h - 3); }
      icon(g, "i-gear", w / 2, h / 2, w * 0.5, hover ? C.hot : C.dim, 1.8);
    }, hover);
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
  const hiMat = new THREE.LineBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, depthWrite: false, ...GLOW });
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
    this.pulseMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.hot), transparent: true, depthWrite: false, ...GLOW });
    this.pulses = [];
    this.next = 0;
    // up to the strip, down to the log: the hub's vertical line through the core
    this.base = [[new THREE.Vector3(0, 0.56, -D), new THREE.Vector3(0, 0.98, -D)], [new THREE.Vector3(0, -0.56, -D), new THREE.Vector3(0, -0.61, -D)]];
    this.set(this.base);
  }
  /** The traces to the module buttons (plus the vertical ones). */
  setModules(paths) { this.set(this.base, paths); }
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
