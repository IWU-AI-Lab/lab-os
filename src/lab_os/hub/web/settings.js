// The settings page: draws the brain's settings list (/api/settings) and saves each change at once
// (POST /api/settings, this computer only). "This screen" is kept in this browser (localStorage
// "lab-os.screen"), read by the hub. After a save, the hub around this page (if any) re-reads the theme.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const APPLIES = {
  reload: "Saved. The hub shows it now (other screens: on their next reload).",
  next: "Saved. Applies from the next question.",
  restart: "Saved. Applies when the brain restarts (Ctrl+C, then start it again).",
};
const tellHub = () => window.parent !== window && window.parent.postMessage({ type: "lab-os:settings" }, location.origin);

/* ---------- this screen (localStorage) ---------- */
const SCREEN_KEY = "lab-os.screen";
function screenGet() {
  try { return JSON.parse(localStorage.getItem(SCREEN_KEY)) || {}; } catch { return {}; }
}
function screenSet(k, v) {
  const s = screenGet();
  s[k] = v;
  try { localStorage.setItem(SCREEN_KEY, JSON.stringify(s)); } catch { /* storage blocked: nothing kept */ }
  tellHub();
}
const LOCAL = [
  { key: "quality", label: "Level of detail", help: "this screen only; the theme's level otherwise (minimal for slow screens, maximal adds the extra rings and verses)",
    kind: "choice", choices: ["theme", "maximal", "full", "reduced", "minimal"], value: () => screenGet().quality || "theme",
    save: (v) => screenSet("quality", v === "theme" ? "" : v) },
  { key: "res", label: "Drawing resolution", help: "this screen only: the designed hub's moving pictures drawn at fewer pixels and scaled up by the screen (softer, much lighter). auto = the screen's own, up to 2×; try 1 or 0.5 on a slow screen (the Newline). ?res= in the address wins",
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
  row.innerHTML = `<label>Monitors on this computer</label><div class="help">for "Show on another screen" in the hub's modules (asks the browser's permission once)</div>
    <div class="ctl"><button class="btn small" type="button">Find them</button></div><ul id="screens" class="said"></ul>`;
  row.querySelector("button").addEventListener("click", async () => {
    const out = row.querySelector("#screens");
    if (!("getScreenDetails" in window)) {
      out.innerHTML = "<li>This browser can't place windows on other monitors: open the page there by hand (docs/hub.md → Other monitors).</li>";
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

/* ---------- start ---------- */
const local = $("#this-screen");
for (const f of LOCAL) local.append(fieldRow(f, f.value(), async (v) => { f.save(v); return { ok: true, message: "Kept on this screen." }; }, false));
local.append(screensRow());

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
  for (const s of data.sections) {
    const card = document.createElement("section");
    card.className = "card";
    card.innerHTML = `<div class="in"><h2>${esc(s.title)}</h2>${s.help ? `<p class="section-help">${esc(s.help)}</p>` : ""}</div>`;
    const inner = card.querySelector(".in");
    for (const f of s.fields) {
      inner.append(fieldRow(f, f.value, async (value) => {
        try {
          const res = await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: f.key, value }) });
          const r = res.headers.get("Content-Type")?.includes("json") ? await res.json() : { ok: false, message: await res.text() };
          if (r.ok) tellHub();
          return { ok: r.ok, message: r.ok ? APPLIES[r.applies] || "Saved." : r.message };
        } catch (e) {
          return { ok: false, message: `Not saved: ${e.message}` };
        }
      }, !data.writable));
    }
    $("#sections").append(card);
  }
}
load();
