// When has a spoken question ended? The page's silence watch (web/voice.js re-exports it). No imports,
// so the tests run it with node (tests/test_silence_watch.py).

// The question after the wake word ends after this much quiet (1.5 s, then 1 s, then 1.6 s, now 2 s; the
// brain may end it sooner, when the voice service hears the pause at the end of a sentence).
// Quick job 98: 1.6 s with a room level that rose while the person talked cut long questions and
// "37 times 48, … then add 199".
export const WAKE_QUIET_MS = 2000;

// A piece of sound is speech when it's this many times the room's level (and at least LOUD).
const OVER_ROOM = 3;
const LOUD = 0.02;
// Every piece this long was "speech", and its level stayed in this range: that's a steady noise (a fan
// came on), not a voice (a voice goes up and down with its syllables). The room's level then rises to
// the quietest piece of that time.
const STEADY_MS = 4000;
const STEADY_RANGE = 2;

// Stop listening after a short silence once something was said, or after a while with nothing said.
// level(l): the microphone's level (onLevel, a piece each 50 ms); words(): the brain heard words (counts
// as speech). floor: the room's level so far (v.noiseFloor): in a noisy room, its hum isn't taken for
// talking. While the person talks, the room's level stays as it was (quick job 98: before, it rose toward
// the voice, so a fast, steady voice counted as quiet after a few seconds).
export function silenceWatch(onStop, { quietMs = WAKE_QUIET_MS, idleMs = 8000, maxMs = 45_000, floor: floor0 = 0.005, now = () => performance.now() } = {}) {
  const t0 = now();
  let spoke = false, quietSince = t0, floor = Math.max(0.005, floor0 || 0), done = false;
  let loud = []; // [time, level] of the pieces since the last quiet one
  const stop = () => { if (!done) { done = true; onStop(spoke); } };
  return {
    level(l) {
      if (done) return;
      const t = now();
      if (l > Math.max(LOUD, floor * OVER_ROOM)) {
        spoke = true;
        quietSince = t;
        loud.push([t, l]);
        while (t - loud[0][0] > STEADY_MS) loud.shift();
        if (t - loud[0][0] >= STEADY_MS - 50) { // no quiet piece for a while: a voice, or a louder room?
          const vs = loud.map(([, v]) => v), lo = Math.min(...vs);
          if (Math.max(...vs) < lo * STEADY_RANGE) { floor = lo; loud = []; } // steady: the room
        }
      } else {
        loud = [];
        floor = l < floor ? floor * 0.8 + l * 0.2 : floor * 0.98 + l * 0.02; // quiet down fast, up slowly
      }
      if ((spoke && t - quietSince > quietMs) || (!spoke && t - t0 > idleMs) || t - t0 > maxMs) stop();
    },
    words() { spoke = true; quietSince = now(); },
    cancel() { done = true; },
    get floor() { return floor; },
  };
}
