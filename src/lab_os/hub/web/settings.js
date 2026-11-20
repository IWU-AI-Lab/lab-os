// The settings page (quick job 38): groups by what a setting affects, most-used first: This Device, Assistant,
// The Lab, Robots, then the risky ones apart at the bottom (switching a safety limit off, shutting down). A
// sidebar jumps to a group; each group folds. Every row: its label (and a help line only where it isn't
// obvious), its current value on the right (all ending at one edge), the unit, and "Saved" for a moment.
// Settings that apply on a restart collect in a bar with "Restart Now". The brain's settings come from
// /api/settings (src/lab_os/settings.py) and save at once (POST /api/settings, this computer only). "This
// Device" is kept by the brain under the device's name (the ?device= in the hub's address; /web/device.js).
// After a save, the hub around this page (if any) re-reads the theme.
import { deviceName, prefs, setPref } from "/web/device.js";

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const tellHub = () => window.parent !== window && window.parent.postMessage({ type: "lab-os:settings" }, location.origin);
const ICONS = "/web/design/icons.svg";
const ico = (id) => `<svg class="ico" aria-hidden="true"><use href="${ICONS}#${id}"/></svg>`;

/* ---------- words: Title Case for what the page shows (the values saved stay as they are) ---------- */
const NAMES = { ai: "AI Control", design: "Designed Hub", plain: "Plain Hub", jarvis: "J.A.R.V.I.S.", "24h": "24-Hour", "12h": "12-Hour", "push-to-talk": "Push-to-Talk" };
const SMALL = new Set(["a", "an", "and", "of", "the", "to", "on", "in", "for"]);
function show(v) {
  const s = String(v);
  if (NAMES[s]) return NAMES[s];
  return s.split(/[\s-]+/).map((w, i) => (i > 0 && SMALL.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(" ");
}

/* ---------- this device (kept by the brain under its name) ---------- */
const NAME = deviceName();
const screenGet = () => prefs();
async function screenSet(k, v) {
  const r = await setPref(k, v);
  tellHub();
  return r;
}
const LOCAL = [
  { key: "quality", label: "Level of Detail", help: "Maximal adds rings and verses; Minimal suits slow screens. Theme: the lab's default.",
    kind: "choice", choices: ["theme", "maximal", "full", "reduced", "minimal"], value: () => screenGet().quality || "theme",
    save: (v) => screenSet("quality", v === "theme" ? "" : v) },
  { key: "sound", label: "Sound", help: "", kind: "bool", value: () => screenGet().sound !== false, save: (v) => screenSet("sound", v) },
];
const FULL = { key: "full", label: "Full Screen on the Start Press", help: "Off for a laptop you work on.", kind: "bool", value: () => screenGet().full !== false, save: (v) => screenSet("full", v) };
const SLOW = [
  { key: "res", label: "Drawing Resolution", help: "Lower is lighter and a little softer. Auto: the screen's own. ?res= in the address wins.",
    kind: "choice", choices: ["auto", "1", "0.75", "0.5"], value: () => screenGet().res || "auto",
    save: (v) => screenSet("res", v === "auto" ? "" : v) },
  { key: "startup_video", label: "Startup as a Video", help: "A test for screens where the startup stutters: plays a recording of the jump.", kind: "bool", value: () => screenGet().startup_video === true, save: (v) => screenSet("startup_video", v ? true : "") },
];

/* ---------- the controls ---------- */
function control(f, value, onSave, disabled) {
  const wrap = document.createElement("div");
  wrap.className = "ctl";
  const off = disabled ? "disabled" : "";
  if (f.kind === "choice" && f.choices.length <= 5) {
    wrap.innerHTML = `<div class="seg" role="group">${f.choices.map((c) => `<button type="button" ${off} aria-pressed="${c === value}" data-v="${esc(c)}">${esc(show(c))}</button>`).join("")}</div>`;
    wrap.querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
      if (await onSave(b.dataset.v)) wrap.querySelectorAll("button").forEach((o) => o.setAttribute("aria-pressed", o === b));
    }));
  } else if (f.kind === "choice") {
    wrap.innerHTML = `<select ${off}>${f.choices.map((c) => `<option value="${esc(c)}" ${c === value ? "selected" : ""}>${esc(show(c))}</option>`).join("")}</select>`;
    wrap.querySelector("select").addEventListener("change", (e) => onSave(e.target.value));
  } else if (f.kind === "bool") {
    wrap.innerHTML = `<input type="checkbox" class="switch" ${off} ${value ? "checked" : ""} aria-label="${esc(f.label)}">`;
    const box = wrap.querySelector("input");
    box.addEventListener("change", async () => { if (!(await onSave(box.checked))) box.checked = !box.checked; });
  } else if (f.kind === "number") {
    wrap.innerHTML = `<input type="number" ${off} value="${value ?? ""}" min="${f.min ?? ""}" max="${f.max ?? ""}" step="${f.step ?? "any"}"><span class="unit">${esc(f.unit)}</span>`;
    wrap.querySelector("input").addEventListener("change", (e) => onSave(e.target.value === "" ? null : Number(e.target.value)));
  } else if (f.kind === "range") {
    // a slider: saved when let go; the words under it say what the number means
    wrap.innerHTML = `<span class="unit"></span><input type="range" ${off} value="${value}" min="${f.min}" max="${f.max}" step="1" aria-label="${esc(f.label)}">`;  // the words left: the slider ends at the values' edge
    const slider = wrap.querySelector("input"), unit = wrap.querySelector(".unit");
    slider.style.setProperty("--steps", String(Math.max(1, f.max - f.min)));
    const show = () => {
      unit.textContent = f.words ? f.words(Number(slider.value)) : slider.value;
      slider.style.setProperty("--fill", `${((slider.value - f.min) / (f.max - f.min)) * 100}%`);  // the cyan part of the line
    };
    let saved = value;
    show();
    slider.addEventListener("input", show);
    slider.addEventListener("change", async () => {
      if (await onSave(Number(slider.value))) saved = Number(slider.value);
      else { slider.value = saved; show(); }
    });
  } else if (f.kind === "text") {
    wrap.innerHTML = `<input type="text" ${off} value="${esc(value)}" maxlength="60">`;
    wrap.querySelector("input").addEventListener("change", (e) => onSave(e.target.value));
  } else if (f.kind === "color") {
    wrap.innerHTML = `<input type="color" ${off} value="${esc(value || "#29d4ff")}"><span class="unit">${esc(value)}</span>`;
    const pick = wrap.querySelector("input");
    pick.addEventListener("change", async () => { if (await onSave(pick.value)) wrap.querySelector(".unit").textContent = pick.value; });
  } else if (f.kind === "list") {
    // an ordered pick: ticked ones first, in their order; arrows move them
    let chosen = [...(value || [])];
    const draw = () => {
      const rest = f.choices.filter((c) => !chosen.includes(c));
      wrap.innerHTML = `<div class="order">${[...chosen, ...rest].map((c) => {
        const i = chosen.indexOf(c);
        return `<div><input type="checkbox" ${off} ${i >= 0 ? "checked" : ""} data-v="${esc(c)}"><span>${esc(show(c))}</span>` +
          `<button type="button" ${off || i <= 0 ? "disabled" : ""} data-up="${esc(c)}" aria-label="Earlier">↑</button>` +
          `<button type="button" ${off || i < 0 || i === chosen.length - 1 ? "disabled" : ""} data-down="${esc(c)}" aria-label="Later">↓</button></div>`;
      }).join("")}</div>`;
      wrap.querySelectorAll("input").forEach((box) => box.addEventListener("change", () => save(box.checked ? [...chosen, box.dataset.v] : chosen.filter((c) => c !== box.dataset.v))));
      wrap.querySelectorAll("[data-up],[data-down]").forEach((b) => b.addEventListener("click", () => {
        const c = b.dataset.up || b.dataset.down, i = chosen.indexOf(c), j = b.dataset.up ? i - 1 : i + 1, next = [...chosen];
        [next[i], next[j]] = [next[j], next[i]];
        save(next);
      }));
    };
    const save = async (next) => { if (await onSave(next)) chosen = next; draw(); };
    draw();
  }
  return wrap;
}

