const MOTION = {
  forward: "Forward", back: "Back", left: "Turning left", right: "Turning right", stick: "Driving",
  "forward-left": "Forward left", "forward-right": "Forward right",
  "strafe-left": "Sideways left", "strafe-right": "Sideways right",
  "back-left": "Back left", "back-right": "Back right",
};

export function raspbotMotion(status) {
  return status?.connected ? MOTION[status.moving] || "Stopped" : "Unavailable";
}

/** The Monitor's socket (role=monitor): onStatus(status | null); onMessage(m) gets the other messages
 * (labels), onOpen() each time it connects. */
export function watchRaspbot(onStatus, { onMessage, onOpen } = {}) {
  let socket;
  function connect() {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${scheme}//${location.host}/ws/raspbot?role=monitor`);
    socket.onopen = () => onOpen?.();
    socket.onmessage = (event) => {
      const m = JSON.parse(event.data);
      if (m.type === "raspbot_status") onStatus(m);
      else onMessage?.(m);
    };
    socket.onclose = () => {
      onStatus(null);
      setTimeout(connect, 2000);
    };
  }
  connect();
  function send(msg) {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg));
  }
  return { send, stop: (device) => send({ type: "stop", device }) };
}
