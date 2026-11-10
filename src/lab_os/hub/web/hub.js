// The plain hub (current-focus.md step 1). Parts and names follow docs/design/hub-concept.html.
// All data comes from the brain's endpoints (/api/...), including the title (the place's name);
// the few theme values come from /theme.json.
//
// Two taps (browsers allow full screen and sound only after a press):
//   tap 1 = full screen (+ unlock sound), skipped when already full screen or impossible;
//   tap 2 = start: the hub. Losing full screen afterwards brings back the start screen (tap 1).
// Back to the start screen after hub.reset_after_s with no input, never while something is in use.
// `#skip` in the address jumps straight to the hub (for quick looks on a laptop).
import { theme } from "/web/theme.js";

const $ = (s) => document.querySelector(s);
const body = document.body;
const hubCfg = theme.hub || {};

const S = {
  screen: "start", // start | hub
  module: null, // the open module ({id, title, page}) or null
  modules: [],
  startedFull: false, // started while full screen: losing it returns to the start screen
  fullFailed: false, // the browser refused full screen once: don't keep asking for tap 1
  lastInput: performance.now(),
  resetAfterMs: 180_000,
  resetting: false,
  startGuardUntil: 0, // ignore start presses right after showing the start screen
  status: null, // last /api/status (null = brain not reachable)
  clockOffset: 0, // brain clock − this screen's clock, ms
  days: null, // commits range
  chat: [], // the conversation on screen: {role: "user" | "assistant" | "error", content}
  asking: false, // a turn is streaming
};

/* ---------- talking to the brain ---------- */
async function getJSON(url) {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`hub: ${url} failed (${e.message})`);
    return null;
  }
}

/* ---------- full screen, Esc and sound ---------- */
const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
const fsPossible = () => !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
// full screen without the Fullscreen API: kiosk mode, F11, an installed app
const fullByOther = () =>
  matchMedia("(display-mode: fullscreen)").matches ||
  matchMedia("(display-mode: standalone)").matches ||
  (Math.abs(screen.width - innerWidth) <= 2 && Math.abs(screen.height - innerHeight) <= 2);
const isFull = () => !!fsElement() || fullByOther();
const needsTap1 = () => fsPossible() && !S.fullFailed && !isFull();

async function goFull() {
  unlockSound();
  const el = document.documentElement;
  try {
    if (el.requestFullscreen) await el.requestFullscreen({ navigationUI: "hide" });
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else throw new Error("no Fullscreen API");
  } catch (e) {
    console.warn(`hub: full screen refused (${e.message}); starting without it`);
    S.fullFailed = true;
  }
  lockEsc();
  renderStart();
}

// Chrome/Edge: in full screen, Esc then reaches the page ("Back") instead of leaving full screen
// (holding Esc still leaves). Needs a secure page (localhost or https).
function lockEsc() {
  if (fsElement() && navigator.keyboard?.lock) navigator.keyboard.lock(["Escape"]).catch(() => {});
}

function onFullscreenChange() {
  if (fsElement()) lockEsc();
  if (S.screen === "start") renderStart();
  else checkStillFull();
}
document.addEventListener("fullscreenchange", onFullscreenChange);
document.addEventListener("webkitfullscreenchange", onFullscreenChange);

function checkStillFull() {
  if (S.screen === "hub" && S.startedFull && !isFull() && !busy()) toStart("full screen was left");
}

// Sound is unlocked by the first press (browsers' rule). Phase 1 plays none; the reveal adds them.
let audioCtx = null;
function unlockSound() {
  try {
    audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
    audioCtx.resume?.();
  } catch {
    // no WebAudio: the hub works silently
  }
}

/* ---------- start screen ---------- */
// say how to start with the inputs this device has (a keyboard can't be detected; keys always work)
function startWords() {
  const ways = [];
  if (navigator.maxTouchPoints > 0) ways.push("tap");
  if (matchMedia("(any-pointer: fine)").matches) ways.push("click");
  ways.push("press any key");
  const text = ways.length > 1 ? `${ways.slice(0, -1).join(", ")} or ${ways.at(-1)}` : ways[0];
  return `${text[0].toUpperCase()}${text.slice(1)} to start`;
}

function renderStart() {
  body.dataset.tap = needsTap1() ? "full" : "start";
  $("#ign-what").textContent = startWords();
}

function onStartPress() {
  if (S.screen !== "start" || performance.now() < S.startGuardUntil) return;
  if (needsTap1()) {
    S.startGuardUntil = performance.now() + 400; // a quick double tap shouldn't also start
    goFull();
  } else {
    unlockSound();
    start();
  }
}

