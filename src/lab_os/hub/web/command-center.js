// The Command Center (quick job 134; the spec: docs/design/command-center.md).
//
// Items: a *device* (a computer or screen with the hub open, by its device name, or a device of the live
// list: an arm, a camera, raspbot1, the Quest) and a *screen* (one hub window of a device: one per
// monitor). A device's monitors are grouped under it by themselves; a person can group a screen under
// another device, or put it on its own, by dragging it. That, the places and what is hidden is the
// workspace's layout: only the picture, kept by the brain, never a change to a device.
//
// Highlight and focus are different: a press highlights (Ctrl or Shift adds more), in the workspace and in
// the list on the left; ⤢ focuses one device in a modal with its screens, actions, modules and settings.
// The inspector on the right (quick job 148) shows the highlighted items: one item's details, settings,
// actions and modules; for several, only the actions that apply to every item, with the number of screens
// or devices they change. Real changes carry the cast mark; workspace-only ones are dashed.
//
// The Pages list (quick job 148) has a tile for each page that can open on another screen. Drag a tile onto
// a screen or a device (in the workspace or in the list on the left) to open it there, as Open on… does.
// The drag is one "carrier" with four steps (start, move, drop, cancel) at screen coordinates: the mouse and
// touch use it through pointer events, and a webcam hand can use it later (docs/plan/ideas.md → "Far future").
//
// Quick job 149: the workspace zooms to fit its items (until a person pans or zooms; Fit goes back to it), a
// device seen before but off now is a dim card that lights up when it connects, and the activity list under
// the devices shows what happened, newest first (the brain keeps it: /api/command-center/activity).
//
// The positions are plain 2D numbers in the workspace's own units, kept apart from the drawing, so a 3D
// view of the lab can use the same layout later (the spec's "keep the design open to 3D").

import { PAGE_GROUPS, VIEW_ICON } from "./page-groups.js";
import { playIntro } from "/hub/command-center-intro.js";
import { screenPreview, screenTitle as shows } from "/hub/screen-preview.js";

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ico = (id) => `<svg class="ico"><use href="/web/design/icons.svg#${id}"/></svg>`;
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const POLL_MS = 1500;
const SHOT_W = 160, GAP = 24;  // workspace units (px at zoom 1)
const KIND_ICON = { hub: "i-pc", arm: "i-arm", leader: "i-leader", camera: "i-cam", robot: "i-pi", headset: "i-headset", usb: "i-chip" };
const KIND_WORD = { hub: "Computer or screen", arm: "Arm", leader: "Leader arm", camera: "Camera", robot: "Robot", headset: "Headset", usb: "USB device" };
// the modules that match a kind of device (examples from the spec; only views the brain has are shown)
// (quick job 135: every device has Diagnostics, made to fit it: /diagnostics?show=<id>)
const KIND_MODULES = { hub: ["diagnostics"], arm: ["teleop", "ai", "diagnostics"], leader: ["teleop", "diagnostics"], robot: ["raspbot", "diagnostics"],
  camera: ["cameras", "diagnostics"], headset: ["teleop", "diagnostics"], usb: ["diagnostics"] };
// the Pages list: its groups, in order (a page in none goes in "Other"), the pages that cannot open on
// another screen, and the short names of the tiles (the full name is the tile's title)
const NOT_ELSEWHERE = new Set(["xr", "remote", "pages", "command"]);
// each page tile says the page's own title, as All Pages and the hub do (quick job 153: shorter names here
// made "Monitors" and "SO-101" of "Monitor" and "SO-101 Monitor")
// "This device" settings the modal can change (the rest stay in ⚙ → This device on that device)
const SETTINGS = [
  { key: "quality", label: "Level of detail", choices: [["", "Default"], ["maximal", "Maximal"], ["full", "Full"], ["reduced", "Reduced"], ["minimal", "Minimal"]] },
  { key: "voice", label: "Way in to voice", choices: [["", "Default"], ["push-to-talk", "Push-to-talk"], ["dictation", "Dictation"], ["wake word", "Wake word"]] },
  { key: "sound", label: "Sound", choices: [["", "Default"], ["on", "On"], ["off", "Off"]] },
];

const S = {
  hub: [], live: [], views: [], drive: new Set(), events: [], seenEvent: 0, wasOff: new Set(),
  layout: { places: {}, hidden: [], groups: {} },
  sel: new Set(), search: "", pageSearch: "", page: "", group: "",
  view: { x: 40, y: 40, z: 1 }, autoFit: true, fitKey: "", drag: null, msg: "", msgBad: false, last: "",
};

// ---------- the brain ----------
async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}
async function postJSON(url, body) {
  try {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const ct = r.headers.get("Content-Type") || "";
    return ct.includes("json") ? r.json() : { ok: false, message: await r.text() };
  } catch (e) {
    return { ok: false, message: `The brain didn't answer (${e.message}).` };
  }
}
let saveTimer = 0;
function saveLayout() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    const r = await postJSON("/api/command-center/layout", S.layout);
    if (!r.ok) say(`The layout was not kept: ${r.message}`, true);
  }, 400);
}
function say(text, bad = false) {
  S.msg = text; S.msgBad = bad;
  renderInspector(true);
}

// ---------- the items ----------
function devices() {
  const out = [];
  for (const d of S.hub) {
    out.push({
      key: `d:${d.name}`, kind: "hub", id: d.name, title: d.named ? (d.display_name || d.name) : d.title,
      sub: d.named && d.display_name && d.display_name !== d.name ? d.name : "", named: d.named, address: d.address, here: d.here,
      what: d.here ? "The brain's own computer." : `At ${d.address || "an unknown address"}.`, hub: d,
    });
  }
  for (const d of S.live) {
    if (!d.connected || d.kind === "screen") continue;  // the screens are the hub's devices above
    const kind = d.leader ? "leader" : KIND_ICON[d.kind] ? d.kind : "usb";
    out.push({ key: `l:${d.id}`, kind, id: d.id, title: d.name || d.id, sub: "", what: d.problem || d.what || "", bad: !!d.problem, live: d });
  }
  // seen before, off now (quick job 149): a dim card under the same key, so it lights up in its place
  const have = new Set(out.map((d) => d.key));
  for (const d of S.live) {
    if (d.connected) continue;
    const screen = d.kind === "screen";
    const key = screen ? `d:${String(d.id).slice("screen:".length)}` : `l:${d.id}`;
    if (have.has(key)) continue;
    const kind = screen ? "hub" : d.leader ? "leader" : KIND_ICON[d.kind] ? d.kind : "usb";
    out.push({ key, kind, id: screen ? key.slice(2) : d.id, title: d.name || d.id, sub: "", what: "", gone: true, lastSeen: d.last_seen || "", live: d });
  }
  return out;
}
function screens(devs) {
  const keys = new Set(devs.map((d) => d.key));
  const out = [];
  for (const d of S.hub) {
    d.windows.forEach((w, i) => {
      const key = `s:${d.name}#${i + 1}`;
      const want = S.layout.groups[key];
      const group = want && (want === key || keys.has(want)) ? want : `d:${d.name}`;
      out.push({ key, device: d, w, n: i + 1, count: d.windows.length, group });
    });
  }
  return out;
}
const isHidden = (key) => S.layout.hidden.includes(key);
const viewTitle = (id) => S.views.find((v) => v.id === id)?.title || id;
const devTitle = (d) => (d.named ? (d.display_name || d.name) : d.title);
function resolution(w) {
  const s = w.screen || {}, r = s.ratio || 1;
  return s.width ? `${Math.round(s.width * r)} × ${Math.round(s.height * r)}` : "";
}
function matches(text) {
  const want = S.search.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const have = text.toLowerCase();
  return want.every((w) => have.includes(w));
}
const devText = (d) => `${d.title} ${d.id} ${d.sub} ${d.what} ${KIND_WORD[d.kind]}`;
const scrText = (s) => `${devTitle(s.device)} ${s.device.name} screen ${s.n} ${shows(s.w)}`;

