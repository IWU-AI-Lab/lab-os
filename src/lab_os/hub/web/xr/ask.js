// Asking in VR (decision 2026-11-12, the builder: push-to-talk, and the wake word heard by the Quest's or
// the desktop's microphone). Like the designed hub's ask line under the core (design.html → voice):
//   - the ask line: "Ask anything" with the mic; point at it and HOLD the trigger (or a pinch), talk, let
//     go; the answer types out under the core as it's spoken (web/voice.js, the brain's /ws/voice: the same
//     conversation as typing, API keys stay on the brain);
//   - the wake word: while the hub is up (a module or page open too, 2026-11-14), the Quest's microphone streams to the brain,
//     which listens for the phrase itself; a small dot in the strip says so. Then the core listens and the
//     question ends after a short silence;
//   - another screen heard it (the desktop's microphone, its own wake word or push-to-talk): the brain's
//     conversation (/api/chat) gets a new question and answer, and they show here too; the core follows
//     the brain's state (/api/status). That screen speaks the answer;
//   - the spoken greeting after the jump, like the screen's (asked for at the start press).
// No voice here (no microphone, not a secure page, no voice at the brain): the ask line says why.
import { C, CanvasPlane, FONT, clamp, icon, rgba } from "./draw.js";
import { wrap } from "./panels.js";

const REPLY_S = 14; // the answer fades after this long, like the screen's

export class Ask {
  constructor({ sfx }) {
    this.sfx = sfx;
    this.line = new CanvasPlane(0.72, 0.1, 1000);
    this.line.mesh.userData.hit = { hit: () => ({ kind: "ask" }) };
    this.reply = new CanvasPlane(1.9, 0.32, 1000);
    this.q = ""; this.a = ""; this.shown = 0; this.typing = false; this.replyAt = -1e9; this.note = ""; this.noteAt = -1e9;
    this.state = null; // the assistant's state while a turn runs here (else the brain's)
    this.V = null; this.VM = null;
    this.turn = null; // {answer, pacer}
    this.voiced = false;
    this.hover = false;
    this.lastChat = null; // the brain's conversation, to see turns asked on other screens
    import("/web/voice.js").then((m) => {
      this.VM = m;
      this.V = m.createVoice({
        onEvent: (ev) => this._event(ev),
        onLoud: (l) => (this.loud = l),
        onLevel: (l) => { this.level = l; this.watch?.level(l); },
        pages: () => this.pages?.() || null, // what the hub can show (the assistant opens them)
      });
      if (this.status) this.V.setStatus(this.status.voice);
    }).catch((e) => console.warn(`xr hub: no voice (${e.message})`));
  }

  get mesh() { return this.line.mesh; }
  get wakeOn() { return !!this.V?.wakeOn; }
  /** The brain's status (every 1.5 s). */
  setStatus(st) { this.status = st; this.V?.setStatus(st?.voice); }
  /** The wake word listens while the hub is up, with or without a page open (and the brain can do it). */
  syncWake(want) {
    if (!this.V) return;
    const w = this.status?.voice?.wake;
    this.V.wake(want && this.V.can().ok && !!w?.available);
  }

  /* ---------- the spoken greeting: asked for at the start press, played while it's typed ---------- */
  greet() {
    if (!this.V || !this.sfx.on) return;
    this.V.unlock();
    const wake = this.status?.voice?.wake?.available;
    this.greeting = this.V.greet(this.V.can().ok ? (wake ? "wake_word" : "push_to_talk") : "none");
  }
  playGreeting() { if (this.greeting) { this.V.playHeld(); this.state = "speaking"; } }

  /* ---------- push-to-talk: hold on the ask line ---------- */
  async pressStart(now) {
    const V = this.V;
    if (!V) return;
    if (!V.can().ok) { this._note(V.can().why, now); this.sfx.error(); return; }
    if (V.pressed || V.wakeTurn) return;
    V.unlock();
    this.greeting = false;
    if (this.voiced && !this.turn) { V.stopSpeaking(); this._end(); }
    if (this.voiced) return;
    this.voiced = true;
    this._show("Listening…", "", now);
    this.state = "listening"; this.sfx.listen();
    if (!(await V.press("ask"))) this._end();
  }
  pressEnd() {
    if (!this.V?.pressed) return;
    this.V.release();
    this.state = "thinking";
  }

