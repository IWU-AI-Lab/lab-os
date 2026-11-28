// The Monitor list (quick job 147): a card for each kind of robot (KINDS), like All Pages' tiles
// (quick job 170), with how many of that kind are connected. A tap opens that kind's Monitor page: in
// the hub as its module (the hub's views: monitor-so101, monitor-xarm), else the page.
import { getLink } from "/static/link.js";
import { armView } from "/static/arm/arm-feed.js";
import { KINDS } from "/static/arm/kinds.js";
import { watchRaspbot } from "/web/raspbot-status.js";

const $ = (id) => document.getElementById(id);
const link = getLink("monitor"); // a watcher: it can only stop

let inHub = false;
try { inHub = parent !== window && parent.location.origin === location.origin && parent.location.pathname === "/"; } catch {}

function addCard(kind, title) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn tile";
  button.innerHTML = '<svg class="ico" aria-hidden="true"><use href="/web/design/icons.svg#i-screen"/></svg><b></b><small>Connecting…</small>';
  button.querySelector("b").textContent = title;
  button.onclick = () => {
    if (inHub) return parent.postMessage({ type: "lab-os-open-view", id: `monitor-${kind}` }, location.origin);
    location.href = `/monitor/${kind}${location.search}`; // ?device= stays
  };
  $("kinds").append(button);
  return button.querySelector("small");
}

// one form for every card (quick job 155); written only on a change (status comes many times a second)
function showCount(line, n) {
  const text = n ? `${n} connected` : "None connected";
  if (line.textContent !== text) line.textContent = text;
}

const cards = {};
for (const [kind, k] of Object.entries(KINDS)) cards[kind] = addCard(kind, k.title);

// Only the full hub has a Raspbot view and a Raspbot status socket.
fetch("/api/hub").then((response) => response.ok ? response.json() : null).then((hub) => {
  const view = hub?.views.find((v) => v.id === "monitor-raspbot");
  if (!view) return;
  const line = addCard("raspbot", view.title);
  watchRaspbot((status) => showCount(line, status?.connected ? 1 : 0));
}).catch(() => {});

link.on("status", (s) => {
  for (const [kind, line] of Object.entries(cards)) {
    showCount(line, ["right", "left"].filter((side) => armView(s, side, kind)).length);
  }
});
const setConn = (text, cls) => { $("conn").textContent = text; $("conn").className = `pill ${cls}`; };
link.on("open", () => setConn("Connected", "on"));
link.on("close", () => setConn("Disconnected", "off"));
$("stop").onclick = () => link.send({ type: "stop" });
