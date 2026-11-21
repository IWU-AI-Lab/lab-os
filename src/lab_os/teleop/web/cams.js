// Camera pictures on the teleop page (quick job 63): under the joint angles, a picture from each camera of the
// arm (stand and wrist; the brain's /api/arm-cameras), a few a second. The brain opens a camera on the first
// picture and closes it ~5 s after the last, so this page asks only while it's shown. A camera that another
// program has open (LeLab, a recording) gives the brain's sentence instead of a picture.
//   initCams(link)   the teleop page; does nothing where the brain has no cameras API (lab-os-teleop)

const EVERY_MS = 250, AFTER_ERROR_MS = 3000;

export function initCams(link, tries = 50) {
  const box = document.getElementById("arm-cams");
  // the 3D panel's script (arm-panel.js) makes the box, and it runs after this page's script
  if (!box) { if (tries > 0) setTimeout(() => initCams(link, tries - 1), 100); return; }
  let arm = null, running = 0;

  async function load() {
    let d;
    try {
      const r = await fetch("/api/arm-cameras", { cache: "no-store" });
      if (!r.ok) return; // no cameras API here (teleop on its own)
      d = await r.json();
    } catch {
      return;
    }
    const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    box.hidden = false;
    box.innerHTML = d.cameras.length
      ? d.cameras.map((c) => `<figure data-name="${esc(c.name)}"><img alt="${esc(c.label)} camera"><figcaption>${esc(c.label)}</figcaption><p class="hint cam-why" hidden></p></figure>`).join("")
      : `<p class="hint">No cameras for ${esc(d.arm)} (devices.yaml names them ${esc(d.arm)}-cam-stand and ${esc(d.arm)}-cam-wrist).</p>`;
    start();
  }

  // one loop per camera: ask, show, wait; a new loop replaces the old ones (`running` counts them)
  function start() {
    const run = ++running;
    for (const fig of box.querySelectorAll("figure")) loop(fig, run);
  }
  async function loop(fig, run) {
    const img = fig.querySelector("img"), why = fig.querySelector(".cam-why");
    while (run === running && !document.hidden) {
      let wait = EVERY_MS;
      try {
        const r = await fetch(`/api/camera-feed/${encodeURIComponent(fig.dataset.name)}`, { cache: "no-store" });
        if (r.ok) {
          const url = URL.createObjectURL(await r.blob()), old = img.src;
          img.src = url;
          if (old.startsWith("blob:")) URL.revokeObjectURL(old);
          why.hidden = true;
          img.hidden = false;
        } else {
          why.textContent = `No picture: ${await r.text()}`;
          why.hidden = false;
          img.hidden = !img.src; // no broken picture before the first one
          wait = AFTER_ERROR_MS;
        }
      } catch {
        wait = AFTER_ERROR_MS; // the brain is away: the page's own banner says so
      }
      await new Promise((ok) => setTimeout(ok, wait));
    }
  }

  document.addEventListener("visibilitychange", () => { if (!document.hidden) start(); else running++; });
  link.on("status", (s) => {
    const name = s.arm?.name ?? null;
    if (name !== arm) { arm = name; load(); } // another arm (one plugged in later): its cameras
  });
  load();
}
