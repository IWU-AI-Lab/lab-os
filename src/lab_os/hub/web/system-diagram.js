// The system diagram (quick job 12): the brain as a core of rings in the middle, the screens with the hub open on
// the left, the robots (cameras, arms) on the right, the AI service above, an AI tool (MCP) and the training
// program below their columns. Drawn from the real facts every time it opens (devices.yaml, the devices with the
// hub open, the AI setup, the robot tools), so a new arm or a missing one shows as it is. Not a second devices map:
// that one lists every device; this one shows how the pieces connect (USB solid, network dashed, MCP dotted,
// internet long dashes: readable without colour), what sits inside the brain, and the AI around it.
//
//   systemFacts({devices, hubDevices, status, mcp, here})  the facts, from the brain's answers (see the hub)
//   systemSVG(facts, {animate, icons})                     the drawing, an SVG string (self-contained styles)
//
// Colours come from the page's CSS variables (the theme), with the theme's numbers as fallbacks so the saved copy
// (docs/dev/system-diagram.svg) looks the same outside the hub. Only real links pulse (DESIGN.md: never claim
// what isn't real): a screen with the hub open, the arm the brain drives, a connected AI.

const ARM_KINDS = new Set(["so101", "xarm1s", "arm", "fake"]);
const SCREEN_ICON = { quest: "i-headset", headset: "i-headset", pi: "i-pi", pc: "i-pc" };
const W = 1600, H = 900, CX = 800, CY = 440, R = 170; // the core's outer ring: where every trace lands
const MAX_ROWS = 6; // per column; more are folded into one "+N more"
const LOCAL = /^(127\.|::1$|::ffff:127\.)/;

