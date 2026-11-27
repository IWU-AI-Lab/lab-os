// Settings in the hub in VR and AR (quick job 60): ⚙ in the strip opens this page, like ⚙ on the screens.
// The same groups as the settings page (/settings, settings.js): This Device first (here: the Quest), then
// the brain's sections from /api/settings, the risky ones last. Groups on the left, the group's rows on the
// right. Point and pull the trigger:
//   on/off        the switch flips
//   a choice      a button for each choice (up to 5), else ‹ and › go through them
//   a number      − and + (by its step)
//   text, colours and lists only show their value: change them on a screen (no keyboard in VR).
// Saved at once, as on the screen: "✓ Saved" beside the setting's name, or why not on the line at the bottom.
// A changed setting has ↺ at its left: it goes back to its default at once (quick jobs 161, 164). × (or B) closes it.
// Drawn 200 units across, like the details pages (panels.js), whatever the page's size.
import { prefs, setPref } from "/web/device.js";
import { C, CanvasPlane, FONT, icon, rgba, spaced } from "./draw.js";
import { wrap } from "./panels.js";
import { cutRect } from "./way.js";

const NAMES = { ai: "AI Control", design: "Designed Hub", plain: "Plain Hub", jarvis: "J.A.R.V.I.S.", "24h": "24-Hour", "12h": "12-Hour", "push-to-talk": "Push-to-Talk" };
const SMALL = new Set(["a", "an", "and", "of", "the", "to", "on", "in", "for"]);
/** A value in Title Case, as the settings page shows it (the value saved stays as it is). */
export function show(v) {
  if (v === true) return "On";
  if (v === false) return "Off";
  const s = String(v ?? "");
  if (NAMES[s]) return NAMES[s];
  return s.split(/[\s-]+/).map((w, i) => (i > 0 && SMALL.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(" ");
}

const ICON = { device: "i-screen", assistant: "i-chat", lab: "i-pin", robots: "i-hand", limits: "i-warn" }; // settings.js's
const LANGS = { "": "Any", en: "English" }; // the brain's codes (lab_os/ai/languages.py) → words
const SENS_WORDS = { 1: "Fewest false wakes", 3: "Quiet room", 5: "The default", 7: "Noisy room", 9: "Hears the most" };

/** This Device: the Quest's own settings, kept by the brain under its name (as settings.js does). */
export function deviceFields(status) {
  const p = prefs(), wake = status?.voice?.wake;
  const ways = ["push-to-talk", ...(wake?.available ? ["wake word"] : [])];
  const out = [
    { key: "sound", label: "Sound", kind: "bool", value: p.sound !== false, save: (v) => setPref("sound", v) },
    { key: "voice", label: "Talking to It", kind: "choice", choices: ways, value: ways.includes(p.voice) ? p.voice : "push-to-talk",
      help: wake?.available ? `Push-to-Talk: hold the trigger on the ask line. Wake Word: say "${wake.phrase}".` : "Hold the trigger on the ask line and talk.",
      save: (v) => setPref("voice", v) },
  ];
  if (wake?.available) {
    out.push({ key: "wake_sensitivity", label: "Wake Word Sensitivity", kind: "number", min: 1, max: 9, step: 1,
      value: Number(p.wake_sensitivity) || 5, words: (v) => SENS_WORDS[v] || "", help: "Higher for a noisy room; lower if it wakes by itself.",
      save: (v) => setPref("wake_sensitivity", v === 5 ? "" : v) });
  }
  out.push({ key: "answer_in", label: "Assistant Answers In", kind: "choice", choices: Object.values(LANGS), value: LANGS[p.answer_in || ""] || "Any",
    save: (v) => setPref("answer_in", Object.keys(LANGS).find((k) => LANGS[k] === v) ?? "") });
  const mine = prefs();
  for (const f of out) f.changed = mine[f.key] !== undefined && mine[f.key] !== ""; // ↺ goes back to the device's default
  return out;
}

/** What a press on a control does to the value: the next value, or undefined (nothing to do). */
export function nextValue(f, act) {
  if (act.op === "flip") return !f.value;
  if (act.op === "pick") return act.value;
  const list = f.choices || [], i = Math.max(0, list.indexOf(f.value));
  if (act.op === "prev") return list[(i - 1 + list.length) % list.length];
  if (act.op === "next") return list[(i + 1) % list.length];
  if (act.op === "minus" || act.op === "plus") {
    const step = f.step || 1, v = Number(f.value) || 0;
    const n = Math.round((v + (act.op === "plus" ? step : -step)) / step) * step;
    return Math.min(f.max ?? Infinity, Math.max(f.min ?? -Infinity, Number(n.toFixed(4))));
  }
  return undefined;
}

const RST = 6; // the reset column's width (page units)

export class SettingsPage {
  constructor(w = 2.7, h = 1.6) {
    this.w = w; this.h = h;
    this.p = new CanvasPlane(w, h, 1100);
    this.p.mesh.userData.hit = this;
    this.hover = null;
    this.groups = []; // [{id, title, risky, fields}]
    this.at = 0; // the group shown
    this.top = 0; // its first row shown (more rows than fit: ▲ ▼)
    this.writable = true;
    this.whyNot = "";
    this.said = { text: "", bad: false, t: 0 };
    this.regions = []; // where the controls were drawn: {x, y, w, h, what}
    this.busy = false;
  }
  get mesh() { return this.p.mesh; }

  /** Read the settings again (on opening, and after a save). */
  async load() {
    let st = null, s = null;
    try { [st, s] = await Promise.all([fetch("/api/status", { cache: "no-store" }).then((r) => r.json()), fetch("/api/settings", { cache: "no-store" }).then((r) => r.json())]); } catch { /* the brain didn't answer */ }
    const brain = (s?.sections || []).map((x) => ({ id: x.id, title: x.title, risky: x.risky, fields: x.fields, brain: true }));
    brain.sort((a, b) => Number(a.risky) - Number(b.risky)); // the risky ones apart, at the bottom
    this.groups = [{ id: "device", title: "This Device", fields: deviceFields(st) }, ...brain];
    this.writable = s ? s.writable !== false : false;
    this.whyNot = !s ? "The brain didn't answer, so its settings aren't here." : s.why_not || "";
    this.restartKeys = new Set(s?.restart_keys || []);
    this.at = Math.min(this.at, this.groups.length - 1);
    this.p.key = null; // draw it again
  }

  hit(u, v) {
    const x = u * 200, y = (1 - v) * (200 * this.h / this.w);
    if (x > 200 - 14 && y < 12) return { kind: "back" };
    const r = this.regions.find((r) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h);
    return r ? { kind: "set", ...r.what } : { kind: "page" };
  }

  /** A press on the page (`what` from hit). Returns a promise when it saves. */
  async press(what) {
    if (what.op === "group") { this.at = what.i; this.top = 0; return; }
    if (what.op === "up") { this.top = Math.max(0, this.top - 1); return; }
    if (what.op === "down") { this.top += 1; return; }
    const g = this.groups[this.at], f = g?.fields[what.row];
    if (!f || this.busy) return;
    if (what.op === "reset") return this._reset(g, f);
    const value = nextValue(f, what);
    if (value === undefined || value === f.value) return;
    this.busy = true;
    let res;
    try {
      res = g.brain
        ? await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: f.key, value }) })
          .then(async (r) => (r.headers.get("Content-Type") || "").includes("json") ? r.json() : { ok: false, message: await r.text() })
        : await f.save(value);
    } catch (e) {
      res = { ok: false, message: `The brain didn't get it (${e.message}).` };
    }
    this.busy = false;
    const now = performance.now();
    if (res?.ok) {
      this.said = { text: f.applies === "restart" ? `Saved: ${f.label}. It applies when the brain restarts.` : `Saved: ${f.label}.`, bad: false, t: now, key: f.key };
      await this.load();
    } else this.said = { text: res?.message || "Not saved.", bad: true, t: now };
    this.p.key = null;
  }

  /** ↺: one setting back to its default (the brain's POST /api/settings/reset; this device's: its pref cleared). */
  async _reset(g, f) {
    this.busy = true;
    let res;
    try {
      res = g.brain
        ? await fetch("/api/settings/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ keys: [f.key] }) })
          .then((r) => (r.headers.get("Content-Type") || "").includes("json") ? r.json() : { ok: false, message: "Not reset: the brain had a problem. Its terminal has the details." })
        : await setPref(f.key, "");
    } catch (e) {
      res = { ok: false, message: `Not reset: ${e.message}` };
    }
    this.busy = false;
    const now = performance.now();
    if (res?.ok) { this.said = { text: `Reset: ${f.label}.`, bad: false, t: now, key: f.key }; await this.load(); }
    else this.said = { text: res?.message || "Not reset.", bad: true, t: now };
    this.p.key = null;
  }

  paint(now) {
    const key = JSON.stringify([this.at, this.top, this.hover, this.said.text, this.busy, this.groups.length, this.writable, Math.floor(now / 1000)]);
    this.p.paint((g, cw) => this._draw(g, cw), key);
  }

  _draw(g, cw) {
    const w = 200, h = (200 * this.h) / this.w, u = cw / w, c = 3;
    g.scale(u, u);
    this.regions = [];
    const hv = this.hover || {};
    const same = (what) => hv.kind === "set" && Object.keys(what).every((k) => hv[k] === what[k]);
    const box = (x, y, bw, bh, what, on = false, enabled = true) => {
      const over = enabled && same(what);
      if (on || over) { g.fillStyle = rgba(C.primary, on ? 0.22 : 0.12); g.fillRect(x, y, bw, bh); }
      g.strokeStyle = !enabled ? rgba(C.dim, 0.4) : on || over ? C.primary : rgba(C.primary, 0.45);
      g.lineWidth = 0.25; g.strokeRect(x, y, bw, bh);
      if (enabled) this.regions.push({ x, y, w: bw, h: bh, what });
    };
    const label = (text, x, y, size, color, align = "left", weight = 600, font = FONT.ui) => {
      g.font = `${weight} ${size}px ${font}`; g.fillStyle = color; g.textAlign = align; g.textBaseline = "middle"; g.fillText(text, x, y);
    };
    // the page: near-black, a cut-corner frame, the title tab, Back (as the details pages)
    g.beginPath(); g.moveTo(c, 0); g.lineTo(w, 0); g.lineTo(w, h - c); g.lineTo(w - c, h); g.lineTo(0, h); g.lineTo(0, c); g.closePath();
    g.fillStyle = rgba(C.bg, 0.95); g.fill();
    g.strokeStyle = rgba(C.primary, 0.45); g.lineWidth = 0.2; g.stroke();
    g.fillStyle = C.primary; g.fillRect(0, c, 0.4, 6); g.fillRect(c, 0, 8, 0.4);
    icon(g, "i-gear", 5, 7, 4, C.primary, 1.5);
    spaced(g, 0.18); label("SETTINGS", 9, 7, 3.2, C.hot, "left", 700, FONT.title); spaced(g, 0);
    const bh = hv.kind === "back";
    cutRect(g, w - 14, 2.5, 11, 9, 2); // cut corners (quick job 157)
    if (bh) { g.fillStyle = rgba(C.primary, 0.16); g.fill(); }
    g.strokeStyle = bh ? C.primary : rgba(C.primary, 0.5); g.lineWidth = 0.25; g.stroke();
    { // × in place of ← (choice 2, quick job 157)
      const cx = w - 8.5, cy = 7, r = 2.2;
      g.strokeStyle = bh ? C.hot : C.text; g.lineWidth = 0.6; g.lineCap = "round";
      g.beginPath(); g.moveTo(cx - r, cy - r); g.lineTo(cx + r, cy + r); g.moveTo(cx + r, cy - r); g.lineTo(cx - r, cy + r); g.stroke();
    }
    // the groups, on the left
    const top = 16, navW = 44;
    this.groups.forEach((gr, i) => {
      const y = top + i * 8.2;
      box(5, y, navW, 7, { op: "group", i }, i === this.at);
      // an icon on each group, in the main colour; the safety group is not red (quick job 156)
      icon(g, ICON[gr.id] || "i-gear", 8.6, y + 3.5, 3.2, C.primary, 1.5);
      label(gr.title, 12, y + 3.6, 2.5, i === this.at ? C.hot : C.text, "left", 600);
    });
    // the rows of the group shown
    const gr = this.groups[this.at];
    const L = 5 + navW + 6, R = w - 6, rowH = 14.5, bottom = h - 12;
    if (!gr) { label("Loading…", L, top + 5, 2.6, C.dim); return; }
    const fits = Math.max(1, Math.floor((bottom - top) / rowH));
    this.top = Math.min(this.top, Math.max(0, gr.fields.length - fits));
    const can = this.writable || !gr.brain;
    const recent = this.said.text && performance.now() - this.said.t < 6000;
    gr.fields.slice(this.top, this.top + fits).forEach((f, k) => {
      const i = this.top + k, y = top + k * rowH;
      g.fillStyle = C.line; g.fillRect(L, y + rowH - 0.6, R - L, 0.12);
      const ctlW = 64, cx = R - ctlW, N = L + RST; // the reset column, then the name (quick job 164)
      const off = !can || (f.safety && f.locked);
      if (f.changed && !off) { // ↺ in a circle: back to the default at once
        const what = { op: "reset", row: i }, over = same(what), rx = L + RST / 2 - 0.6, ry = y + 3.2, r = 2.3;
        g.beginPath(); g.arc(rx, ry, r, 0, Math.PI * 2);
        if (over) { g.fillStyle = rgba(C.primary, 0.16); g.fill(); }
        g.strokeStyle = over ? C.primary : rgba(C.primary, 0.45); g.lineWidth = 0.25; g.stroke();
        label("↺", rx, ry + 0.1, 2.8, over ? C.hot : C.text, "center", 600);
        this.regions.push({ x: rx - r - 0.6, y: ry - r - 0.6, w: 2 * r + 1.2, h: 2 * r + 1.2, what });
      }
      label(f.label, N, y + 3.2, 2.6, C.text);
      if (recent && !this.said.bad && this.said.key === f.key) { // "✓ Saved" beside the name (quick job 163)
        g.font = `600 2.6px ${FONT.ui}`; const nw = g.measureText(f.label).width;
        label("✓ Saved", N + nw + 2, y + 3.2, 2.1, C.primary, "left", 500); // the main colour, as the flat page
      }
      if (f.help) {
        g.font = `${FONT.linesW} 1.9px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "left";
        wrap(g, f.help, cx - N - 3, 3).forEach((l, n) => g.fillText(l, N, y + 6.6 + n * 2.6));
      }
      const cy = y + 1.2, ch = 6;
      if (f.safety && f.locked) {
        label("On", R, cy + 3, 2.6, C.dim, "right");
        g.font = `${FONT.linesW} 1.8px ${FONT.lines}`; g.fillStyle = C.dim; g.textAlign = "right"; g.fillText(`Locked: ${f.locked}`.slice(0, 60), R, cy + ch + 2.4);
      } else if (f.kind === "bool") {
        box(R - 16, cy, 16, ch, { op: "flip", row: i }, !!f.value, !off);
        label(f.value ? "On" : "Off", R - 8, cy + 3, 2.5, f.safety && !f.value ? C.accent : f.value ? C.hot : C.dim, "center");
      } else if (f.kind === "choice" && (f.choices || []).length <= 5) {
        const n = f.choices.length, bw = Math.min(16, ctlW / n);
        f.choices.forEach((ch2, j) => {
          const x = R - (n - j) * bw;
          box(x, cy, bw - 0.6, ch, { op: "pick", row: i, value: ch2 }, ch2 === f.value, !off);
          label(show(ch2), x + (bw - 0.6) / 2, cy + 3, Math.min(2.2, (bw - 1.5) / Math.max(4, show(ch2).length * 0.55)), ch2 === f.value ? C.hot : C.text, "center", 500);
        });
      } else if (f.kind === "choice") {
        box(cx, cy, 7, ch, { op: "prev", row: i }, false, !off); label("‹", cx + 3.5, cy + 3, 3.4, C.text, "center");
        box(R - 7, cy, 7, ch, { op: "next", row: i }, false, !off); label("›", R - 3.5, cy + 3, 3.4, C.text, "center");
        label(show(f.value), (cx + R) / 2, cy + 3, 2.4, C.hot, "center", 500);
      } else if (f.kind === "number" || f.kind === "range") {
        box(cx, cy, 7, ch, { op: "minus", row: i }, false, !off); label("−", cx + 3.5, cy + 3, 3.4, C.text, "center");
        box(R - 7, cy, 7, ch, { op: "plus", row: i }, false, !off); label("+", R - 3.5, cy + 3, 3.4, C.text, "center");
        const words = f.words?.(f.value);
        label(`${f.value ?? "—"}${f.unit ? ` ${f.unit}` : ""}${words ? `: ${words}` : ""}`, (cx + R) / 2, cy + 3, 2.3, C.hot, "center", 500);
      } else {
        const v = Array.isArray(f.value) ? f.value.map(show).join(", ") : show(f.value);
        g.font = `500 2.3px ${FONT.ui}`; g.fillStyle = C.text; g.textAlign = "right";
        g.fillText(wrap(g, v, ctlW, 1)[0] || "—", R, cy + 3);
        g.font = `${FONT.linesW} 1.8px ${FONT.lines}`; g.fillStyle = C.dim; g.fillText("Change it on a screen", R, cy + ch + 2.4);
      }
      if (this.restartKeys?.has(f.key)) { g.font = `${FONT.linesW} 1.8px ${FONT.lines}`; g.fillStyle = C.accent; g.textAlign = "left"; g.fillText("Applies when the brain restarts", N, y + rowH - 2); }
    });
    // more rows than fit: ▲ ▼
    if (gr.fields.length > fits) {
      box(R - 16, bottom + 1, 7, 6, { op: "up" }, false, this.top > 0); label("▲", R - 12.5, bottom + 4, 2.4, C.text, "center");
      box(R - 7, bottom + 1, 7, 6, { op: "down" }, false, this.top + fits < gr.fields.length); label("▼", R - 3.5, bottom + 4, 2.4, C.text, "center");
    }
    // a save shows "✓ Saved" in its row; the line says why not, or why nothing can change here
    const line = this.busy ? "Saving…" : recent && this.said.bad ? this.said.text : !can ? this.whyNot : "";
    if (line) {
      g.font = `${FONT.linesW} 2.2px ${FONT.lines}`; g.fillStyle = recent && this.said.bad ? C.accent : C.dim; g.textAlign = "left";
      g.fillText(wrap(g, line, R - L - 20, 1)[0], L, bottom + 4);
    }
  }
}
