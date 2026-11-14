// The settings page: draws the brain's settings list (/api/settings) and saves each change at once
// (POST /api/settings, this computer only). "This device" is kept by the brain under the device's name (the
// ?device= in the hub's address; /web/device.js), so every window of the device and the next browser under
// that name get it; a page with no name keeps it in this browser. After a save, the hub around this page (if
// any) re-reads the theme.
import { deviceName, prefs, setPref } from "/web/device.js";

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const APPLIES = {
  reload: "Saved. The hub shows it now (other screens: on their next reload).",
  next: "Saved. Applies from the next question.",
  restart: "Saved. Applies when the brain restarts (Ctrl+C, then start it again).",
};
const tellHub = () => window.parent !== window && window.parent.postMessage({ type: "lab-os:settings" }, location.origin);

/* ---------- this device (kept by the brain under its name) ---------- */
const NAME = deviceName();
const screenGet = () => prefs();
async function screenSet(k, v) {
  const r = await setPref(k, v);
  tellHub();
  return r;
}
const LOCAL = [
  { key: "quality", label: "Level of detail", help: "this device only; the theme's level otherwise (minimal for slow screens, maximal adds the extra rings and verses)",
    kind: "choice", choices: ["theme", "maximal", "full", "reduced", "minimal"], value: () => screenGet().quality || "theme",
    save: (v) => screenSet("quality", v === "theme" ? "" : v) },
  { key: "res", label: "Drawing resolution", help: "this device only: the designed hub's moving pictures drawn at fewer pixels and scaled up by the screen (softer, much lighter). auto = the screen's own, up to 2×; try 1 or 0.5 on a slow screen (the Newline). ?res= in the address wins",
    kind: "choice", choices: ["auto", "1", "0.75", "0.5"], value: () => screenGet().res || "auto",
    save: (v) => screenSet("res", v === "auto" ? "" : v) },
  { key: "sound", label: "Sound", help: "the startup and the interface sounds", kind: "bool", value: () => screenGet().sound !== false, save: (v) => screenSet("sound", v) },
  { key: "full", label: "Full screen on the start press", help: "off for a laptop you work on", kind: "bool", value: () => screenGet().full !== false, save: (v) => screenSet("full", v) },
];

