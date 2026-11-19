// Two arms at once, in the headset (xr.js): hold Y, and each grip moves its own 3D arm instead of driving
// the real arm. A short tap of Y alone (no grip during it) puts both 3D arms back. While Y is held, and
// after it until each grip is let go, the brain gets that grip as released, so the real arms hold still
// and never start to follow by themselves when Y is let go. A grip already held when Y is pressed must
// be let go before it moves a 3D arm.
// No imports, so tests run it with node.
export const TAP_MS = 400;
const GRIP_ON = 0.6; // as the brain's clutch: engage above this...
const GRIP_OFF = 0.4; // ...release below this
const SIDES = ["left", "right"];

export class ArmMoves {
  constructor() {
    this.since = null; // when Y went down (ms), or null
    this.gripped = false; // a grip was used during this Y press (then it isn't a tap)
    this.dragging = { left: false, right: false };
    this.waitRelease = { left: false, right: false }; // held when Y went down: let go first
    this.blocked = { left: false, right: false }; // held when Y came up: the brain waits for a release
  }

  /** One XR frame. `y`: Y is held; `grips`: {left, right} 0..1 (missing = 0); `now`: ms.
   * Returns {drag: {left, right}: move that 3D arm now; reset: put both back; send: {left, right}:
   * the grip to send to the brain}. */
  step(now, y, grips) {
    const g = { left: grips.left || 0, right: grips.right || 0 };
    let reset = false;
    if (y && this.since == null) {
      this.since = now;
      this.gripped = false;
      for (const s of SIDES) this.waitRelease[s] = g[s] > GRIP_OFF;
    } else if (!y && this.since != null) {
      reset = !this.gripped && now - this.since < TAP_MS;
      this.since = null;
      for (const s of SIDES) if (g[s] > GRIP_OFF) this.blocked[s] = true;
    }
    const drag = {}, send = {};
    for (const s of SIDES) {
      if (y && g[s] > GRIP_OFF) this.gripped = true;
      if (this.waitRelease[s] && g[s] < GRIP_OFF) this.waitRelease[s] = false;
      if (this.blocked[s] && g[s] < GRIP_OFF) this.blocked[s] = false;
      if (!y || this.waitRelease[s] || g[s] < GRIP_OFF) this.dragging[s] = false;
      else if (g[s] > GRIP_ON) this.dragging[s] = true;
      drag[s] = this.dragging[s];
      send[s] = y || this.blocked[s] ? 0 : g[s];
    }
    return { drag, reset, send };
  }
}
