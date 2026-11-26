#!/usr/bin/env python3
"""lab-os's program on the Raspbot (Yahboom Raspbot v2, Raspberry Pi 5). Quick job 72.

Robots stay thin: this one file, the Python 3 of the Raspbot and Yahboom's own `Raspbot_Lib`
(installed on the factory image). It is deployed from the lab-os repo (`lab-os raspbot deploy`);
never edit it on the Raspbot.

    TCP  :8765   the brain's commands, one JSON line each (lab_os/robots/raspbot.py):
                 {"drive": [left, right]} (-1.0 … 1.0), {"stop": true},
                 {"look": [pan, tilt]}: the camera's two servos, degrees from their centre
                 (pan + = left, tilt + = up), kept inside PAN_RANGE and TILT_RANGE (quick job 107)
                 {"diagnostics": true}: read the ultrasonic distance in mm
    HTTP :8766   /camera.mjpg, the camera's picture (only when OpenCV and a camera are there)

Safety on the car itself: the motors stop when no command came for WATCHDOG_S, when the brain's
connection drops, and when this program ends. SPEED_CAP is the fastest any command can drive.
Forward motion stops at the ultrasonic threshold. An AI forward command also requires a reading.
Yahboom's own app program ("raspbot.pyc", started at login) also drives the motors and holds the
camera: stop it first (docs/guides/raspbot.md).

Run `python3 lab_os_raspbot.py --fake` on any computer to try it without a car.
"""

import argparse
import contextlib
import json
import logging
import signal
import socket
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
CAMERA_PORT = 8766
WATCHDOG_S = 0.5  # no command for this long: the motors stop
OBSTACLE_STOP_MM = 200  # stop forward motion at 20 cm from the sensor
SPEED_CAP = 120  # of the board's 255: the fastest a command at 1.0 drives
CAMERA_FPS = 10
CAMERA_IDLE_S = 5.0  # the camera closes this long after the last viewer left
# Yahboom's motor numbers (Raspbot_Lib.Ctrl_Muto): 0 front left, 1 back left, 2 front right,
# 3 back right
LEFT, RIGHT = (0, 1), (2, 3)
# The camera's pan-and-tilt mount (Raspbot_Lib.Ctrl_Servo): servo 1 turns left and right, servo 2 up
# and down. Yahboom's own code centres them at 90 and 25, and keeps servo 2 at 110 or less. Its
# library checks the angle only after it has made the I2C data, so lab-os keeps the limits itself.
PAN_SERVO, TILT_SERVO = 1, 2
PAN_CENTRE, TILT_CENTRE = 90, 25
PAN_RANGE, TILT_RANGE = (0, 180), (0, 110)
PAN_SIGN, TILT_SIGN = 1, 1  # -1 turns that servo the other way (lab check R, quick job 107)

log = logging.getLogger("lab_os_raspbot")


class YahboomBoard:
    """The Raspbot's motor board, through Yahboom's library (I2C bus 1, address 0x2B)."""

    def __init__(self) -> None:
        sys.path.append("/home/pi/project_demo/raspbot")  # where the factory image keeps it
        from Raspbot_Lib import Raspbot

        self._bot = Raspbot()
        self._bot.Ctrl_Ulatist_Switch(1)

    def set_motor(self, motor: int, speed: int) -> None:
        self._bot.Ctrl_Muto(motor, speed)

    def set_servo(self, servo: int, angle: int) -> None:
        self._bot.Ctrl_Servo(servo, angle)

    def distance_mm(self) -> int | None:
        """Read the high and low bytes of Yahboom's ultrasonic distance."""
        try:
            high = self._bot.read_data_array(0x1B, 1)[0]
            low = self._bot.read_data_array(0x1A, 1)[0]
        except (OSError, IndexError, TypeError):
            return None
        distance = (high << 8) | low
        return distance if 0 < distance < 0xFFFF else None


