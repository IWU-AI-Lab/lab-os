// The plain hub (docs/plan/current-focus.md step 1). Parts and names follow docs/design/hub-concept.html.
// All data comes from the brain's endpoints (/api/...), including the title (the place's name);
// the few theme values come from /theme.json.
//
// Two taps (browsers allow full screen and sound only after a press):
//   tap 1 = full screen (+ unlock sound), skipped when already full screen or impossible;
//   tap 2 = start: the hub. Losing full screen afterwards brings back the start screen (tap 1).
// Back to the start screen after hub.reset_after_s with no input, never while something is in use.
// `#skip` in the address jumps straight to the hub (for quick looks on a laptop).
import { fsElement, fsPossible, fullscreenButton, isFull } from "/web/fullscreen.js";
import { theme } from "/web/theme.js";
import { connectDevice, fillOpenOn, fillSent, isPrefsKey, prefs, shouldRefill } from "/web/device.js";
import { WAKE_QUIET_MS, assistantLanguage, createVoice, revealPacer, silenceWatch, wayIn } from "/web/voice.js";

const $ = (s) => document.querySelector(s);
const body = document.body;
const hubCfg = theme.hub || {};

const S = {
  screen: "start", // start | hub
  module: null, // the open module ({id, title, page}) or null
  sentFrom: null, // the open module came from another device: {from, from_window}
  modules: [],
  startedFull: false, // started while full screen: losing it returns to the start screen
  fullFailed: false, // the browser refused full screen once: don't keep asking for tap 1
  lastInput: performance.now(),
  resetAfterMs: 1_800_000,
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
// (fsElement, isFull, …: /web/fullscreen.js, shared with every page)
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

// the strip's full-screen button: in case something left full screen (a swipe, a system pop-up);
// does what tap 1 does, and says why where the browser can't
fullscreenButton($("#fs-btn"), {
  onFull: () => {
    S.fullFailed = false;
    lockEsc();
  },
});

// what the Quest sees (quick job 36): scrcpy in a window on the brain's computer. Only there, and only
// once it's installed (lab-os quest-view --install)
async function pollQuestView() {
  const q = await getJSON("/api/quest-view");
  const b = $("#qv-btn");
  b.hidden = !q?.here || !q.installed;
  if (b.hidden) return;
  b.setAttribute("aria-pressed", q.running);
  b.textContent = q.running ? "Close Quest view" : "Quest view";
  b.title = q.running ? `The view of ${q.headset} is open` : q.why_not || "Show what the Quest sees, in a window here";
}
$("#qv-btn").addEventListener("click", async () => {
  const on = $("#qv-btn").getAttribute("aria-pressed") === "true";
  try {
    const res = await fetch(`/api/quest-view/${on ? "stop" : "start"}`, { method: "POST", body: "{}" });
    const r = await res.json();
    if (!r.ok) showError(r.message);
  } catch (e) {
    showError(`The Quest's view didn't ${on ? "close" : "open"}: ${e.message}`);
  }
  pollQuestView();
});
pollQuestView();
setInterval(pollQuestView, 5000);

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
    voice.unlock();
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

// quiet: opened for a page sent from another device: no greeting, no fresh conversation
function start(quiet = false) {
  S.startedFull = isFull();
  S.screen = "hub";
  body.classList.remove("waiting");
  $("#ignite").hidden = true;
  $("#hub").hidden = false;
  noteInput();
  refreshFacts();
  if (!quiet) greet();
  quick.focus();
  device.update();
}

// The start press: a fresh conversation whose first message is the greeting (built by the brain
// from real facts, else the persona's line). Shown as plain text under the title until the reset.
async function greet() {
  const res = await fetch("/api/chat/start", { method: "POST" }).catch(() => null);
  const g = res?.ok ? await res.json() : null;
  if (!g || S.screen !== "hub") return;
  $("#boot-greet").textContent = g.text;
  if (!S.chat.some((m) => m.role === "user")) S.chat = [{ role: "assistant", content: g.text }];
  renderLog();
  showRestore(g.previous);
  // spoken too, where voice works at the brain (with how to talk, where this screen has a microphone)
  const way = wayIn() === "wake_word" && !S.status?.voice?.wake?.available ? "push_to_talk" : wayIn();
  if (voice.greet(voice.can().ok ? way : "none")) {
    VS.greeting = true;
    voice.playHeld();
  }
}

function toStart(why) {
  console.info(`hub: back to the start screen (${why})`);
  closeModule();
  dictateCancel();
  VW?.cancel();
  VW = null;
  voice.cancel();
  voice.stopSpeaking();
  voice.wake(false);
  renderWakeDot();
  endVoice();
  clearChat(); // the next visitor shouldn't see the last one's questions
  S.screen = "start";
  body.classList.add("waiting");
  $("#hub").hidden = true;
  $("#ignite").hidden = false;
  S.startGuardUntil = performance.now() + 600;
  renderStart();
  device.update();
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

function openModule(m, sentFrom = null) {
  if (S.module) return;
  S.module = m;
  S.sentFrom = sentFrom;
  $("#mod-from").hidden = !sentFrom;
  $("#mod-from").textContent = sentFrom ? `opened from ${sentFrom.from || "another device"}` : "";
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
  $("#orb-dock").classList.toggle("talk", voice.can().ok);
  $("#dock-say").appendChild($("#reply"));
  $("#mod-back").focus();
  device.update();
}

function closeModule() {
  if (!S.module) return;
  // removing the page closes its connection: the arm freezes (dead-man) and control is free
  $("#mod-slot").replaceChildren();
  $("#module").hidden = true;
  delete body.dataset.mod;
  $(".core").prepend($("#orb"));
  $("#orb-dock").classList.remove("talk");
  REPLY_HOME.parent.insertBefore($("#reply"), REPLY_HOME.next);
  S.module = null;
  S.sentFrom = null;
  closeOpenOn();
  device.update();
}
$("#mod-back").addEventListener("click", closeModule);
const REPLY_HOME = { parent: $("#reply").parentNode, next: $("#reply").nextSibling };

/* ---------- the assistant opens pages on this screen (decision 2026-11-14) ----------
   What this screen can show goes with each question (typed or spoken); an "open" event in the answer shows it. */
const PANELS = { project: ["#p-panel", "Current Project"], spend: ["#s-panel", "AI Spend"], commits: ["#c-panel", "Commits"] };
function pagesHere() {
  const out = { hub: "the hub", chat: "the conversation" };
  for (const m of S.modules) out[m.id] = m.title;
  for (const [id, [sel, title]] of Object.entries(PANELS)) if (!$(sel)?.hidden) out[id] = title;
  return out;
}
function showPage(id) {
  if (S.screen !== "hub") return;
  noteInput();
  if (id === "hub") return (closeModule(), closeChat());
  if (id === "chat") return (closeModule(), openChat());
  if (S.modules.some((m) => m.id === id)) {
    closeChat();
    if (S.module?.id !== id) openHere(id, null);
    return;
  }
  const panel = PANELS[id] && $(PANELS[id][0]);
  if (!panel || panel.hidden) return;
  closeModule();
  closeChat();
  panel.scrollIntoView({ block: "center", behavior: "smooth" }); // the plain hub's panels are on the hub itself
  panel.classList.add("flash");
  setTimeout(() => panel.classList.remove("flash"), 2500);
}
// hold the docked core to talk, like the mic (a module is open)
$("#orb-dock").addEventListener("pointerdown", (e) => {
  if (!$("#orb-dock").classList.contains("talk")) return;
  e.preventDefault();
  $("#orb-dock").setPointerCapture?.(e.pointerId);
  talkStart();
});
for (const t of ["pointerup", "pointercancel"]) $("#orb-dock").addEventListener(t, () => talkEnd());

/* ---------- devices (step 8): this one's name, "open on…", pages sent here, "bring it back" ---------- */
const device = connectDevice({
  look: "plain",
  state: () => ({
    stage: S.screen,
    showing: S.module?.id || null,
    from: S.sentFrom?.from || "",
    from_window: S.sentFrom?.from_window || "",
  }),
  onOpen: (id, from, fromWindow) => openHere(id, { from, from_window: fromWindow }),
  onClose: () => closeModule(),
  onDevices: () => {
    renderSent();
    if (shouldRefill($("#open-on")) && S.module) fillMenu(); // the list changed while it's open
  },
  onSettings: () => renderMic(),
  onOff: () => voice.off(),
});

// a module sent from another device: shown at once, even from the start screen (that device has the hub
// open, so it's there for this); a module already open here gives way
function openHere(id, sentFrom) {
  const m = S.modules.find((x) => x.id === id);
  if (!m) return device.update();
  if (S.screen !== "hub") start(true);
  closeModule();
  openModule(m, sentFrom);
  noteInput(); // someone wants this on screen: no reset right away
}

function fillMenu() {
  fillOpenOn($("#open-on"), device, S.module.id, { title: S.module.title, onSent: () => setTimeout(closeModule, 900) });
}
function closeOpenOn() {
  $("#open-on").hidden = true;
  $("#mod-open-on").setAttribute("aria-expanded", "false");
}
$("#mod-open-on").addEventListener("click", () => {
  if (!S.module) return;
  if (!$("#open-on").hidden) return closeOpenOn();
  fillMenu();
  $("#open-on").hidden = false;
  $("#mod-open-on").setAttribute("aria-expanded", "true");
});

function renderSent() {
  fillSent($("#sent"), device, {
    onBack: (it) => {
      if (S.screen !== "hub" || S.module) return;
      const m = S.modules.find((x) => x.id === it.showing.id);
      if (m) openModule(m);
    },
  });
}

// The module page is on the same brain, so the hub can hear its keys and taps: they count as
// input (no reset while someone uses it), and Esc there means Back too.
function watchFrame(frame) {
  try {
    const w = frame.contentWindow;
    for (const ev of INPUT_EVENTS) w.addEventListener(ev, noteInput, { passive: true, capture: true });
    w.addEventListener("pointerdown", closeOpenOn, { capture: true }); // a tap on the page closes "Open on…"
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
// one missed poll (every 3 s) isn't "brain not reachable" yet: two in a row are (quick job 32)
let statusMisses = 0;
// visitor mode (quick job 35): the venue's "try this" cards; tapping one asks it, like saying it
function renderTry(visitors) {
  const box = $("#try"), cards = visitors?.cards || [], key = JSON.stringify(cards);
  box.hidden = !cards.length;
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.replaceChildren(
    ...cards.map((c) => {
      const card = document.createElement(c.ask ? "button" : "div");
      card.className = "trycard";
      if (c.ask) {
        card.type = "button";
        card.addEventListener("click", () => ask(c.ask));
      }
      card.append(Object.assign(document.createElement("b"), { textContent: c.say }));
      if (c.line) card.append(Object.assign(document.createElement("small"), { textContent: c.line }));
      return card;
    }),
  );
}

async function pollStatus() {
  const st = await getJSON("/api/status");
  statusMisses = st ? 0 : statusMisses + 1;
  if (!st && statusMisses < 2 && S.status) return S.status;
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
    voice.setStatus(null);
    if (!S.asking) setAssistant("offline", 0);
    return;
  }
  S.clockOffset = st.time_ms - Date.now();
  for (const el of [$("#f-venue"), $("#ign-venue")]) el.textContent = `Venue: ${st.venue}`;
  renderTry(st.visitors);
  $("#f-persona").textContent = `Assistant: ${st.persona.display_name}`;
  net.textContent =
    st.internet === true ? "Internet: online" : st.internet === false ? "Internet: offline" : "Internet: checking…";
  net.classList.toggle("off", st.internet !== true);
  ai.textContent = aiText(st.ai);
  // only when something's wrong: the arm's USB was unplugged (the brain reconnects by itself)
  const arm = $("#f-arm");
  arm.hidden = st.arm?.connected !== false;
  arm.textContent = `Arm: ${st.arm?.name} disconnected`;
  ai.classList.toggle("off", st.ai.connected !== true || !!st.ai.paused);
  showPaused(st.ai.paused);
  voice.setStatus(st.voice);
  syncWake();
  if (!S.asking) setAssistant(st.assistant.state, st.assistant.loudness);
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
      if (m.role === "assistant" && navigator.clipboard) div.append(copyButton(m.content));
      return div;
    }),
  );
  log.scrollTop = log.scrollHeight;
}