// Device names show as they are stored ("so101-white"), or a screen's display name (quick job 153: the
// drawing made "Rv Laptop" of "rv-laptop", so one device had two names on the hub).

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** The facts to draw, from /api/devices, /api/hub-devices (or the device link's list), /api/status, /api/ai-calls. */
export function systemFacts({ devices = [], hubDevices = [], status = null, mcp = false, here = "" } = {}) {
  const open = new Map(hubDevices.map((d) => [d.name, d]));
  const listed = new Map(devices.map((d) => [d.name, d]));
  const screens = hubDevices.map((d) => ({
    name: d.name, title: d.title || d.display_name || d.name, icon: SCREEN_ICON[listed.get(d.name)?.kind] || "i-screen", live: true,
    local: LOCAL.test(d.address || ""), here: d.name === here,
  }));
  // screens the place lists (headsets, computers, Pis) that don't have the hub open now: dim
  for (const d of devices) {
    if (SCREEN_ICON[d.kind] && !open.has(d.name)) screens.push({ name: d.name, icon: SCREEN_ICON[d.kind], live: false, here: false });
  }
  if (!screens.some((s) => s.live)) screens.unshift({ name: here || "this screen", icon: "i-screen", live: true, local: true, here: true });
  const arms = devices.filter((d) => ARM_KINDS.has(d.kind) && (d.kind !== "fake" || d.linked))
    .map((d) => ({ name: d.name, kind: d.kind, linked: !!d.linked, borrowed: !!d.borrowed, fake: d.kind === "fake" }))
    .sort((a, b) => a.borrowed - b.borrowed); // borrowed last: next to the training program below them
  const cameras = devices.filter((d) => d.kind === "camera");
  const ai = status?.ai || {};
  return {
    screens, arms,
    cameras: { count: cameras.length, borrowed: cameras.filter((c) => c.borrowed).length },
    ai: { name: ai.where || null, connected: ai.connected === true },
    mcp: !!mcp,
    training: arms.some((a) => a.borrowed),
  };
}

/* ---------- drawing helpers ---------- */
const hexPts = (x, y, r) => Array.from({ length: 6 }, (_, i) => {
  const a = (Math.PI / 3) * i + Math.PI / 6;
  return `${(x + r * Math.cos(a)).toFixed(1)},${(y + r * Math.sin(a)).toFixed(1)}`;
}).join(" ");
const cut = (x, y, w, h, c = 8) => `M${x + c} ${y}H${x + w}V${y + h - c}L${x + w - c} ${y + h}H${x}V${y + c}Z`;

// a trace from a column into the core: straight, one 45° bend, straight, landing on the outer ring
function trace(sx, sy, side, spread) {
  const dir = side === "left" ? 1 : -1;
  const off = Math.max(-R * 0.72, Math.min(R * 0.72, (sy - CY) * spread));
  const ey = CY + off, ex = CX - dir * Math.sqrt(R * R - off * off);
  const dy = Math.abs(sy - ey), bendEnd = ex - dir * 34, bendStart = bendEnd - dir * dy;
  const okBend = dir * (bendStart - sx) >= 0;
  const d = okBend
    ? `M${sx} ${sy}H${bendStart.toFixed(1)}L${bendEnd.toFixed(1)} ${ey.toFixed(1)}H${ex.toFixed(1)}`
    : `M${sx} ${sy}L${bendEnd.toFixed(1)} ${ey.toFixed(1)}H${ex.toFixed(1)}`;
  return { d, ex, ey };
}

function rows(n, top, bottom) {
  if (n <= 0) return [];
  const step = n > 1 ? Math.min(92, (bottom - top) / (n - 1)) : 0, start = (top + bottom) / 2 - (step * (n - 1)) / 2;
  return Array.from({ length: n }, (_, i) => start + i * step);
}

// fold a long list into MAX_ROWS: the live ones first, then "+N more"
function fold(list, keep = MAX_ROWS) {
  if (list.length <= keep) return list;
  const sorted = [...list].sort((a, b) => (b.live || b.linked ? 1 : 0) - (a.live || a.linked ? 1 : 0));
  const rest = sorted.length - (keep - 1);
  return [...sorted.slice(0, keep - 1), { name: `+${rest} more`, icon: "i-hex", more: true }];
}

/** The drawing: an SVG string, 1600×900. opts.icons(id) → the symbol's inner markup (for a copy outside the hub). */
export function systemSVG(f, { animate = true, icons = null } = {}) {
  const out = [], defs = [], pulses = [];
  let pid = 0;
  const icon = (id, x, y, size = 26) => `<svg class="ico" x="${x - size / 2}" y="${y - size / 2}" width="${size}" height="${size}" viewBox="0 0 24 24"><use href="#${id}"/></svg>`;
  const used = new Set();
  // one device: a hexagon badge with its icon; the name beside it (on the side away from the core)
  function node(x, y, n, side, sub) {
    used.add(n.icon);
    const cls = ["node", n.live || n.linked ? "live" : "", n.here ? "here" : "", n.more ? "more" : "", n.borrowed ? "borrowed" : ""].join(" ");
    const tx = side === "left" ? x - 44 : x + 44, anchor = side === "left" ? "end" : "start";
    out.push(`<g class="${cls.trim()}">`);
    if (n.here) out.push(`<path class="reticle" d="M${x - 40} ${y - 26}v-14h14M${x + 26} ${y - 40}h14v14M${x + 40} ${y + 26}v14h-14M${x - 26} ${y + 40}h-14v-14"/>`);
    out.push(`<polygon class="hex" points="${hexPts(x, y, 28)}"/>`);
    if (n.borrowed) out.push(`<polygon class="hatchfill" points="${hexPts(x, y, 22)}"/>`);
    out.push(icon(n.icon, x, y));
    const count = n.count ? `<tspan class="count" dx="10">${n.count}</tspan>` : "";
    out.push(`<text class="name" x="${tx}" y="${y + (sub ? -2 : 6)}" text-anchor="${anchor}">${esc(n.title || n.name)}${count}</text>`);
    if (sub) out.push(`<text class="sub" x="${tx}" y="${y + 18}" text-anchor="${anchor}">${esc(sub)}</text>`);
    out.push(`</g>`);
  }
  function link(d, kind, live, inward = true) {
    out.push(`<path class="ln ${kind}${live ? " live" : ""}" d="${d}"/>`);
    if (live && animate) {
      const id = `p${pid++}`, dur = 2.6 + ((pid * 0.37) % 1.6);
      defs.push(`<path id="${id}" d="${d}"/>`);
      pulses.push(`<circle class="pulse" r="3.2"><animateMotion dur="${dur.toFixed(2)}s" begin="-${((pid * 0.9) % dur).toFixed(2)}s" repeatCount="indefinite" keyPoints="${inward ? "0;1" : "1;0"}" keyTimes="0;1" calcMode="linear"><mpath href="#${id}"/></animateMotion></circle>`);
    }
  }
  const dot = (x, y, cls = "") => out.push(`<circle class="end ${cls}" cx="${x}" cy="${y}" r="3.5"/>`);
  function caption(x1, x2, y, text, side) {
    const tx = side === "left" ? x1 : x2, anchor = side === "left" ? "start" : "end";
    out.push(`<path class="capline" d="M${x1} ${y}H${x2}"/><circle class="end" cx="${side === "left" ? x2 : x1}" cy="${y}" r="2.5"/>`);
    out.push(`<text class="cap" x="${tx}" y="${y - 9}" text-anchor="${anchor}">${esc(text)}</text>`);
  }

  /* ---- the background: + marks at grid crossings, a ruler and a hatch block, as on the hub (the page frames it) ---- */
  for (let x = 200; x < W; x += 200) for (let y = 100; y < H; y += 200) if (Math.abs(x - CX) > 260 || Math.abs(y - CY) > 240) out.push(`<path class="plus" d="M${x - 5} ${y}h10M${x} ${y - 5}v10"/>`);
  out.push(`<g class="ruler">${Array.from({ length: 41 }, (_, i) => `<path d="M${CX - 200 + i * 10} ${H - 30}v${i % 10 ? -5 : -11}"/>`).join("")}</g>`);
  out.push(`<rect class="hatchfill" x="${W - 132}" y="40" width="80" height="10"/>`);

  /* ---- left: screens, then the AI tool below them ---- */
  const LX = 420, RX = 1180;
  const screens = fold(f.screens);
  const leftRows = rows(screens.length, 170, f.mcp ? 600 : 720);
  caption(170, 460, leftRows[0] - 52, "Screens", "left");
  screens.forEach((s, i) => {
    const y = leftRows[i], t = trace(LX + 30, y, "left", 0.42);
    if (!s.more) { link(t.d, "net", s.live, true); dot(LX + 30, y); dot(t.ex, t.ey); }
    node(LX, y, s, "left", s.more ? "" : !s.live ? "Hub not open" : s.local ? "This computer: drives" : "Network: watches, STOP");
  });
  if (f.mcp) {
    const y = 760, t = trace(LX + 30, y, "left", 0.3);
    link(t.d, "mcp", false); dot(LX + 30, y); dot(t.ex, t.ey);
    node(LX, y, { name: "AI tools", icon: "i-chip" }, "left", "MCP :8081, this computer only");
  }

  /* ---- right: cameras, arms, then the training program below the borrowed arm ---- */
  const right = [];
  if (f.cameras.count) right.push({ name: "Cameras", icon: "i-cam", count: f.cameras.count, cam: true });
  right.push(...fold(f.arms.map((a) => ({ ...a, icon: "i-arm" })), MAX_ROWS - (f.cameras.count ? 1 : 0)));
  const rightRows = rows(right.length, 170, f.training ? 600 : 720);
  if (right.length) caption(1140, 1430, rightRows[0] - 52, "Robots", "right");
  right.forEach((n, i) => {
    const y = rightRows[i], t = trace(RX - 30, y, "right", 0.42);
    if (!n.more) { link(t.d, "usb", n.linked, !!n.cam); dot(RX - 30, y); dot(t.ex, t.ey); }
    const sub = n.cam ? `USB, by socket${f.cameras.borrowed ? `, ${f.cameras.borrowed} borrowed` : ""}`
      : n.more ? "" : n.fake ? "Software, no cable" : `USB${n.linked ? ", driven now" : ""}${n.borrowed ? ", borrowed" : ""}`;
    node(RX, y, n, "right", sub);
  });
  if (f.training) {
    const y = 760, armY = rightRows[right.length - 1];
    out.push(`<path class="ln turn" d="M${RX} ${y - 30}V${armY + 30}"/>`);
    dot(RX, y - 30, "warm"); dot(RX, armY + 30, "warm");
    const lent = f.arms.filter((a) => a.borrowed).map((a) => a.name).join(", ");
    node(RX, y, { name: "LeLab", icon: "i-leader" }, "right", `Training: takes turns on ${lent}`);
  }
  if (!right.length) out.push(`<text class="sub" x="${RX}" y="${CY}">No arms or cameras in devices.yaml</text>`);

  /* ---- above: the AI service ---- */
  {
    const y = 110, ai = { name: f.ai.name || "AI", icon: "i-globe", live: f.ai.connected };
    link(`M${CX} ${y + 30}V${CY - R}`, "web", f.ai.connected, true);
    dot(CX, y + 30); dot(CX, CY - R);
    node(CX, y, ai, "right", f.ai.name ? (f.ai.connected ? "Answers, speech, voices" : "Not connected") : "Not set up (.env)");
  }

  /* ---- the core: the brain ---- */
  const ticks = Array.from({ length: 72 }, (_, i) => {
    const a = (i / 72) * Math.PI * 2, r1 = R - (i % 6 ? 6 : 13);
    return `M${(CX + R * Math.cos(a)).toFixed(1)} ${(CY + R * Math.sin(a)).toFixed(1)}L${(CX + r1 * Math.cos(a)).toFixed(1)} ${(CY + r1 * Math.sin(a)).toFixed(1)}`;
  }).join("");
  const arc = (r, a0, a1) => {
    const p = (a) => `${(CX + r * Math.cos(a)).toFixed(1)} ${(CY + r * Math.sin(a)).toFixed(1)}`;
    return `M${p(a0)}A${r} ${r} 0 0 1 ${p(a1)}`;
  };
  const deg = Math.PI / 180;
  out.push(`<g class="core">
    <path class="ticks" d="${ticks}"/>
    <g class="spin slow"><circle class="seg" cx="${CX}" cy="${CY}" r="150"/></g>
    <g class="spin rev glow"><path class="arcs" d="${arc(128, -80 * deg, -10 * deg)}${arc(128, 40 * deg, 110 * deg)}${arc(128, 160 * deg, 230 * deg)}"/></g>
    <circle class="thin" cx="${CX}" cy="${CY}" r="104"/>
    <g class="spin fast"><circle class="sat" cx="${CX}" cy="${CY}" r="88"/><circle class="satdot" cx="${CX + 88}" cy="${CY}" r="3"/></g>
    <circle class="ring" cx="${CX}" cy="${CY}" r="66"/>
    <circle class="halo breathe" cx="${CX}" cy="${CY}" r="58"/>
  </g>`);
  out.push(`<text class="brain" x="${CX}" y="${CY + R + 46}" text-anchor="middle">BRAIN</text>`);
  {
    // inside the brain, in the order a move takes: who asks, then the safety layer, then the arm
    const parts = ["Assistant", "Hub :8080", "Robot tools", "Safety layer", "Arm drivers"], w = 104, gap = 20;
    const x0 = CX - (parts.length * w + (parts.length - 1) * gap) / 2, y = CY + R + 82;
    parts.forEach((p, i) => {
      const x = x0 + i * (w + gap);
      out.push(`<path class="part${p === "Safety layer" ? " safe" : ""}" d="${cut(x, y, w, 34)}"/><text class="pname" x="${x + w / 2}" y="${y + 22}" text-anchor="middle">${p}</text>`);
      if (i) out.push(`<path class="chev" d="M${x - 15} ${y + 11}l5 6-5 6"/>`);
    });
    out.push(`<text class="sub" x="${CX}" y="${y + 58}" text-anchor="middle">Every move, from a screen or an AI tool, goes through the safety layer</text>`);
    // the key to the lines
    const key = [["usb", "USB"], ["net", "Network"], ["mcp", "MCP"], ["web", "Internet"], ["turn", "Takes turns"]];
    out.push(`<g class="key">${key.map(([k, t], i) => `<path class="ln ${k}" d="M${60 + i * 150} 60h40"/><text class="sub" x="${110 + i * 150}" y="65">${t}</text>`).join("")}</g>`);
  }

  const symbols = icons ? [...used, "i-hex"].map((id) => icons(id)).filter(Boolean).join("") : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" class="sysdiag" viewBox="0 0 ${W} ${H}" role="img" aria-label="System diagram: the brain in the middle, the screens on the left, the robots on the right">
<style>${STYLE}</style>
<defs>
  <pattern id="sd-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--accent, #ff9a2e)" stroke-opacity="0.55" stroke-width="2"/></pattern>
  <radialGradient id="sd-core"><stop offset="0" stop-color="var(--hot, #eafcff)"/><stop offset="0.35" stop-color="var(--hot, #eafcff)" stop-opacity="0.9"/><stop offset="0.6" stop-color="var(--primary, #29d4ff)" stop-opacity="0.55"/><stop offset="1" stop-color="var(--primary, #29d4ff)" stop-opacity="0"/></radialGradient>
  <filter id="sd-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  ${symbols}${defs.join("")}
</defs>
${out.join("\n")}
${pulses.join("\n")}
</svg>`;
}

const STYLE = `
.sysdiag { --sd-c: var(--primary, #29d4ff); --sd-line: var(--line, #1f3d48); --sd-text: var(--text, #d4eef5); --sd-dim: var(--text-dim, #6d8c96);
  --sd-hot: var(--hot, #eafcff); --sd-off: var(--offline, #56636a); --sd-warm: var(--accent, #ff9a2e); --sd-bg: var(--bg, #05080b); --sd-surface: var(--surface, #0b161c); }
.sysdiag .ico { color: var(--sd-c); fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; overflow: visible; }
.sysdiag .node:not(.live) .ico { color: var(--sd-off); }
.sysdiag .hex { fill: var(--sd-surface); stroke: var(--sd-off); stroke-width: 1.2; }
.sysdiag .node.live .hex { stroke: var(--sd-c); stroke-width: 1.8; filter: url(#sd-glow); }
.sysdiag .node.here .hex { fill: color-mix(in srgb, var(--sd-c) 18%, var(--sd-surface)); }
.sysdiag .reticle { fill: none; stroke: var(--sd-hot); stroke-width: 1.5; }
.sysdiag .hatchfill { fill: url(#sd-hatch); stroke: none; }
.sysdiag .name { font: 500 22px var(--f-ui, "Chakra Petch", system-ui, sans-serif); fill: var(--sd-text); }
.sysdiag .node:not(.live) .name { fill: var(--sd-dim); }
.sysdiag .node.here .name { fill: var(--sd-hot); }
.sysdiag .sub { font: var(--w-lines, 300) 14px var(--f-lines, Inter, system-ui, sans-serif); fill: var(--sd-dim); }
.sysdiag .count { font: 18px var(--f-digits, DSEG7, monospace); fill: var(--sd-hot); }
.sysdiag .cap { font: 600 13px var(--f-ui, "Chakra Petch", system-ui, sans-serif); letter-spacing: 0.22em; text-transform: uppercase; fill: var(--sd-c); }
.sysdiag .capline { stroke: color-mix(in srgb, var(--sd-c) 55%, transparent); stroke-width: 1; }
.sysdiag .brain { font: 700 20px var(--f-title, Orbitron, system-ui, sans-serif); letter-spacing: 0.4em; fill: var(--sd-hot); }
.sysdiag .end { fill: var(--sd-c); }
.sysdiag .end.warm { fill: var(--sd-warm); }
.sysdiag .ln { fill: none; stroke: var(--sd-off); stroke-width: 1.5; }
.sysdiag .ln.live { stroke: var(--sd-c); stroke-width: 2; }
.sysdiag .ln.net { stroke-dasharray: 9 6; }
.sysdiag .ln.mcp { stroke-dasharray: 1 6; stroke-linecap: round; stroke-width: 2.4; stroke: var(--sd-c); }
.sysdiag .ln.web { stroke-dasharray: 22 7; }
.sysdiag .ln.usb { }
.sysdiag .ln.turn { stroke: var(--sd-warm); stroke-dasharray: 4 5; }
.sysdiag .key .ln { stroke: var(--sd-c); }
.sysdiag .key .ln.turn { stroke: var(--sd-warm); }
.sysdiag .pulse { fill: var(--sd-hot); filter: url(#sd-glow); }
.sysdiag .frame { fill: none; stroke: var(--sd-c); stroke-width: 2; }
.sysdiag .plus { stroke: var(--sd-line); stroke-width: 1; }
.sysdiag .ruler path { stroke: var(--sd-line); stroke-width: 1; }
.sysdiag .core .brk { fill: none; stroke: var(--sd-c); stroke-width: 1.5; }
.sysdiag .core .ticks { stroke: var(--sd-line); stroke-width: 1.2; }
.sysdiag .core .seg { fill: none; stroke: var(--sd-c); stroke-opacity: 0.8; stroke-width: 2; stroke-dasharray: 30 6 4 6; }
.sysdiag .core .arcs { fill: none; stroke: var(--sd-c); stroke-width: 4; }
.sysdiag .core .glow { filter: url(#sd-glow); }
.sysdiag .core .thin { fill: none; stroke: var(--sd-c); stroke-opacity: 0.45; stroke-dasharray: 1 4; }
.sysdiag .core .sat { fill: none; stroke: var(--sd-c); stroke-opacity: 0.35; stroke-width: 0.8; }
.sysdiag .core .satdot { fill: var(--sd-c); }
.sysdiag .core .halo { fill: url(#sd-core); }
.sysdiag .core .ring { fill: none; stroke: var(--sd-c); stroke-opacity: 0.6; stroke-width: 1; }
.sysdiag .core .breathe { transform-box: view-box; transform-origin: ${CX}px ${CY}px; animation: sd-breathe 5s ease-in-out infinite; }
@keyframes sd-breathe { 50% { transform: scale(0.92); opacity: 0.85; } }
.sysdiag .spin { transform-box: view-box; transform-origin: ${CX}px ${CY}px; }
.sysdiag .spin.slow { animation: sd-spin 80s linear infinite; }
.sysdiag .spin.rev { animation: sd-spin 50s linear infinite reverse; }
.sysdiag .spin.fast { animation: sd-spin 24s linear infinite; }
@keyframes sd-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .sysdiag .spin, .sysdiag .breathe { animation: none; } .sysdiag .pulse { display: none; } }
.sysdiag .part { fill: var(--sd-surface); stroke: var(--sd-line); }
.sysdiag .part.safe { stroke: var(--sd-c); }
.sysdiag .pname { font: 500 14px var(--f-ui, "Chakra Petch", system-ui, sans-serif); fill: var(--sd-text); }
.sysdiag .chev { fill: none; stroke: var(--sd-c); stroke-width: 1.5; }
`;