/* ---------- rows: label and help | value | unit | saved ---------- */
function row(label, help, ctl, unit = "") {
  const r = document.createElement("div");
  r.className = "row";
  r.innerHTML = `<div class="lbl"><label>${esc(label)}</label>${help ? `<div class="help">${esc(help)}</div>` : ""}</div><div class="ctl"></div><div class="unit">${esc(unit)}</div><div class="st" aria-live="polite"></div><div class="err" aria-live="polite"></div>`;
  if (ctl) r.querySelector(".ctl").append(ctl);
  return r;
}
let flashTimer = new WeakMap();
/** "✓ Saved" for a moment in the row's status column; a problem as a sentence under the row. */
function said(r, ok, message) {
  const st = r.querySelector(".st"), err = r.querySelector(".err");
  err.textContent = ok ? "" : message;
  if (!ok) return;
  st.textContent = "✓ Saved";
  st.classList.add("on");
  clearTimeout(flashTimer.get(st));
  flashTimer.set(st, setTimeout(() => st.classList.remove("on"), 2200));
}
/** A setting's row: its control, the unit moved to its own column, saving shown. */
function fieldRow(f, value, save, disabled) {
  let r = null;
  const ctl = control(f, value, async (v) => {
    const res = await save(v);
    said(r, res.ok, res.message);
    return res.ok;
  }, disabled);
  const unit = f.kind === "number" ? ctl.querySelector(".unit") : null;
  unit?.remove();
  r = row(f.label, f.help, ctl, f.unit || "");
  return r;
}

