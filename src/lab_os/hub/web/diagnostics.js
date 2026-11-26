// Diagnostics (quick job 135): a card for each device, made to fit its kind, from GET /api/diagnostics every
// second. ?device=<words> shows one device: its id, name or display name, or words such as "the Raspbot" or
// "white arm" (the assistant passes what the person said). Only reads; nothing here changes a device.

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ico = (id) => `<svg class="ico"><use href="/web/design/icons.svg#${id}"/></svg>`;
const POLL_MS = 1000;
const KIND = {
  arm: ["i-arm", "Arm", "arm robot"], leader: ["i-leader", "Leader arm", "arm leader"], robot: ["i-pi", "Robot", "robot car raspbot"],
  camera: ["i-cam", "Camera", "camera cam"], screen: ["i-pc", "Computer or screen", "screen computer desktop monitor display"],
  headset: ["i-headset", "Headset", "headset quest vr"], usb: ["i-chip", "USB device", "usb"],
};
const kindOf = (d) => KIND[d.kind] || KIND.usb;
const STOP_WORDS = new Set(["the", "a", "an", "for", "of", "on", "show", "me", "diagnostics", "device"]);

// ---------- one device from words ----------
const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
export function pick(devices, words) {
  const want = norm(words);
  if (!want) return null;
  const flat = want.replace(/ /g, "");
  const exact = devices.find((d) => [d.id, d.name].some((n) => norm(n).replace(/ /g, "") === flat));
  if (exact) return exact;
  const tokens = want.split(" ").filter((t) => !STOP_WORDS.has(t));
  if (!tokens.length) return null;
  const scored = devices.map((d) => {
    const hay = `${norm(d.id)} ${norm(d.name)} ${kindOf(d)[2]}`;
    const flatHay = hay.replace(/ /g, "");
    const hits = tokens.filter((t) => hay.split(" ").some((w) => w.startsWith(t)) || flatHay.includes(t)).length;
    return { d, hits, named: tokens.some((t) => norm(d.name).includes(t)) };
  }).filter((x) => x.hits === tokens.length);
  scored.sort((a, b) => (b.named - a.named) || (b.d.connected - a.d.connected));
  return scored[0]?.d || null;
}

