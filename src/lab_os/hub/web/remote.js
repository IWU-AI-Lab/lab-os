// The phone's remote (quick job 124; remote.html says what it is). The same voice as the hub
// (/web/voice.js: hold Talk, or the wake word) and the same conversation (/api/chat for typing). It
// sends no pages: the phone shows none, so the assistant opens a page on the screen the person names,
// else on the brain's own computer (show_on_screens, lab_os/hub/screens.py).

import { deviceName } from "/web/device.js";
import { WAKE_QUIET_MS, assistantLanguage, createVoice, silenceWatch } from "/web/voice.js";

const $ = (s) => document.querySelector(s);
const WAKE_KEY = "lab-os.remote.wake"; // the wake word switch, kept in this browser
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* not kept */ } },
};

const S = { asking: false, status: null, turn: false, watch: null };

function say(state, q, a) {
  if (state !== undefined) $("#state").textContent = state;
  if (q !== undefined) $("#q").textContent = q;
  if (a !== undefined) $("#a").textContent = a;
}
function showError(m, detail = "") {
  $("#msg").textContent = m || "";
  $("#msg").title = detail || ""; // the keys and the file of "Add an AI key…" (quick job 153)
}
const TOOL_WORDS = { show_on_screens: "showing it on a screen", set_up_room: "setting up the room" };

// one event of an answer (typed or spoken): the words, what it does, an error
function onAnswer(ev) {
  if (ev.type === "state") say(ev.state === "thinking" ? "Thinking" : ev.state === "speaking" ? "Answering" : "");
  else if (ev.type === "tool") say(TOOL_WORDS[ev.name] || "Looking it up");
  else if (ev.type === "text") $("#a").textContent += ev.text;
  else if (ev.type === "error") {
    showError(ev.message, ev.detail);
    say("");
  } else if (ev.type === "done") say("");
}

/* ---------- typing ---------- */
async function ask(text) {
  text = text.trim();
  if (!text || S.asking) return;
  S.asking = true;
  voice.stopSpeaking();
  showError(null);
  say("Thinking", text, "");
  let complete = false, failed = false;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, pages: null, lang: assistantLanguage(), device: deviceName() }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader(), decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "error") failed = true;
        if (event.type === "done") complete = true;
        onAnswer(event);
      }
    }
    if (!complete && !failed) throw new Error("Incomplete answer");
  } catch (e) {
    failed = true;
    onAnswer({ type: "error", message: "The brain didn't answer, please try again." });
    console.warn(`remote: chat failed (${e.message})`);
  }
  say("");
  S.asking = false;
  return complete && !failed;
}
$("#ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const line = $("#ask");
  const sent = line.value;
  if (!await ask(sent) || line.value !== sent) return;
  line.value = "";
  line.blur(); // the phone's keyboard goes away, so the answer is in view
});

$("#ask-form").inert = false;

/* ---------- voice: hold Talk, or the wake word ---------- */
const voice = createVoice({
  pages: () => null,
  onEvent: onVoiceEvent,
  onChange: render,
  onLevel: (l) => S.watch?.level(l),
});

function endTurn(state = "") {
  S.turn = false;
  S.asking = false;
  $("#talk").classList.remove("on");
  say(state);
}
function onVoiceEvent(ev) {
  if (ev.type === "wake") return wakeTurn();
  if (ev.type === "ended") {
    S.watch?.cancel();
    S.watch = null;
    return say("Thinking");
  }
  if (ev.type === "wake_on" || ev.type === "wake_off" || ev.type === "wake_elsewhere") {
    if (ev.type === "wake_off" && wantWake()) showError(ev.why);
    return render();
  }
  if (ev.type === "heard") {
    S.watch?.words();
    say(undefined, ev.text ? ev.text + (ev.final ? "" : " …") : "Listening…");
    if (!ev.final) return;
    if (!ev.text) {
      endTurn();
      return say(undefined, "I didn't hear a question.");
    }
    if (ev.command) return endTurn();
    $("#a").textContent = "";
    return;
  }
  if (["state", "tool", "text", "done"].includes(ev.type)) return onAnswer(ev);
  if (ev.type === "error" || ev.type === "mic_error" || ev.type === "voice_error") {
    S.watch?.cancel();
    S.watch = null;
    endTurn();
    return showError(ev.message, ev.detail);
  }
  if (ev.type === "played" || ev.type === "stopped") endTurn();
}

