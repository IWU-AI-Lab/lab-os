// Voice on the hub (focus step 7, docs/voice.md). The page records and plays; the brain hears, thinks
// and speaks over /ws/voice (docs/protocol.md → "Voice"), so API keys never leave the brain.
//
//   const v = createVoice({ onEvent, onChange, onLoud, onLevel });
//   v.setStatus(status.voice)   the brain's word on voice (/api/status → voice)
//   v.can()                     {ok, why}: a secure page, a microphone, voice on at the brain
//   v.unlock()                  in a press (the start tap): lets the page play sound
//   v.press("ask" | "dictate")  start listening (push-to-talk / dictation); v.release() to stop
//   v.cancel()                  stop listening, ask nothing
//   v.greet(way)                the spoken greeting: asked for at the start press, held until
//   v.playHeld()                ... the page plays it (after the jump); talking first drops it
//   v.stopSpeaking()            cut the answer short
//
// onEvent gets everything the brain sends (heard, state, text, tool, done, error, audio_end,
// voice_error), plus {type: "played"} once the last word has played and {type: "mic_error",
// message} when the browser won't give the microphone. onLoud(0..1): the answer's loudness while
// it plays (the core follows it). onLevel(0..1): the microphone's level while listening.
// onChange(): the mic button should be shown or hidden (plugging, unplugging, the brain's status).

// The way in, chosen per screen (Settings → This screen, kept in this browser): push-to-talk (the
// default) or dictation. The setting's words → the brain's names (the greeting's hint).
export const WAYS = { "push-to-talk": "push_to_talk", dictation: "dictation" };
export function wayIn() {
  try {
    return WAYS[JSON.parse(localStorage.getItem("lab-os.screen"))?.voice] || "push_to_talk";
  } catch {
    return "push_to_talk";
  }
}

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
  return { ok: true, why: null };
}

const MIC_KEEP_MS = 60_000; // keep the microphone open this long after the last use (no lost words)
const QUEUE_MAX = 400; // audio pieces kept while the connection opens (20 s)

export function createVoice({ onEvent = () => {}, onChange = () => {}, onLoud = () => {}, onLevel = () => {} } = {}) {
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
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/voice`);
    st.ws = ws;
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
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
      else if (ev.type === "audio_end") {
        st.awaitingEnd = false;
        st.decoding.then(checkPlayed);
      }
      onEvent(ev);
    };
    ws.onclose = () => {
      st.ws = null;
      if (st.pressed) {
        st.pressed = st.sending = false;
        onEvent({ type: "error", message: "Lost the connection to the brain." });
      }
      setTimeout(() => can().ok && connect(), 2000);
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
      if (st.sending) send(e.data.pcm);
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
    send({ type: "listen", mode });
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
  function release() {
    if (!st.pressed) return;
    st.pressed = st.sending = false;
    st.awaitingEnd = true;
    send({ type: "end" });
    st.closeTimer = setTimeout(closeMic, MIC_KEEP_MS);
  }
  function cancel() {
    if (!st.pressed) return;
    st.pressed = st.sending = false;
    send({ type: "cancel" });
    st.closeTimer = setTimeout(closeMic, MIC_KEEP_MS);
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
  function playHeld() {
    if (!st.holding) return;
    st.holding = false;
    for (const ev of st.held.splice(0)) play(ev);
    st.decoding.then(checkPlayed);
  }

  return {
    can,
    setStatus,
    unlock,
    press,
    release,
    cancel,
    greet,
    playHeld,
    stopSpeaking,
    speaking,
    get pressed() {
      return st.pressed;
    },
    get denied() {
      return st.denied;
    },
  };
}
