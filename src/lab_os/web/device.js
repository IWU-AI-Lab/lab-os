// This page's device (focus step 8, docs/archive/guides-2026-11-25/hub.md → "Devices"): a computer or screen with the hub open
// under a name in its address (`/?device=desk`). The brain keeps the list of devices that have the hub open
// and each device's own settings ("This device"); a hub page keeps one WebSocket to it (/ws/hub-device,
// docs/dev/protocol.md → "Devices"), which reconnects by itself when the brain restarts. When the brain is shut
// down from the hub ("brain_off"), the page says lab-os is off (/web/off.js) and reloads once it's back.
//
//   deviceName()       the name: `?device=` in this page's address, else the hub's around it, else the
//                      name this browser last used, else the name the brain remembers for this
//                      device's address (quick job 132: the page reloads under it; "" = no name)
//   displayName()      the name that is easy to read ("Windows desktop 3"), else the device name
//   renameDevice(to)   add or change this device's name: its settings move along; the hub reloads
//   prefs()            this device's settings (a copy kept in this browser, filled from the brain)
//   setPref(k, v)      change one: kept by the brain under the name (in this browser only without one)
//   connectDevice({…}) the hub page's connection: the device list and "open on…"
//
// The designed hub (design.html) reads the settings with the same rule inline (prefsKey there).

import { backOn, showOff } from "/web/off.js";

const NAME_KEY = "lab-os.device"; // the name this browser last used
const LEGACY_KEY = "lab-os.screen"; // "This screen" before step 8; still the settings of a page with no name

const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* storage blocked: nothing kept */ } },
};

export function cleanName(s) {
  return String(s || "").trim().toLowerCase().replace(/[\s_]+/g, "-").replace(/[^a-z0-9-]/g, "")
    .replace(/^-+|-+$/g, "").slice(0, 32);
}

export function deviceName() {
  const own = new URLSearchParams(location.search).get("device");
  if (own !== null) return cleanName(own);
  try {
    const hub = new URLSearchParams(window.top.location.search).get("device"); // the hub around a module page
    if (hub !== null) return cleanName(hub);
  } catch {
    // another origin above us: only our own address counts
  }
  return cleanName(store.get(NAME_KEY));
}

/** The name people read: the display name (⚙ → This device, quick job 132), else the device name. */
export const displayName = (name = deviceName()) => prefs(name).display_name || name;

// open the hub (the top window: a module page is inside it) again under another device name
function reopenAs(name) {
  store.set(NAME_KEY, name);
  let top = window;
  try { void window.top.location.href; top = window.top; } catch { /* another origin above: this page */ }
  const u = new URL(top.location.href);
  u.searchParams.set("device", name);
  top.location.replace(u.href);
}

/** Add or change this device's name (the `?device=` name). Resolves to {ok, message}; on ok, the hub reloads. */
export async function renameDevice(to) {
  const want = cleanName(to), now = deviceName();
  if (!want) {
    return { ok: false, message: "Use lowercase letters, digits and dashes (desk, newline, quest), up to 32." };
  }
  if (want === now) return { ok: true, message: "That is already this device's name." };
  if (now) {
    try {
      const r = await postJSON(`/api/hub-devices/${now}/rename`, { to: want });
      if (!r.ok) return { ok: false, message: r.message };
    } catch (e) {
      return { ok: false, message: `The brain didn't answer (${e.message}).` };
    }
  }
  reopenAs(want);
  return { ok: true, message: `Opening the hub as ${want}…` };
}

export const prefsKey = (name = deviceName()) => (name ? `lab-os.device.${name}` : LEGACY_KEY);
export const isPrefsKey = (k) => k === LEGACY_KEY || !!k?.startsWith("lab-os.device.");
export function prefs(name) {
  try { return JSON.parse(store.get(prefsKey(name))) || {}; } catch { return {}; }
}

async function postJSON(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const ct = res.headers.get("Content-Type") || "";
  return ct.includes("json") ? res.json() : { ok: false, message: await res.text() };
}

