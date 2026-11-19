// Voice on the hub (focus step 7, docs/guides/voice.md). The page records and plays; the brain hears, thinks
// and speaks over /ws/voice (docs/dev/protocol.md → "Voice"), so API keys never leave the brain.
//
//   const v = createVoice({ onEvent, onChange, onLoud, onLevel, pages });
//                               pages(): what this screen can show ({id: title}), sent with each question
//                               so the assistant can open one here ("open" events, decision 2026-11-14)
//   v.setStatus(status.voice)   the brain's word on voice (/api/status → voice)
//   v.can()                     {ok, why}: a secure page, a microphone, voice on at the brain
//   v.unlock()                  in a press (the start tap): lets the page play sound
//   v.press("ask" | "dictate")  start listening (push-to-talk / dictation); v.release() to stop
//   v.cancel()                  stop listening, ask nothing
//   v.greet(way)                the spoken greeting: asked for at the start press, held until
//   v.playHeld()                ... the page plays it (after the jump); talking first drops it
//   v.say()                     speak the brain's waiting line: a typed visitors' welcome (quick job 35)
//   v.stopSpeaking()            cut the answer short
//   v.wake(on)                  stream the microphone for the wake word (the brain listens for it, at
//                               this device's sensitivity); on "wake", the brain hears the question:
//                               v.finish() when it's said (silenceWatch), v.cancel() to drop it; the
//                               brain may end it first ("ended": it heard a pause after the question)
//   v.chime()                   the short, quiet "I heard you" sound (the plain hub; the designed hub
//                               and VR play their own listening sound)
//   v.noiseFloor                the room's level while listening for the phrase (for silenceWatch)
//   v.micStalled                the microphone gave no audio for a while (the Quest after sleeping)
//
// onEvent gets everything the brain sends (heard, state, text, tool, done, error, audio_end,
// voice_error), plus {type: "playing", seq, text, duration} as each spoken piece starts (so the page
// can show the text as it's said: revealPacer), {type: "played"} once the last word has played and
// {type: "mic_error", message} when the browser won't give the microphone, {type: "mic_stalled", on} when
// the microphone stops giving audio while the wake word is on (and when it's back). onLoud(0..1): the answer's loudness while
// it plays (the core follows it). onLevel(0..1): the microphone's level while listening.
// onChange(): the mic button should be shown or hidden (plugging, unplugging, the brain's status).

import { deviceName, prefs } from "/web/device.js";

// The way in, chosen per device (Settings → This device, kept by the brain under its name): push-to-talk
// (the default), dictation or the wake word. The setting's words → the brain's names (the greeting's hint).
export const WAYS = { "push-to-talk": "push_to_talk", dictation: "dictation", "wake word": "wake_word" };
export function wayIn() {
  return WAYS[prefs().voice] || "push_to_talk";
}
// How readily this device hears the wake word (Settings → This device): 1 = fewest false wakes … 9 = hears
// the most (noisy rooms, weak microphones). 5 = openWakeWord's own default.
export const WAKE_SENSITIVITY = 5;
export function wakeSensitivity() {
  const v = Number(prefs().wake_sensitivity);
  return Number.isInteger(v) && v >= 1 && v <= 9 ? v : WAKE_SENSITIVITY;
}

// The assistant's languages, per device (Settings → This device → "Assistant language", quick job 33):
// what speech-to-text expects and what it answers in; "" = any. Sent with every question.
export function assistantLanguage() {
  const p = prefs();
  return { hear: p.hear_in || "", answer: p.answer_in || "" };
}

// The question after the wake word ends after this much quiet (it was 1.5 s; the brain may end it sooner,
// when the voice service hears the pause).
export const WAKE_QUIET_MS = 1000;