// for drafted prompts: copy an answer to paste into Claude Code or Codex (needs localhost/https)
function copyButton(text) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "copy";
  b.textContent = "Copy";
  b.addEventListener("click", async () => {
    const prompt = text.includes("Prompt:") ? text.slice(text.indexOf("Prompt:") + 7).trim() : text;
    try {
      await navigator.clipboard.writeText(prompt);
      b.textContent = "Copied";
    } catch {
      b.textContent = "Can't copy here";
    }
  });
  return b;
}

// a turn: the question on screen, then the answer as it streams in (typed here, spoken: voice below)
function beginTurn(text) {
  S.asking = true;
  showError(null);
  const answer = { role: "assistant", content: "" };
  S.chat.push({ role: "user", content: text });
  $("#reply .q").textContent = text;
  $("#reply .a").textContent = "";
  renderLog();
  const handle = (ev) => onChatEvent(ev, answer, handle.paced);
  handle.answer = answer;
  return handle;
}

async function ask(text) {
  text = text.trim();
  if (!text || S.asking) return;
  const onEvent = beginTurn(text);
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, pages: pagesHere(), lang: assistantLanguage() }),
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
      for (const line of lines) if (line.trim()) onEvent(JSON.parse(line));
    }
  } catch (e) {
    onEvent({ type: "error", message: "The brain didn't answer, so the question was lost. Try again." });
    console.warn(`hub: chat failed (${e.message})`);
  }
  S.asking = false;
  noteInput();
  if (S.sayAfter) {
    S.sayAfter = false;
    voice.say();
  }
  renderSpend(await getJSON("/api/spend")); // what that answer cost
}