/** Change one of this device's settings ("" or null = the default). Resolves to {ok, message}. */
export async function setPref(key, value) {
  const name = deviceName(), mine = prefs(name);
  if (value === "" || value == null) delete mine[key];
  else mine[key] = value;
  store.set(prefsKey(name), JSON.stringify(mine));
  if (!name) return { ok: true, message: "Kept in this browser (this device has no name)." };
  try {
    const r = await postJSON(`/api/hub-devices/${name}/settings`, { [key]: value ?? "" });
    if (!r.ok) return { ok: false, message: r.message };
    store.set(prefsKey(name), JSON.stringify(r.settings));
    return { ok: true, message: `Kept for ${name} (every window of it).` };
  } catch (e) {
    return { ok: false, message: `Kept in this browser, but the brain didn't get it (${e.message}).` };
  }
}

// which monitor this window is on: its position in the desktop, and the monitor's name where the browser
// already allowed "window management" (never asks here)
async function screenInfo() {
  const s = screen, out = { left: s.availLeft ?? window.screenX ?? 0, top: s.availTop ?? 0, width: s.width, height: s.height, ratio: window.devicePixelRatio || 1, label: "" };
  try {
    if ("getScreenDetails" in window && (await navigator.permissions.query({ name: "window-management" })).state === "granted") {
      out.label = (await window.getScreenDetails()).currentScreen.label || "";
    }
  } catch {
    // not in this browser
  }
  return out;
}

/**
 * The hub page's connection to the brain, for as long as the page is open (reconnects by itself).
 * h.state(): {stage: "start"|"hub", showing: module id | null, from, from_window};
 * h.onOpen(module, from, fromWindow): open that module here (sent from another device);
 * h.onClose(): close the module here when the brain requests it; h.onDevices(list): the brain's list changed;
 * h.onLive(list): the live device list changed (quick job 109: every device seen, connected or not);
 * h.onSettings(): this device's settings changed (re-read prefs()); h.onLink(up): connected or not;
 * h.onCard(): the brain read a card swipe on its own computer's card reader (quick job 113);
 * h.onStart(how, from): another device started (how: "tap" | "card"; from: its name): start here too (quick job 139);
 * h.onOff(): lab-os was shut down (the page is covered; close the microphone).
 */