/* ---------- the controls ---------- */
function control(f, value, onSave, disabled) {
  const wrap = document.createElement("div");
  wrap.className = "ctl";
  const off = disabled ? "disabled" : "";
  if (f.kind === "choice" && f.choices.length <= 5) {
    wrap.innerHTML = `<div class="seg" role="group">${f.choices.map((c) => `<button type="button" ${off} aria-pressed="${c === value}" data-v="${esc(c)}">${esc(c)}</button>`).join("")}</div>`;
    wrap.querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
      if (await onSave(b.dataset.v)) wrap.querySelectorAll("button").forEach((o) => o.setAttribute("aria-pressed", o === b));
    }));
  } else if (f.kind === "choice") {
    wrap.innerHTML = `<select ${off}>${f.choices.map((c) => `<option ${c === value ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>`;
    wrap.querySelector("select").addEventListener("change", (e) => onSave(e.target.value));
  } else if (f.kind === "bool") {
    wrap.innerHTML = `<input type="checkbox" class="switch" ${off} ${value ? "checked" : ""} aria-label="${esc(f.label)}">`;
    const box = wrap.querySelector("input");
    box.addEventListener("change", async () => { if (!(await onSave(box.checked))) box.checked = !box.checked; });
  } else if (f.kind === "number") {
    wrap.innerHTML = `<input type="number" ${off} value="${value ?? ""}" min="${f.min ?? ""}" max="${f.max ?? ""}" step="${f.step ?? "any"}"><span class="unit">${esc(f.unit)}</span>`;
    wrap.querySelector("input").addEventListener("change", (e) => onSave(e.target.value === "" ? null : Number(e.target.value)));
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
        return `<div><input type="checkbox" ${off} ${i >= 0 ? "checked" : ""} data-v="${esc(c)}"><span>${esc(c)}</span>` +
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

function fieldRow(f, value, save, disabled) {
  const row = document.createElement("div");
  row.className = "field";
  row.innerHTML = `<label>${esc(f.label)}</label><div class="help">${esc(f.help)}</div><div class="said" aria-live="polite"></div>`;
  const said = row.querySelector(".said");
  row.insertBefore(control(f, value, async (v) => {
    const r = await save(v);
    said.className = `said${r.ok ? "" : " bad"}`;
    said.textContent = r.message;
    return r.ok;
  }, disabled), said);
  return row;
}

/* ---------- this screen's other monitors (Window Management API, Chrome on this computer) ---------- */
function screensRow() {
  const row = document.createElement("div");
  row.className = "field";
  row.innerHTML = `<label>Monitors on this computer</label><div class="help">for "Open on…" → "Another monitor of this computer" in the hub's modules, and the monitors' names in other devices' "Open on…" lists (asks the browser's permission once)</div>
    <div class="ctl"><button class="btn small" type="button">Find them</button></div><ul id="screens" class="said"></ul>`;
  row.querySelector("button").addEventListener("click", async () => {
    const out = row.querySelector("#screens");
    if (!("getScreenDetails" in window)) {
      out.innerHTML = "<li>This browser can't place windows on other monitors: open the page there by hand (docs/guides/hub.md → Other monitors).</li>";
      return;
    }
    try {
      const d = await window.getScreenDetails();
      out.innerHTML = d.screens.map((s) => `<li>${esc(s.label || "Screen")} · ${s.width}×${s.height}${s === d.currentScreen ? " · this one" : ""}${s.isPrimary ? " · main" : ""}</li>`).join("");
    } catch (e) {
      out.innerHTML = `<li>Not allowed (${esc(e.message)}). Allow "window management" for this site in the browser's site settings.</li>`;
    }
  });
  return row;
}

/* ---------- the way in for voice (docs/guides/voice.md): what this screen can do ---------- */
const VOICE = { key: "voice", label: "Talking to it", kind: "choice", choices: ["push-to-talk", "dictation"],
  help: "push-to-talk: hold the mic (or Space), talk, let go, and it answers aloud. dictation: tap the mic, the words go into the ask line, fix them and send like typing",
  value: () => screenGet().voice || "push-to-talk", save: (v) => screenSet("voice", v) };
async function voiceRow() {
  const { screenCanHear } = await import("/web/voice.js");
  const [can, status] = await Promise.all([screenCanHear(), fetch("/api/status", { cache: "no-store" }).then((r) => r.json()).catch(() => null)]);
  const wake = status?.voice?.wake;
  let f = can.ok ? VOICE : { ...VOICE, help: `Push-to-talk only, and not here: ${can.why}.` };
  if (can.ok && wake?.available) {
    f = { ...VOICE, choices: [...VOICE.choices, "wake word"],
      help: `${VOICE.help}. wake word: say "${wake.phrase}" from anywhere in the room (heard on the brain's computer; this device's microphone stays open while the hub is up), and push-to-talk still works` };
  } else if (can.ok && wake) f = { ...VOICE, help: `${VOICE.help}. wake word: not here (${wake.why})` };
  return fieldRow(f, can.ok ? f.value() : "push-to-talk", (v) => f.save(v), !can.ok);
}