// what the assistant is reading while it looks something up (the brain's read tools)
const TOOL_WORDS = {
  project_status: "the current focus",
  list_docs: "the docs",
  read_doc: "a doc",
  search_docs: "the docs",
  git_status: "git",
  git_log: "the git history",
  list_devices: "the devices",
  arm_status: "the arm",
  list_poses: "the arm's poses",
};

// paced: a spoken answer, whose text the voice reveals as it's said (revealPacer), not as it's written
function onChatEvent(ev, answer, paced = false) {
  if (ev.type === "state") {
    if (!paced) setAssistant(ev.state, ev.state === "speaking" ? 1 : 0);
  }
  else if (ev.type === "open") showPage(ev.page); // the assistant opened a page on this screen
  else if (ev.type === "venue") { // visitor mode on or off (quick job 35): cards, spend, settings
    pollStatus();
    refreshFacts();
    S.sayAfter = !paced && ev.visitors; // typed: the welcome is spoken too, once it's all there
  }
  else if (ev.type === "tool" && ev.name === "open_page") return;
  else if (ev.type === "tool") $("#state-word").textContent = `looking up: ${TOOL_WORDS[ev.name] || ev.name}`;
  else if (ev.type === "text") {
    if (!answer.content) S.chat.push(answer);
    answer.content += ev.text;
    if (!paced) $("#reply .a").textContent = answer.content;
    $("#reply .a").scrollTop = $("#reply .a").scrollHeight;
    renderLog();
  } else if (ev.type === "error") {
    showError(ev.message);
    S.chat.push({ role: "error", content: ev.message });
    renderLog();
  }
}