class FakeBoard:
    """No car: keeps the speeds, for tests and `--fake`."""

    def __init__(self) -> None:
        self.speeds = {m: 0 for m in LEFT + RIGHT}
        self.servos = {}
        self.distance = None

    def set_motor(self, motor: int, speed: int) -> None:
        if self.speeds.get(motor) != speed:
            log.info("motor %d: %d", motor, speed)
        self.speeds[motor] = speed

    def set_servo(self, servo: int, angle: int) -> None:
        if self.servos.get(servo) != angle:
            log.info("servo %d: %d", servo, angle)
        self.servos[servo] = angle

    def distance_mm(self) -> int | None:
        return self.distance


class Car:
    """The four motors, with the speed cap and the watchdog."""

    def __init__(self, board, watchdog_s: float = WATCHDOG_S) -> None:
        self.board = board
        self.watchdog_s = watchdog_s
        self._lock = threading.Lock()
        self._moving = False
        self._forward = False
        self._require_clear = False
        self._drive_stop = ""
        self._last = 0.0

    def _clearance_stop(self) -> str:
        distance = self.board.distance_mm()
        if distance is None:
            return "sensor_unavailable" if self._require_clear else ""
        return "obstacle" if distance <= OBSTACLE_STOP_MM else ""

    def drive(self, left: float, right: float, *, require_clear: bool = False) -> None:
        def speed(v: float) -> int:
            return int(round(max(-1.0, min(float(v), 1.0)) * SPEED_CAP))

        with self._lock:
            if require_clear and self._drive_stop:
                return  # a stopped AI drive cannot restart before it releases control
            left_speed, right_speed = speed(left), speed(right)
            self._forward = left_speed + right_speed > 0
            self._require_clear = require_clear
            reason = self._clearance_stop() if self._forward else ""
            if reason:
                self._stop_locked(reason)
                return
            for m in LEFT:
                self.board.set_motor(m, left_speed)
            for m in RIGHT:
                self.board.set_motor(m, right_speed)
            self._moving = bool(left_speed or right_speed)
            self._last = time.monotonic()

    def _stop_locked(self, reason: str = "") -> None:
        self._drive_stop = reason if self._require_clear else ""
        for m in LEFT + RIGHT:
            self.board.set_motor(m, 0)
        self._moving = False

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def check_watchdog(self) -> bool:
        """Check the input timeout and front clearance. Return true if the car stops."""
        with self._lock:
            if not self._moving:
                return False
            if time.monotonic() - self._last > self.watchdog_s:
                reason = "input_timeout"
            else:
                reason = self._clearance_stop() if self._forward else ""
            if not reason:
                return False
            log.info("drive stopped: %s", reason)
            self._stop_locked(reason)
            return True

    def look(self, pan: float, tilt: float) -> tuple[int, int]:
        """The camera's servos, in degrees from their centre. Returns the servo angles sent."""

        def angle(centre: int, sign: int, deg: float, lo_hi: tuple[int, int]) -> int:
            return int(round(max(lo_hi[0], min(centre + sign * float(deg), lo_hi[1]))))

        a = angle(PAN_CENTRE, PAN_SIGN, pan, PAN_RANGE)
        b = angle(TILT_CENTRE, TILT_SIGN, tilt, TILT_RANGE)
        with self._lock:
            self.board.set_servo(PAN_SERVO, a)
            self.board.set_servo(TILT_SERVO, b)
        return a, b

    def diagnostics(self) -> dict:
        with self._lock:
            return {
                "distance_mm": self.board.distance_mm(),
                "drive_stop": self._drive_stop,
            }

    def handle(self, msg: dict) -> None:
        if "look" in msg:  # the camera only: the wheels keep what they do
            pan, tilt = msg["look"]
            self.look(pan, tilt)
        elif "drive" in msg:
            left, right = msg["drive"]
            self.drive(left, right, require_clear=msg.get("require_clear") is True)
        else:  # {"stop": true}, and anything not understood
            self.stop()


