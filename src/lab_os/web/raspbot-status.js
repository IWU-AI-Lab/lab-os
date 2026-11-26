const MOTION = {
  forward: "Forward", back: "Back", left: "Turning left", right: "Turning right", stick: "Driving",
  "forward-left": "Forward left", "forward-right": "Forward right",
  "strafe-left": "Sideways left", "strafe-right": "Sideways right",
  "back-left": "Back left", "back-right": "Back right",
};

export function raspbotMotion(status) {
  return status?.connected ? MOTION[status.moving] || "Stopped" : "Unavailable";
}

export function watchRaspbot(onStatus) {
  let socket;
  function connect() {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${scheme}//${location.host}/ws/raspbot?role=monitor`);
    socket.onmessage = (event) => {
      const status = JSON.parse(event.data);
      if (status.type === "raspbot_status") onStatus(status);
    };
    socket.onclose = () => {
      onStatus(null);
      setTimeout(connect, 2000);
    };
  }
  connect();
  return {
    stop(device) {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "stop", device }));
      }
    },
  };
}
