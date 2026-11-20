// No long-press menu on the hub pages (quick job 65): on a touch screen (the Newline), a long press opened
// the browser's menu (Inspect, Save image). The ask line and other text fields keep it, so text there can
// still be selected and pasted. A mouse's right click keeps it too (Inspect on the desktop), except where a
// page uses the right button itself (desktop control's gripper).
//   <script type="module" src="/web/no-menu.js"></script>   (or import "/web/no-menu.js")

const FIELDS = "input, textarea, [contenteditable]:not([contenteditable='false'])";

export function blocksMenu(e) {
  if (e.pointerType === "mouse") return false; // a right click: the developer's menu stays
  return !e.target?.closest?.(FIELDS);
}

addEventListener("contextmenu", (e) => { if (blocksMenu(e)) e.preventDefault(); }, { capture: true });

// iOS and some Android browsers show their own callout (Save image, Copy link) without a contextmenu event
const style = document.createElement("style");
style.textContent = `body { -webkit-touch-callout: none; } input, textarea, [contenteditable] { -webkit-touch-callout: default; }`;
document.head.append(style);
