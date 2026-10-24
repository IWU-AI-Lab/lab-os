// One auto-reconnecting WebSocket to the brain per role, shared by every module on the page.
//   const link = getLink("input");  link.on("status", fn);  link.send({type: "xr_input", ...})
// Message format: docs/protocol.md. Events "open" / "close" fire on (re)connect / disconnect.
const links = {};

export function getLink(role = "input") {
  if (links[role]) return links[role];
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${location.host}/ws${role === "input" ? "" : `?role=${role}`}`;
  const listeners = {};
  const emit = (type, msg) => (listeners[type] || []).forEach((fn) => fn(msg));
  let ws = null;

  function open() {
    ws = new WebSocket(url);
    ws.onopen = () => emit("open");
    ws.onclose = () => {
      emit("close");
      setTimeout(open, 1000);
    };
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      emit(msg.type, msg);
    };
  }
  open();

  links[role] = {
    send(obj) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    },
    on(type, fn) {
      (listeners[type] ||= []).push(fn);
    },
  };
  return links[role];
}
