// What an arm driver has been told, tracked from a link's status / arm_* messages (docs/dev/protocol.md).
// Shared by every view of the arm (desktop 3D panel, XR ghost arm) so they always agree:
//   joints       angles of the latest arm_command (unclamped), or the driver's state before any
//   lastCommand  that arm_command message (has seq, speed_scale, driver_joints), or null
//   frozen       arm_stop sent and not resumed
//   status       latest status message (clutch, speed, arm.model, ...), or null
//
// Two arms at once (status.left_arm): one feed per arm. The "right" feed is the brain's first arm
// (status.arm), the "left" feed the left controller's arm. Each takes only the arm_* messages whose
// `device` is its arm. The left feed's `status` is the status as one arm would have it (its own
// joints, limits, frozen, clutch, arm), and null while the brain drives one arm.
// No imports, so tests run it with node.
export class ArmFeed {
  /** @param {"right"|"left"} side */
  constructor(link, side = "right") {
    this.side = side;
    this.joints = {};
    this.lastCommand = null;
    this.frozen = false;
    this.status = null;
    this.armId = null; // "name/model" of the connected arm; a change (or a reconnect) starts over
    this._listeners = [];
    // A reconnect may be a restarted server with another arm: forget the old arm's commands.
    link.on("open", () => this._forget());
    link.on("status", (raw) => {
      const s = side === "left" ? leftView(raw) : raw;
      const id = s ? `${s.arm?.name}/${s.arm?.model}` : null;
      if (id !== this.armId) {
        this._forget();
        this.armId = id;
        this.status = s;
        this._emit("arm");
      }
      this.status = s;
      if (!s) return;
      this.frozen = s.frozen;
      if (!this.lastCommand) {
        this.lastCommand = s.last_command;
        this.joints = s.last_command ? s.last_command.joints : s.joints;
      }
      this._emit("status");
    });
    link.on("arm_command", (m) => {
      if (!this._mine(m)) return;
      this.lastCommand = m;
      this.joints = m.joints;
      this._emit("command");
    });
    link.on("arm_stop", (m) => {
      if (!this._mine(m)) return;
      this.frozen = true;
      this._emit("stop");
    });
    link.on("arm_resume", (m) => {
      if (!this._mine(m)) return;
      this.frozen = false;
      this._emit("resume");
    });
  }

  /** A message for this feed's arm: its `device` is the arm's name (known from the status). */
  _mine(m) {
    return !!this.status && m.device === this.status.arm?.name;
  }

  _forget() {
    this.lastCommand = null;
    this.joints = {};
    this.armId = null;
  }

  /** The 3D model kind the brain says this arm is ("so101", "xarm1s", ...). */
  get modelKind() {
    return this.status?.arm?.model;
  }

  /** fn(feed, why) on every change; why = "arm" (another arm connected, or none) | "status" | "command" | "stop" | "resume". */
  onChange(fn) {
    this._listeners.push(fn);
  }

  _emit(why) {
    for (const fn of this._listeners) fn(this, why);
  }
}

/** The status as the left arm would have it alone, or null without a left arm. */
export function leftView(s) {
  const l = s?.left_arm;
  if (!l) return null;
  return {
    ...s,
    frozen: l.frozen,
    clutch: l.clutch,
    needs_release: l.needs_release,
    joints: l.joints,
    limits: l.limits,
    arm: { name: l.name, model: l.model, connected: l.connected, problem: l.problem },
    last_command: null,
    mode: l.mode,
    one_to_one: l.one_to_one,
    hand_gap_cm: l.hand_gap_cm,
    capture_cm: l.capture_cm,
    servos: null,
    left_arm: null,
  };
}

const feeds = new Map();

/** One ArmFeed per link and side, so modules on the same page share it. */
export function getArmFeed(link, side = "right") {
  if (!feeds.has(link)) feeds.set(link, {});
  const mine = feeds.get(link);
  if (!mine[side]) mine[side] = new ArmFeed(link, side);
  return mine[side];
}
