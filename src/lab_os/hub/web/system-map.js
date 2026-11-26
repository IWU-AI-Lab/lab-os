import { screenTitle } from "/hub/screen-preview.js";

// The live list supplies the devices. The registry supplies model types for older saved entries.
const brain = { id: "", name: "Brain", kind: "brain", connected: true };
const list = document.querySelector("#map-devices");
const status = document.querySelector("#list-status");
const name = document.querySelector("#device-name");
const connection = document.querySelector("#device-connection");
const reset = document.querySelector("#reset-view");
const message = document.querySelector(".map-message");
const mapChrome = document.querySelectorAll(".map-controls, .map-key");
let devices = [brain], selected = brain.id, scene;

function choose(id) {
  const device = devices.find((entry) => entry.id === id) || brain;
  selected = device.id;
  name.textContent = device.name;
  const via = device.via === "network" ? "Network" : device.via;
  connection.textContent = device === brain ? "Runs lab-os."
    : [device.connected ? "Connected to the brain" : "Disconnected", via, device.preview && screenTitle(device.preview)].filter(Boolean).join(" · ");
  for (const button of list.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.dataset.id === selected));
  }
  scene?.select(device);
}

function show(rows) {
  const focus = list.contains(document.activeElement) ? document.activeElement.dataset.id : undefined;
  devices = [brain, ...rows].sort((a, b) => {
    if (a === brain || b === brain) return a === brain ? -1 : 1;
    return a.kind.localeCompare(b.kind) || a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
  });
  list.replaceChildren(...devices.map((device) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn";
    button.dataset.id = device.id;
    const dot = document.createElement("span");
    dot.className = device.connected ? "pill on" : "pill off";
    dot.setAttribute("aria-hidden", "true");
    const title = document.createElement("span");
    title.textContent = device.name;
    button.append(dot, title);
    if (device !== brain) {
      button.setAttribute("aria-label", `${device.name}, ${device.connected ? "Connected" : "Disconnected"}`);
    }
    li.append(button);
    return li;
  }));
  scene?.setDevices(devices);
  choose(selected);
  fade();
  if (focus !== undefined) {
    ([...list.querySelectorAll("button")].find((button) => button.dataset.id === focus)
      || list.querySelector("button")).focus({ preventScroll: true });
  }
}

list.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (button) choose(button.dataset.id);
});
list.addEventListener("dblclick", (event) => {
  const button = event.target.closest("button");
  if (button) scene?.focus(button.dataset.id);
});

// The list scrolls when it holds more than fits: a fade at the bottom until you reach the end.
const scroller = list.closest(".in");
const fade = () => scroller.classList.toggle("more",
  scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight > 4);
scroller.addEventListener("scroll", fade, { passive: true });
new ResizeObserver(fade).observe(scroller);

async function read(path) {
  const response = await fetch(path, { cache: "no-store", signal: AbortSignal.timeout(6000) });
  if (!response.ok) throw new Error(`Could not read ${path}`);
  return (await response.json()).devices;
}

const configured = read("/api/devices")
  .then((rows) => new Map(rows.map((row) => [row.name, row.kind])))
  .catch(() => new Map());

function showStatus(text) {
  if (status.textContent !== text) status.textContent = text;
}

function entriesWithScreens(rows, types, screens) {
  const windowsByDevice = new Map(screens.map(({ name, windows }) => [`screen:${name}`, windows]));
  return rows.flatMap(({ id, name, kind, via, model, connected }) => {
    const device = { id, name: name || id, kind: kind || "usb", via, connected, model: model || types.get(id) };
    const windows = connected && kind === "screen" ? windowsByDevice.get(id) : null;
    if (!windows?.length) return [device];
    return windows.map(({ stage, screen, showing, from }, index) => ({
      ...device,
      id: index ? `${id}#${index + 1}` : id,
      name: windows.length > 1 ? `${device.name} · Screen ${index + 1}` : device.name,
      preview: { stage, screen: { width: screen?.width, height: screen?.height },
        showing: showing && { id: showing.id, title: showing.title }, from },
    }));
  });
}

let last;
async function refresh() {
  try {
    if (document.hidden) return;
    const [rows, types, screens] = await Promise.all([
      read("/api/live-devices"), configured, read("/api/hub-devices").catch(() => []),
    ]);
    const entries = entriesWithScreens(rows, types, screens);
    const latest = JSON.stringify(entries);
    if (latest !== last) {
      show(entries);
      last = latest;
    }
    showStatus(`${entries.filter((row) => row.connected).length} of ${entries.length} connected`);
  } catch {
    showStatus(last === undefined ? "Cannot read the device list." : "Cannot update the device list. Showing the last update.");
  } finally {
    setTimeout(refresh, 2000);
  }
}

show([]);
refresh();
const canvas = document.querySelector("canvas");
function fallback() {
  canvas.hidden = true;
  for (const element of mapChrome) element.hidden = true;
  document.querySelector(".map-labels").hidden = true;
  message.hidden = false;
}
canvas.addEventListener("webglcontextlost", fallback, { once: true });
import("/hub/system-map-scene.js").then(({ createMap }) => {
  scene = createMap(canvas, document.querySelector(".map-labels"), choose);
  reset.addEventListener("click", scene.reset);
  const hint = document.querySelector(".map-hint");
  const used = () => hint.classList.add("used");
  for (const type of ["pointerdown", "wheel", "keydown"]) {
    canvas.addEventListener(type, used, { once: true, passive: true });
  }
  scene.setDevices(devices);
  choose(selected);
  for (const element of mapChrome) element.hidden = false;
}).catch(fallback);