// the screens a highlighted item stands for (a device: the screens grouped under it) and the hub
// devices it stands for (for the teleop permission)
function screensOf(key, scr) {
  if (key.startsWith("s:")) return scr.filter((s) => s.key === key);
  return scr.filter((s) => s.group === key);
}
function hubOf(key, devs, scr) {
  if (key.startsWith("s:")) {
    const s = scr.find((x) => x.key === key);
    return s ? devs.find((d) => d.key === `d:${s.device.name}`) : null;
  }
  return devs.find((d) => d.key === key && d.kind === "hub") || null;
}
const mayDrive = (d) => d.here || (d.address && S.drive.has(d.address));

// ---------- drawing: the preview of a screen ----------
function under(s) {
  const d = s.device, title = devTitle(d), sub = d.named && d.display_name && d.display_name !== d.name ? d.name : "";
  const name = s.count > 1 ? `<span>Screen ${s.n}</span>` : "";
  const res = resolution(s.w);
  return `<div class="under"><b>${esc(title)}${sub ? `<small>${esc(sub)}</small>` : ""}</b>${name}${res ? `<span class="res num">${res}</span>` : ""}</div>`;
}

// ---------- the list on the left: each device, with the screens grouped under it ----------
function eye(key) {
  const off = isHidden(key);
  return `<button class="iconbtn eye${off ? "" : " on"}" type="button" title="${off ? "Show in the workspace" : "Hide from the workspace"}">${ico(off ? "i-eye-off" : "i-eye")}</button>`;
}
function devRow(d) {
  const r = document.createElement("div");
  r.className = `row${S.sel.has(d.key) ? " sel" : ""}${isHidden(d.key) ? " off" : ""}${d.gone ? " gone" : ""}${lit(d) ? " lit" : ""}`;
  r.tabIndex = 0;
  r.dataset.key = d.key;
  const drive = d.kind === "hub" && !d.gone && mayDrive(d) ? ` ${ico("i-hand")}` : "";
  r.innerHTML = `<span class="k">${ico(KIND_ICON[d.kind])}</span><b title="${esc(d.title)}">${esc(d.title)}${drive}</b>${eye(d.key)}`
    + (d.gone ? "" : `<button class="iconbtn foc" type="button" title="Focus: its screens, actions and modules">${ico("i-open")}</button>`)
    + `<small>${esc(d.sub || KIND_WORD[d.kind])}</small>`;
  return r;
}
function scrRow(s, under) {
  // under its own device: "Screen 2" (or what it shows, when the device has one screen); elsewhere: its device too
  const n = s.count > 1 ? `Screen ${s.n}` : "";
  const own = s.group === `d:${s.device.name}`;
  const name = own ? n || shows(s.w) : `${devTitle(s.device)}${n ? ` ${n}` : ""}`;
  const r = document.createElement("div");
  r.className = `row${under ? " scr" : ""}${S.sel.has(s.key) ? " sel" : ""}${isHidden(s.key) ? " off" : ""}`;
  r.tabIndex = 0;
  r.dataset.key = s.key;
  const sub = own && !n ? resolution(s.w) || "Screen" : shows(s.w);
  // under its device: one line, "Screen 2, Teleop" (quick job 161: compact)
  r.innerHTML = `<span class="k">${ico(VIEW_ICON[s.w.showing?.id] || "i-screen")}</span>`
    + (under ? `<b title="${esc(`${name}, ${sub}`)}">${esc(name)}<span class="sub">, ${esc(sub)}</span></b>` : `<b title="${esc(name)}">${esc(name)}</b>`)
    + eye(s.key)
    + `<button class="iconbtn foc" type="button" title="Focus: its device's screens, actions and modules">${ico("i-open")}</button>`
    + (under ? "" : `<small>${esc(sub)}</small>`);
  return r;
}
function renderLists(devs, scr) {
  const dl = $("#devices");
  dl.innerHTML = "";
  const lone = scr.filter((s) => s.group === s.key);
  // the same order as the workspace: screens' devices, screens on their own, the other devices
  for (const item of itemOrder(devs, lone)) {
    if (item.device) { if (matches(scrText(item))) dl.append(scrRow(item, false)); continue; }
    const mine = scr.filter((s) => s.group === item.key && s.key !== s.group && matches(scrText(s)));
    if (!mine.length && !matches(devText(item))) continue;
    if (!mine.length) { dl.append(devRow(item)); continue; }
    // a device and its screens in one group: a line joins the device to each screen (quick job 161)
    const g = document.createElement("div");
    g.className = "dgrp";
    g.append(devRow(item), ...mine.map((s) => scrRow(s, true)));
    dl.append(g);
  }
  if (!dl.children.length) dl.innerHTML = `<div class="empty">${devs.length ? "No device or screen matches the search." : "No device is connected."}</div>`;
  $("#dev-count").textContent = `${plural(devs.length, "device")}, ${plural(scr.length, "screen")}`;
  $("#show-all").hidden = !S.layout.hidden.length;
}