/* ---------- groups: a heading that folds the group, and a button in the sidebar ---------- */
const FOLDED = "lab-os.settings.folded";
let folded = {};
try { folded = JSON.parse(localStorage.getItem(FOLDED) || "{}") || {}; } catch { folded = {}; }
function keepFolded() { try { localStorage.setItem(FOLDED, JSON.stringify(folded)); } catch { /* private window: forgets */ } }
function group(id, title, note = "", { icon = "i-gear", risky = false } = {}) {
  const g = document.createElement("section");
  g.className = `group${risky ? " risky" : ""}`;
  g.id = `g-${id}`;
  g.innerHTML = `<button class="ghead" type="button" aria-expanded="true"><svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 10l4 4 4-4"/></svg><span class="gtitle">${esc(title)}</span>${note ? `<small>${esc(note)}</small>` : ""}</button><div class="rows"></div>`;
  const head = g.querySelector(".ghead");
  const fold = (on) => { g.classList.toggle("folded", on); head.setAttribute("aria-expanded", String(!on)); folded[id] = on; keepFolded(); };
  if (folded[id]) fold(true);
  head.addEventListener("click", () => fold(!g.classList.contains("folded")));
  const nav = document.createElement("button");
  nav.type = "button";
  nav.className = `navb${risky ? " risky" : ""}`;
  nav.dataset.g = id;
  nav.innerHTML = `${ico(icon)}<span>${esc(title)}</span>`;
  nav.addEventListener("click", () => { if (g.classList.contains("folded")) fold(false); g.scrollIntoView({ behavior: "smooth", block: "start" }); });
  (risky ? $("#nav-risky") : $("#nav-main")).append(nav);
  $("#list").append(g);
  spy.observe(g);
  return g.querySelector(".rows");
}
// the sidebar lights the group at the top of the list
const spy = new IntersectionObserver((seen) => {
  for (const e of seen) if (e.isIntersecting) document.querySelectorAll(".navb").forEach((b) => b.classList.toggle("on", b.dataset.g === e.target.id.slice(2)));
}, { root: $("#list"), rootMargin: "0px 0px -70% 0px" });
function sub(rows, title) {
  const s = document.createElement("div");
  s.className = "sub";
  s.textContent = title;
  rows.append(s);
}
function note(rows, text) {
  const n = document.createElement("div");
  n.className = "note";
  n.textContent = text;
  rows.append(n);
}
function btn(label, cls = "") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `btn small ${cls}`;
  b.textContent = label;
  return b;
}

/* ---------- this screen's other monitors (Window Management API, Chrome on this computer) ---------- */
function screensRow() {
  const b = btn("Find Them");
  const r = row("Monitors on This Computer", "For \"Open on…\" → \"Another monitor of this computer\". Asks the browser once.", b);
  const list = document.createElement("ul");
  list.className = "screens";
  r.append(list);
  b.addEventListener("click", async () => {
    if (!("getScreenDetails" in window)) {
      list.innerHTML = "<li>This browser can't place windows on other monitors: open the page there by hand (docs/guides/hub.md → Other monitors).</li>";
      return;
    }
    try {
      const d = await window.getScreenDetails();
      list.innerHTML = d.screens.map((s) => `<li>${esc(s.label || "Screen")}: ${s.width}×${s.height}${s === d.currentScreen ? ", this one" : ""}${s.isPrimary ? ", the main one" : ""}</li>`).join("");
    } catch (e) {
      list.innerHTML = `<li>Not allowed (${esc(e.message)}). Allow "window management" for this site in the browser's site settings.</li>`;
    }
  });
  return r;
}