  _event(ev) {
    const now = this.now?.() ?? performance.now();
    (this.events ||= []).push(ev.type); // the last few, for the console
    if (this.events.length > 30) this.events.shift();
    if (ev.type === "wake") { // the brain heard the phrase on this headset's microphone
      this.greeting = false;
      if (this.voiced && !this.turn) this._end();
      this.voiced = true; this._show("Listening…", "", now); this.state = "listening"; this.sfx.listen();
      this.watch = this.VM.silenceWatch((spoke) => {
        this.watch = null;
        if (spoke) { this.V.finish(); this.state = "thinking"; }
        else { this.V.cancel(); this._show("I didn't hear a question.", "", now); this._end(); }
      }, { quietMs: this.VM.WAKE_QUIET_MS, idleMs: 6000, maxMs: 20_000, floor: this.V.noiseFloor });
      return;
    }
    if (ev.type === "open") { this.onOpen?.(ev.page); return; } // the assistant opened a page here
    if (ev.type === "ended") { this.watch?.cancel(); this.watch = null; this.state = "thinking"; return; } // the brain heard the pause
    if (["wake_on", "wake_off", "wake_elsewhere", "mic_stalled"].includes(ev.type)) return;
    if ((ev.type === "error" || ev.type === "voice_error") && this.greeting && !this.voiced) { this.greeting = false; this._note(ev.message, now); this.state = null; return; }
    if (ev.type === "heard" && !ev.final) this.watch?.words();
    if ((ev.type === "error" || ev.type === "mic_error") && this.watch) { this.watch.cancel(); this.watch = null; }
    if (ev.type === "heard") {
      if (!this.turn) this.q = ev.text ? ev.text + (ev.final ? "" : " …") : "Listening…";
      this.replyAt = now;
      if (!ev.final) return;
      if (!ev.text) { this.q = "I didn't catch that. Hold the trigger while you talk."; this._end(); return; }
      // the answer appears as it's said (the pieces' "playing"), like the screen's
      const answer = { text: "" };
      this.turn = { answer, pacer: this.VM.revealPacer(() => answer.text.length, (n, typing) => { this.shown = n; this.typing = typing; this.a = answer.text; }) };
      this.state = "thinking";
    } else if (this.turn && ev.type === "text") {
      this.turn.answer.text += ev.text;
    } else if (this.turn && (ev.type === "done" || ev.type === "error")) {
      if (ev.type === "error") { this._note(ev.message, now); this.turn.pacer.free(); }
      this.turn.done = true;
      this.freeTimer = setTimeout(() => this.turn?.pacer.free(), 15_000); // no voice after all: show it anyway
    } else if (ev.type === "playing" && this.turn) {
      clearTimeout(this.freeTimer);
      this.turn.pacer.pace(ev.text.length, ev.duration * 1000);
      this.state = "speaking";
    } else if (ev.type === "played" && this.greeting) { this.greeting = false; if (!this.voiced) this.state = null; }
    else if (ev.type === "played" && this.voiced && this.turn?.done && !this.V.pressed) { this.turn.pacer.free(); this.sfx.done(); this._end(); }
    else if (ev.type === "error" || ev.type === "mic_error") { this._note(ev.message, now); this.sfx.error(); this._end(); }
    else if (ev.type === "voice_error") { this._note(ev.message, now); this.turn?.pacer.free(); }
  }
  _show(q, a, now) { this.q = q; this.a = a; this.shown = a.length; this.replyAt = now; }
  _note(text, now) { this.note = text || ""; this.noteAt = now; }
  _end() { // the answer stays REPLY_S from now, like the screen's
    this.voiced = false; this.turn = null; this.state = null; this.lastChat = null;
    this.replyAt = this.now?.() ?? performance.now();
  }