// ---------- the Pages list ----------
function pages() {
  const views = [{ id: "hub", title: "The Hub" }, ...S.views].filter((v) => !NOT_ELSEWHERE.has(v.id));
  const groups = PAGE_GROUPS.map(([name, ids]) => [name, ids.map((id) => views.find((v) => v.id === id)).filter(Boolean)]);
  const known = new Set(PAGE_GROUPS.flatMap(([, ids]) => ids));
  groups.push(["Other", views.filter((v) => !known.has(v.id))]);
  return groups.filter(([, vs]) => vs.length);
}
function pageFade() {
  const list = $("#pages");
  list.classList.toggle("more", list.scrollHeight > list.clientHeight + list.scrollTop + 2);
}
$("#pages").addEventListener("scroll", pageFade);
new ResizeObserver(pageFade).observe($("#pages"));
function renderPages() {
  const box = $("#pages"), want = S.pageSearch.trim().toLowerCase();
  box.innerHTML = "";
  for (const [name, vs] of pages()) {
    const shown = vs.filter((v) => !want || `${v.title} ${name}`.toLowerCase().includes(want));
    if (!shown.length) continue;
    box.insertAdjacentHTML("beforeend", `<div class="grp">${esc(name)}</div>`);
    const tiles = document.createElement("div");
    tiles.className = "tiles";
    for (const v of shown) {
      tiles.insertAdjacentHTML("beforeend", `<div class="tile${v.id === S.page ? " on" : ""}" tabindex="0" role="button" data-view="${esc(v.id)}"`
        + ` title="${esc(v.title)}: drag it onto a screen or a device to open it there">${ico(VIEW_ICON[v.id] || "i-test")}<span>${esc(v.title)}</span></div>`);
    }
    box.append(tiles);
  }
  if (!box.children.length) box.innerHTML = `<div class="empty">No page matches the search.</div>`;
  pageFade();
}
function choosePage(id) {
  S.page = S.page === id ? "" : id;
  renderPages();
  renderInspector(true);
}
const SHUT_KEY = "lab-os-command-center-pages-shut";
function shutPages(shut) {
  $("#pages-card").classList.toggle("shut", shut);
  $("#pages-shut").setAttribute("aria-expanded", String(!shut));
  try { localStorage.setItem(SHUT_KEY, shut ? "1" : ""); } catch { /* private mode: not kept */ }
}
$("#pages-shut").addEventListener("click", () => shutPages(!$("#pages-card").classList.contains("shut")));
$("#page-search").addEventListener("input", (e) => { S.pageSearch = e.target.value; renderPages(); });
try { shutPages(!!localStorage.getItem(SHUT_KEY)); } catch { /* not kept */ }

// ---------- drag a page onto a screen or a device: one carrier for every kind of pointer ----------
// start(view, x, y) lifts a page, move(x, y) follows the pointer and marks the target under it, drop(x, y)
// opens the page there (as Open on… does), cancel() puts it back. x and y are screen coordinates, so a
// webcam hand (hover, close the hand, move, open the hand) can call the same steps later.
function dropTargetAt(x, y) {
  for (const el of document.elementsFromPoint(x, y)) {
    const t = el.closest?.("#stage .shot, #stage .node, #devices .row");
    if (t) return t;
  }
  return null;
}
const carry = {
  view: "", ghost: null, over: null,
  start(view, x, y) {
    this.cancel();
    this.view = view;
    const v = pages().flatMap(([, vs]) => vs).find((p) => p.id === view);
    this.ghost = document.createElement("div");
    this.ghost.className = "tile ghost";
    this.ghost.innerHTML = `${ico(VIEW_ICON[view] || "i-test")}<span>${esc(v?.title || view)}</span>`;
    document.body.append(this.ghost);
    this.move(x, y);
  },
  move(x, y) {
    if (!this.view) return;
    this.ghost.style.left = `${x + 8}px`; this.ghost.style.top = `${y + 8}px`;
    const t = dropTargetAt(x, y);
    if (t !== this.over) { this.over?.classList.remove("drop"); t?.classList.add("drop"); this.over = t; }
  },
  drop(x, y) {
    const view = this.view, t = this.view ? dropTargetAt(x, y) : null;
    this.cancel();
    if (view && t) openPageOn(view, t.dataset.key);
  },
  cancel() {
    this.over?.classList.remove("drop");
    this.ghost?.remove();
    this.view = ""; this.ghost = null; this.over = null;
  },
};
// the mouse and touch: a press and a move of a few pixels lifts the page; a press alone chooses it
let press = null;
$("#pages").addEventListener("pointerdown", (e) => {
  const tile = e.target.closest(".tile");
  if (!tile || e.button !== 0) return;
  press = { view: tile.dataset.view, sx: e.clientX, sy: e.clientY, id: e.pointerId, moved: false };
  tile.setPointerCapture(e.pointerId);
});
$("#pages").addEventListener("pointermove", (e) => {
  if (!press || e.pointerId !== press.id) return;
  if (matchMedia("(max-width: 1100px)").matches) return; // the other panels are behind their tabs
  if (!press.moved && Math.hypot(e.clientX - press.sx, e.clientY - press.sy) < 6) return;
  if (!press.moved) { press.moved = true; carry.start(press.view, e.clientX, e.clientY); } else carry.move(e.clientX, e.clientY);
});
$("#pages").addEventListener("pointerup", (e) => {
  if (!press || e.pointerId !== press.id) return;
  const p = press;
  press = null;
  if (p.moved) carry.drop(e.clientX, e.clientY);
  else choosePage(p.view);
});
$("#pages").addEventListener("pointercancel", () => { press = null; carry.cancel(); });
$("#pages").addEventListener("keydown", (e) => {
  const tile = e.target.closest(".tile");
  if (tile && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); choosePage(tile.dataset.view); }
});
// a page dropped on an item: on its screens (a device: the screens grouped under it)
function openPageOn(view, key) {
  const devs = devices(), scr = screens(devs);
  const targets = screensOf(key, scr);
  const name = key.startsWith("s:") ? "That screen" : devs.find((d) => d.key === key)?.title || "That device";
  if (!targets.length) return say(`${name} has no screen with the hub open.`, true);
  return view === "hub" ? backToHub(targets) : openOn(targets, view);
}