export function connectDevice(h) {
  const name = deviceName();
  if (name) store.set(NAME_KEY, name);
  const u = new URL(location.href); // keep the name in the address: a reload, and the pages inside, see it
  if (name && u.searchParams.get("device") !== name) {
    u.searchParams.set("device", name);
    history.replaceState(history.state, "", u);
  }
  let ws = null, retry = 1000, list = [], up = false;
  let wid = "";
  try { wid = sessionStorage.getItem("lab-os.window") || ""; } catch { /* none */ }
  const send = (m) => ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify(m));

  async function applySettings(values, first) {
    values = values || {};
    const legacy = (() => { try { return JSON.parse(store.get(LEGACY_KEY)) || {}; } catch { return {}; } })();
    if (first && name && !Object.keys(values).length && Object.keys(legacy).length && !store.get(prefsKey(name))) {
      // the first time under this name: this browser's "This screen" settings become the device's
      try {
        const r = await postJSON(`/api/hub-devices/${name}/settings`, legacy);
        if (r.ok) values = r.settings;
      } catch { /* kept for next time */ }
    }
    if (!name) return;
    const before = store.get(prefsKey(name));
    store.set(prefsKey(name), JSON.stringify(values));
    if (before !== JSON.stringify(values)) h.onSettings?.();
  }

  function open() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${scheme}://${location.host}/ws/hub-device?device=${encodeURIComponent(name)}&window=${encodeURIComponent(wid)}`);
    ws.onmessage = async (e) => {
      let m;
      try { m = JSON.parse(e.data); } catch { return; }
      if (m.type === "welcome") {
        backOn();
        wid = m.window;
        try { sessionStorage.setItem("lab-os.window", wid); } catch { /* none */ }
        if (m.why_no_name) console.warn(`device: ${m.why_no_name}`);
        if (!name && m.found && m.device) { // the brain knows this device by its address (quick job 132)
          console.info(`device: the brain knows this device as ${m.device}`);
          reopenAs(m.device);
          return;
        }
        retry = 1000; up = true;
        send({ type: "hello", ...h.state(), screen: await screenInfo() });
        list = m.devices || [];
        h.onLink?.(true);
        h.onDevices?.(list);
        applySettings(m.settings, true);
      } else if (m.type === "devices") {
        list = m.devices || [];
        h.onDevices?.(list);
      } else if (m.type === "live-devices") h.onLive?.(m.devices || []);
      else if (m.type === "settings") applySettings(m.settings, false);
      else if (m.type === "open") h.onOpen?.(m.module, m.from || "", m.from_window || "");
      else if (m.type === "close") h.onClose?.();
      else if (m.type === "card") h.onCard?.();
      else if (m.type === "start") h.onStart?.(m.how === "card" ? "card" : "tap", m.from || "");
      else if (m.type === "renamed" && m.device) reopenAs(m.device); // its other monitors too
      else if (m.type === "brain_off") {
        showOff(m);
        h.onOff?.();
      }
    };
    ws.onclose = () => {
      if (up) console.info("device: the brain went away; reconnecting");
      up = false;
      h.onLink?.(false);
      setTimeout(open, retry);
      retry = Math.min(retry * 2, 5000);
    };
  }
  open();

  return {
    name,
    window: () => wid,
    up: () => up,
    devices: () => list,
    /** Tell the brain what this window shows now (after opening or closing a module, starting, resetting). */
    update: () => send({ type: "state", ...h.state() }),
    /** A person started this window's start screen: the brain starts every other one (quick job 139). */
    started: (how = "tap") => send({ type: "start", how }),
    /** Open a module on another device (window: a monitor the brain asked about). */
    openOn: (module, device, window = "") =>
      postJSON("/api/hub-devices/open", { module, device, window, from: name, from_window: wid })
        .catch((e) => ({ ok: false, message: `The brain didn't answer (${e.message}).` })),
    /** Where a module can be opened: every window of the other devices, and this device's other windows. */
    targets: () => list.map((d) => ({ ...d, windows: d.windows.filter((w) => w.id !== wid) })).filter((d) => d.windows.length),
  };
}

/* ---------- the Open on… menu ---------- */
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};
const where = (w) => (w.showing ? `showing ${w.showing.title}` : w.stage === "start" ? "at the start screen" : "the hub");

/** Redraw an open "Open on…" list after the device list changed (not while it asks which monitor). */
export const shouldRefill = (box) => !box.hidden && !box.dataset.asking;

/**
 * "Open on…": fill `box` with the devices a module can go to. Picking one opens it there (the brain picks the
 * free monitor, or asks: then the monitors are listed). opts.title: the module's name; opts.onSent(result):
 * it's open there (the hub closes its own copy); opts.extra: more rows [{label, sub, run}] (another monitor
 * of this computer).
 */
