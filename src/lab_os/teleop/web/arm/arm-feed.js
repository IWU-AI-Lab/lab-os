// What the arm driver has been told, tracked from a link's status / arm_* messages (protocol.md).
// Shared by every view of the arm (desktop 3D panel, XR ghost arm) so they always agree:
//   joints       angles of the latest arm_command (unclamped), or the driver's state before any
//   lastCommand  that arm_command message (has seq, speed_scale, driver_joints), or null
//   frozen       arm_stop sent and not resumed
//   status       latest status message (clutch, speed, arm.model, ...)
export class ArmFeed {
  constructor(link) {
    this.joints = {};
    this.lastCommand = null;
    this.frozen = false;
    this.status = null;
    this._listeners = [];
    link.on("status", (s) => {
      this.status = s;
      this.frozen = s.frozen;
      if (!this.lastCommand) {
        this.lastCommand = s.last_command;
        this.joints = s.last_command ? s.last_command.joints : s.joints;
      }
      this._emit("status");
    });
    link.on("arm_command", (m) => {
      this.lastCommand = m;
      this.joints = m.joints;
      this._emit("command");
    });
    link.on("arm_stop", () => {
      this.frozen = true;
      this._emit("stop");
    });
    link.on("arm_resume", () => {
      this.frozen = false;
      this._emit("resume");
    });
  }

  /** The 3D model kind the brain says this arm is ("so101", "xarm1s", ...). */
  get modelKind() {
    return this.status?.arm?.model;
  }

  /** fn(feed, why) on every change; why = "status" | "command" | "stop" | "resume". */
  onChange(fn) {
    this._listeners.push(fn);
  }

  _emit(why) {
    for (const fn of this._listeners) fn(this, why);
  }
}

const feeds = new Map();

/** One ArmFeed per link, so modules on the same page share it. */
export function getArmFeed(link) {
  if (!feeds.has(link)) feeds.set(link, new ArmFeed(link));
  return feeds.get(link);
}