// ---------- the workspace ----------
function placeNew(els) {
  const stage = $("#stage");
  const active = [...stage.children].filter((el) => !el.classList.contains("gone"));
  const placed = active.filter((el) => !els.includes(el));
  const rowWidth = Math.max(340, $("#ws").clientWidth - 60);
  let x = 0, y = placed.length ? Math.max(...placed.map((el) => el.offsetTop + el.offsetHeight)) + GAP : 0;
  let height = 0;
  function put(el) {
    if (x && x + el.offsetWidth > rowWidth) { x = 0; y += height + GAP; height = 0; }
    el.style.left = `${x}px`; el.style.top = `${y}px`;
    S.layout.places[el.dataset.key] = [x, y];
    x += el.offsetWidth + GAP;
    height = Math.max(height, el.offsetHeight);
  }
  for (const el of active) if (els.includes(el)) put(el);
  x = 0;
  y = active.length ? Math.max(...active.map((el) => el.offsetTop + el.offsetHeight)) + GAP : 0;
  height = 0;
  for (const el of stage.querySelectorAll(".gone")) put(el);
  if (els.length) saveLayout();
}
// screens' devices first, then screens on their own, then the other devices, then the ones off now (the
// order new ones get places in, and the list's order)
function itemOrder(devs, lone) {
  const on = devs.filter((d) => !d.gone);
  return [...on.filter((d) => d.kind === "hub"), ...lone, ...on.filter((d) => d.kind !== "hub"), ...devs.filter((d) => d.gone)];
}
// an item that was off a moment ago and is connected now lights up once
const lit = (d) => !d.gone && S.wasOff.has(d.key);
function renderWorkspace(devs, scr) {
  const stage = $("#stage");
  const lone = scr.filter((s) => s.group === s.key);
  stage.innerHTML = "";
  const fresh = [];
  const put = (el, key) => {
    el.tabIndex = 0;
    const at = S.layout.places[key];
    if (at && !(S.wasOff.has(key) && !el.classList.contains("gone"))) { el.style.left = `${at[0]}px`; el.style.top = `${at[1]}px`; } else fresh.push(el);
    stage.append(el);
  };
  for (const item of itemOrder(devs, lone)) {
    if (isHidden(item.key)) continue;
    if (item.device) {  // a screen on its own
      const el = document.createElement("div");
      el.className = `node lone${S.sel.has(item.key) ? " sel" : ""}${matches(scrText(item)) ? "" : " dim"}`;
      el.dataset.key = item.key;
      el.append(shotEl(item));
      put(el, item.key);
      continue;
    }
    const d = item;
    const el = document.createElement("div");
    el.className = `node${S.sel.has(d.key) ? " sel" : ""}${matches(devText(d)) ? "" : " dim"}${d.gone ? " gone" : ""}${lit(d) ? " lit" : ""}`;
    el.dataset.key = d.key;
    const mine = scr.filter((s) => s.group === d.key && !isHidden(s.key));
    const drive = d.kind === "hub" && !d.gone && mayDrive(d) ? `<span class="k" title="May drive a real arm">${ico("i-hand")}</span>` : "";
    el.innerHTML = `<div class="head"><span class="k">${ico(KIND_ICON[d.kind])}</span><b>${esc(d.title)}</b>${d.sub ? `<small>${esc(d.sub)}</small>` : ""}${drive}<span class="grow"></span>`
      + (d.gone ? "" : `<button class="iconbtn more" type="button" title="Settings and actions">⋯</button>`
        + `<button class="iconbtn foc" type="button" title="Focus: its screens, actions and modules">${ico("i-open")}</button>`) + `</div>`
      + (mine.length || d.gone ? "" : `<div class="what${d.bad ? " bad" : ""}">${esc(d.what || KIND_WORD[d.kind])}</div>`);
    if (mine.length) {
      const row = document.createElement("div");
      row.className = "shots";
      for (const s of mine) row.append(shotEl(s));
      el.append(row);
    }
    put(el, d.key);
  }
  placeNew(fresh);
  applyView();
}
function shotEl(s) {
  const el = document.createElement("div");
  el.className = `shot${S.sel.has(s.key) ? " sel" : ""}${matches(scrText(s)) ? "" : " dim"}`;
  el.tabIndex = 0;
  el.dataset.key = s.key;
  el.innerHTML = screenPreview(s.w, SHOT_W) + under(s);
  return el;
}
function applyView() {
  $("#stage").style.transform = `translate(${S.view.x}px, ${S.view.y}px) scale(${S.view.z})`;
}
function fit() {
  const nodes = [...$("#stage").children];
  if (!nodes.length || !$("#ws").clientWidth) return;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const n of nodes) {
    const x = n.offsetLeft, y = n.offsetTop;
    x0 = Math.min(x0, x); y0 = Math.min(y0, y);
    x1 = Math.max(x1, x + n.offsetWidth); y1 = Math.max(y1, y + n.offsetHeight);
  }
  const ws = $("#ws").getBoundingClientRect(), pad = 30;
  // Keep previews at their native size when the workspace has room.
  const z = Math.max(0.02, Math.min(1, (ws.width - 2 * pad) / (x1 - x0), (ws.height - 2 * pad) / (y1 - y0)));
  S.view = { z, x: pad - x0 * z + Math.max(0, (ws.width - 2 * pad - (x1 - x0) * z) / 2), y: pad - y0 * z + Math.max(0, (ws.height - 2 * pad - (y1 - y0) * z) / 2) };
  applyView();
}
// fit again when items come or go, or the workspace changes size, until a person pans or zooms
function autoFit(force = false) {
  const r = $("#ws").getBoundingClientRect();
  const key = `${[...$("#stage").children].map((n) => n.dataset.key).join(" ")}|${Math.round(r.width)}x${Math.round(r.height)}`;
  if (!force && (!S.autoFit || key === S.fitKey)) return;
  S.fitKey = key;
  fit();
}
new ResizeObserver(() => autoFit()).observe($("#ws"));

