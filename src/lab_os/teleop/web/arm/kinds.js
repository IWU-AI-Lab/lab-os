// The kinds of robot with a Monitor page of their own (quick job 147): /monitor/<kind>. A new kind is
// one more entry here and in MONITOR_KINDS (src/lab_os/teleop/server.py). `models`: the arm drivers'
// `model` values (status.arm.model) of that kind. No imports, so tests run it with node.
export const KINDS = {
  so101: { title: "SO-101 Monitor", robot: "SO-101 arm", models: ["so101"] },
  xarm: { title: "xArm Monitor", robot: "xArm", models: ["xarm1s"] },
};

/** The kind of an arm driver's model ("so101" → "so101", "xarm1s" → "xarm"), or null. */
export function kindOf(model) {
  for (const [kind, k] of Object.entries(KINDS)) if (k.models.includes(model)) return kind;
  return null;
}

/** The kind a page's address names (/monitor/xarm → "xarm"), or null (every other page). */
export function pageKind(pathname) {
  const m = /^\/monitor\/([a-z0-9-]+)\/?$/.exec(pathname || "");
  return m && KINDS[m[1]] ? m[1] : null;
}
