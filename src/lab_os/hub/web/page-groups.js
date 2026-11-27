export const PAGE_GROUPS = [
  ["Robots", ["teleop", "monitor", "monitor-so101", "monitor-xarm", "monitor-raspbot", "ai", "training", "webcam", "raspbot"]],
  ["Cameras", ["cameras"]],
  ["The hub", ["hub", "settings", "wake-word", "diagnostics", "project", "spend", "commits", "devices", "system", "chat", "pages", "remote", "xr", "command"]],
];

// each page's icon: the Command Center and All Pages show the same ones (quick job 160)
export const VIEW_ICON = {
  teleop: "i-hand", diagnostics: "i-test", monitor: "i-screen", "monitor-so101": "i-screen", "monitor-xarm": "i-screen", "monitor-raspbot": "i-screen", ai: "i-chip", training: "i-leader", cameras: "i-cam", webcam: "i-cam",
  hub: "i-hex", settings: "i-gear", pages: "i-apps", project: "i-next", spend: "i-coin", commits: "i-commit", devices: "i-net",
  system: "i-net", chat: "i-chat", raspbot: "i-pi", "wake-word": "i-user", remote: "i-touch", xr: "i-headset", command: "i-target",
};
// each group's icon
export const GROUP_ICON = { Robots: "i-arm", Cameras: "i-cam", "The hub": "i-hex", Other: "i-apps" };
