// This page's device (focus step 8, docs/guides/hub.md → "Devices"): a computer or screen with the hub open
// under a name in its address (`/?device=desk`). The brain keeps the list of devices that have the hub open
// and each device's own settings ("This device"); a hub page keeps one WebSocket to it (/ws/hub-device,
// docs/dev/protocol.md → "Devices"), which reconnects by itself when the brain restarts. When the brain is shut
// down from the hub ("brain_off"), the page says lab-os is off (/web/off.js) and reloads once it's back.
//
//   deviceName()       the name: `?device=` in this page's address, else the hub's around it, else the
//                      name this browser last used ("" = no name)
//   prefs()            this device's settings (a copy kept in this browser, filled from the brain)
//   setPref(k, v)      change one: kept by the brain under the name (in this browser only without one)
//   connectDevice({…}) the hub page's connection: the device list, "open on…", "bring it back"
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
  const s = screen, out = { left: s.availLeft ?? window.screenX ?? 0, top: s.availTop ?? 0, width: s.width, height: s.height, label: "" };
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
 * h.look: "plain" | "design"; h.state(): {stage: "start"|"hub", showing: module id | null, from, from_window};
 * h.onOpen(module, from, fromWindow): open that module here (sent from another device);
 * h.onClose(): close the module here ("bring it back" there); h.onDevices(list): the brain's list changed;
 * h.onSettings(): this device's settings changed (re-read prefs()); h.onLink(up): connected or not;
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
        retry = 1000; up = true;
        send({ type: "hello", look: h.look, ...h.state(), screen: await screenInfo() });
        list = m.devices || [];
        h.onLink?.(true);
        h.onDevices?.(list);
        applySettings(m.settings, true);
      } else if (m.type === "devices") {
        list = m.devices || [];
        h.onDevices?.(list);
      } else if (m.type === "settings") applySettings(m.settings, false);
      else if (m.type === "open") h.onOpen?.(m.module, m.from || "", m.from_window || "");
      else if (m.type === "close") h.onClose?.();
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
    /** Open a module on another device (window: a monitor the brain asked about). */
    openOn: (module, device, window = "") =>
      postJSON("/api/hub-devices/open", { module, device, window, from: name, from_window: wid })
        .catch((e) => ({ ok: false, message: `The brain didn't answer (${e.message}).` })),
    /** Close what another device's window shows (it was opened from here). */
    bringBack: (device, window) =>
      postJSON("/api/hub-devices/close", { device, window })
        .catch((e) => ({ ok: false, message: `The brain didn't answer (${e.message}).` })),
    /** The windows showing something opened from this device (or this window), for "bring it back". */
    sentFromHere: () => list.flatMap((d) => d.windows
      .filter((w) => w.showing && ((name && w.from === name) || (wid && w.from_window === wid)))
      .map((w) => ({ device: d.name, window: w.id, label: w.label, showing: w.showing }))),
    /** Where a module can be opened: every window of the other devices, and this device's other windows. */
    targets: () => list.map((d) => ({ ...d, windows: d.windows.filter((w) => w.id !== wid) })).filter((d) => d.windows.length),
  };
}

/* ---------- the two lists both hubs show (each hub styles them: .oo-*) ---------- */
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
        box.append(row(own ? `${d.name} (this device)` : d.name, sub, () => go(d.name)));
      }
      for (const x of opts.extra || []) box.append(row(x.label, x.sub || "", async () => x.run(msg)));
      if (!targets.length) {
        box.append(el("p", "oo-none", dev.up()
          ? "No other device has the hub open. Open it there with ?device=<name> in the address (docs/guides/hub.md → Devices)."
          : "Not connected to the brain right now: trying again."));
      }
    }
    box.append(msg);
  }
  draw(null);
}

/** "Bring it back": a row per page this device opened elsewhere; opts.onBack(item) after it closed there. */
export function fillSent(box, dev, opts = {}) {
  const items = dev.sentFromHere();
  box.replaceChildren();
  box.hidden = !items.length;
  for (const it of items) {
    const line = el("div", "oo-sent");
    const at = it.label ? `${it.device} (${it.label})` : it.device;
    line.append(el("span", "oo-what", `${it.showing.title} is on ${at}`));
    const b = el("button", "oo-back", "Bring it back");
    b.type = "button";
    b.addEventListener("click", async (e) => {
      e.stopPropagation();
      b.disabled = true;
      const r = await dev.bringBack(it.device, it.window);
      if (r.ok) opts.onBack?.(it);
      else { b.disabled = false; b.title = r.message; }
    });
    line.append(b);
    box.append(line);
  }
}