// ---------- highlight, drag, pan, zoom ----------
let multi = false;
for (const control of document.querySelectorAll("#multi, .multi")) control.onclick = () => {
  multi = !multi;
  for (const b of document.querySelectorAll("#multi, .multi")) {
    b.setAttribute("aria-pressed", String(multi));
    b.textContent = multi ? "Selecting multiple: On" : "Select multiple";
  }
  $("#ws").classList.toggle("multi-on", multi);
};
$(".cc-tabs").onclick = (event) => {
  const tab = event.target.closest("button");
  if (!tab) return;
  $(".cc").dataset.panel = tab.textContent;
  for (const b of $(".cc-tabs").children) b.setAttribute("aria-pressed", String(b === tab));
  if (tab.textContent === "Pages") shutPages(false);
  render(true);
};
function pick(key, add) {
  if (add || multi) S.sel.has(key) ? S.sel.delete(key) : S.sel.add(key);
  else if (S.sel.size === 1 && S.sel.has(key)) S.sel.clear();
  else S.sel = new Set([key]);
  S.msg = "";
  render(true);
}
function wsPoint(e) {
  const r = $("#ws").getBoundingClientRect();
  return { x: (e.clientX - r.left - S.view.x) / S.view.z, y: (e.clientY - r.top - S.view.y) / S.view.z };
}
function nodeUnder(e, not) {
  for (const el of document.elementsFromPoint(e.clientX, e.clientY)) {
    const n = el.closest?.(".node");
    if (n && n.dataset.key !== not && !n.classList.contains("lone")) return n;
  }
  return null;
}
$("#ws").addEventListener("pointerdown", (e) => {
  if (e.button !== 0 || e.target.closest("button")) return;
  const shot = e.target.closest(".shot"), node = e.target.closest(".node");
  const p = wsPoint(e);
  if (shot && !node?.classList.contains("lone")) {
    S.drag = { kind: "shot", key: shot.dataset.key, sx: e.clientX, sy: e.clientY, moved: false, el: shot, add: e.ctrlKey || e.metaKey || e.shiftKey };
  } else if (node) {
    const [x, y] = S.layout.places[node.dataset.key] || [0, 0];
    S.drag = { kind: "node", key: node.dataset.key, sx: e.clientX, sy: e.clientY, ox: x - p.x, oy: y - p.y, moved: false, el: node, add: e.ctrlKey || e.metaKey || e.shiftKey, lone: node.classList.contains("lone") };
  } else {
    S.drag = { kind: "pan", sx: e.clientX, sy: e.clientY, vx: S.view.x, vy: S.view.y, moved: false };
    $("#ws").classList.add("panning");
  }
  $("#ws").setPointerCapture(e.pointerId);
});
$("#ws").addEventListener("pointermove", (e) => {
  const d = S.drag;
  if (!d) return;
  if (!d.moved && Math.hypot(e.clientX - d.sx, e.clientY - d.sy) < 5) return;
  d.moved = true;
  if (d.kind === "pan") {
    S.autoFit = false;
    S.view.x = d.vx + e.clientX - d.sx; S.view.y = d.vy + e.clientY - d.sy;
    applyView();
  } else if (d.kind === "node") {
    const p = wsPoint(e);
    S.layout.places[d.key] = [Math.round(p.x + d.ox), Math.round(p.y + d.oy)];
    d.el.style.left = `${S.layout.places[d.key][0]}px`; d.el.style.top = `${S.layout.places[d.key][1]}px`;
    if (d.lone) markDrop(nodeUnder(e, d.key));
  } else {
    if (!d.ghost) {
      d.ghost = d.el.cloneNode(true);
      d.ghost.classList.add("ghost");
      d.ghost.style.width = `${d.el.getBoundingClientRect().width}px`;
      document.body.append(d.ghost);
      d.el.style.opacity = "0.3";
    }
    d.ghost.style.left = `${e.clientX - 20}px`; d.ghost.style.top = `${e.clientY - 20}px`;
    markDrop(nodeUnder(e, null));
  }
});
function markDrop(n) {
  document.querySelectorAll(".node.drop").forEach((x) => x !== n && x.classList.remove("drop"));
  n?.classList.add("drop");
}
$("#ws").addEventListener("pointerup", (e) => {
  const d = S.drag;
  S.drag = null;
  $("#ws").classList.remove("panning");
  markDrop(null);
  if (!d) return;
  if (!d.moved) {
    if (d.kind === "pan") { if (S.sel.size) { S.sel.clear(); S.msg = ""; render(true); } return; }
    return pick(d.key, d.add);
  }
  if (d.kind === "node") {
    const target = d.lone ? nodeUnder(e, d.key) : null;
    if (target) groupUnder([d.key], target.dataset.key);
    saveLayout();
    return render(true);
  }
  if (d.kind === "shot") {
    d.ghost?.remove();
    const target = nodeUnder(e, null);
    if (target) groupUnder([d.key], target.dataset.key);
    else {  // on its own, where it was dropped
      const p = wsPoint(e);
      S.layout.groups[d.key] = d.key;
      S.layout.places[d.key] = [Math.round(p.x - 20), Math.round(p.y - 20)];
    }
    saveLayout();
    render(true);
  }
});
$("#ws").addEventListener("wheel", (e) => {
  e.preventDefault();
  const r = $("#ws").getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  S.autoFit = false;
  const z = Math.max(0.2, Math.min(2.6, S.view.z * Math.exp(-e.deltaY * 0.0015)));
  S.view.x = mx - ((mx - S.view.x) * z) / S.view.z;
  S.view.y = my - ((my - S.view.y) * z) / S.view.z;
  S.view.z = z;
  applyView();
}, { passive: false });
$("#ws").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  const key = e.target.closest("[data-key]")?.dataset.key;
  if (!b || !key) return;
  const node = e.target.closest(".node")?.dataset.key || key;
  if (b.classList.contains("foc")) focus(node);
  else if (b.classList.contains("more")) openMenu(node, b);
});
$("#devices").addEventListener("click", (e) => {
  const row = e.target.closest(".row");
  if (!row) return;
  const key = row.dataset.key;
  if (e.target.closest(".eye")) return hide([key], !isHidden(key));
  if (e.target.closest(".foc")) return focus(key.startsWith("s:") ? `d:${key.slice(2).split("#")[0]}` : key);
  pick(key, e.ctrlKey || e.metaKey || e.shiftKey);
});
$(".cc").addEventListener("keydown", (e) => {
  if (!e.target.matches("[data-key]") || !["Enter", " "].includes(e.key)) return;
  e.preventDefault();
  const selector = e.target.closest("#devices") ? "#devices" : "#stage";
  const key = e.target.dataset.key;
  pick(key, e.ctrlKey || e.metaKey || e.shiftKey);
  $(selector).querySelector(`[data-key="${CSS.escape(key)}"]`)?.focus();
});
$("#search").addEventListener("input", (e) => { S.search = e.target.value; render(true); });
$("#fit").addEventListener("click", () => { placeNew([...$("#stage").children]); S.autoFit = true; autoFit(true); });
$("#show-all").addEventListener("click", () => { S.layout.hidden = []; saveLayout(); render(true); });

// ---------- workspace-only changes ----------
function hide(keys, yes) {
  const set = new Set(S.layout.hidden);
  for (const k of keys) yes ? set.add(k) : set.delete(k);
  S.layout.hidden = [...set];
  if (yes) keys.forEach((k) => S.sel.delete(k));
  saveLayout();
  render(true);
}
function groupUnder(keys, target) {
  for (const k of keys) {
    if (!k.startsWith("s:")) continue;
    const own = `d:${k.slice(2).split("#")[0]}`;
    if (target === own) delete S.layout.groups[k];
    else S.layout.groups[k] = target;
    delete S.layout.places[k];
  }
}

// ---------- real changes ----------
async function openOn(targets, view) {
  if (!view) return say("Choose a page first: press it in Pages, or drag it onto a screen.", true);
  if (view === "hub") return backToHub(targets);
  const said = [];
  for (const s of targets) {
    const r = await postJSON("/api/hub-devices/open", { module: view, device: s.device.name, window: s.w.id, from: "the Command Center" });
    if (!r.ok) said.push(`${devTitle(s.device)}: ${r.message}`);
  }
  await refresh();
  say(said.length ? said.join(" ") : `${viewTitle(view)} is open on ${plural(targets.length, "screen")}.`, !!said.length);
}
async function backToHub(targets) {
  if (!targets.some((t) => t.w.showing)) return say(`${plural(targets.length, "screen")} already ${targets.length === 1 ? "shows" : "show"} the hub.`);
  const said = [];
  for (const s of targets.filter((t) => t.w.showing)) {
    const r = await postJSON("/api/hub-devices/close", { device: s.device.name, window: s.w.id });
    if (!r.ok) said.push(`${devTitle(s.device)}: ${r.message}`);
  }
  await refresh();
  say(said.length ? said.join(" ") : `Back to the hub on ${plural(targets.length, "screen")}.`, !!said.length);
}
// one start for every start screen (quick job 139): all of them, or the highlighted ones
async function startScreens(targets = null) {
  const r = await postJSON("/api/hub-devices/start", targets ? { windows: targets.map((s) => s.w.id) } : {});
  await refresh();
  say(r.message || "It did not start.", !r.ok);
}
$("#start-all").addEventListener("click", () => startScreens());
async function setDrive(hubs, allowed) {
  const addresses = [...new Set(hubs.filter((d) => !d.here && d.address).map((d) => d.address))];
  const r = await postJSON("/api/command-center/drive", { addresses, allowed });
  if (!r.ok) return say(r.message, true);
  S.drive = new Set(r.drive_from);
  say(`${plural(hubs.length, "device")} ${allowed ? "may" : "may not"} drive a real arm now. Its Teleop page checks this when it opens.`);
  render(true);
}

