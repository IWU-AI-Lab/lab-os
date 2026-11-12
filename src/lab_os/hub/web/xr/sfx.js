// The hub's sounds in VR: the same WebAudio recipes as the designed hub's SFX (design.html), so the
// headset sounds like the screen. Generated, no files. `?sound=0` on the page = silent.
//   const sfx = new Sfx(T);  sfx.unlockAudio() in a press (browsers allow sound only after one)
const rand = (a, b) => a + Math.random() * (b - a);

export class Sfx {
  /** @param {{ramp: number, hold: number, brake: number}} T the jump's timings in ms */
  constructor(T) {
    this.T = T;
    const q = new URLSearchParams(location.search);
    this.on = q.get("sound") !== "0" && !q.has("slow");
    this.ac = null;
    this.master = null;
  }
  unlockAudio() {
    if (!this.on) return;
    if (!this.ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ac = new AC();
      this.master = this.ac.createGain();
      this.master.gain.value = 0.5;
      this.master.connect(this.ac.destination);
    }
    if (this.ac.state === "suspended") this.ac.resume();
  }
  get ready() { return this.on && !!this.ac; }
  tone({ f = 440, f2 = 0, type = "sine", dur = 0.15, vol = 0.1, attack = 0.005, delay = 0, lp = 0 }) {
    if (!this.ready) return;
    const ac = this.ac, t = ac.currentTime + delay, o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    let node = o;
    if (lp) { const fl = ac.createBiquadFilter(); fl.type = "lowpass"; fl.frequency.value = lp; o.connect(fl); node = fl; }
    node.connect(g); g.connect(this.master); o.start(t); o.stop(t + dur + 0.05);
  }
  whoosh({ dur = 1.5, vol = 0.12, from = 150, to = 1400, attack = 0.7, delay = 0 }) {
    if (!this.ready) return;
    const ac = this.ac, t = ac.currentTime + delay, len = Math.floor(ac.sampleRate * dur);
    const buf = ac.createBuffer(1, len, ac.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const src = ac.createBufferSource(); src.buffer = buf;
    const fl = ac.createBiquadFilter(); fl.type = "lowpass";
    fl.frequency.setValueAtTime(from, t); fl.frequency.exponentialRampToValueAtTime(to, t + dur * 0.85);
    const g = ac.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(fl); fl.connect(g); g.connect(this.master); src.start(t);
  }
  lock(i) { this.tone({ f: 520 * Math.pow(1.122, i), type: "triangle", dur: 0.09, vol: 0.05 }); this.tone({ f: 1800, type: "triangle", dur: 0.02, vol: 0.03 }); }
  unlock() {
    // a low breath on the wind-up, a clack per bolt, a heavy thunk and a slow servo groan as the ring
    // turns, a latch clank as it opens, then the chime with the burst
    this.tone({ f: 70, f2: 50, dur: 0.35, vol: 0.18, attack: 0.08 });
    for (let i = 0; i < 8; i++) {
      const t = 0.2 + i * 0.06;
      this.whoosh({ dur: 0.05, vol: 0.07, from: 4200, to: 2400, attack: 0.003, delay: t });
      this.tone({ f: 1400 - i * 70, f2: 600, type: "square", dur: 0.03, vol: 0.015, lp: 3200, delay: t });
    }
    this.tone({ f: 95, f2: 34, dur: 0.8, vol: 0.42, attack: 0.006, delay: 0.55 }); this.whoosh({ dur: 0.3, vol: 0.06, from: 900, to: 200, attack: 0.005, delay: 0.55 });
    this.tone({ f: 140, f2: 420, type: "sawtooth", dur: 0.75, vol: 0.035, attack: 0.2, lp: 1100, delay: 0.58 });
    this.whoosh({ dur: 0.12, vol: 0.12, from: 2600, to: 900, attack: 0.004, delay: 1.15 }); this.tone({ f: 220, f2: 160, type: "triangle", dur: 0.25, vol: 0.08, delay: 1.15 });
    this.tone({ f: 1319, type: "triangle", dur: 0.8, vol: 0.035, delay: 1.22 }); this.tone({ f: 1976, type: "triangle", dur: 0.9, vol: 0.025, delay: 1.28 });
  }
  sweep() { this.tone({ f: 160, f2: 1300, type: "triangle", dur: 0.9, vol: 0.06, attack: 0.35, lp: 2600 }); }
  tick() { this.tone({ f: 2300, type: "triangle", dur: 0.025, vol: 0.018 }); }
  line() { this.tone({ f: 880, dur: 0.2, vol: 0.05 }); }
  decode() { this.tone({ f: rand(1200, 2400), type: "square", dur: 0.02, vol: 0.012, lp: 3000 }); }
  title() { for (let i = 0; i < 3; i++) this.tone({ f: [523, 659, 784][i], dur: 1.4, vol: 0.035, attack: 0.08, delay: i * 0.05 }); }
  land() { this.tone({ f: 300, f2: 120, type: "triangle", dur: 0.5, vol: 0.06, lp: 1200 }); this.whoosh({ dur: 0.7, vol: 0.05, from: 2000, to: 300, attack: 0.05 }); }
  hyper() {
    // follows the star speed: a hum that rises steadily with it, then the sustained roar at full speed
    if (!this.ready) return;
    const ac = this.ac, t = ac.currentTime, rp = this.T.ramp / 1000, hd = this.T.hold / 1000, end = t + rp + hd;
    const o = ac.createOscillator(), g = ac.createGain(), fl = ac.createBiquadFilter();
    o.type = "sawtooth"; fl.type = "lowpass";
    o.frequency.setValueAtTime(40, t); o.frequency.exponentialRampToValueAtTime(140, t + rp); o.frequency.exponentialRampToValueAtTime(220, end);
    fl.frequency.setValueAtTime(220, t); fl.frequency.exponentialRampToValueAtTime(2200, t + rp); fl.frequency.exponentialRampToValueAtTime(3500, end);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.12, t + rp); g.gain.linearRampToValueAtTime(0.15, end); g.gain.exponentialRampToValueAtTime(0.0001, end + 0.15);
    o.connect(fl); fl.connect(g); g.connect(this.master); o.start(t); o.stop(end + 0.2);
    this.whoosh({ dur: rp + hd, vol: 0.2, from: 200, to: 7000, attack: rp, delay: 0 });
  }
  arrive() { const d = this.T.brake / 1000; this.tone({ f: 70, f2: 32, dur: d, vol: 0.4, attack: 0.01 }); this.whoosh({ dur: d, vol: 0.12, from: 5000, to: 160, attack: 0.01 }); }
  blip() { this.tone({ f: 900, f2: 1350, dur: 0.08, vol: 0.07 }); }
  hover() { this.tone({ f: 1500, type: "triangle", dur: 0.03, vol: 0.02 }); }
  open() { this.tone({ f: 300, f2: 900, type: "triangle", dur: 0.45, vol: 0.06, attack: 0.1, lp: 2000 }); this.whoosh({ dur: 0.6, vol: 0.05, from: 400, to: 3000, attack: 0.25 }); }
  close() { this.tone({ f: 900, f2: 300, type: "triangle", dur: 0.35, vol: 0.05, lp: 2000 }); }
  listen() { this.tone({ f: 523, dur: 0.12, vol: 0.07 }); this.tone({ f: 784, dur: 0.2, vol: 0.07, delay: 0.1 }); }
  done() { this.tone({ f: 784, dur: 0.12, vol: 0.06 }); this.tone({ f: 523, dur: 0.2, vol: 0.06, delay: 0.1 }); }
  relock() { this.tone({ f: 1600, type: "triangle", dur: 0.03, vol: 0.05 }); this.tone({ f: 2100, type: "triangle", dur: 0.03, vol: 0.05, delay: 0.07 }); }
  shimmer() { for (let i = 0; i < 4; i++) this.tone({ f: rand(1900, 3400), dur: 1.2, vol: 0.012, attack: 0.3, delay: i * 0.06 }); }
  error() { this.tone({ f: 330, f2: 220, type: "triangle", dur: 0.4, vol: 0.08 }); }
}