/* ---------- the way in for voice (docs/guides/voice.md): what this screen can do ---------- */
const VOICE = { key: "voice", label: "Talking to It", kind: "choice", choices: ["push-to-talk", "dictation"],
  help: "Push-to-Talk: hold the mic (or Space) and talk. Dictation: the words go into the ask line.",
  value: () => screenGet().voice || "push-to-talk", save: (v) => screenSet("voice", v) };
async function voiceRows() {
  const { screenCanHear } = await import("/web/voice.js");
  const [can, status] = await Promise.all([screenCanHear(), fetch("/api/status", { cache: "no-store" }).then((r) => r.json()).catch(() => null)]);
  const wake = status?.voice?.wake;
  let f = can.ok ? VOICE : { ...VOICE, help: `Push-to-Talk only, and not here: ${String(can.why).replace(/\.+$/, "")}.` };
  if (can.ok && wake?.available) {
    f = { ...VOICE, choices: [...VOICE.choices, "wake word"], help: `${VOICE.help} Wake Word: say "${wake.phrase}" from anywhere in the room.` };
  } else if (can.ok && wake) f = { ...VOICE, help: `${VOICE.help} No wake word here: ${String(wake.why).replace(/\.+$/, "")}.` };
  const rows = [fieldRow(f, can.ok ? f.value() : "push-to-talk", (v) => f.save(v), !can.ok)];
  if (can.ok && wake?.available) rows.push(fieldRow(SENSITIVITY, SENSITIVITY.value(), (v) => SENSITIVITY.save(v), false));
  return rows;
}

/* ---------- how readily this device hears the wake word (docs/guides/voice.md → "Sensitivity") ---------- */
const SENS_WORDS = { 1: "Fewest false wakes", 3: "Quiet room", 5: "The default", 7: "Noisy room", 9: "Hears the most" };
const SENSITIVITY = { key: "wake_sensitivity", label: "Wake Word Sensitivity", kind: "range", min: 1, max: 9,
  help: "Higher for a noisy room or a weak microphone; lower if it wakes by itself.",
  words: (v) => `${v}${SENS_WORDS[v] ? `: ${SENS_WORDS[v]}` : ""}`,
  value: () => Number(screenGet().wake_sensitivity) || 5,
  save: (v) => screenSet("wake_sensitivity", v === 5 ? "" : v) };

/* ---------- the assistant's languages for this device (quick job 33): what it hears, what it answers in ---------- */
const LANG_NAMES = { "": "Any", en: "English" };  // the brain's codes (lab_os/ai/languages.py) → words
function languageRow() {
  const pair = document.createElement("div");
  pair.className = "pair";
  const r = row("Assistant Language", "What it listens for (OpenAI's voice only) and what it answers in.", pair);
  for (const [key, label] of [["hear_in", "Listens"], ["answer_in", "Answers"]]) {
    const f = { key, label, kind: "choice", choices: Object.values(LANG_NAMES) };
    pair.append(Object.assign(document.createElement("span"), { className: "unit", textContent: label }));
    pair.append(control(f, LANG_NAMES[screenGet()[key] || ""] || "Any", async (v) => {
      const res = await screenSet(key, Object.keys(LANG_NAMES).find((k) => LANG_NAMES[k] === v) ?? "");
      said(r, res.ok, res.message);
      return res.ok;
    }, false));
  }
  return r;
}