/* ---------- voice (step 7, docs/guides/voice.md): hold the mic or Space, talk, let go; the answer is spoken ----------
   web/voice.js records and plays; the brain hears, thinks (the same conversation) and speaks. No secure page,
   no microphone or no voice at the brain: no mic button, typing unchanged. */
const VS = { turn: null, voiced: false, greeting: false, shown: null, freeTimer: 0 };
const voice = createVoice({
  pages: () => pagesHere(),
  onEvent: onVoiceEvent,
  onChange: renderMic,
  onLoud: (l) => (VS.voiced || VS.greeting) && setAssistant("speaking", l),
  onLevel: (l) => {
    dictateLevel(l);
    VW?.level(l);
  },
});

// the wake word (Settings → This device): while the hub is up, no module or conversation page open and the tab
// in front, the brain listens for the phrase (the dot in the strip). After it, the question ends after a silence.
let VW = null;
function syncWake() {
  const w = S.status?.voice?.wake;
  // with a module or the conversation open too (2026-11-14, the builder): "hey Jarvis, go back to the hub"
  const want =
    wayIn() === "wake_word" && voice.can().ok && !!w?.available && S.screen === "hub" &&
    document.visibilityState === "visible";
  voice.wake(want);
  renderWakeDot();
}
function renderWakeDot() {
  $("#f-wake").hidden = !voice.wakeOn;
  $("#f-wake").classList.toggle("stalled", voice.micStalled);
  $("#f-wake").title = voice.micStalled
    ? "Not hearing the microphone (the browser paused it): press the mic once to wake it"
    : `Listening for "${S.status?.voice?.wake?.phrase || "the wake word"}"`;
}
function wakeTurnStart() {
  VS.greeting = false;
  if (S.asking && !VS.voiced) {
    voice.cancel(); // a typed question is being answered
    return;
  }
  if (VS.voiced && !VS.turn) endVoice();
  if (prefs().sound !== false) voice.chime(); // "I heard you", at once
  S.asking = VS.voiced = true;
  showError(null);
  $("#reply .q").textContent = "Listening…";
  $("#reply .a").textContent = "";
  setAssistant("listening", 0);
  VW = silenceWatch(
    (spoke) => {
      VW = null;
      if (spoke) {
        voice.finish();
        setAssistant("thinking", 0);
      } else {
        voice.cancel();
        $("#reply .q").textContent = "I didn't hear a question.";
        endVoice();
        setAssistant("idle", 0);
      }
    },
    { quietMs: WAKE_QUIET_MS, idleMs: 6000, maxMs: 20_000, floor: voice.noiseFloor },
  );
}
document.addEventListener("visibilitychange", syncWake);
function renderMic() {
  const dict = wayIn() === "dictation";
  document.querySelectorAll(".mic").forEach((b) => {
    b.hidden = !voice.can().ok;
    b.textContent = dict ? "Dictate" : "Talk";
    b.title = dict ? "Tap to dictate (or tap Space): the words go into the ask line" : "Hold to talk (or hold Space)";
  });
}
addEventListener("storage", (e) => isPrefsKey(e.key) && renderMic());
addEventListener("message", (e) => e.origin === location.origin && e.data?.type === "lab-os:settings" && renderMic());