// Can this screen hear at all? (A secure page and a microphone; the brain's side is in /api/status.)
export async function screenCanHear() {
  if (!window.isSecureContext) return { ok: false, why: "not a secure page: the microphone works only on https or this computer's localhost" };
  if (!navigator.mediaDevices?.getUserMedia) return { ok: false, why: "this browser gives pages no microphone" };
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    if (!devices.some((d) => d.kind === "audioinput")) return { ok: false, why: "no microphone is plugged in" };
  } catch {
    return { ok: false, why: "the browser won't list the microphones" };
  }
  try {
    const p = await navigator.permissions?.query({ name: "microphone" });
    if (p?.state === "denied") return { ok: false, why: "the browser blocks the microphone for this page (site settings)" };
  } catch {
    // no permission query (Firefox): the first press asks
  }
  return { ok: true, why: null };
}

// Shows a spoken answer at the pace it's said, instead of before it: render(n, typing) shows the
// first n characters of the answer (length() of them so far). pace(chars, ms): the next `chars` are
// being said over `ms`. free(): nothing more will be said (the end, or no voice): show the rest
// quickly; `finished` resolves when all is shown.
export function revealPacer(length, render) {
  let shown = 0, target = 0, rate = 0, free = false, last = performance.now(), resolve;
  const finished = new Promise((r) => (resolve = r));
  const timer = setInterval(() => {
    const now = performance.now(), dt = Math.min(100, now - last), total = length();
    last = now;
    if (free) shown = Math.min(total, shown + Math.max(2, dt * 0.25)); // ~250 characters/s
    else shown = Math.min(target, total, shown + rate * dt);
    render(Math.floor(shown), !(free && shown >= total));
    if (free && shown >= total) {
      clearInterval(timer);
      resolve();
    }
  }, 16);
  return {
    pace(chars, ms) {
      target = Math.max(target, shown) + chars;
      rate = (target - shown) / Math.max(1, ms);
    },
    free() {
      free = true;
    },
    finished,
  };
}

// Stop listening after a short silence once something was said, or after a while with nothing said.
// level(l): the microphone's level (onLevel); words(): the brain heard words (counts as speech).
// floor: the room's level so far (v.noiseFloor): in a noisy room, its hum isn't taken for talking. The floor
// also creeps up while it's "loud" (a steady noise is the room, not a voice).
export function silenceWatch(onStop, { quietMs = 1600, idleMs = 8000, maxMs = 45_000, floor: floor0 = 0.005 } = {}) {
  const t0 = performance.now();
  let spoke = false, quietSince = t0, floor = Math.max(0.005, floor0 || 0), done = false;
  const stop = () => { if (!done) { done = true; onStop(spoke); } };
  return {
    level(l) {
      if (done) return;
      const now = performance.now();
      if (l > Math.max(0.02, floor * 3)) { spoke = true; quietSince = now; floor = floor * 0.99 + l * 0.01; } else floor = floor * 0.95 + l * 0.05;
      if ((spoke && now - quietSince > quietMs) || (!spoke && now - t0 > idleMs) || now - t0 > maxMs) stop();
    },
    words() { spoke = true; quietSince = performance.now(); },
    cancel() { done = true; },
  };
}

const MIC_KEEP_MS = 60_000; // keep the microphone open this long after the last use (no lost words)
const MIC_STALL_MS = 1500; // the wake word is on but no audio came this long: wake the microphone up

// "I heard you": two short, quiet notes (like the designed hub's listening sound), on the page's own sound.
export function chimeOn(ctx) {
  if (!ctx || ctx.state !== "running") return;
  const t = ctx.currentTime;
  [[523, 0, 0.1], [784, 0.08, 0.16]].forEach(([f, at, dur]) => {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, t + at);
    g.gain.exponentialRampToValueAtTime(0.06, t + at + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, t + at + dur);
    o.connect(g).connect(ctx.destination);
    o.start(t + at);
    o.stop(t + at + dur + 0.02);
  });
}
const QUEUE_MAX = 400; // audio pieces kept while the connection opens (20 s)

