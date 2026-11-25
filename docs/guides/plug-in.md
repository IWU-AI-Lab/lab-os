# Plug in every USB device

This guide tells you what to plug in where on the lab desktop (the brain), and when. Then one command starts lab-os with every arm that is plugged in. Quick job 115.

## The plan
- **The white set** (`so101-white` and its two cameras) is on its own USB hub. The arm is in port 1 of the hub, the wrist camera in port 2, and the stand camera in port 3. The hub goes in any back socket of the desktop. lab-os finds the cameras by their port on the arm's hub, so the names stay correct in every socket.
- **The green set** (the follower, the leader, and their two cameras) stays as the training uses it: the wrist camera in back socket 7, the stand camera in back socket 8, and the two arms in other back sockets.
- **The USB microphone** is in the front port.
- **The Quest** is in the front USB-C port, for adb. Usually it uses the Wi-Fi.
- **The mouse and the keyboard** are in the other free sockets.
- **The card reader and the webcam** go on another computer of the room (a Windows desktop or a laptop). Open the hub on that computer. The card reader types into that computer's hub, and its swipe starts that hub. Open `/webcam` on that computer for webcam teleop: it uses the webcam of the computer that opens the page.
- **The xArm** goes in a free back socket only when you use it.

Each camera and the USB microphone send their data on a fixed timetable. One USB 2.0 controller has room for only a few of them. For this reason, keep the cameras and the microphone on different controllers when you can. `lab-os usb` shows which controller each device is on.

## The order
1. Connect the power supply of each SO-101 (12 V). Do this before you start the brain: an arm with USB but no motor power gives the fake arm.
2. Plug in the USB devices as in "The plan".
3. Run the command below. Read its output:
   ```bash
   uv run lab-os usb
   ```
   - Each device is listed under its USB controller, with its lab-os name.
   - A camera on an arm's hub shows `[beside: …, hub_port: "…"]`. If a white camera shows "not in devices.yaml", or the wrist camera shows the stand camera's name, change its `hub_port` in `config/devices.yaml` to the number that the command shows.
   - A line that starts with `!` tells you that too many cameras and microphones share one controller. Move a camera or the microphone to a socket on another controller.
4. Start the brain. Add no arm options:
   ```bash
   uv run --extra so101 lab-os serve --host 0.0.0.0
   ```
   - With the white set and the green follower plugged in, the terminal says "Driving so101-white and so101-green". The right controller drives the white arm, and the left controller drives the green arm. The AI tools drive the white arm.
   - With only the white set plugged in, the brain drives the white arm alone (for tic-tac-toe).
5. Open the Cameras page. Make sure that each picture is under the correct name.

**Caution:** Do not start lab-os on the green arms while LeLab runs (`AGENTS.md` → "Hard rules").
