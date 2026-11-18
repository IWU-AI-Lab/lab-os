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
  { key: "startup_video", label: "Startup as a video", help: "a test for screens where the startup stutters: the designed hub plays a recording of the jump instead of drawing it (the words stay live, the hub after it too). Recorded at full and maximal detail (Level of detail above picks which) for the hyperspace startup and a 16:9 screen; otherwise drawn as usual", kind: "bool", value: () => screenGet().startup_video === true, save: (v) => screenSet("startup_video", v ? true : "") },
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
  } else if (f.kind === "range") {
    // a slider: saved when let go; the words under it say what the number means
    wrap.innerHTML = `<input type="range" ${off} value="${value}" min="${f.min}" max="${f.max}" step="1" aria-label="${esc(f.label)}"><span class="unit"></span>`;
    const slider = wrap.querySelector("input"), unit = wrap.querySelector(".unit");
    const show = () => (unit.textContent = f.words ? f.words(Number(slider.value)) : slider.value);
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
  const rows = [fieldRow(f, can.ok ? f.value() : "push-to-talk", (v) => f.save(v), !can.ok)];
  if (can.ok && wake?.available) rows.push(fieldRow(SENSITIVITY, SENSITIVITY.value(), (v) => SENSITIVITY.save(v), false));
  return rows;
}

/* ---------- how readily this device hears the wake word (docs/guides/voice.md → "Sensitivity") ---------- */
const SENS_WORDS = { 1: "fewest false wakes", 3: "quiet room", 5: "the default", 7: "noisy room or weak microphone", 9: "hears the most" };
const SENSITIVITY = { key: "wake_sensitivity", label: "Wake word sensitivity", kind: "range", min: 1, max: 9,
  help: "this device only. Higher hears \"hey Jarvis\" more readily: for a noisy room or a weak microphone. Too high and it may wake by itself; lower it if it does. 5 is openWakeWord's default. Applies at once",
  words: (v) => `${v}${SENS_WORDS[v] ? ` · ${SENS_WORDS[v]}` : ""}`,
  value: () => Number(screenGet().wake_sensitivity) || 5,
  save: (v) => screenSet("wake_sensitivity", v === 5 ? "" : v) };

/* ---------- the assistant's languages for this device (quick job 33): what it hears, what it answers in ---------- */
const LANG_NAMES = { "": "Any", en: "English" };  // the brain's codes (lab_os/ai/languages.py) → words
function languageRow() {
  const row = document.createElement("div");
  row.className = "field";
  row.innerHTML = `<label>Assistant language</label><div class="help">this device only. Input: the language speech-to-text expects (OpenAI's voice; the Gemini fallback has no such setting). Output: the language it answers in, typed or spoken, whatever it was asked in. Any = it decides. Applies from the next question</div><div class="ctl pair"></div><div class="said" aria-live="polite"></div>`;
  const said = row.querySelector(".said"), pair = row.querySelector(".pair");
  for (const [key, label] of [["hear_in", "Input"], ["answer_in", "Output"]]) {
    const f = { key, label: `${label} language`, kind: "choice", choices: Object.values(LANG_NAMES) };
    const line = pair.appendChild(document.createElement("div"));
    line.innerHTML = `<span class="unit">${label}</span>`;
    line.append(control(f, LANG_NAMES[screenGet()[key] || ""] || "Any", async (v) => {
      const r = await screenSet(key, Object.keys(LANG_NAMES).find((k) => LANG_NAMES[k] === v) ?? "");
      said.className = `said${r.ok ? "" : " bad"}`;
      said.textContent = r.message;
      return r.ok;
    }, false));
  }
  return row;
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
voiceRow().then((rows) => voiceSlot.replaceWith(...rows), () => voiceSlot.remove());
local.append(languageRow());
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
  $("#sections").append(await shutdownCard());
}

/* ---------- shut lab-os down (quick job 6): the brain's computer only, never on a public venue ---------- */
async function shutdownCard() {
  const r = await fetch("/api/shutdown", { cache: "no-store" }).then((x) => x.json()).catch(() => null);
  const card = document.createElement("section");
  card.className = "card";
  card.innerHTML = `<div class="in"><h2><svg class="ico"><use href="/web/design/icons.svg#i-power"/></svg>Shut down</h2>
    <div class="field"><label>Shut down lab-os</label>
      <div class="help">Stops any move, lets go of the arm (as Ctrl+C in its terminal does), closes the cameras and microphones and stops the brain. Every screen then says lab-os is off; the "Start lab-os" icon starts it again</div>
      <div class="ctl"><button class="btn small" type="button" data-ask ${r?.allowed ? "" : "disabled"}>Shut down…</button></div>
      <div class="said bad" aria-live="polite"></div></div></div>`;
  const said = card.querySelector(".said"), ctl = card.querySelector(".ctl");
  if (!r?.allowed) { said.textContent = r?.why_not || "The brain didn't answer."; return card; }
  card.querySelector("[data-ask]").addEventListener("click", async () => {
    const now = await fetch("/api/shutdown", { cache: "no-store" }).then((x) => x.json()).catch(() => null);
    said.textContent = `${now?.warning ? `${now.warning} ` : ""}Shut down lab-os now?`;
    ctl.innerHTML = `<button class="btn small" type="button" data-cancel>Cancel</button><button class="btn small go" type="button" data-go>Shut down</button>`;
    ctl.querySelector("[data-cancel]").addEventListener("click", async () => card.replaceWith(await shutdownCard()));
    ctl.querySelector("[data-go]").addEventListener("click", async () => {
      ctl.querySelectorAll("button").forEach((b) => (b.disabled = true));
      said.textContent = "Shutting down…";
      try {
        const res = await fetch("/api/shutdown", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: NAME }) });
        if (!res.ok) throw new Error(await res.text());
        (await import("/web/off.js")).showOff({ from: NAME, time_ms: Date.now() });
      } catch (e) {
        said.textContent = `Not shut down: ${e.message}`;
        ctl.querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    });
  });
  return card;
}
load();