// ---------- the panels ----------
const num = (v, digits = 1, unit = "") => (v === null || v === undefined ? "—" : `<span class="num">${Number(v).toFixed(digits)}</span>${unit}`);
const stat = (label, html) => `<div><dt>${esc(label)}</dt><dd>${html}</dd></div>`;
function armPanel(p) {
  const lines = [];
  if (p.fake) lines.push(`<p class="what">The fake arm has no motors to read: only the positions.</p>`);
  else if (p.health === "no_answer") lines.push(`<p class="what bad">The motors do not answer. Is their power on?</p>`);
  else if (p.health === "waiting") lines.push(`<p class="what">Reading the motors…</p>`);
  if (p.problem) lines.push(`<p class="what bad">${esc(p.problem)}</p>`);
  const rows = p.motors.map((m) => `<tr class="${m.state}"><td>${esc(m.joint)}</td><td class="n">${num(m.position_deg, 1, "°")}</td>`
    + `<td class="n ${m.state === "ok" ? "" : m.state}">${num(m.temp_c, 0, " °C")}</td><td class="n">${num(m.load_pct, 1, " %")}</td><td class="n">${num(m.volts, 1, " V")}</td>`
    + `<td class="${m.errors.length ? "bad" : ""}">${m.errors.length ? esc(m.errors.map((e) => e[0].toUpperCase() + e.slice(1)).join(", ")) : m.temp_c === null ? "—" : "None"}</td></tr>`).join("");
  const facts = `<dl class="stats">${stat("Model", esc(p.model || "—"))}${stat("Control", p.frozen ? "Holding still" : "Ready")}`
    + `${stat("Motors read", p.read_s_ago === null ? "—" : `${num(p.read_s_ago, 0)} s ago`)}</dl>`;
  return `${lines.join("")}${facts}<table class="motors"><thead><tr><th>Motor</th><th class="n">Position</th><th class="n">Temperature</th><th class="n">Load</th><th class="n">Voltage</th><th>Errors</th></tr></thead><tbody>${rows}</tbody></table>`;
}
const POWER = { ok: ["OK", "ok"], low: ["Low now", "bad"], was_low: ["Was low since the start", "warn"], "?": ["Not known", ""] };
function robotPanel(p) {
  const pi = p.pi || {};
  const power = pi.power ? POWER[pi.power] || POWER["?"] : null;
  const link = p.connected
    ? `<span class="ok">Connected</span>${p.round_trip_ms !== null && p.round_trip_ms !== undefined ? ` · ${num(p.round_trip_ms, 0, " ms")}` : ""}`
    : `<span class="bad">Not connected</span>`;
  const wifi = pi.wifi_dbm === undefined ? "—" : `${num(pi.wifi_dbm, 0, " dBm")}${pi.wifi_quality !== undefined ? ` · ${pi.wifi_quality}/70` : ""}`;
  return (p.message ? `<p class="what bad">${esc(p.message)}</p>` : "")
    + `<dl class="stats">${stat("Connection", link)}${stat("Address", esc(p.address || (p.fake ? "None (fake)" : "—")))}`
    + stat("Power", power ? `<span class="${power[1]}">${power[0]}</span>${pi.input_v ? ` · ${num(pi.input_v, 2, " V")}` : ""}` : p.connected ? "Not reported (an older program)" : "—")
    + stat("Temperature", pi.temp_c === undefined ? "—" : num(pi.temp_c, 1, " °C")) + stat("Wi-Fi", wifi)
    + stat("Distance", p.distance_mm === null || p.distance_mm === undefined ? "—" : num(p.distance_mm / 10, 1, " cm"))
    + stat("Motion", esc(p.moving ? p.moving.replace(/-/g, " ") : "Still")) + stat("Control", esc({ free: "Free", you: "This page", other: "Another page" }[p.control] || p.control || "—"))
    + stat("Camera", p.camera ? "Yes" : "No") + `</dl>`
    + (power ? `<p class="what">The board has no battery reading. A low battery shows as low power at the Pi.</p>` : "");
}
function cameraPanel(d, one) {
  const p = d.panel || {};
  const pic = one && d.connected ? `<div class="pic"><img alt="${esc(d.name)}" data-cam="${esc(d.name)}"></div>` : "";
  if (!p.open) return `<p class="what">Closed. It opens while a page shows its picture${one ? " (as this page does now)" : ""}.</p>${pic}`;
  return `<dl class="stats">${stat("Picture rate", `${num(p.fps, 1)} a second`)}${stat("Size", p.width ? `${p.width} × ${p.height}` : "—")}`
    + `${stat("To the pages", `${num(p.sent_fps, 0)} a second at most`)}</dl>${p.error ? `<p class="what bad">${esc(p.error)}</p>` : ""}${pic}`;
}
function screenPanel(p) {
  if (!p.windows) return "";
  const wins = p.windows.map((w, i) => `<div><span>${esc(w.label || (p.windows.length > 1 ? `Screen ${i + 1}` : "Screen"))}</span>`
    + `<span>${w.width ? `${w.width} × ${w.height}` : "—"}</span><span>${esc(w.showing || (w.stage === "start" ? "Start screen" : "The hub"))}</span></div>`).join("");
  return `<dl class="stats">${stat("Address", esc(p.address || "—"))}${stat("Brain's computer", p.here ? "Yes" : "No")}</dl><div class="wins">${wins}</div>`;
}
function card(d, one) {
  const [icon, word] = kindOf(d);
  const p = d.panel || {};
  let body = "";
  // the Raspbot the brain tries to reach: its connection panel says why it does not answer
  if (d.kind === "robot" && "pi" in p) body = robotPanel(p);
  else if (!d.connected) body = `<p class="what">Off now.${d.last_seen ? ` Last seen ${esc(d.last_seen)}.` : ""}</p>`;
  else if (d.kind === "arm" && p.motors) body = armPanel(p);
  else if (d.kind === "camera") body = cameraPanel(d, one);
  else if (d.kind === "screen") body = screenPanel(p);
  const what = d.connected && d.what ? `<p class="what${d.bad ? " bad" : ""}">${esc(d.what)}</p>` : "";
  const via = d.connected && d.via ? `<dl class="stats">${stat("Connected by", esc(d.via))}</dl>` : "";
  const tag = p.fake ? `<span class="tag">Fake</span>` : "";
  const state = d.connected ? `<span class="pill on">Connected</span>` : `<span class="pill off">Off</span>`;
  const more = one ? "" : `<button class="btn small" type="button" data-one="${esc(d.id)}" title="Only this device">${ico("i-open")}</button>`;
  return `<section class="card dev${d.connected ? "" : " off"}" data-id="${esc(d.id)}"><div class="in">
    <div class="head">${ico(icon)}<b title="${esc(word)}">${esc(d.name)}</b>${tag}${state}${more}</div>${what}${body || via}</div></section>`;
}