const IGNORED_KEYS = new Set(["Escape", "Tab", "Shift", "Control", "Alt", "Meta", "CapsLock"]);
$("#ignite").addEventListener("click", onStartPress);
document.addEventListener("keydown", (e) => {
  if (S.screen !== "start" || e.repeat || IGNORED_KEYS.has(e.key) || /^F\d+$/.test(e.key)) return;
  e.preventDefault();
  onStartPress();
});

function start() {
  S.startedFull = isFull();
  S.screen = "hub";
  body.classList.remove("waiting");
  $("#ignite").hidden = true;
  $("#hub").hidden = false;
  noteInput();
  refreshFacts();
  quick.focus();
}

function toStart(why) {
  console.info(`hub: back to the start screen (${why})`);
  closeModule();
  clearChat(); // the next visitor shouldn't see the last one's questions
  S.screen = "start";
  body.classList.add("waiting");
  $("#hub").hidden = true;
  $("#ignite").hidden = false;
  S.startGuardUntil = performance.now() + 600;
  renderStart();
}

/* ---------- nobody there: back to the start screen ---------- */
const busy = () => (S.status?.in_use || []).length > 0;
function noteInput() {
  S.lastInput = performance.now();
}
const INPUT_EVENTS = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];
for (const ev of INPUT_EVENTS) addEventListener(ev, noteInput, { passive: true, capture: true });

async function checkReset() {
  if (S.screen !== "hub" || S.resetting) return;
  if (performance.now() - S.lastInput < S.resetAfterMs) return;
  S.resetting = true;
  const st = await pollStatus(); // fresh: never reset while teleop has the arm
  S.resetting = false;
  if (st && st.in_use.length) return; // still in use; check again on the next tick
  if (performance.now() - S.lastInput >= S.resetAfterMs) toStart("nobody there");
}

/* ---------- modules: open inside the hub (no page load, so full screen stays) ---------- */
function renderMods() {
  const l = $("#mods .l"), r = $("#mods .r");
  l.replaceChildren();
  r.replaceChildren();
  S.modules.forEach((m, i) => {
    const b = document.createElement("button");
    b.className = "mod panel";
    b.type = "button";
    b.dataset.module = m.id;
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = m.title;
    b.appendChild(name);
    b.addEventListener("click", () => openModule(m));
    (i % 2 ? r : l).appendChild(b); // alternate left and right of the core
  });
  body.dataset.mods = S.modules.length;
}

function openModule(m) {
  if (S.module) return;
  S.module = m;
  const frame = document.createElement("iframe");
  frame.src = m.page;
  frame.title = m.title;
  frame.allow = "xr-spatial-tracking; fullscreen";
  frame.addEventListener("load", () => watchFrame(frame));
  $("#mod-slot").replaceChildren(frame);
  $("#mod-title").textContent = m.title;
  $("#module").hidden = false;
  body.dataset.mod = m.id;
  $("#orb-dock").appendChild($("#orb"));
  $("#mod-back").focus();
}

function closeModule() {
  if (!S.module) return;
  // removing the page closes its connection: the arm freezes (dead-man) and control is free
  $("#mod-slot").replaceChildren();
  $("#module").hidden = true;
  delete body.dataset.mod;
  $(".core").prepend($("#orb"));
  S.module = null;
}
$("#mod-back").addEventListener("click", closeModule);

// The module page is on the same brain, so the hub can hear its keys and taps: they count as
// input (no reset while someone uses it), and Esc there means Back too.
function watchFrame(frame) {
  try {
    const w = frame.contentWindow;
    for (const ev of INPUT_EVENTS) w.addEventListener(ev, noteInput, { passive: true, capture: true });
    w.addEventListener("keydown", (e) => e.key === "Escape" && onEsc(e, w.document));
  } catch (e) {
    console.warn(`hub: can't watch the module page (${e.message}); use the Back button`);
  }
}

function onEsc(e, doc) {
  if (!$("#chat").hidden) {
    e.preventDefault();
    closeChat();
    return;
  }
  if (!S.module) return;
  // In desktop control the first Esc only leaves it (the teleop page's own Esc); the next is Back.
  if (doc.pointerLockElement) {
    doc.exitPointerLock();
    return;
  }
  e.preventDefault();
  closeModule();
}
document.addEventListener("keydown", (e) => e.key === "Escape" && onEsc(e, document));

/* ---------- status strip, the assistant's state, the clock ---------- */
async function pollStatus() {
  const st = await getJSON("/api/status");
  S.status = st;
  renderStatus(st);
  return st;
}