// dictation (the way in chosen in Settings → This device): tap the mic (or Space on an empty ask line); the words
// go into the ask line while you talk; it stops after a short silence, a second tap or Space; Enter stops and
// sends; Esc or any other key stops and keeps what's there, to fix and send like typing
let VD = null;
async function dictateStart(line) {
  if (voice.pressed || VD) return;
  voice.unlock();
  VS.greeting = false;
  voice.stopSpeaking();
  const now = performance.now();
  VD = { line, base: line.value.trim(), started: now, spoke: false, quietSince: now, floor: 0.005, send: false, ph: line.placeholder };
  line.placeholder = "Listening… tap the mic again to stop";
  line.focus();
  document.querySelectorAll(".mic").forEach((b) => b.classList.add("on"));
  setAssistant("listening", 0);
  if (!(await voice.press("dictate"))) dictateDone();
}
function dictateStop(send) {
  if (!VD) return;
  if (send) VD.send = true;
  if (voice.pressed) {
    voice.release();
    document.querySelectorAll(".mic").forEach((b) => b.classList.remove("on"));
  } else dictateDone();
}
function dictateCancel() {
  if (!VD) return;
  if (voice.pressed) voice.cancel();
  dictateDone();
}
function dictateDone() {
  const d = VD;
  VD = null;
  if (!d) return;
  document.querySelectorAll(".mic").forEach((b) => b.classList.remove("on"));
  d.line.placeholder = d.ph;
  setAssistant("idle", 0);
  d.line.focus();
  if (d.send && d.line.value.trim()) d.line.form.requestSubmit();
}
function dictateLevel(l) {
  if (!VD || !voice.pressed) return;
  const now = performance.now();
  if (l > Math.max(0.02, VD.floor * 3)) {
    VD.spoke = true;
    VD.quietSince = now;
  } else VD.floor = VD.floor * 0.95 + l * 0.05;
  const quiet = VD.spoke && now - VD.quietSince > 1600;
  if (quiet || (!VD.spoke && now - VD.started > 8000) || now - VD.started > 45_000) dictateStop(false);
}
addEventListener(
  "keydown",
  (e) => {
    if (!VD) return;
    if (e.key === "Enter" || e.key === "Escape" || e.code === "Space") {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
    if (e.key === "Enter") dictateStop(true);
    else if (e.code === "Space") dictateStop(false);
    else if (e.key === "Escape") dictateCancel();
    else if (e.key.length === 1 || ["Backspace", "Delete", "ArrowLeft", "ArrowRight"].includes(e.key)) dictateCancel();
  },
  true,
);
async function talkStart() {
  if (voice.pressed || voice.wakeTurn) return;
  voice.unlock();
  VS.greeting = false;
  if (VS.voiced && !VS.turn) {
    voice.stopSpeaking(); // talking over the last answer cuts it short
    endVoice();
  }
  if (S.asking) return;
  S.asking = VS.voiced = true;
  showError(null);
  $("#reply .q").textContent = "Listening…";
  $("#reply .a").textContent = "";
  document.querySelectorAll(".mic").forEach((b) => b.classList.add("on"));
  setAssistant("listening", 0);
  if (!(await voice.press("ask")) && !VS.turn) endVoice();
}
function talkEnd() {
  if (!voice.pressed || VD) return;
  document.querySelectorAll(".mic").forEach((b) => b.classList.remove("on"));
  voice.release();
  setAssistant("thinking", 0);
}
// the spoken answer's text: shown as it's said; all of it once the voice is done (or never came)
function freeText() {
  clearTimeout(VS.freeTimer);
  VS.shown?.free();
  VS.shown = null;
}
function endVoice() {
  freeText();
  VS.voiced = false;
  VS.turn = null;
  S.asking = false;
  document.querySelectorAll(".mic").forEach((b) => b.classList.remove("on"));
  noteInput();
}
function onVoiceEvent(ev) {
  if (VD && ev.type === "heard") {
    VD.line.value = [VD.base, ev.text].filter(Boolean).join(" ");
    if (ev.text) {
      VD.spoke = true;
      VD.quietSince = performance.now();
    }
    if (ev.final) dictateDone();
    return;
  }
  if (VD && (ev.type === "error" || ev.type === "mic_error")) dictateDone();
  if (ev.type === "wake") return wakeTurnStart();
  if (ev.type === "ended") { // the brain heard the pause after the question
    VW?.cancel();
    VW = null;
    setAssistant("thinking", 0);
    return;
  }
  if (ev.type === "mic_stalled") return renderWakeDot();
  if (ev.type === "wake_on" || ev.type === "wake_off" || ev.type === "wake_elsewhere") {
    renderWakeDot();
    if (ev.type === "wake_off" && wayIn() === "wake_word") showError(ev.why);
    return;
  }
  if (ev.type === "heard" && !ev.final) VW?.words();
  if ((ev.type === "error" || ev.type === "mic_error") && VW) {
    VW.cancel();
    VW = null;
  }
  if (ev.type === "heard") {
    if (!VS.turn) $("#reply .q").textContent = ev.text ? ev.text + (ev.final ? "" : " …") : "Listening…";
    if (!ev.final) return;
    if (!ev.text) {
      $("#reply .q").textContent = "I didn't catch that. Hold the mic while you talk.";
      endVoice();
      return;
    }
    const turn = (VS.turn = beginTurn(ev.text));
    turn.paced = true;
    VS.shown = revealPacer(
      () => turn.answer.content.length,
      (n) => ($("#reply .a").textContent = turn.answer.content.slice(0, n)),
    );
  } else if (VS.turn && ["state", "tool", "text", "open", "error", "done"].includes(ev.type)) {
    VS.turn(ev);
    if (ev.type === "done" || ev.type === "error") {
      VS.turn = null;
      if (ev.type === "error") freeText();
      else VS.freeTimer = setTimeout(freeText, 15_000); // no voice after all: show it anyway
      getJSON("/api/spend").then(renderSpend);
    }
  } else if (ev.type === "playing" && VS.shown) {
    clearTimeout(VS.freeTimer);
    VS.shown.pace(ev.text.length, ev.duration * 1000);
    setAssistant("speaking", 0.5);
  } else if (ev.type === "error" || ev.type === "mic_error" || ev.type === "voice_error") {
    if (ev.type === "voice_error") freeText();
    if (ev.type !== "voice_error" && VS.voiced) endVoice();
    showError(ev.message);
  } else if (ev.type === "played" && VS.greeting) {
    VS.greeting = false;
    if (!S.asking) setAssistant("idle", 0);
  } else if (ev.type === "played" && VS.voiced && !VS.turn && !voice.pressed) {
    endVoice();
    setAssistant("idle", 0);
  }
}
document.querySelectorAll(".mic").forEach((b) => {
  b.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    if (wayIn() === "dictation") {
      if (VD) dictateStop(false);
      else dictateStart(b.id === "mic" ? quick : $("#ask"));
      return;
    }
    b.setPointerCapture?.(e.pointerId);
    talkStart();
  });
  for (const t of ["pointerup", "pointercancel"]) b.addEventListener(t, talkEnd);
  b.addEventListener("contextmenu", (e) => e.preventDefault());
});
// hold Space to talk (where there's a mic button), unless you're typing something; Esc stops
document.addEventListener("keydown", (e) => {
  if (S.screen !== "hub" || S.module) return;
  if (e.key === "Escape" && (voice.pressed || voice.wakeTurn || voice.speaking())) {
    if (voice.pressed || voice.wakeTurn) {
      VW?.cancel();
      VW = null;
      voice.cancel();
      endVoice();
    } else voice.stopSpeaking();
    return;
  }
  const ae = document.activeElement;
  const emptyLine = (ae.id === "quick" || ae.id === "ask") && !ae.value;
  if (e.code !== "Space" || !voice.can().ok || (!emptyLine && /INPUT|SELECT|TEXTAREA|BUTTON/.test(ae.tagName))) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  if (e.repeat) return;
  if (wayIn() === "dictation") dictateStart($("#chat").hidden ? quick : $("#ask"));
  else talkStart();
});
document.addEventListener("keyup", (e) => e.code === "Space" && voice.pressed && !VD && talkEnd());
addEventListener("blur", talkEnd);

function clearChat() {
  S.chat = [];
  $("#boot-greet").textContent = "";
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
  // after a reload: the conversation the brain still has (put aside by the reset)
  const c = await getJSON("/api/chat");
  if (!c) return;
  showChat(c.messages);
  showRestore(c.previous);
}

// A reset or a restart keeps the last conversation for a while (place.yaml chat_keep_minutes):
// "Bring back" swaps it in (and the current one aside, so a second press swaps back).
function showRestore(prev) {
  const b = $("#restore-chat");
  b.hidden = !prev;
  if (!prev) return;
  const at = new Date(prev.saved_at * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const n = prev.questions;
  b.textContent = `Bring back the last conversation (${n} question${n === 1 ? "" : "s"}, ${at})`;
}

async function restoreChat() {
  if (S.asking) return;
  const res = await fetch("/api/chat/restore", { method: "POST" }).catch(() => null);
  const r = res?.ok ? await res.json() : null;
  if (r?.ok) showChat(r.messages);
  showRestore(r?.previous);
}
$("#restore-chat").addEventListener("click", restoreChat);

function showChat(messages) {
  S.chat = messages.map((m) => ({ role: m.role, content: m.content }));
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