/* ---------- the "Lab hub" icon for this device: one tap opens the hub under its name ---------- */
function iconRow() {
  const row = document.createElement("div");
  row.className = "field";
  const url = `${location.origin}/?device=${NAME || "<name>"}`;
  const cmd = `google-chrome --app=${url} --start-fullscreen`;
  row.innerHTML = `<label>"Lab hub" icon</label><div class="help">one tap opens the hub on this device under its name, full screen (docs/guides/hub.md → Devices). The address is the brain's as this device reaches it: if the brain's IP address changes, make the icon again</div>
    <div class="ctl"><button class="btn small" type="button" data-get="linux" ${NAME ? "" : "disabled"}>Linux icon (.desktop)</button> <button class="btn small" type="button" data-get="windows" ${NAME ? "" : "disabled"}>Windows icon (.bat)</button></div>
    <ul class="said"><li>Or by hand: <code>${esc(cmd)}</code></li><li>A tablet or the Newline (Android): open <code>${esc(url)}</code> in Chrome, then ⋮ → Add to Home screen.</li></ul>`;
  const save = (name, text, type) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  row.querySelector('[data-get="linux"]').addEventListener("click", () => save(`lab-hub-${NAME}.desktop`,
    `[Desktop Entry]\nType=Application\nName=Lab hub (${NAME})\nComment=The lab's hub on this device\nExec=sh -c "google-chrome --app=${url} --start-fullscreen || chromium --app=${url} --start-fullscreen || chromium-browser --app=${url} --start-fullscreen"\nIcon=applications-science\nCategories=Science;\n`,
    "application/x-desktop"));
  row.querySelector('[data-get="windows"]').addEventListener("click", () => save(`lab-hub-${NAME}.bat`,
    `@echo off\r\nrem The lab's hub on this device (lab-os, docs/guides/hub.md -> Devices)\r\nstart "" chrome --app=${url} --start-fullscreen\r\n`,
    "application/octet-stream"));
  return row;
}

/* ---------- start ---------- */
const local = $("#this-screen");
$("#this-device-name").textContent = NAME ? `: ${NAME}` : "";
$("#this-device-help").textContent = NAME
  ? `Kept by the brain under the name "${NAME}": every window of ${NAME} (each monitor) uses them, and so does the next browser opened as ${NAME}.`
  : "This device has no name, so these are kept in this browser only. Name it by opening the hub with ?device=<name> in the address (desk, newline, quest…): the brain then keeps them under that name.";
for (const f of LOCAL) local.append(fieldRow(f, f.value(), (v) => f.save(v), false));
const voiceSlot = local.appendChild(document.createElement("div"));
voiceRow().then((row) => voiceSlot.replaceWith(row), () => voiceSlot.remove());
local.append(screensRow());
local.append(iconRow());

async function load() {
  let data;
  try {
    data = await (await fetch("/api/settings", { cache: "no-store" })).json();
  } catch {
    $("#mode").textContent = "brain not reachable";
    $("#mode").className = "pill bad";
    return;
  }
  $("#mode").textContent = data.writable ? `saved into the config files (venue: ${data.venue})` : data.why_not;
  $("#mode").className = `pill ${data.writable ? "on" : "warn"}`;
  const offNow = new Map(); // safety limits that are off in the venue file: label → true
  const showOff = () => {
    $("#limits-off").hidden = offNow.size === 0;
    $("#limits-off .pill").textContent = [...offNow.keys()].join(", ");
  };
  for (const s of data.sections) {
    const card = document.createElement("section");
    card.className = "card";
    card.innerHTML = `<div class="in"><h2>${esc(s.title)}</h2>${s.help ? `<p class="section-help">${esc(s.help)}</p>` : ""}</div>`;
    const inner = card.querySelector(".in");
    for (const f of s.fields) {
      // a safety limit: marked when off; locked (public / visit-day venue) = can't be switched
      const field = f.locked ? { ...f, help: `${f.help}. Locked: ${f.locked}` } : f;
      let row = null;
      const markOff = (on) => {
        if (!f.safety) return;
        row?.classList.toggle("limit-off", !on);
        if (on) offNow.delete(f.label); else offNow.set(f.label, true);
        showOff();
      };
      row = fieldRow(field, f.value, async (value) => {
        try {
          const res = await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: f.key, value }) });
          const r = res.headers.get("Content-Type")?.includes("json") ? await res.json() : { ok: false, message: await res.text() };
          if (r.ok) { tellHub(); markOff(value); }
          return { ok: r.ok, message: r.ok ? APPLIES[r.applies] || "Saved." : r.message };
        } catch (e) {
          return { ok: false, message: `Not saved: ${e.message}` };
        }
      }, !data.writable || !!f.locked);
      markOff(f.value);
      inner.append(row);
    }
    $("#sections").append(card);
  }
}
load();
