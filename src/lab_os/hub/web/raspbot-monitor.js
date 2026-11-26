import { raspbotMotion, watchRaspbot } from "/web/raspbot-status.js";

const $ = (id) => document.getElementById(id);
const unavailable = "Unavailable";
const device = new URLSearchParams(location.search).get("device") || "";
const image = $("camera");
const placeholder = $("camera-status");
let latest, model, retryAt = 0;

import("/web/raspbot-view.js")
  .then(({ createRaspbotView }) => createRaspbotView($("raspbot-model")))
  .then((view) => { model = view; view.update(latest); })
  .catch(() => { $("raspbot-model").hidden = true; $("model-error").hidden = false; });

image.onload = () => { image.hidden = false; placeholder.hidden = true; };
image.onerror = () => {
  image.removeAttribute("src");
  image.hidden = true;
  placeholder.hidden = false;
  placeholder.textContent = "The camera does not answer.";
  retryAt = Date.now() + 2000;
};

function showCamera(status) {
  if (status?.connected && status.camera) {
    if (!image.hasAttribute("src") && Date.now() >= retryAt) {
      image.src = `/api/raspbot/camera.mjpg?t=${Date.now()}`;
    }
    return;
  }
  image.removeAttribute("src");
  image.hidden = true;
  placeholder.hidden = false;
  placeholder.textContent = status?.fake ? "The fake Raspbot has no camera." : "No camera picture.";
}

function show(status) {
  latest = status;
  model?.update(status);
  showCamera(status);
  const live = status?.connected;
  const state = $("state");
  state.textContent = !status ? "Brain not reachable" : !live ? "Not connected" : status.fake ? "Fake Raspbot" : "Connected";
  state.className = `pill ${!live ? "bad" : status.fake ? "off" : "on"}`;
  $("name").textContent = status?.name && !status.fake ? status.name : "Raspbot";
  $("control").textContent = live ? { free: "Free", other: "Another controller" }[status.control] || unavailable : unavailable;
  $("motion").textContent = raspbotMotion(status);
  $("speed").textContent = live ? `${Math.round(status.speed * 100)}%` : unavailable;
  $("pan").textContent = live && status.pan_deg != null ? `${status.pan_deg}°` : unavailable;
  $("tilt").textContent = live && status.tilt_deg != null ? `${status.tilt_deg}°` : unavailable;
  $("distance").textContent = live && status.distance_mm != null ? `${status.distance_mm / 10} cm` : unavailable;
}

const link = watchRaspbot(show);
$("stop").onclick = () => link.stop(device);