  /** The brain's conversation: a turn asked on another screen (e.g. the desktop heard "hey Jarvis"). */
  async pollChat(now) {
    if (this.voiced) return;
    try {
      const d = await (await fetch("/api/chat", { cache: "no-store" })).json();
      const msgs = (d.messages || []).filter((m) => m.role === "user" || m.role === "assistant");
      const key = `${msgs.length}|${msgs.at(-1)?.content?.length}`;
      if (this.lastChat != null && key !== this.lastChat) {
        const lastQ = [...msgs].reverse().find((m) => m.role === "user");
        const lastA = msgs.at(-1)?.role === "assistant" ? msgs.at(-1).content : "";
        if (lastQ) { this.q = lastQ.content; this.a = lastA; this.shown = lastA.length; this.replyAt = now; }
      }
      this.lastChat = key;
    } catch { /* the brain will be back */ }
  }

  step(now, hover) {
    this.hover = hover;
    const can = this.V?.can(), pressed = !!this.V?.pressed;
    const lvl = pressed ? Math.min(1, (this.level || 0) * 8) : 0;
    this.line.paint((g, w, h) => {
      const c = h * 0.28;
      g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
      g.fillStyle = rgba(C.surface, 0.86); g.fill();
      g.strokeStyle = rgba(C.primary, hover || pressed ? 0.8 : 0.32); g.lineWidth = 2; g.stroke();
      icon(g, "i-chat", h * 0.55, h / 2, h * 0.38, C.dim, 1.6);
      g.font = `${FONT.linesW} ${h * 0.36}px ${FONT.lines}`; g.fillStyle = pressed ? C.text : C.dim; g.textBaseline = "middle"; g.textAlign = "left";
      g.fillText(pressed ? "Listening… let go when you're done" : can?.ok ? (hover ? "Hold the trigger and talk" : "Ask anything") : "Ask anything", h * 1.05, h / 2);
      // the mic, at the end (lit while it listens, with the level)
      const mx = w - h * 0.6;
      g.fillStyle = rgba(C.line, 1); g.fillRect(mx - h * 0.55, h * 0.15, 1.5, h * 0.7);
      if (pressed) { g.fillStyle = rgba(C.primary, 0.15 + 0.5 * lvl); g.fillRect(mx - h * 0.5, 2, h, h - 4); }
      icon(g, "i-mic", mx, h / 2, h * 0.5, can?.ok ? (pressed ? C.hot : C.primary) : C.offline, 1.6);
    }, `${hover}|${pressed}|${can?.ok}|${lvl.toFixed(1)}`);
    // the reply under the line: the question, small; the answer, up to three lines; a note when something's off
    const age = (now - this.replyAt) / 1000, noteAge = (now - this.noteAt) / 1000;
    const showReply = this.voiced || age < REPLY_S, showNote = noteAge < 7;
    const fade = this.voiced ? 1 : clamp((REPLY_S - age) / 1.5, 0, 1);
    this.reply.opacity = showNote ? 1 : showReply ? fade : 0;
    if (this.reply.opacity > 0) {
      const a = this.turn ? this.turn.answer.text.slice(0, this.shown) : this.a.slice(0, this.shown || this.a.length);
      const cursor = this.typing && Math.floor(now / 400) % 2 === 0;
      this.reply.paint((g, w, h) => {
        g.textAlign = "center"; g.textBaseline = "top";
        if (showNote) {
          g.font = `500 ${h * 0.14}px ${FONT.ui}`; g.fillStyle = C.accent;
          wrap(g, this.note, w * 0.95, 3).forEach((l, i) => g.fillText(l, w / 2, h * 0.05 + i * h * 0.19));
          return;
        }
        g.font = `${FONT.linesW} ${h * 0.12}px ${FONT.lines}`; g.fillStyle = C.dim;
        g.fillText(wrap(g, this.q, w * 0.95, 1)[0] || "", w / 2, h * 0.02);
        g.font = `500 ${h * 0.15}px ${FONT.ui}`; g.fillStyle = C.text;
        const lines = wrap(g, a.replace(/\s+/g, " ") + (cursor ? " ▌" : ""), w * 0.95, 3);
        lines.forEach((l, i) => g.fillText(l, w / 2, h * 0.24 + i * h * 0.24));
      }, `${this.q}|${a.length}|${cursor}`);
    }
  }
}
