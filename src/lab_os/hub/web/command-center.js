// The Command Center (quick job 134; the spec: docs/design/command-center.md).
//
// Items: a *device* (a computer or screen with the hub open, by its device name, or a device of the live
// list: an arm, a camera, raspbot1, the Quest) and a *screen* (one hub window of a device: one per
// monitor). A device's monitors are grouped under it by themselves; a person can group a screen under
// another device, or put it on its own, by dragging it. That, the places and what is hidden is the
// workspace's layout: only the picture, kept by the brain, never a change to a device.
//
// Highlight and focus are different: a press highlights (Ctrl or Shift adds more), in the workspace and in
// both lists; ⤢ focuses one device in a modal with its screens, actions, modules and settings. The actions
// for the highlighted items show under the workspace: only the ones that apply to every item, with the
// number of screens or devices they change. Real changes carry the cast mark; workspace-only ones are dashed.
//
// The positions are plain 2D numbers in the workspace's own units, kept apart from the drawing, so a 3D
// view of the lab can use the same layout later (the spec's "keep the design open to 3D").

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ico = (id) => `<svg class="ico"><use href="/web/design/icons.svg#${id}"/></svg>`;
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const POLL_MS = 1500;
const SHOT_W = 200, GAP = 48, ROW_W = 1500;  // workspace units (px at zoom 1)
const KIND_ICON = { hub: "i-pc", arm: "i-arm", leader: "i-leader", camera: "i-cam", robot: "i-pi", headset: "i-headset", usb: "i-chip" };
const KIND_WORD = { hub: "Computer or screen", arm: "Arm", leader: "Leader arm", camera: "Camera", robot: "Robot", headset: "Headset", usb: "USB device" };
const VIEW_ICON = {
  teleop: "i-hand", monitor: "i-screen", ai: "i-chip", training: "i-leader", cameras: "i-cam", webcam: "i-cam",
  settings: "i-gear", pages: "i-link", project: "i-next", spend: "i-coin", commits: "i-commit", devices: "i-net",
  system: "i-net", chat: "i-chat", raspbot: "i-pi", "wake-word": "i-user", remote: "i-touch", xr: "i-headset", command: "i-target",
};
// the modules that match a kind of device (examples from the spec; only views the brain has are shown)
const KIND_MODULES = { arm: ["monitor", "teleop", "ai"], leader: ["teleop"], robot: ["raspbot"], camera: ["cameras"], headset: ["teleop"] };
// "This device" settings the modal can change (the rest stay in ⚙ → This device on that device)
const SETTINGS = [
  { key: "quality", label: "Level of detail", choices: [["", "Default"], ["maximal", "Maximal"], ["full", "Full"], ["reduced", "Reduced"], ["minimal", "Minimal"]] },
  { key: "voice", label: "Way in to voice", choices: [["", "Default"], ["push-to-talk", "Push-to-talk"], ["dictation", "Dictation"], ["wake word", "Wake word"]] },
  { key: "sound", label: "Sound", choices: [["", "Default"], ["on", "On"], ["off", "Off"]] },
];