// ---------- the page ----------
const params = new URLSearchParams(location.search);
let want = params.get("device") || "";
let devices = [];
function render() {
  const grid = $("#grid");
  const one = want ? pick(devices, want) : null;
  $("#msg").textContent = want && !one && devices.length ? `No device matches "${want}". Here are all the devices.` : "";
  $("#all").hidden = !one;
  const shown = one ? [one] : devices;
  grid.classList.toggle("one", !!one);
  // keep a camera's picture element (it loads on its own timer); redraw the rest
  grid.innerHTML = shown.length ? shown.map((d) => card(d, !!one)).join("") : `<p class="what">The brain lists no device yet.</p>`;
  const on = devices.filter((d) => d.connected).length;
  const problems = devices.filter((d) => d.connected && (d.bad || d.panel?.health === "no_answer" || d.panel?.motors?.some((m) => m.state === "bad") || d.panel?.pi?.power === "low")).length;
  $("#sum").innerHTML = `<span class="chip"><b>Connected</b> ${on}</span><span class="chip"><b>Off</b> ${devices.length - on}</span>`
    + `<span class="pill ${problems ? "bad" : "on"}">${problems ? `${problems} with a problem` : "No problem found"}</span>`;
  for (const img of grid.querySelectorAll("img[data-cam]")) loadPicture(img);
}
let picTimer = 0;
function loadPicture(img) {
  // a camera opens while a page asks for its picture: the one-device view asks twice a second
  clearTimeout(picTimer);
  const next = () => {
    const live = document.querySelector(`img[data-cam="${CSS.escape(img.dataset.cam)}"]`);
    if (!live) return;
    live.src = `/api/camera-feed/${encodeURIComponent(img.dataset.cam)}?t=${Date.now()}`;
    picTimer = setTimeout(next, 500);
  };
  next();
}
async function poll() {
  try {
    const r = await fetch("/api/diagnostics", { cache: "no-store" });
    devices = (await r.json()).devices || [];
    render();
  } catch (e) {
    $("#msg").textContent = `The brain didn't answer (${e.message}). Trying again.`;
  }
  setTimeout(poll, POLL_MS);
}
$("#grid").addEventListener("click", (e) => {
  const b = e.target.closest("[data-one]");
  if (!b) return;
  want = b.dataset.one;
  history.replaceState(null, "", `?device=${encodeURIComponent(want)}`);
  render();
});
$("#all").addEventListener("click", () => {
  want = "";
  history.replaceState(null, "", location.pathname);
  render();
});
poll();