// ---------- the actions for some items: only the ones that apply to every item ----------
function actionsFor(keys, devs, scr) {
  const acts = [];
  const targets = [], seen = new Set();
  let allScreens = true;
  for (const k of keys) {
    const mine = screensOf(k, scr);
    if (!mine.length) allScreens = false;
    for (const s of mine) if (!seen.has(s.key)) { seen.add(s.key); targets.push(s); }
  }
  if (allScreens && targets.length) {
    const one = targets.length === 1, n = plural(targets.length, "screen");
    acts.push({ kind: "page", real: true, label: one ? "Open" : `Open on ${n}`, title: "Open the chosen page there (or drag a page onto it)", run: (view) => openOn(targets, view) });
    const busy = targets.filter((t) => t.w.showing), m = plural(busy.length, "screen");
    if (busy.length) acts.push({ real: true, icon: "i-back", label: one ? "Back to the hub" : `Hub on ${m}`, title: `Close what ${m} show: back to the hub`, run: () => backToHub(busy) });
    const waiting = targets.filter((t) => t.w.stage === "start"), st = plural(waiting.length, "screen");
    if (waiting.length) acts.push({ real: true, icon: "i-power", label: one ? "Start" : `Start ${st}`, title: `Start the start screen on ${st}`, run: () => startScreens(waiting) });
  }
  const hubs = [...new Map(keys.map((k) => hubOf(k, devs, scr)).map((d) => [d?.key, d])).values()];
  if (hubs.length && hubs.every((d) => d && !d.here && d.address)) {
    const all = hubs.every(mayDrive), n = plural(hubs.length, "device");
    acts.push({ real: true, icon: "i-hand", label: all ? `Stop driving (${n})` : `Allow driving (${n})`,
      title: all ? "These devices may not drive a real arm any more" : "These devices may drive a real arm (Teleop, Raspbot)", run: () => setDrive(hubs, !all) });
  }
  if (keys.every((k) => k.startsWith("s:"))) {
    acts.push({ kind: "group", label: "Group under", run: (target) => { groupUnder(keys, target); saveLayout(); render(true); } });
    if (keys.some((k) => S.layout.groups[k])) acts.push({ label: "Ungroup", title: "Back under its own device", run: () => { keys.forEach((k) => { delete S.layout.groups[k]; delete S.layout.places[k]; }); saveLayout(); render(true); } });
  }
  acts.push({ label: keys.length > 1 ? `Hide ${keys.length}` : "Hide", title: "Hide from the workspace (the device does not change)", run: () => hide(keys, true) });
  return acts;
}
function pageSelect() {
  const opts = pages().flatMap(([, vs]) => vs).map((v) => `<option value="${esc(v.id)}"${v.id === S.page ? " selected" : ""}>${esc(v.title)}</option>`);
  return `<select aria-label="Page"><option value="">Choose a page…</option>${opts.join("")}</select>`;
}
function groupSelect(devs) {
  const opts = devs.filter((d) => !isHidden(d.key)).map((d) => `<option value="${esc(d.key)}"${d.key === S.group ? " selected" : ""}>${esc(d.title)}</option>`);
  return `<select aria-label="Device to group under"><option value="">Choose a device…</option>${opts.join("")}</select>`;
}
function actButtons(box, acts, devs, after = () => {}) {
  for (const a of acts) {
    const wrap = document.createElement("span");
    wrap.style.display = "contents";
    if ((a.kind === "page" && !box.closest("#insp")) || a.kind === "group") {
      wrap.innerHTML = a.kind === "page" ? pageSelect() : groupSelect(devs);
      const sel = wrap.querySelector("select");
      sel.addEventListener("change", () => {
        if (a.kind === "page") { S.page = sel.value; renderPages(); } else S.group = sel.value;
      });
    }
    const b = document.createElement("button");
    b.type = "button";
    b.className = `btn small${a.real ? "" : " virtual"}`;
    b.innerHTML = `${a.real ? ico("i-cast") : ""}${a.icon && !a.real ? ico(a.icon) : ""}${esc(a.label)}`;
    if (a.title) b.title = a.title;
    b.addEventListener("click", () => {
      const sel = wrap.querySelector("select");
      if (a.kind === "group" && !sel.value) return say("Choose a device first.", true);
      a.run(sel?.value ?? S.page);
      after();
    });
    wrap.append(b);
    box.append(wrap);
  }
}
// ---------- the inspector: the highlighted items' details, settings, actions and modules ----------
const factsHTML = (rows) => `<dl class="facts">${rows.filter(([, v]) => v).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
function deviceFacts(d) {
  if (d.gone) return [["Kind", KIND_WORD[d.kind]], ["Connected", "Not now"], ["Last seen", d.lastSeen]];
  return [["Kind", KIND_WORD[d.kind]], ["What", d.what], ["Connected", d.live?.via || (d.kind === "hub" ? "The hub is open" : "")], ["Address", d.address || ""]];
}
function driveLine(d) {
  if (d.kind !== "hub") return "";
  if (d.here) return `<p class="hint">${ico("i-hand")} Drives a real arm: it is the brain's own computer.</p>`;
  return `<p class="hint">${mayDrive(d) ? "May drive a real arm." : "Watches only: it may not drive a real arm."}</p>`;
}
// the modules that match a device: an arm's Monitor page is its kind's (quick job 147)
function modulesOf(d) {
  const monitor = d.kind === "arm" ? [String(d.live?.model || "").startsWith("xarm") ? "monitor-xarm" : "monitor-so101"] : [];
  return [...monitor, ...(KIND_MODULES[d.kind] || [])].map((id) => S.views.find((v) => v.id === id)).filter((v) => v?.page)
    .map((v) => (v.id === "diagnostics" ? { ...v, page: `${v.page}?show=${encodeURIComponent(d.id)}` } : v));
}
function moduleButtons(box, mods) {
  for (const v of mods) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "btn small virtual";
    b.innerHTML = `${ico(VIEW_ICON[v.id] || "i-test")}${esc(v.title)}`;
    b.title = "Open it here, in the Command Center";
    b.addEventListener("click", () => openModule(v));
    box.append(b);
  }
}
let inspected = "";
function renderInspector(force = false) {
  const box = $("#insp > .in"), devs = devices(), scr = screens(devs);
  const keys = [...S.sel].filter((k) => devs.some((d) => d.key === k) || scr.some((s) => s.key === k));
  // a person typing or choosing in the inspector keeps it, until the highlight changes
  const now = keys.join(" ");
  if (!force && now === inspected && box.contains(document.activeElement) && document.activeElement.matches("input, select")) return;
  inspected = now;
  box.innerHTML = `<h2>${ico("i-test")}Inspector</h2>`;
  const msg = S.msg ? `<p class="msg${S.msgBad ? "" : " ok"}">${esc(S.msg)}</p>` : "";
  if (!keys.length) {
    box.insertAdjacentHTML("beforeend", `<p class="hint">Press a device or a screen, in the list or the workspace, to see it here. Select multiple, Ctrl or Shift adds more. ⤢ opens one device. Drag a page onto a screen to open it there.</p>${msg}`);
    return;
  }
  const part = (title, html = "") => {
    const el = document.createElement("div");
    el.innerHTML = `<h3>${title}</h3>${html}`;
    box.append(el);
    return el;
  };
  const acts = actionsFor(keys, devs, scr);
  const one = keys.length === 1 ? keys[0] : "";
  const d = one && devs.find((x) => x.key === one);
  const s = one && scr.find((x) => x.key === one);
  if (d) {
    box.insertAdjacentHTML("beforeend", `<div class="who">${ico(KIND_ICON[d.kind])}<b title="${esc(d.title)}">${esc(d.title)}</b>`
      + (d.gone ? "" : `<button class="iconbtn foc" type="button" title="Focus: its screens, actions and modules">${ico("i-open")}</button>`) + `</div>`
      + (d.sub ? `<p class="hint">${esc(d.sub)}</p>` : ""));
    part("Details", factsHTML(deviceFacts(d)) + driveLine(d));
  } else if (s) {
    box.insertAdjacentHTML("beforeend", `<div class="who">${ico("i-screen")}<b>${esc(devTitle(s.device))}${s.count > 1 ? `, screen ${s.n}` : ""}</b>`
      + `<button class="iconbtn foc" type="button" title="Focus: its device's screens, actions and modules">${ico("i-open")}</button></div>`);
    part("Details", factsHTML([["Shows", shows(s.w)], ["From", s.w.showing && s.w.from ? s.w.from : ""], ["Resolution", resolution(s.w)], ["Device", s.device.name]]));
  } else {
    box.insertAdjacentHTML("beforeend", `<div class="who"><b class="count">${plural(keys.length, "item")}</b></div><p class="hint">Only the actions that apply to every item.</p>`);
  }
  const ab = part("Actions", `<div class="acts"></div>`).querySelector(".acts");
  actButtons(ab, acts, devs);
  const clear = document.createElement("button");
  clear.type = "button"; clear.className = "btn small virtual"; clear.textContent = "Clear";
  clear.title = "Highlight nothing";
  clear.addEventListener("click", () => { S.sel.clear(); S.msg = ""; render(true); });
  ab.append(clear);
  if (msg) ab.insertAdjacentHTML("afterend", msg);
  const mods = d ? modulesOf(d) : [];
  if (mods.length) moduleButtons(part("Modules", `<div class="acts"></div>`).querySelector(".acts"), mods);
  if (d && d.kind === "hub" && d.named) fillSettings(part("Settings", `<p class="hint">Reading…</p>`), d);
  box.querySelector(".who .foc")?.addEventListener("click", () => focus(one));
}