const S = {
  hub: [], live: [], views: [], drive: new Set(),
  layout: { places: {}, hidden: [], groups: {} },
  sel: new Set(), search: "", page: "", group: "",
  view: { x: 40, y: 40, z: 1 }, fitted: false, drag: null, msg: "", msgBad: false, last: "",
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
  renderActs();
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
const shows = (w) => (w.showing ? w.showing.title : w.stage === "start" ? "Start screen" : "The Hub");
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
function preview(s, width) {
  const sc = s.w.screen || {};
  const aspect = sc.width && sc.height ? Math.min(1.0, Math.max(0.42, sc.height / sc.width)) : 9 / 16;
  const w = s.w;
  let inner;
  if (w.showing) inner = `<div class="mod">${ico(VIEW_ICON[w.showing.id] || "i-test")}</div>`;
  else if (w.stage === "start") inner = `<div class="ring"></div>`;
  else inner = `<div class="core"></div>`;
  const from = w.showing && w.from ? `<span class="from">From ${esc(w.from)}</span>` : "";
  return `<div class="pv" style="width:${width}px;height:${Math.round(width * aspect)}px">${inner}${from}<span class="say">${esc(shows(w))}</span></div>`;
}
function under(s) {
  const d = s.device, title = devTitle(d), sub = d.named && d.display_name && d.display_name !== d.name ? d.name : "";
  const name = s.count > 1 ? `<span>Screen ${s.n}</span>` : "";
  const res = resolution(s.w);
  return `<div class="under"><b>${esc(title)}${sub ? `<small>${esc(sub)}</small>` : ""}</b>${name}${res ? `<span class="res num">${res}</span>` : ""}</div>`;
}

// ---------- the lists ----------
function renderLists(devs, scr) {
  const dl = $("#devices"), sl = $("#screens");
  const shownDevs = devs.filter((d) => matches(devText(d)));
  dl.innerHTML = shownDevs.length ? "" : `<div class="empty">${devs.length ? "No device matches the search." : "No device is connected."}</div>`;
  for (const d of shownDevs) {
    const r = document.createElement("div");
    r.className = `row${S.sel.has(d.key) ? " sel" : ""}${isHidden(d.key) ? " off" : ""}`;
    r.dataset.key = d.key;
    const drive = d.kind === "hub" && mayDrive(d) ? ` ${ico("i-hand")}` : "";
    r.innerHTML = `<span class="k">${ico(KIND_ICON[d.kind])}</span><b title="${esc(d.title)}">${esc(d.title)}${drive}</b>`
      + `<button class="iconbtn eye${isHidden(d.key) ? "" : " on"}" type="button" title="${isHidden(d.key) ? "Show in the workspace" : "Hide from the workspace"}">${ico(isHidden(d.key) ? "i-eye-off" : "i-eye")}</button>`
      + `<button class="iconbtn foc" type="button" title="Focus: its screens, actions and modules">${ico("i-open")}</button>`
      + `<small>${esc(d.sub || KIND_WORD[d.kind])}</small>`;
    dl.append(r);
  }
  $("#dev-count").textContent = devs.length;
  const shownScr = scr.filter((s) => matches(scrText(s)));
  sl.innerHTML = shownScr.length ? "" : `<div class="empty">${scr.length ? "No screen matches the search." : "No screen has the hub open."}</div>`;
  for (const s of shownScr) {
    const r = document.createElement("div");
    r.className = `row${S.sel.has(s.key) ? " sel" : ""}${isHidden(s.key) ? " off" : ""}`;
    r.dataset.key = s.key;
    const name = s.count > 1 ? ` Screen ${s.n}` : "";
    r.innerHTML = `<span class="k">${ico(VIEW_ICON[s.w.showing?.id] || "i-screen")}</span><b>${esc(devTitle(s.device))}${esc(name)}</b>`
      + `<button class="iconbtn eye${isHidden(s.key) ? "" : " on"}" type="button" title="${isHidden(s.key) ? "Show in the workspace" : "Hide from the workspace"}">${ico(isHidden(s.key) ? "i-eye-off" : "i-eye")}</button>`
      + `<button class="iconbtn foc" type="button" title="Focus: its device's screens, actions and modules">${ico("i-open")}</button>`
      + `<small>${esc(shows(s.w))}</small>`;
    sl.append(r);
  }
  $("#scr-count").textContent = scr.length;
  $("#show-all").hidden = !S.layout.hidden.length;
}

// ---------- the workspace ----------
function placeNew(els) {
  // items without a place go in rows under the placed ones (measured, so they never overlap)
  const placed = Object.values(S.layout.places);
  const all = [...$("#stage").children].filter((n) => !els.includes(n));
  let y = all.length ? Math.max(...all.map((n) => n.offsetTop + n.offsetHeight)) + GAP : placed.length ? Math.max(...placed.map((p) => p[1])) + 300 : 0;
  let x = 0, rowH = 0;
  for (const el of els) {
    const w = el.offsetWidth, h = el.offsetHeight;
    if (x && x + w > ROW_W) { x = 0; y += rowH + GAP; rowH = 0; }
    S.layout.places[el.dataset.key] = [x, y];
    el.style.left = `${x}px`; el.style.top = `${y}px`;
    x += w + GAP; rowH = Math.max(rowH, h);
  }
  if (els.length) saveLayout();
}
function renderWorkspace(devs, scr) {
  const stage = $("#stage");
  const lone = scr.filter((s) => s.group === s.key);
  stage.innerHTML = "";
  const fresh = [];
  const put = (el, key) => {
    const at = S.layout.places[key];
    if (at) { el.style.left = `${at[0]}px`; el.style.top = `${at[1]}px`; } else fresh.push(el);
    stage.append(el);
  };
  // screens' devices first, then screens on their own, then the other devices (the order new ones get)
  const order = [...devs.filter((d) => d.kind === "hub"), ...lone, ...devs.filter((d) => d.kind !== "hub")];
  for (const item of order) {
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
    el.className = `node${S.sel.has(d.key) ? " sel" : ""}${matches(devText(d)) ? "" : " dim"}`;
    el.dataset.key = d.key;
    const mine = scr.filter((s) => s.group === d.key && !isHidden(s.key));
    const drive = d.kind === "hub" && mayDrive(d) ? `<span class="k" title="May drive a real arm">${ico("i-hand")}</span>` : "";
    el.innerHTML = `<div class="head"><span class="k">${ico(KIND_ICON[d.kind])}</span><b>${esc(d.title)}</b>${d.sub ? `<small>${esc(d.sub)}</small>` : ""}${drive}<span class="grow"></span>`
      + `<button class="iconbtn more" type="button" title="Settings and actions">⋯</button>`
      + `<button class="iconbtn foc" type="button" title="Focus: its screens, actions and modules">${ico("i-open")}</button></div>`
      + (mine.length ? "" : `<div class="what${d.bad ? " bad" : ""}">${esc(d.what || KIND_WORD[d.kind])}</div>`);
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
  el.dataset.key = s.key;
  el.innerHTML = preview(s, SHOT_W) + under(s);
  return el;
}
function applyView() {
  $("#stage").style.transform = `translate(${S.view.x}px, ${S.view.y}px) scale(${S.view.z})`;
}
function fit() {
  const nodes = [...$("#stage").children];
  if (!nodes.length) return;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const n of nodes) {
    const x = n.offsetLeft, y = n.offsetTop;
    x0 = Math.min(x0, x); y0 = Math.min(y0, y);
    x1 = Math.max(x1, x + n.offsetWidth); y1 = Math.max(y1, y + n.offsetHeight);
  }
  const ws = $("#ws").getBoundingClientRect(), pad = 30;
  const z = Math.max(0.25, Math.min(1.4, (ws.width - 2 * pad) / (x1 - x0), (ws.height - 2 * pad) / (y1 - y0)));
  S.view = { z, x: pad - x0 * z + Math.max(0, (ws.width - 2 * pad - (x1 - x0) * z) / 2), y: pad - y0 * z };
  applyView();
}

// ---------- highlight, drag, pan, zoom ----------
function pick(key, add) {
  if (add) S.sel.has(key) ? S.sel.delete(key) : S.sel.add(key);
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
  const z = Math.max(0.2, Math.min(2.5, S.view.z * Math.exp(-e.deltaY * 0.0015)));
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
for (const id of ["#devices", "#screens"]) {
  $(id).addEventListener("click", (e) => {
    const row = e.target.closest(".row");
    if (!row) return;
    const key = row.dataset.key;
    if (e.target.closest(".eye")) return hide([key], !isHidden(key));
    if (e.target.closest(".foc")) return focus(key.startsWith("s:") ? `d:${key.slice(2).split("#")[0]}` : key);
    pick(key, e.ctrlKey || e.metaKey || e.shiftKey);
  });
}
$("#search").addEventListener("input", (e) => { S.search = e.target.value; render(true); });
$("#fit").addEventListener("click", fit);
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
  if (!view) return say("Choose a page first.", true);
  const said = [];
  for (const s of targets) {
    const r = await postJSON("/api/hub-devices/open", { module: view, device: s.device.name, window: s.w.id, from: "the Command Center" });
    if (!r.ok) said.push(`${devTitle(s.device)}: ${r.message}`);
  }
  await refresh();
  say(said.length ? said.join(" ") : `${viewTitle(view)} is open on ${plural(targets.length, "screen")}.`, !!said.length);
}
async function backToHub(targets) {
  const said = [];
  for (const s of targets.filter((t) => t.w.showing)) {
    const r = await postJSON("/api/hub-devices/close", { device: s.device.name, window: s.w.id });
    if (!r.ok) said.push(`${devTitle(s.device)}: ${r.message}`);
  }
  await refresh();
  say(said.length ? said.join(" ") : `Back to the hub on ${plural(targets.length, "screen")}.`, !!said.length);
}
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
    acts.push({ kind: "page", real: true, label: one ? "Open" : `Open on ${n}`, run: (view) => openOn(targets, view) });
    const busy = targets.filter((t) => t.w.showing), m = plural(busy.length, "screen");
    if (busy.length) acts.push({ real: true, icon: "i-back", label: one ? "Back to the hub" : `Hub on ${m}`, title: `Close what ${m} show: back to the hub`, run: () => backToHub(busy) });
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
function pageSelect(cls = "") {
  const opts = S.views.filter((v) => v.id !== "command" && v.id !== "xr").map((v) => `<option value="${esc(v.id)}"${v.id === S.page ? " selected" : ""}>${esc(v.title)}</option>`);
  return `<select class="${cls}" aria-label="Page"><option value="">Choose a page…</option>${opts.join("")}</select>`;
}
function groupSelect(devs) {
  const opts = devs.filter((d) => !isHidden(d.key)).map((d) => `<option value="${esc(d.key)}"${d.key === S.group ? " selected" : ""}>${esc(d.title)}</option>`);
  return `<select aria-label="Device to group under"><option value="">Choose a device…</option>${opts.join("")}</select>`;
}
function actButtons(box, acts, devs, after = () => {}) {
  for (const a of acts) {
    const wrap = document.createElement("span");
    wrap.style.display = "contents";
    if (a.kind === "page" || a.kind === "group") {
      wrap.innerHTML = a.kind === "page" ? pageSelect() : groupSelect(devs);
      const sel = wrap.querySelector("select");
      sel.addEventListener("change", () => (a.kind === "page" ? (S.page = sel.value) : (S.group = sel.value)));
    }
    const b = document.createElement("button");
    b.type = "button";
    b.className = `btn small${a.real ? "" : " virtual"}`;
    b.innerHTML = `${a.real ? ico("i-cast") : ""}${a.icon && !a.real ? ico(a.icon) : ""}${esc(a.label)}`;
    if (a.title) b.title = a.title;
    b.addEventListener("click", () => {
      const sel = wrap.querySelector("select");
      if (a.kind === "group" && !sel.value) return say("Choose a device first.", true);
      a.run(sel?.value);
      after();
    });
    wrap.append(b);
    box.append(wrap);
  }
}
function renderActs() {
  const box = $("#acts"), devs = devices(), scr = screens(devs);
  const keys = [...S.sel].filter((k) => devs.some((d) => d.key === k) || scr.some((s) => s.key === k));
  box.innerHTML = "";
  if (!keys.length) {
    box.innerHTML = `<span class="hint">Press an item to highlight it. Ctrl or Shift adds more. ⤢ opens one device.</span>`;
  } else {
    box.insertAdjacentHTML("beforeend", `<span class="count">${plural(keys.length, "item")}</span>`);
    actButtons(box, actionsFor(keys, devs, scr), devs);
    const clear = document.createElement("button");
    clear.type = "button"; clear.className = "btn small virtual"; clear.textContent = "Clear";
    clear.title = "Highlight nothing";
    clear.addEventListener("click", () => { S.sel.clear(); S.msg = ""; render(true); });
    box.append(clear);
  }
  if (S.msg) box.insertAdjacentHTML("beforeend", `<span class="msg${S.msgBad ? "" : " ok"}">${esc(S.msg)}</span>`);
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
let focused = "";
function closeFocus() { document.querySelector(".veil")?.remove(); focused = ""; }
async function focus(key) {
  closeMenu();
  const devs = devices(), scr = screens(devs);
  const d = devs.find((x) => x.key === key);
  if (!d) {
    const s = scr.find((x) => x.key === key);  // a screen on its own: its own device
    return s ? focus(`d:${s.device.name}`) : undefined;
  }
  focused = key;
  document.querySelector(".veil")?.remove();
  const veil = document.createElement("div");
  veil.className = "veil";
  const mine = scr.filter((s) => s.device.name === d.id && d.kind === "hub");
  const facts = [["Kind", KIND_WORD[d.kind]], ["What", d.what], ["Connected", d.live?.via || (d.kind === "hub" ? "The hub is open" : "")], ["Address", d.address || ""]]
    .filter(([, v]) => v).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
  const mods = (KIND_MODULES[d.kind] || []).map((id) => S.views.find((v) => v.id === id)).filter((v) => v?.page);
  veil.innerHTML = `<div class="card modal" role="dialog" aria-label="${esc(d.title)}"><div class="in">
    <div class="top"><h2>${ico(KIND_ICON[d.kind])}${esc(d.title)}${d.sub ? ` <small class="hint">${esc(d.sub)}</small>` : ""}</h2>
      <button class="btn small" type="button" data-close>${ico("i-back")}Back</button></div>
    ${mine.length ? `<div><h3>${plural(mine.length, "screen")}</h3><div class="shots" id="f-shots"></div></div>` : ""}
    <div class="cols">
      <div><h3>Facts</h3><dl class="facts">${facts}</dl></div>
      <div id="f-actions"><h3>Actions</h3></div>
      ${mods.length ? `<div><h3>Modules</h3><div class="mods" id="f-mods"></div></div>` : ""}
      ${d.kind === "hub" && d.named ? `<div id="f-settings"><h3>Settings</h3><p class="hint">Reading…</p></div>` : ""}
    </div></div></div>`;
  veil.addEventListener("pointerdown", (e) => { if (e.target === veil) closeFocus(); });
  veil.querySelector("[data-close]").addEventListener("click", closeFocus);
  document.body.append(veil);
  const shots = veil.querySelector("#f-shots");
  for (const s of mine) {
    const el = document.createElement("div");
    el.className = "shot";
    el.innerHTML = preview(s, 288) + under(s) + `<div class="do"></div>`;
    const acts = actionsFor([s.key], devs, scr).filter((a) => a.real && a.kind === "page" || a.icon === "i-back");
    actButtons(el.querySelector(".do"), acts, devs);
    shots.append(el);
  }
  const fa = veil.querySelector("#f-actions"), box = document.createElement("div");
  box.className = "mods";
  const acts = actionsFor([key], devs, scr).filter((a) => !(mine.length && (a.kind === "page" || a.icon === "i-back")));
  if (d.kind === "hub" && d.here) fa.insertAdjacentHTML("beforeend", `<p class="hint">${ico("i-hand")} Drives a real arm: it is the brain's own computer.</p>`);
  else if (d.kind === "hub") fa.insertAdjacentHTML("beforeend", `<p class="hint">${mayDrive(d) ? "May drive a real arm." : "Watches only: it may not drive a real arm."}</p>`);
  actButtons(box, acts, devs, () => setTimeout(() => focused === key && focus(key), 300));
  fa.append(box);
  const mb = veil.querySelector("#f-mods");
  for (const v of mods) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "btn small virtual";
    b.innerHTML = `${ico(VIEW_ICON[v.id] || "i-test")}${esc(v.title)}`;
    b.title = "Open it here, in the Command Center";
    b.addEventListener("click", () => openModule(v));
    mb.append(b);
  }
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
  if (!$("#module").hidden) closeModule();
  else if (document.querySelector(".menu")) closeMenu();
  else if (document.querySelector(".veil")) closeFocus();
  else if (S.sel.size) { S.sel.clear(); render(true); }
});