export function fillOpenOn(box, dev, module, opts = {}) {
  const msg = el("p", "oo-msg");
  msg.setAttribute("aria-live", "polite");
  const row = (label, sub, run) => {
    const b = el("button", "oo-row");
    b.type = "button";
    b.append(el("span", "oo-name", label), el("span", "oo-sub", sub));
    b.addEventListener("click", async (e) => {
      e.stopPropagation();
      box.querySelectorAll("button").forEach((x) => (x.disabled = true));
      try { await run(); } finally { box.querySelectorAll("button").forEach((x) => (x.disabled = false)); }
    });
    return b;
  };
  const go = async (device, window = "") => {
    msg.textContent = `Opening on ${device}…`;
    const r = await dev.openOn(module, device, window);
    if (r.ok) { msg.textContent = r.message; opts.onSent?.(r); return; }
    if (r.ask) { draw(r); return; }
    msg.textContent = r.message || "It didn't open.";
  };
  function draw(ask) {
    box.dataset.asking = ask ? "1" : ""; // while asking, a change in the list doesn't redraw it
    box.replaceChildren(el("p", "oo-head", ask ? ask.message : `Open ${opts.title || module} on…`));
    if (ask) {
      for (const w of ask.ask) box.append(row(w.label, where(w), () => go(ask.device, w.id)));
      box.append(row("Back", "the other devices", async () => draw(null)));
    } else {
      const targets = dev.targets();
      for (const d of targets) {
        const own = d.name === dev.name;
        const sub = d.windows.length > 1 ? `${d.windows.length} monitors` : where(d.windows[0]);
        const title = d.title || d.name; // a page with no device name: its address (quick job 101)
        box.append(row(own ? `${title} (this device)` : title, sub, () => go(d.name)));
      }
      for (const x of opts.extra || []) box.append(row(x.label, x.sub || "", async () => x.run(msg)));
      if (!targets.length) {
        box.append(el("p", "oo-none", dev.up()
          ? "No other device has the hub open. Open the hub there first (docs/archive/guides-2026-11-25/hub.md → Devices)."
          : "Not connected to the brain right now: trying again."));
      }
    }
    box.append(msg);
  }
  draw(null);
}

/**
 * "Another monitor of this computer" (HDMI/DP): open `url` full size on another monitor. Chrome's Window
 * Management API finds the monitor (it asks once; localhost or https only). The new window opens there and
 * moves there (a window manager may put a new window where it likes), and in lab-os's own browser the brain
 * moves it too (quick job 138). Elsewhere: a new window to drag over. say(text) tells the person. Returns
 * "placed", "window", or "" (nothing opened).
 */
let screenDetails = null;
export async function openOnMonitor(url, name, say) {
  let to = null;
  if ("getScreenDetails" in window) {
    try {
      screenDetails ||= await window.getScreenDetails();
      const others = screenDetails.screens.filter((s) => s !== screenDetails.currentScreen);
      const s = others.find((o) => !o.isPrimary) || others[0];
      if (!s) { say("Only one monitor is connected to this computer."); return ""; }
      to = { left: s.availLeft, top: s.availTop, width: s.availWidth, height: s.availHeight };
    } catch (e) {
      say(`The browser didn't allow placing windows (${e.message}); dragging the new window works too.`);
    }
  }
  const place = to ? `popup,left=${to.left},top=${to.top},width=${to.width},height=${to.height}` : "";
  const w = window.open(url, name, place || "popup,width=1280,height=800");
  if (!w) { say("The browser blocked the new window: press the button again."); return ""; }
  if (!to) {
    say(window.isSecureContext
      ? "Opened in a new window: drag it to the other monitor, then click it for full screen."
      : "Opened in a new window: drag it to the other monitor. To place it by itself, open the hub at http://localhost:8080 on this computer (the \"Start lab-os\" icon does).");
    return "window";
  }
  try { w.moveTo(to.left, to.top); w.resizeTo(to.width, to.height); } catch { /* the brain moves it */ }
  brainPlaces(new URL(url, location.href).href, to);
  say("Opened on the other monitor.");
  return "placed";
}

// The brain moves lab-os's own browser window to the monitor (its DevTools; GNOME placed the new window
// on the same monitor, lab check M.7). It tries while the new page loads; full screen stays as the page
// chose. Elsewhere (another browser) it can't, and the window stays where the browser put it.
async function brainPlaces(url, bounds, tries = 10) {
  for (let i = 0; i < tries; i++) {
    await new Promise((r) => setTimeout(r, 400));
    try {
      const r = await fetch("/api/window-state", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, state: "keep", bounds }),
      });
      const got = r.ok ? await r.json() : { ok: false, why: `${r.status}` };
      if (got.ok) return;
      if (i === tries - 1 || /brain's computer/.test(got.why || "")) return console.info(`other monitor: ${got.why}`);
    } catch (e) {
      return console.info(`other monitor: ${e.message}`);
    }
  }
}
