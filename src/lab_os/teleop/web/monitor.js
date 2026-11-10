// Live view of the arm: one bar per joint, driven by the server's `status` messages.
"use strict";

const $ = (id) => document.getElementById(id);
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws?role=monitor`;
const rows = {};

function setPill(el, text, cls) {
  el.textContent = text;
  el.className = `pill ${cls}`;
}

function row(name, lo, hi) {
  if (rows[name]) return rows[name];
  const el = document.createElement("div");
  el.className = "joint";
  el.innerHTML = `<span class="label">${name}</span>
    <div class="track"><div class="zero"></div><div class="knob"></div></div>
    <span class="value"></span>`;
  $("joints").appendChild(el);
  rows[name] = { el, lo, hi, knob: el.querySelector(".knob"), value: el.querySelector(".value") };
  return rows[name];
}

function show(s) {
  setPill($("input"), s.connected ? "live" : "none", s.connected ? "on" : "off");
  const who = { free: "free", ai: "the AI tools" }[s.control] || "an input page";
  setPill($("control"), who, s.control === "free" ? "off" : "on");
  if (s.frozen) setPill($("state"), s.needs_release ? "frozen: release grip" : "frozen", "warn");
  else if (s.clutch) setPill($("state"), "following (clutch)", "on");
  else setPill($("state"), "holding", "off");
  for (const [name, v] of Object.entries(s.joints)) {
    const [lo, hi] = s.limits[name] || [-180, 180];
    const r = row(name, lo, hi);
    r.knob.style.left = `${((v - lo) / (hi - lo)) * 100}%`;
    r.value.textContent = `${v >= 0 ? "+" : ""}${v.toFixed(1)}°`;
  }
}

let socket = null;
$("stop").onclick = () => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify({ type: "stop" }));

function connect() {
  const ws = new WebSocket(WS_URL);
  socket = ws;
  ws.onopen = () => setPill($("conn"), "connected", "on");
  ws.onclose = () => {
    setPill($("conn"), "disconnected", "off");
    setTimeout(connect, 1000);
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "status") show(msg);
  };
}

connect();