// ---------- the loop ----------
function render(force = false) {
  const devs = devices(), scr = screens(devs);
  const now = JSON.stringify([S.hub, S.live.filter((d) => d.connected), [...S.drive]]);
  if (!force && now === S.last) return;
  S.last = now;
  for (const k of [...S.sel]) if (!devs.some((d) => d.key === k) && !scr.some((s) => s.key === k)) S.sel.delete(k);
  renderLists(devs, scr);
  if (!S.drag) renderWorkspace(devs, scr);
  if (!document.querySelector(".menu")) renderActs();
  if (!S.fitted && $("#stage").children.length) { S.fitted = true; requestAnimationFrame(fit); }
}
async function refresh() {
  try {
    const [hub, live] = await Promise.all([getJSON("/api/hub-devices"), getJSON("/api/live-devices")]);
    S.hub = hub.devices || []; S.live = live.devices || [];
    render();
  } catch (e) {
    say(`The brain didn't answer (${e.message}). Trying again.`, true);
  }
}
async function start() {
  try {
    const [hub, cc] = await Promise.all([getJSON("/api/hub"), getJSON("/api/command-center")]);
    S.views = hub.views || [];
    S.layout = cc.layout || S.layout;
    S.drive = new Set(cc.drive_from || []);
  } catch (e) {
    say(`The brain didn't answer (${e.message}).`, true);
  }
  await refresh();
  setInterval(() => { if (!S.drag) refresh(); }, POLL_MS);
}
start();