/* ---------- the "Lab hub" icon for this device: one tap opens the hub under its name ---------- */
function iconRow() {
  const url = `${location.origin}/?device=${NAME || "<name>"}`;
  const two = document.createElement("div");
  two.className = "pair";
  const linux = btn("Linux"), windows = btn("Windows");
  linux.disabled = windows.disabled = !NAME;
  two.append(linux, windows);
  const r = row('"Lab Hub" Icon', "One tap opens the hub on this device, full screen. Make it again if the brain's address changes.", two);
  const save = (name, text, type) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  linux.addEventListener("click", () => save(`lab-hub-${NAME}.desktop`,
    `[Desktop Entry]\nType=Application\nName=Lab hub (${NAME})\nComment=The lab's hub on this device\nExec=sh -c "google-chrome --app=${url} --start-fullscreen || chromium --app=${url} --start-fullscreen || chromium-browser --app=${url} --start-fullscreen"\nIcon=applications-science\nCategories=Science;\n`,
    "application/x-desktop"));
  windows.addEventListener("click", () => save(`lab-hub-${NAME}.bat`,
    `@echo off\r\nrem The lab's hub on this device (lab-os, docs/guides/hub.md -> Devices)\r\nstart "" chrome --app=${url} --start-fullscreen\r\n`,
    "application/octet-stream"));
  return r;
}

/* ---------- visitor mode (quick job 35): start or exit it here, without asking the assistant ---------- */
function visitorRow(m) {
  const b = btn(m.on ? "Exit Visitor Mode" : "Start Visitor Mode");
  b.disabled = !m.here;
  const help = !m.here ? "Only on the brain's own computer."
    : m.on ? `The ${m.venue} venue. Exit here or ask the assistant; back to ${m.back_to}.`
      : `The try-this cards; Settings and the AI spend hidden. Or ask the assistant ("hey Jarvis, it's demo time").`;
  const r = row("Visitor Mode", help, b, "");
  r.querySelector(".unit").textContent = m.on ? "On" : "Off";
  b.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/venue", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to: m.on ? "normal" : "visitors" }) });
      const out = res.headers.get("Content-Type")?.includes("json") ? await res.json() : { ok: false, message: await res.text() };
      if (out.ok) { tellHub(); location.reload(); return; }
      said(r, false, out.message);
    } catch (e) {
      said(r, false, `Not switched: ${e.message}`);
    }
  });
  return r;
}

/* ---------- shut lab-os down (quick job 6) and restart it (quick job 38): the brain's computer only ---------- */
async function stopBrain(restart) {
  const res = await fetch(restart ? "/api/restart" : "/api/shutdown", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: NAME }) });
  if (!res.ok) throw new Error(await res.text());
  (await import("/web/off.js")).showOff({ from: NAME, time_ms: Date.now(), restart });
  // this page has no live link to the brain: look every 2 s, and come back once it answers again
  let gone = false;
  const look = async () => {
    const up = await fetch("/api/status", { cache: "no-store" }).then((r) => r.ok).catch(() => false);
    if (!up) gone = true;
    if (up && gone) location.reload();
    else setTimeout(look, 2000);
  };
  setTimeout(look, 1000);
}
/** Asks first, with the arm's warning: Cancel puts the button back. */
function confirmIn(r, ctl, button, question, goLabel, run) {
  button.addEventListener("click", async () => {
    const now = await fetch("/api/shutdown", { cache: "no-store" }).then((x) => x.json()).catch(() => null);
    if (!now?.allowed) return said(r, false, now?.why_not || "The brain didn't answer.");
    said(r, false, `${now.warning ? `${now.warning} ` : ""}${question}`);
    const cancel = btn("Cancel"), go = btn(goLabel, "go");
    ctl.replaceChildren(cancel, go);
    cancel.addEventListener("click", () => { ctl.replaceChildren(button); said(r, true, ""); r.querySelector(".st").classList.remove("on"); });
    go.addEventListener("click", async () => {
      cancel.disabled = go.disabled = true;
      try { await run(); } catch (e) { said(r, false, `Didn't work: ${e.message}`); cancel.disabled = go.disabled = false; }
    });
  });
}
async function shutdownRow() {
  const allowed = await fetch("/api/shutdown", { cache: "no-store" }).then((x) => x.json()).catch(() => null);
  const b = btn("Shut Down…", "go");
  b.disabled = !allowed?.allowed;
  const wrap = document.createElement("div");
  wrap.append(b);
  const r = row("Shut Down lab-os", allowed?.allowed ? "Stops any move, lets go of the arm, stops the brain. Asks first." : allowed?.why_not || "The brain didn't answer.", wrap);
  if (allowed?.allowed) confirmIn(r, wrap, b, "Shut down lab-os now?", "Shut Down", () => stopBrain(false));
  return r;
}
/** The bar for settings that apply on a restart, with "Restart Now" (the brain's computer only). */
function restartBar(labels, writable) {
  const bar = $("#restart-bar");
  bar.hidden = !labels.length;
  if (!labels.length) return;
  bar.querySelector(".what").textContent = `${labels.join(", ")}: ${labels.length === 1 ? "applies" : "apply"} when the brain restarts.`;
  const ctl = bar.querySelector(".act");
  if (ctl.dataset.ready) return;
  ctl.dataset.ready = "1";
  const b = btn("Restart Now");
  b.disabled = !writable;
  ctl.replaceChildren(b);
  const r = { querySelector: (s) => (s === ".st" ? bar.querySelector(".st") : bar.querySelector(".err")) };
  confirmIn(r, ctl, b, "Restart lab-os now? Every screen comes back by itself.", "Restart", () => stopBrain(true));
}
const restartNeeded = [];
function needsRestart(label) {
  if (!restartNeeded.includes(label)) restartNeeded.push(label);
  restartBar(restartNeeded, true);
}