export function createVoice({ onEvent = () => {}, onChange = () => {}, onLoud = () => {}, onLevel = () => {}, pages = () => null } = {}) {
  const st = {
    secure: window.isSecureContext,
    api: !!navigator.mediaDevices?.getUserMedia,
    mics: 0, // audio inputs the browser lists
    denied: false, // the person or the browser refused the microphone
    brain: null, // /api/status → voice
    ws: null,
    pending: [], // messages waiting for the connection
    ctx: null,
    worklet: null, // loading the recorder
    mic: null, // {stream, node}
    closeTimer: 0,
    pressId: 0,
    pressed: false,
    sending: false,
    playing: [], // sources scheduled
    decoding: Promise.resolve(),
    playEnd: 0,
    awaitingEnd: false, // audio of this turn may still come (until audio_end)
    holding: false, // the greeting: keep its audio until playHeld()
    held: [],
    wakeWanted: false, // the page wants the wake word on (the brain may say no: wake_off)
    wakeOn: false, // the brain listens for it
    wakeTurn: false, // the brain heard it and hears the question
    wakeSens: 0, // the sensitivity last sent
    lastPiece: 0, // when the microphone last gave audio
    floor: 0.005, // the room's level while listening for the phrase
    stalled: false,
    watchTimer: 0,
    analyser: null,
    loudTimer: 0,
    lastReport: 0,
  };

  // ---------- can this screen talk? ----------
  async function countMics() {
    if (!st.api) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      st.mics = devices.filter((d) => d.kind === "audioinput").length;
    } catch {
      st.mics = 0;
    }
    onChange();
  }
  if (st.api) {
    navigator.mediaDevices.addEventListener?.("devicechange", countMics);
    countMics();
  }

  function can() {
    if (!st.secure) return { ok: false, why: "The microphone works only on a secure page (https or this computer's localhost)." };
    if (!st.api) return { ok: false, why: "This browser gives pages no microphone." };
    if (!st.mics) return { ok: false, why: "No microphone is plugged in." };
    if (!st.brain?.available) return { ok: false, why: st.brain?.why || "Voice is off at the brain." };
    return { ok: true, why: null };
  }

  function setStatus(voice) {
    const before = JSON.stringify(can());
    st.brain = voice || null;
    if (can().ok) connect();
    if (JSON.stringify(can()) !== before) onChange();
  }

  // ---------- the connection ----------
  function connect() {
    if (st.ws) return;
    const name = deviceName(); // for the brain's log ("voice timing (quest, …)")
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/voice${name ? `?device=${name}` : ""}`);
    st.ws = ws;
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      if (st.wakeWanted) ws.send(JSON.stringify({ type: "wake", on: true, sensitivity: st.wakeSens, pages: pages(), lang: assistantLanguage() })); // again after a reconnect
      for (const m of st.pending.splice(0)) ws.send(m);
    };
    ws.onmessage = (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      if (ev.type === "audio") play(ev);
      else if (ev.type === "wake_on") st.wakeOn = true;
      else if (ev.type === "wake_off") st.wakeOn = false;
      else if (ev.type === "wake") {
        stopSpeaking();
        st.wakeTurn = true;
      } else if (ev.type === "ended") { // the brain heard the pause after the question: it's over
        if (!st.wakeTurn) return;
        st.wakeTurn = false;
        st.awaitingEnd = true;
      }
      else if (ev.type === "audio_end") {
        st.awaitingEnd = false;
        st.decoding.then(checkPlayed);
      }
      onEvent(ev);
    };
    ws.onclose = () => {
      st.ws = null;
      st.wakeOn = st.wakeTurn = false;
      if (st.pressed) {
        st.pressed = st.sending = false;
        if (!st.off) onEvent({ type: "error", message: "Lost the connection to the brain." });
      }
      if (!st.off) setTimeout(() => can().ok && connect(), 2000);
    };
  }
  function send(msg) {
    const data = typeof msg === "string" || msg instanceof ArrayBuffer ? msg : JSON.stringify(msg);
    if (st.ws?.readyState === WebSocket.OPEN) st.ws.send(data);
    else {
      connect();
      if (st.pending.length < QUEUE_MAX) st.pending.push(data);
    }
  }

  // ---------- sound ----------
  function context() {
    if (!st.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      st.ctx = new AC();
      st.analyser = st.ctx.createAnalyser();
      st.analyser.fftSize = 1024;
      st.analyser.connect(st.ctx.destination);
    }
    return st.ctx;
  }
  function unlock() {
    try {
      context().resume();
    } catch {
      // no WebAudio: no voice on this screen
    }
  }

  // ---------- the microphone ----------
  async function openMic() {
    clearTimeout(st.closeTimer);
    if (st.mic) return;
    const ctx = context();
    await ctx.resume();
    st.worklet ||= ctx.audioWorklet.addModule("/web/voice-worklet.js");
    await st.worklet;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
    const node = new AudioWorkletNode(ctx, "lab-os-mic");
    node.port.onmessage = (e) => {
      // pressed, or the wake word (not while the answer plays: its own voice shouldn't wake it)
      const forWake = st.wakeOn && !st.playing.length && st.ws?.readyState === WebSocket.OPEN;
      if (st.sending || forWake || st.wakeTurn) send(e.data.pcm);
      st.lastPiece = performance.now();
      if (forWake) { // the room's level: follows quiet down fast, noise up slowly
        const l = e.data.level;
        st.floor = l < st.floor ? st.floor * 0.8 + l * 0.2 : st.floor * 0.995 + l * 0.005;
      }
      onLevel(e.data.level);
    };
    ctx.createMediaStreamSource(stream).connect(node);
    const mute = ctx.createGain();
    mute.gain.value = 0;
    node.connect(mute).connect(ctx.destination); // keeps the recorder running in every browser
    stream.getAudioTracks()[0]?.addEventListener("ended", () => closeMic());
    st.mic = { stream, node };
    st.denied = false;
  }
  function closeMic() {
    clearTimeout(st.closeTimer);
    if (!st.mic) return;
    st.mic.stream.getTracks().forEach((t) => t.stop());
    st.mic.node.disconnect();
    st.mic = null;
  }
  function micWhy(e) {
    if (e?.name === "NotAllowedError" || e?.name === "SecurityError") {
      st.denied = true;
      return "The browser blocked the microphone. Allow it for this page (the icon at the left of the address bar), then try again.";
    }
    if (e?.name === "NotFoundError") return "No microphone is plugged in.";
    if (e?.name === "NotReadableError") return "Another program is using the microphone.";
    return `The microphone didn't start (${e?.message || e}).`;
  }

  async function press(mode = "ask") {
    if (st.pressed || !can().ok) return false;
    const id = ++st.pressId;
    st.pressed = true;
    st.holding = false;
    st.held = [];
    stopSpeaking();
    st.awaitingEnd = false;
    send({ type: "listen", mode, pages: pages(), lang: assistantLanguage() });
    try {
      await openMic();
    } catch (e) {
      if (id === st.pressId) st.pressed = false;
      send({ type: "cancel" });
      onEvent({ type: "mic_error", message: micWhy(e) });
      return false;
    }
    if (id !== st.pressId || !st.pressed) return true; // let go while the microphone opened
    st.sending = true;
    return true;
  }
  // the wake word: the microphone stays open while it's on (the browser shows its recording sign)
  async function wake(on) {
    const sens = wakeSensitivity(), pk = JSON.stringify([pages(), assistantLanguage()]);
    if (on === st.wakeWanted && (!on || (sens === st.wakeSens && pk === st.pagesKey))) return true;
    st.pagesKey = pk;
    if (on && st.wakeWanted) { // only the sensitivity or the languages (This device) or the pages changed
      st.wakeSens = sens;
      send({ type: "wake", on: true, sensitivity: sens, pages: pages(), lang: assistantLanguage() });
      return true;
    }
    st.wakeWanted = on;
    if (!on) {
      st.wakeOn = false;
      clearInterval(st.watchTimer);
      setStalled(false);
      send({ type: "wake", on: false });
      if (!st.pressed && !st.wakeTurn) st.closeTimer = setTimeout(closeMic, MIC_KEEP_MS);
      return true;
    }
    try {
      await openMic();
    } catch (e) {
      st.wakeWanted = false;
      onEvent({ type: "mic_error", message: micWhy(e) });
      return false;
    }
    st.wakeSens = sens;
    st.lastPiece = performance.now();
    send({ type: "wake", on: true, sensitivity: sens, pages: pages(), lang: assistantLanguage() });
    clearInterval(st.watchTimer);
    st.watchTimer = setInterval(watchMic, 1000);
    return true;
  }
  // The Quest (GOTCHAS 2026-11-13): after the headset sleeps or the browser loses audio focus, the page's
  // sound stops (the AudioContext is suspended, or the microphone track is muted) and nothing reaches the
  // brain, until a push-to-talk press wakes the sound again. While the wake word is on, check every second
  // and wake it ourselves: resume the sound, else open the microphone again; tell the brain (its log) and
  // the page (the dot) while it's stuck.
  let reviving = false;
  async function watchMic() {
    if (!st.wakeWanted || reviving) return;
    const quiet = performance.now() - st.lastPiece > MIC_STALL_MS;
    const track = st.mic?.stream.getAudioTracks()[0];
    if (!quiet && st.ctx?.state === "running") return setStalled(false);
    reviving = true;
    let why = "";
    try {
      if (st.ctx && st.ctx.state !== "running") {
        why = `the page's sound is ${st.ctx.state}`;
        await st.ctx.resume().catch(() => {});
      } else if (!st.mic || track?.readyState === "ended") {
        why = "the microphone was closed";
        closeMic();
        await openMic();
      } else if (track?.muted) {
        why = "the system muted the microphone";
      } else {
        why = "no audio from the microphone";
        closeMic();
        await openMic();
      }
    } catch (e) {
      why = `${why}; reopening it failed (${e?.message || e})`;
    } finally {
      reviving = false;
    }
    // still nothing after the try: say so (once)
    setTimeout(() => setStalled(st.wakeWanted && (performance.now() - st.lastPiece > MIC_STALL_MS || st.ctx?.state !== "running"), why), 600);
  }
  function setStalled(on, why = "") {
    if (on === st.stalled) return;
    st.stalled = on;
    send({ type: "wake_mic", ok: !on, why: on ? why : "" });
    onEvent({ type: "mic_stalled", on, why });
  }
  function finish() {  // the question after the wake word is said
    if (!st.wakeTurn) return;
    st.wakeTurn = false;
    st.awaitingEnd = true;
    send({ type: "end" });
  }

  function release() {
    if (!st.pressed) return;
    st.pressed = st.sending = false;
    st.awaitingEnd = true;
    send({ type: "end" });
    if (!st.wakeWanted) st.closeTimer = setTimeout(closeMic, MIC_KEEP_MS);
  }
  function cancel() {
    if (st.wakeTurn) {
      st.wakeTurn = false;
      send({ type: "cancel" });
      return;
    }
    if (!st.pressed) return;
    st.pressed = st.sending = false;
    send({ type: "cancel" });
    if (!st.wakeWanted) st.closeTimer = setTimeout(closeMic, MIC_KEEP_MS);
  }

  // ---------- playing the answer ----------
  function play(ev) {
    if (st.holding) {
      st.held.push(ev);
      return;
    }
    const bytes = Uint8Array.from(atob(ev.data), (c) => c.charCodeAt(0));
    // decode one after another, so the pieces play in order
    st.decoding = st.decoding.then(async () => {
      try {
        const ctx = context();
        const buf = await ctx.decodeAudioData(bytes.buffer);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(st.analyser);
        const at = Math.max(ctx.currentTime + 0.05, st.playEnd);
        src.start(at);
        st.playEnd = at + buf.duration;
        st.playing.push(src);
        setTimeout(() => {  // say when this piece is heard, so its text can appear with it (and the brain's timing)
          if (!st.playing.includes(src)) return;
          onEvent({ type: "playing", seq: ev.seq, text: ev.text || "", duration: buf.duration });
          send({ type: "playing", seq: ev.seq });
        }, Math.max(0, (at - ctx.currentTime) * 1000));
        src.onended = () => {
          st.playing = st.playing.filter((s) => s !== src);
          checkPlayed();
        };
        loudLoop();
      } catch (e) {
        console.warn(`voice: can't play a piece (${e.message})`);
      }
    });
  }
  function loudLoop() {
    if (st.loudTimer) return;
    const data = new Float32Array(st.analyser.fftSize);
    const stepLoud = () => {
      if (!st.playing.length) {
        st.loudTimer = 0;
        onLoud(0);
        return;
      }
      st.analyser.getFloatTimeDomainData(data);
      let sq = 0;
      for (const v of data) sq += v * v;
      const loud = Math.min(1, Math.sqrt(sq / data.length) * 4);
      onLoud(loud);
      const now = performance.now();
      if (now - st.lastReport > 200) {
        st.lastReport = now;
        send({ type: "played", loudness: Math.round(loud * 100) / 100 });
      }
      st.loudTimer = requestAnimationFrame(stepLoud);
    };
    st.loudTimer = requestAnimationFrame(stepLoud);
  }
  function checkPlayed() {
    if (st.playing.length || st.awaitingEnd || st.holding) return;
    send({ type: "played", done: true });
    onEvent({ type: "played" });
  }
  function stopSpeaking() {
    const was = st.playing.length > 0;
    for (const s of st.playing.splice(0)) {
      s.onended = null;
      try {
        s.stop();
      } catch {
        // not started yet
      }
    }
    st.playEnd = 0;
    if (was) {
      send({ type: "played", done: true });
      onEvent({ type: "played" });
    }
  }
  const speaking = () => st.playing.length > 0;

  function greet(way = "push_to_talk") {
    if (!st.brain?.available || st.pressed) return false;
    st.awaitingEnd = true;
    st.holding = true;
    st.held = [];
    send({ type: "greet", way });
    return true;
  }
  function say() {
    if (!st.brain?.available || st.pressed) return false;
    send({ type: "say" });
    return true;
  }
  function playHeld() {
    if (!st.holding) return;
    st.holding = false;
    for (const ev of st.held.splice(0)) play(ev);
    st.decoding.then(checkPlayed);
  }

  // lab-os was shut down (quick job 6): the microphone closes now and stays closed (the page reloads when
  // the brain is back)
  function off() {
    st.off = true;
    st.wakeWanted = st.wakeOn = st.wakeTurn = st.pressed = st.sending = false;
    clearInterval(st.watchTimer);
    stopSpeaking();
    closeMic();
    st.ws?.close();
  }

  return {
    can,
    setStatus,
    off,
    unlock,
    press,
    release,
    cancel,
    greet,
    say,
    playHeld,
    stopSpeaking,
    speaking,
    wake,
    finish,
    chime: () => chimeOn(st.ctx),
    get noiseFloor() {
      return st.floor;
    },
    get micStalled() {
      return st.stalled;
    },
    get wakeOn() {
      return st.wakeOn;
    },
    get wakeTurn() {
      return st.wakeTurn;
    },
    get pressed() {
      return st.pressed;
    },
    get denied() {
      return st.denied;
    },
  };
}