// ---------- the ⋯ menu: one item's settings and actions, without highlighting it ----------
function closeMenu() { document.querySelector(".menu")?.remove(); }
function openMenu(key, btn) {
  closeMenu();
  const devs = devices(), scr = screens(devs);
  const m = document.createElement("div");
  m.className = "menu";
  const foc = document.createElement("button");
  foc.type = "button"; foc.className = "btn small virtual"; foc.innerHTML = `${ico("i-open")}Focus`;
  foc.addEventListener("click", () => { closeMenu(); focus(key); });
  m.append(foc);
  actButtons(m, actionsFor([key], devs, scr), devs, closeMenu);
  document.body.append(m);
  const r = btn.getBoundingClientRect();
  m.style.left = `${Math.min(innerWidth - m.offsetWidth - 8, r.left)}px`;
  m.style.top = `${Math.min(innerHeight - m.offsetHeight - 8, r.bottom + 4)}px`;
}
document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".menu, .more")) closeMenu(); });

// ---------- focus: one device in a modal ----------
let focused = "", focusOrigin = null;
function closeFocus() {
  document.querySelector(".veil")?.remove();
  focused = "";
  if (focusOrigin?.isConnected) focusOrigin.focus();
  focusOrigin = null;
}
async function focus(key) {
  closeMenu();
  const devs = devices(), scr = screens(devs);
  const d = devs.find((x) => x.key === key);
  if (!d) {
    const s = scr.find((x) => x.key === key);  // a screen on its own: its own device
    return s ? focus(`d:${s.device.name}`) : undefined;
  }
  if (!focused) focusOrigin = document.activeElement;
  focused = key;
  document.querySelector(".veil")?.remove();
  const veil = document.createElement("div");
  veil.className = "veil";
  const mine = scr.filter((s) => s.device.name === d.id && d.kind === "hub");
  const mods = modulesOf(d);
  veil.innerHTML = `<div class="card modal" role="dialog" aria-label="${esc(d.title)}"><div class="in">
    <div class="top"><h2>${ico(KIND_ICON[d.kind])}${esc(d.title)}${d.sub ? ` <small class="hint">${esc(d.sub)}</small>` : ""}</h2>
      <button class="btn small" type="button" data-close aria-label="Close focus window">×</button></div>
    <div class="cols">
    ${mine.length ? `<div><h3>${plural(mine.length, "screen")}</h3><div class="shots" id="f-shots"></div></div>` : ""}
      <div><h3>Facts</h3>${factsHTML(deviceFacts(d))}</div>
      <div id="f-actions"><h3>Actions</h3></div>
      ${mods.length ? `<div><h3>Modules</h3><div class="mods" id="f-mods"></div></div>` : ""}
      ${d.kind === "hub" && d.named ? `<div id="f-settings"><h3>Settings</h3><p class="hint">Reading…</p></div>` : ""}
    </div></div></div>`;
  veil.addEventListener("pointerdown", (e) => { if (e.target === veil) closeFocus(); });
  veil.querySelector("[data-close]").addEventListener("click", closeFocus);
  document.body.append(veil);
  veil.querySelector("[data-close]").focus();
  veil.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    const controls = [...veil.querySelectorAll("button:enabled, select:enabled, input:enabled")];
    const first = controls[0], last = controls.at(-1);
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  const shots = veil.querySelector("#f-shots");
  for (const s of mine) {
    const el = document.createElement("div");
    el.className = "shot";
    el.innerHTML = screenPreview(s.w, 288) + under(s) + `<div class="do"></div>`;
    const acts = actionsFor([s.key], devs, scr).filter((a) => a.real && a.kind === "page" || a.icon === "i-back");
    actButtons(el.querySelector(".do"), acts, devs);
    shots.append(el);
  }
  const fa = veil.querySelector("#f-actions"), box = document.createElement("div");
  box.className = "mods";
  const acts = actionsFor([key], devs, scr).filter((a) => !(mine.length && (a.kind === "page" || a.icon === "i-back")));
  fa.insertAdjacentHTML("beforeend", driveLine(d));
  actButtons(box, acts, devs, () => setTimeout(() => focused === key && focus(key), 300));
  fa.append(box);
  if (mods.length) moduleButtons(veil.querySelector("#f-mods"), mods);
  if (d.kind === "hub" && d.named) fillSettings(veil.querySelector("#f-settings"), d);
}
async function fillSettings(box, d) {
  let values = {};
  try { values = (await getJSON(`/api/hub-devices/${encodeURIComponent(d.id)}/settings`)).settings || {}; } catch { /* shown as defaults */ }
  const h = `<h3>Settings</h3><div class="field"><span>Display name</span><input type="text" maxlength="40" data-k="display_name" value="${esc(values.display_name || "")}" placeholder="${esc(d.id)}"></div>`
    + SETTINGS.map((f) => {
      const now = f.key === "sound" ? (values.sound === true ? "on" : values.sound === false ? "off" : "") : String(values[f.key] ?? "");
      return `<div class="field"><span>${esc(f.label)}</span><select data-k="${f.key}">${f.choices.map(([v, t]) => `<option value="${esc(v)}"${v === now ? " selected" : ""}>${esc(t)}</option>`).join("")}</select></div>`;
    }).join("")
    + `<p class="msg" id="f-msg"></p>`;
  box.innerHTML = h;
  const send = async (k, v) => {
    const r = await postJSON(`/api/hub-devices/${encodeURIComponent(d.id)}/settings`, { [k]: v });
    $("#f-msg", box).textContent = r.ok ? "" : r.message;
    if (r.ok && k === "display_name") refresh();
  };
  box.querySelector('[data-k="display_name"]').addEventListener("change", (e) => send("display_name", e.target.value.trim()));
  for (const sel of box.querySelectorAll("select")) {
    sel.addEventListener("change", () => send(sel.dataset.k, sel.dataset.k === "sound" ? (sel.value === "" ? "" : sel.value === "on") : sel.value));
  }
  box.querySelector("h3").insertAdjacentHTML("beforeend", ` <svg class="ico" aria-label="Changes the device"><use href="/web/design/icons.svg#i-cast"/></svg>`);
}

