// The Command Center and System Map draw the same preview from a hub window's state.
const icons = {
  teleop: "i-hand", diagnostics: "i-test", monitor: "i-screen", "monitor-so101": "i-screen",
  "monitor-xarm": "i-screen", "monitor-raspbot": "i-screen", ai: "i-chip", training: "i-leader",
  cameras: "i-cam", webcam: "i-cam", hub: "i-hex", settings: "i-gear", pages: "i-apps",
  project: "i-next", spend: "i-coin", commits: "i-commit", devices: "i-net", system: "i-net",
  "system-map": "i-net", chat: "i-chat", raspbot: "i-pi", "wake-word": "i-user",
  remote: "i-touch", xr: "i-headset", command: "i-target",
};

export const screenTitle = (window) => window.showing?.title || (window.stage === "start" ? "Start screen" : "The Hub");

const escape = (text) => String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** The icon id (in /web/design/icons.svg) for the page a window shows. */
export const previewIcon = (window) => (Object.hasOwn(icons, window.showing?.id) ? icons[window.showing.id] : "i-test");

/** Height over width of a window's screen, kept between 0.42 and 1 (16:9 when unknown). */
export function previewAspect(window) {
  const screen = window.screen || {};
  return screen.width && screen.height ? Math.min(1, Math.max(0.42, screen.height / screen.width)) : 9 / 16;
}

export function screenPreview(window, width) {
  const aspect = previewAspect(window);
  const icon = previewIcon(window);
  const image = window.showing
    ? `<div class="mod"><svg class="ico"><use href="/web/design/icons.svg#${icon}"/></svg></div>`
    : `<div class="${window.stage === "start" ? "ring" : "core"}"></div>`;
  const sender = window.showing && window.from ? `<span class="from">From ${escape(window.from)}</span>` : "";
  return `<div class="pv" style="width:${width}px;height:${Math.round(width * aspect)}px">${image}${sender}<span class="say">${escape(screenTitle(window))}</span></div>`;
}