/* ---------- start ---------- */
async function start() {
  let data = null;
  try {
    data = await (await fetch("/api/settings", { cache: "no-store" })).json();
  } catch {
    $("#mode").textContent = "Brain not reachable";
    $("#mode").className = "pill bad";
  }
  if (data) {
    $("#mode").textContent = data.writable ? `Saved for this place (venue: ${data.venue})` : data.why_not;
    $("#mode").className = `pill ${data.writable ? "on" : "warn"}`;
  }
  const m = data?.visitor_mode;
  if (m?.on) {  // visitor mode: nothing to change but the way out
    group("lab", "The Lab", "", { icon: "i-pin" }).append(visitorRow(m));
    return;
  }
  // This Device: most used first, then what's for slow screens and other monitors
  const dev = group("device", "This Device", NAME ? `${NAME}: every window of ${NAME} uses these` : "This browser only: open the hub with ?device=<name> to keep them under a name", { icon: "i-screen" });
  for (const f of LOCAL) dev.append(fieldRow(f, f.value(), (v) => f.save(v), false));
  const voiceSlot = dev.appendChild(document.createElement("div"));
  voiceRows().then((rows) => voiceSlot.replaceWith(...rows), (e) => { console.warn(`settings: no voice rows (${e.message})`); voiceSlot.remove(); });
  dev.append(languageRow(), fieldRow(FULL, FULL.value(), (v) => FULL.save(v), false));
  sub(dev, "For Slow Screens and Other Monitors");
  for (const f of SLOW) dev.append(fieldRow(f, f.value(), (v) => f.save(v), false));
  dev.append(screensRow(), iconRow());
  if (!data) return;
  restartNeeded.push(...(data.restart_needed || []));
  restartBar(restartNeeded, data.writable);
  const ICON = { assistant: "i-chat", lab: "i-pin", robots: "i-hand", limits: "i-warn" };
  const offNow = new Map();  // safety limits that are off in the venue file: label → true
  const showOff = () => {
    $("#limits-off").hidden = offNow.size === 0;
    $("#limits-off .pill").textContent = [...offNow.keys()].join(", ");
  };
  for (const s of data.sections) {
    const rows = group(s.id, s.title, s.risky ? "" : s.help, { icon: ICON[s.id] || "i-gear", risky: s.risky });
    if (s.id === "lab" && m) rows.append(visitorRow(m));
    for (const f of s.fields) {
      // a safety limit: marked when off; locked (a public venue or limits_locked: true) = can't be switched
      const field = f.locked ? { ...f, help: `${f.help} Locked: ${f.locked}.` } : f;
      let r = null;
      const markOff = (on) => {
        if (!f.safety) return;
        r?.classList.toggle("limit-off", !on);
        if (on) offNow.delete(f.label); else offNow.set(f.label, true);
        showOff();
      };
      r = fieldRow(field, f.value, async (value) => {
        try {
          const res = await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: f.key, value }) });
          const out = res.headers.get("Content-Type")?.includes("json") ? await res.json() : { ok: false, message: await res.text() };
          if (out.ok) { tellHub(); markOff(value); if (out.applies === "restart") needsRestart(f.label); }
          return { ok: out.ok, message: out.message };
        } catch (e) {
          return { ok: false, message: `Not saved: ${e.message}` };
        }
      }, !data.writable || !!f.locked);
      markOff(f.value);
      rows.append(r);
    }
    if (s.risky) {
      if (s.help) note(rows, s.help);
      rows.append(await shutdownRow());
    }
  }
}
start();