function renderStatus(st) {
  const net = $("#f-net"), ai = $("#f-ai");
  if (!st) {
    net.textContent = "Brain not reachable";
    net.classList.add("off");
    ai.textContent = "AI not connected";
    ai.classList.add("off");
    setAssistant("offline", 0);
    return;
  }
  S.clockOffset = st.time_ms - Date.now();
  for (const el of [$("#f-venue"), $("#ign-venue")]) el.textContent = `Venue: ${st.venue}`;
  net.textContent =
    st.internet === true ? "Internet: online" : st.internet === false ? "Internet: offline" : "Internet: checking…";
  net.classList.toggle("off", st.internet !== true);
  ai.textContent = aiText(st.ai);
  ai.classList.toggle("off", st.ai.connected !== true || !!st.ai.paused);
  showPaused(st.ai.paused);
  setAssistant(st.assistant.state, st.assistant.loudness);
  checkStillFull();
}

// the picture only reads the state; it stays a plain circle until the reveal
function setAssistant(state, loudness) {
  for (const el of [$(".core"), $("#orb-dock")]) {
    el.dataset.state = state;
    el.style.setProperty("--loud", loudness);
  }
  $("#state-word").textContent = state;
}

function clockText() {
  const d = new Date(Date.now() + S.clockOffset);
  const p = (n) => String(n).padStart(2, "0");
  if (theme.clock === "12h") {
    return [`${d.getHours() % 12 || 12}:${p(d.getMinutes())}:${p(d.getSeconds())}`, d.getHours() < 12 ? "AM" : "PM"];
  }
  return [`${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`, ""];
}

function tick() {
  const [t, ap] = clockText();
  for (const [c, a] of [["#clock", "#ampm"], ["#ign-clock", "#ign-ampm"]]) {
    $(c).textContent = t;
    $(a).textContent = ap;
  }
  checkReset();
}

function aiText(ai) {
  if (ai.paused) return "AI: paused";
  const name = ai.where ? `${ai.setup} (${ai.where})` : ai.setup;
  if (ai.connected === true) return `AI: ${name}`;
  if (ai.connected === false) return "AI not connected";
  return `AI: ${name}, not checked yet`;
}

/* ---------- typed chat: ask line, the answer under the core, the conversation page ---------- */
const quick = $("#quick");

function showError(text) {
  $("#errmsg").textContent = text || "";
  $("#errmsg").hidden = !text;
}
let pausedShown = null;
function showPaused(why) {
  // the chat's own full sentence while it's paused (no key, budget used up); cleared when it isn't
  why = why || null;
  if (why === pausedShown) return;
  if (why || $("#errmsg").textContent === pausedShown) showError(why);
  pausedShown = why;
}

function renderLog() {
  $("#chat-n").textContent = S.chat.filter((m) => m.role === "user").length || "";
  if ($("#chat").hidden) return;
  const log = $("#log-chat");
  log.replaceChildren(
    ...S.chat.map((m) => {
      const div = document.createElement("div");
      div.className = `msg ${m.role}`;
      div.textContent = m.content;
      return div;
    }),
  );
  log.scrollTop = log.scrollHeight;
}

async function ask(text) {
  text = text.trim();
  if (!text || S.asking) return;
  S.asking = true;
  showError(null);
  const answer = { role: "assistant", content: "" };
  S.chat.push({ role: "user", content: text });
  $("#reply .q").textContent = text;
  $("#reply .a").textContent = "";
  renderLog();
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) if (line.trim()) onChatEvent(JSON.parse(line), answer);
    }
  } catch (e) {
    onChatEvent({ type: "error", message: "The brain didn't answer, so the question was lost. Try again." }, answer);
    console.warn(`hub: chat failed (${e.message})`);
  }
  S.asking = false;
  noteInput();
  renderSpend(await getJSON("/api/spend")); // what that answer cost
}

function onChatEvent(ev, answer) {
  if (ev.type === "state") setAssistant(ev.state, ev.state === "speaking" ? 1 : 0);
  else if (ev.type === "text") {
    if (!answer.content) S.chat.push(answer);
    answer.content += ev.text;
    $("#reply .a").textContent = answer.content;
    $("#reply .a").scrollTop = $("#reply .a").scrollHeight;
    renderLog();
  } else if (ev.type === "error") {
    showError(ev.message);
    S.chat.push({ role: "error", content: ev.message });
    renderLog();
  }
}

function clearChat() {
  S.chat = [];
  $("#reply .q").textContent = "";
  $("#reply .a").textContent = "";
  quick.value = "";
  $("#ask").value = "";
  showError(pausedShown);
  closeChat();
  renderLog();
  fetch("/api/chat/clear", { method: "POST" }).catch(() => {});
}

function openChat() {
  $("#chat").hidden = false;
  renderLog();
  $("#ask").focus();
}
function closeChat() {
  if ($("#chat").hidden) return;
  $("#chat").hidden = true;
  if (S.screen === "hub") quick.focus();
}