// ---------- a module: in a modal here, or in its own window ----------
function openModule(v) {
  $("#module-title").textContent = v.title;
  $("#module-frame").src = v.page;
  $("#module").hidden = false;
  $("#module-own").onclick = () => { window.open(v.page, `lab-os-page-${v.page}`); closeModule(); };
}
function closeModule() { $("#module").hidden = true; $("#module-frame").src = "about:blank"; }
$("#module-back").addEventListener("click", closeModule);
addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  // the hub around this page closes the whole module unless this page closed something (quick job 154)
  if (carry.view || !$("#module").hidden || document.querySelector(".menu, .veil") || S.sel.size) e.preventDefault();
  if (carry.view) { press = null; carry.cancel(); } else if (!$("#module").hidden) closeModule();
  else if (document.querySelector(".menu")) closeMenu();
  else if (document.querySelector(".veil")) closeFocus();
  else if (S.sel.size) { S.sel.clear(); render(true); }
});

// ---------- the loop ----------
function render(force = false) {
  const devs = devices(), scr = screens(devs);
  const now = JSON.stringify([S.hub, S.live.map((d) => [d.id, d.connected, d.name, d.what, d.problem]), [...S.drive]]);
  if (!force && now === S.last) return;
  S.last = now;
  for (const k of [...S.sel]) if (!devs.some((d) => d.key === k) && !scr.some((s) => s.key === k)) S.sel.delete(k);
  renderLists(devs, scr);
  $("#start-all").hidden = !scr.some((s) => s.w.stage === "start");
  if (!S.drag && $("#ws").clientWidth) renderWorkspace(devs, scr);
  if (!document.querySelector(".menu")) renderInspector(force);
  if ($("#stage").children.length) requestAnimationFrame(() => autoFit());
  S.wasOff = new Set(devs.filter((d) => d.gone).map((d) => d.key));
}
// ---------- the activity list: what happened, newest first ----------
function renderActivity() {
  const box = $("#activity");
  if (!S.events.length) { box.innerHTML = `<div class="empty">Nothing yet. Devices that connect and pages that open show here.</div>`; return; }
  const icon = { device: "i-net", page: "i-screen", stop: "i-stop" };
  const newest = S.events[0].t;
  box.innerHTML = S.events.map((e) => {
    const t = new Date(e.t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
    return `<div class="ev ev-${esc(e.kind)}${e.t > S.seenEvent && S.seenEvent ? " new" : ""}"><time>${t}</time>${ico(icon[e.kind] || "i-test")}<span>${esc(e.text)}</span></div>`;
  }).join("");
  S.seenEvent = newest;
}
async function refresh() {
  try {
    const [hub, live, act] = await Promise.all([getJSON("/api/hub-devices"), getJSON("/api/live-devices"), getJSON("/api/command-center/activity")]);
    S.hub = hub.devices || []; S.live = live.devices || [];
    render();
    if (JSON.stringify(act.events?.[0] || null) !== JSON.stringify(S.events[0] || null) || !$("#activity").children.length) {
      S.events = act.events || [];
      renderActivity();
    }
  } catch (e) {
    say(`The brain didn't answer (${e.message}). Trying again.`, true);
  }
}
async function start() {
  playIntro();  // the sweep starts at once; the page fades in at its end (quick job 161)
  try {
    const [hub, cc] = await Promise.all([getJSON("/api/hub"), getJSON("/api/command-center")]);
    S.views = hub.views || [];
    renderPages();
    S.layout = cc.layout || S.layout;
    S.drive = new Set(cc.drive_from || []);
  } catch (e) {
    say(`The brain didn't answer (${e.message}).`, true);
  }
  await refresh();
  setInterval(() => { if (!S.drag) refresh(); }, POLL_MS);
}
start();
