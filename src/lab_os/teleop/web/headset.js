// Is this page in a headset's own browser? (quick job 87)
//
// A headset is told by its browser (the Quest's is "OculusBrowser"), not by WebXR support: a desktop
// with the Immersive Web Emulator extension has WebXR too, and the extension also gives the page a
// Quest's browser name. What the extension can't fake is the browser's own WebXR: it puts a JavaScript
// copy of `navigator.xr` in its place, so a `requestSession` that isn't the browser's own code means
// a desktop. A desktop's system name (macOS, Windows) in `userAgentData` means the same.

const DESKTOP_SYSTEMS = ["macOS", "Windows", "Chrome OS"];

/** True only in a real headset's browser. `nav` is `navigator` (a parameter for the tests). */
export function isHeadset(nav = globalThis.navigator) {
  if (!nav || !/OculusBrowser/.test(nav.userAgent || "")) return false;
  if (DESKTOP_SYSTEMS.includes(nav.userAgentData?.platform)) return false;
  const request = nav.xr?.requestSession;
  if (typeof request === "function" && !/\[native code\]/.test(Function.prototype.toString.call(request))) {
    return false; // an emulator's WebXR
  }
  return true;
}
