// The microphone's audio for the brain (web/voice.js): mono, 16 kHz, 16-bit, in 50 ms pieces,
// each with its loudness (RMS, 0..1). Runs in the browser's audio thread (an AudioWorklet).
const RATE = 16000;
const PIECE = 800; // samples: 50 ms

class LabOsMic extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / RATE; // e.g. 48000 / 16000 = 3
    this.pos = 0;
    this.sum = 0;
    this.n = 0;
    this.out = new Int16Array(PIECE);
    this.k = 0;
    this.sq = 0;
  }

  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let i = 0; i < ch.length; i++) {
      // average the input over each output sample's window: a simple low-pass before thinning out
      this.sum += ch[i];
      this.n++;
      this.pos += 1;
      if (this.pos < this.ratio) continue;
      this.pos -= this.ratio;
      const v = Math.max(-1, Math.min(1, this.sum / this.n));
      this.sum = 0;
      this.n = 0;
      this.out[this.k++] = v * 32767;
      this.sq += v * v;
      if (this.k === PIECE) {
        const level = Math.sqrt(this.sq / PIECE);
        this.port.postMessage({ pcm: this.out.buffer, level }, [this.out.buffer]);
        this.out = new Int16Array(PIECE);
        this.k = 0;
        this.sq = 0;
      }
    }
    return true;
  }
}

registerProcessor("lab-os-mic", LabOsMic);