$("#quick-form").addEventListener("submit", (e) => {
  e.preventDefault();
  ask(quick.value);
  quick.value = "";
});
$("#ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  ask($("#ask").value);
  $("#ask").value = "";
});
$("#open-chat").addEventListener("click", openChat);
$("#chat-back").addEventListener("click", closeChat);
$("#reply").addEventListener("click", openChat); // tap the answer to see the whole conversation

// typing anywhere on the hub lands in the ask line (theme: hub.type_to_chat)
document.addEventListener("keydown", (e) => {
  if (S.screen !== "hub" || S.module || !$("#chat").hidden || hubCfg.type_to_chat === false) return;
  if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.target.closest?.("input, textarea, button, [contenteditable]")) return;
  quick.focus(); // the key's character then goes into the ask line
});

async function loadChat() {
  // after a reload: the conversation the brain still has (cleared by the reset)
  const c = await getJSON("/api/chat");
  if (!c) return;
  S.chat = c.messages.map((m) => ({ role: m.role, content: m.content }));
  const lastQ = [...S.chat].reverse().find((m) => m.role === "user");
  const lastA = S.chat.at(-1)?.role === "assistant" ? S.chat.at(-1) : null;
  $("#reply .q").textContent = lastQ?.content || "";
  $("#reply .a").textContent = lastA?.content || "";
  renderLog();
}

/* ---------- panels: Current Project, AI Spend, Commits ---------- */
async function refreshFacts() {
  const [project, spend, commits] = await Promise.all([
    getJSON("/api/project"),
    getJSON("/api/spend"),
    getJSON(`/api/commits?days=${S.days}`),
  ]);
  renderProject(project);
  renderSpend(spend);
  renderCommits(commits);
}

const usd = (n) => `$${n.toFixed(2)}`;
function renderSpend(s) {
  $("#s-panel").hidden = !s?.available; // hidden on a public venue
  if (!s?.available) return;
  $("#money").textContent = usd(s.spent_usd);
  const budget = s.budget_usd;
  $("#meter").hidden = !budget;
  if (budget) $("#meter-fill").style.setProperty("--fill", Math.min(1, s.spent_usd / budget));
  const chats = `${s.chats} chat${s.chats === 1 ? "" : "s"}`;
  $("#s-budget").textContent = budget ? `of ${usd(budget)} budget · ${chats}` : `no budget set · ${chats}`;
}

function renderProject(p) {
  $("#p-panel").hidden = !p?.available;
  if (!p?.available) return;
  $("#p-focus").textContent = p.focus || "";
  $("#p-step").textContent = `Step ${p.step} of ${p.of}`;
  $("#p-next").textContent = p.next || "all steps done";
}

const dayLabel = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

function renderCommits(c) {
  $("#c-panel").hidden = !c?.available;
  if (!c?.available) return;
  $("#commit-total").textContent = c.total;
  const max = Math.max(1, ...c.per_day.map((d) => d.count));
  $("#spark").replaceChildren(
    ...c.per_day.map((d) => {
      const bar = document.createElement("i");
      bar.style.setProperty("--h", d.count / max);
      bar.classList.toggle("zero", d.count === 0);
      bar.title = `${dayLabel(d.date)}: ${d.count} commit${d.count === 1 ? "" : "s"}`;
      return bar;
    }),
  );
  $("#ax0").textContent = dayLabel(c.per_day[0].date);
  $("#ax1").textContent = "today";
}

function renderRange() {
  const days = hubCfg.commits_days?.length ? hubCfg.commits_days : [7, 14, 30];
  S.days = days.includes(14) ? 14 : days[0]; // the first view shows 14
  $("#range").replaceChildren(
    ...days.map((n) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = `${n}d`;
      b.setAttribute("aria-label", `${n} days`);
      b.setAttribute("aria-pressed", n === S.days);
      b.addEventListener("click", async () => {
        S.days = n;
        for (const o of $("#range").children) o.setAttribute("aria-pressed", o === b);
        renderCommits(await getJSON(`/api/commits?days=${n}`));
      });
      return b;
    }),
  );
}

/* ---------- boot ---------- */
async function boot() {
  renderRange();
  const cfg = await getJSON("/api/hub");
  const title = cfg?.title || "Hub"; // the place's name (place.yaml), not a theme value
  document.title = title;
  $("#brand").textContent = title;
  S.modules = cfg?.modules || [];
  if (cfg?.reset_after_s) S.resetAfterMs = cfg.reset_after_s * 1000;
  renderMods();
  renderStart();
  await Promise.all([pollStatus(), loadChat()]);
  tick();
  setInterval(tick, 250);
  setInterval(pollStatus, 3000);
  setInterval(() => S.screen === "hub" && refreshFacts(), 60_000);
  if (location.hash === "#skip") start();
}
boot();
