# The Raspbot page

The Raspbot page (`/raspbot`) drives raspbot1, a Yahboom Raspbot v2, through the brain. Hold a button to drive: forward, back, turn left or turn right. Let go, and the car stops. The **Speed** slider sets the speed, from 0 % (the wheels do not turn) to 100 % (the top speed). The page also shows the Raspbot's camera. Quick job 72 (2026-11-23).

## How it works
- A small program runs on the Raspbot: `robots/raspbot/lab_os_raspbot.py`. It uses Yahboom's own motor library (`Raspbot_Lib`, already on the Raspbot). It only listens. The car moves only when the brain sends a command.
- The brain connects to the program on port 8765. The program sends the camera's picture on port 8766. The brain passes the picture on to the page, so the page needs no route to the Raspbot.
- The Raspbot's address and the slider's speed when the brain starts are in `config/devices.yaml` → `raspbot1` (`host`, `speed`).
- Without a Raspbot in `devices.yaml`, the page drives a fake Raspbot. The fake Raspbot has no camera.

## Safety
- **STOP** (or Space on the keyboard) stops the car at once. It works on every page that shows the Raspbot, also on a page that only watches. After STOP, let go of the button and press it again to drive.
- **The freeze:** when the page's input stops for 0.3 s (a page that hangs, lost Wi-Fi), the brain stops the car.
- **On the car:** the program stops the motors when no command comes for 0.5 s, when the brain's connection drops, and when the program ends. The Raspbot's board has no stop of its own.
- **One page at a time:** the first page that drives has control until it lets go. Another page shows "Another page" under Control.
- **Speed:** the program never drives faster than 120 of the board's 255. That is 100 % on the slider. All pages share one speed. A page that only watches cannot change it. A change applies at once, also while you hold a button.
- **Who may drive:** the same rule as the arm. A page on the brain's computer may drive. A page on another device only watches and can press STOP, unless its address is in `drive_from` in `config/place.yaml` (or `--drive-from`). The page says which address to add.

## Set up the Raspbot (once)
The Raspbot's own app program (Yahboom's "big program", started at login) also drives the motors and holds the camera. Stop it before you use the page.

1. Run `ssh raspbot1 sh /home/pi/project_demo/raspbot/killprocess.sh`. This stops Yahboom's app program until the next start.
2. On the desktop, in `~/lab-os`, run `uv run lab-os raspbot deploy`. It copies the program to `~/lab-os/` on the Raspbot and starts it as the user service `lab-os-raspbot`. The car does not move.

Yahboom's app program starts again at the next start of the Raspbot. To stop it for good, remove `~/.config/autostart/start_raspbot.desktop` on the Raspbot. The builder decides this: the Yahboom phone app then does not work.

## Use the page
1. Put the Raspbot on the floor with space around it, or on a box with the wheels off the floor.
2. Open **All Pages** → **Raspbot** → **Open** on the brain's computer.
3. Set **Speed**. Start low.
4. Hold a button, or an arrow key (or W, A, S, D). Let go to stop.

raspbot1 logs in by itself when it starts, so the program starts with it (a systemd user service). On a Raspbot that does not log in by itself, run `sudo loginctl enable-linger pi` once.

## When something is wrong
- "raspbot1 does not answer": the Raspbot is off, or not on the router's Wi-Fi, or the program does not run. Run `ssh raspbot1 systemctl --user status lab-os-raspbot`.
- The program's log: `ssh raspbot1 journalctl --user -u lab-os-raspbot -n 50`.
- No camera picture: Yahboom's app program may hold the camera (step 1 above).
- After a change to the program, run `uv run lab-os raspbot deploy` again. Never edit the program on the Raspbot.