class CommandServer(socketserver.ThreadingTCPServer):
    """One brain at a time: a new connection replaces the old one (the car stops in between)."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, car: Car, camera_port: int) -> None:
        super().__init__(address, CommandHandler)
        self.car = car
        self.camera_port = camera_port
        self.current = None
        self.lock = threading.Lock()


class CommandHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        srv: CommandServer = self.server
        with srv.lock:
            if srv.current is not None:  # the old brain is gone (or hangs): it loses the car
                srv.car.stop()
                with contextlib.suppress(OSError):
                    srv.current.shutdown(socket.SHUT_RDWR)
            srv.current = self.connection
        log.info("brain connected from %s", self.client_address[0])
        hello = {
            "hello": socket.gethostname(),
            "camera_port": srv.camera_port,
            "diagnostics": True,
            "obstacle_stop_mm": OBSTACLE_STOP_MM,
            "look_limits": [
                sorted((angle - centre) * sign for angle in limits)
                for centre, sign, limits in (
                    (PAN_CENTRE, PAN_SIGN, PAN_RANGE),
                    (TILT_CENTRE, TILT_SIGN, TILT_RANGE),
                )
            ],
        }
        self.wfile.write((json.dumps(hello) + "\n").encode())
        try:
            for line in self.rfile:
                try:
                    msg = json.loads(line)
                    if msg == {"diagnostics": True}:
                        self.wfile.write((json.dumps(srv.car.diagnostics()) + "\n").encode())
                    else:
                        with srv.lock:
                            if srv.current is not self.connection:
                                return
                            srv.car.handle(msg)
                except (ValueError, TypeError, KeyError):
                    with srv.lock:
                        if srv.current is self.connection:
                            srv.car.stop()  # a bad command never keeps the car moving
        except OSError:
            pass
        finally:
            with srv.lock:
                if srv.current is self.connection:
                    srv.current = None
                    srv.car.stop()  # the brain's connection dropped
            log.info("brain disconnected")


class Camera:
    """The camera, opened while someone watches. One reader; each viewer gets the newest JPEG."""

    def __init__(self, index: int = 0) -> None:
        import cv2  # noqa: F401  (only to fail early when OpenCV isn't there)

        self.index = index
        self.jpeg = b""
        self.viewers = 0
        self._cond = threading.Condition()
        self._thread = None

    def _read(self) -> None:
        import cv2

        cap = cv2.VideoCapture(self.index)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        idle_since = None
        try:
            while True:
                if self.viewers == 0:
                    idle_since = idle_since or time.monotonic()
                    if time.monotonic() - idle_since > CAMERA_IDLE_S:
                        return
                else:
                    idle_since = None
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.5)
                    continue
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                with self._cond:
                    self.jpeg = buf.tobytes() if ok else self.jpeg
                    self._cond.notify_all()
                time.sleep(1 / CAMERA_FPS)
        finally:
            cap.release()
            with self._cond:
                self._thread = None
                self.jpeg = b""

    def frames(self):
        with self._cond:
            self.viewers += 1
            if self._thread is None:
                self._thread = threading.Thread(target=self._read, daemon=True)
                self._thread.start()
        try:
            while True:
                with self._cond:
                    self._cond.wait(timeout=2.0)
                    jpeg = self.jpeg
                if jpeg:
                    yield jpeg
        finally:
            with self._cond:
                self.viewers -= 1


def camera_server(camera: Camera, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/camera.mjpg":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for jpeg in camera.frames():
                    head = f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}"
                    self.wfile.write(head.encode() + b"\r\n\r\n" + jpeg + b"\r\n")
            except OSError:
                pass  # the viewer left

        def log_message(self, *args) -> None:
            pass

    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    return srv


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fake", action="store_true", help="no car: print the motor speeds")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--camera-port", type=int, default=CAMERA_PORT)
    parser.add_argument("--no-camera", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    car = Car(FakeBoard() if args.fake else YahboomBoard())
    car.stop()
    camera_port = 0
    if not args.no_camera and not args.fake:
        try:
            cam_srv = camera_server(Camera(), args.camera_port)
            threading.Thread(target=cam_srv.serve_forever, daemon=True).start()
            camera_port = args.camera_port
        except (ImportError, OSError) as e:
            log.info("no camera picture: %s", e)
    server = CommandServer(("0.0.0.0", args.port), car, camera_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("ready on port %d (camera: %s)", args.port, camera_port or "none")

    done = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    signal.signal(signal.SIGINT, lambda *_: done.set())
    try:
        while not done.wait(0.05):
            car.check_watchdog()
    finally:
        car.stop()
        server.shutdown()
        log.info("stopped")


if __name__ == "__main__":
    main()