function wakeTurn() {
  if (S.asking && !S.turn) return voice.cancel(); // a typed question is being answered
  voice.chime();
  S.asking = S.turn = true;
  showError(null);
  say("Listening", "Listening…", "");
  S.watch = silenceWatch(
    () => {
      S.watch = null;
      voice.finish();
      say("Thinking");
    },
    { quietMs: WAKE_QUIET_MS, idleMs: 6000, maxMs: 20_000, floor: voice.noiseFloor },
  );
}

async function talkStart(e) {
  e.preventDefault();
  if (voice.pressed || voice.wakeTurn) return;
  $("#talk").setPointerCapture?.(e.pointerId);
  voice.unlock();
  voice.stopSpeaking(); // talking over the last answer stops it
  if (S.asking && !S.turn) return;
  S.asking = S.turn = true;
  showError(null);
  $("#talk").classList.add("on");
  say("Listening", "Listening…", "");
  if (!(await voice.press("ask"))) endTurn();
}
function talkEnd() {
  if (!voice.pressed) return;
  $("#talk").classList.remove("on");
  voice.release();
  say("Thinking");
}
$("#talk").addEventListener("pointerdown", talkStart);
for (const t of ["pointerup", "pointercancel"]) $("#talk").addEventListener(t, talkEnd);
$("#talk").addEventListener("contextmenu", (e) => e.preventDefault());

const wantWake = () => store.get(WAKE_KEY) === "on";
$("#wake-on").checked = wantWake();
$("#wake-on").addEventListener("change", (e) => {
  voice.unlock();
  store.set(WAKE_KEY, e.target.checked ? "on" : "off");
  render();
});
document.addEventListener("visibilitychange", render);

function render() {
  const can = voice.can(), wake = S.status?.voice?.wake;
  $("#talk").hidden = !can.ok;
  $("#wake").hidden = !can.ok || !wake?.available;
  voice.wake(can.ok && !!wake?.available && wantWake() && document.visibilityState === "visible");
  $("#wake").classList.toggle("listening", voice.wakeOn);
  $("#wake-word").textContent = `Wake word: "${wake?.phrase || "the wake word"}"`;
  $("#secure").hidden = window.isSecureContext;
  if (window.isSecureContext && !can.ok && S.status) $("#msg").textContent ||= can.why;
}

/* ---------- the brain: status, and the secure address ---------- */
async function poll() {
  try {
    const r = await fetch("/api/status", { cache: "no-store" });
    S.status = r.ok ? await r.json() : null;
  } catch {
    S.status = null;
  }
  $("#brain").textContent = S.status ? "Brain connected" : "No brain";
  $("#brain").className = `pill ${S.status ? "on" : "bad"}`;
  voice.setStatus(S.status?.voice || null);
  render();
}
async function secureLinks() {
  if (window.isSecureContext) return;
  let port = 0;
  try {
    port = (await (await fetch("/api/remote", { cache: "no-store" })).json()).https_port || 0;
  } catch {
    port = 0;
  }
  const link = $("#https-link");
  if (port) {
    const url = `https://${location.hostname}:${port}/${location.search}`;
    link.href = url;
    link.textContent = url;
  } else {
    link.removeAttribute("href");
    link.textContent = "the secure address (the brain has none now: start it with --host 0.0.0.0)"; // in a sentence: "Open the secure address."
  }
}
poll();
setInterval(poll, 5000);
secureLinks();
