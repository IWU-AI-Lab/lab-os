# The Raspbot page

The Raspbot page (`/raspbot`) drives raspbot1, a Yahboom Raspbot v2, through the brain. Hold an arrow under **Drive** to move straight, sideways or diagonally. Hold a curved arrow to turn in place. Let go to stop. Hold an arrow under **Pan and Tilt** to turn the camera. The picture is between the controls on every screen. On a phone, hold the screen sideways. Full screen locks the phone in landscape when the browser allows it. The page turns sideways if the browser keeps the phone screen in portrait. Use **Speed** to set the speed from 0 % to 100 % of the top speed. The status strip shows the connection, control, motion and ultrasonic distance. Deploy the current program to move sideways or diagonally and get the distance reading. The factory board has no documented battery reading.

## How it works
- A small program runs on the Raspbot: `robots/raspbot/lab_os_raspbot.py`. It uses Yahboom's own motor and servo library (`Raspbot_Lib`, already on the Raspbot). It only listens. The car moves only when the brain sends a command.
- The brain connects to the program on port 8765. The program sends the camera's picture on port 8766. The brain passes the picture on to the page, so the page needs no route to the Raspbot.
- The Raspbot's address and the slider's speed when the brain starts are in `config/devices.yaml` → `raspbot1` (`host`, `speed`).
- Without a Raspbot in `devices.yaml`, the page drives a fake Raspbot. The fake Raspbot has no camera.

## Safety
- **STOP** (or Space on the keyboard) stops the car at once. It works on every page that shows the Raspbot, also on a page that only watches. After STOP, let go of the button and press it again to drive.
- **The freeze:** when the page's input stops for 0.3 s (a page that hangs, lost Wi-Fi), the brain stops the car.
- **On the car:** the program stops the motors when no command comes for 0.5 s, when the brain's connection drops, and when the program ends. The Raspbot's board has no stop of its own.
- **One driver at a time:** a page or an AI tool keeps control until it releases control. Another page shows "Another page" under Control.
- **Front obstacle:** The program stops every move with a forward component when the ultrasonic sensor reads 20 cm or less. The sensor measures only objects in front. Check the clearance before you move sideways or back, or turn.
- **Speed:** the program never drives faster than 120 of the board's 255. That is 100 % on the slider. All pages share one speed. A page that only watches cannot change it. A change applies at once, also while you hold a button.
- **Who may drive:** the same rule as the arm. A page on the brain's computer may drive. A page on another device only watches and can press STOP, unless its address is in `drive_from` in `config/place.yaml` (or `--drive-from`). The page says which address to add. On the brain's computer, the Command Center (`/command-center`) can also allow a device to drive.

## Set up the Raspbot (once)
The Raspbot's own app program (Yahboom's "big program", started at login) also drives the motors and holds the camera. Stop it before you use the page.

1. Run `ssh raspbot1 sh /home/pi/project_demo/raspbot/killprocess.sh`. This stops Yahboom's app program until the next start.
2. On the desktop, in `~/lab-os`, run `uv run lab-os raspbot deploy`. It copies the program to `~/lab-os/` on the Raspbot and starts it as the user service `lab-os-raspbot`. The car does not move.

Yahboom's app program starts again at the next start of the Raspbot. To stop it for good, remove `~/.config/autostart/start_raspbot.desktop` on the Raspbot. The builder decides this: the Yahboom phone app then does not work.

## The Raspbot's Wi-Fi at start
Before, raspbot1 always started its own "Raspbot" hotspot at start, and stayed on it. A Wi-Fi in hotspot mode does not look for other networks. With lab-os's Wi-Fi service, raspbot1 looks for the router's Wi-Fi (GL-B7-5G) for up to 60 seconds at start. It joins the router when it finds it. It starts the "Raspbot" hotspot only when it does not find the router. Then connect to the hotspot to reach it (`docs/archive/guides-2026-11-25/network-setup-checklist.md`).

Install it once (`uv run lab-os raspbot deploy` copies the files first):
1. Run `ssh -t raspbot1 sudo sh lab-os/install-wifi.sh`. Type raspbot1's password.
2. Run `ssh raspbot1 sudo reboot`. Wait 1 minute.
3. Run `ssh raspbot1 systemctl status lab-os-wifi`. The last line says "joined GL-B7-5G" or "on GL-B7-5G".

The service works only at start. When the router's Wi-Fi goes away later, raspbot1 tries to join it again, and does not start the hotspot. To undo the service, run `ssh -t raspbot1 'sudo systemctl disable lab-os-wifi; sudo nmcli connection modify Raspbot connection.autoconnect yes'`.

## Use the page
1. Put the Raspbot on the floor with space around it, or on a box with the wheels off the floor.
2. Open **All Pages** → **Raspbot** → **Open** on the brain's computer.
3. Set **Speed**. Start low.
4. Hold a button, or an arrow key (or W, A, S, D). Let go to stop.

raspbot1 logs in by itself when it starts, so the program starts with it (a systemd user service). On a Raspbot that does not log in by itself, run `sudo loginctl enable-linger pi` once.

## Take a picture or record
Use these buttons on the Raspbot page or in the headset.

1. Press **Picture** to save one picture.
2. Press **Record** to start a recording. The red dot and the time show while it records.
3. Press **End rec** to stop the recording.

The status line gives the full file name. The brain saves the files in `recordings/raspbot/`. A recording is an `.mp4` video: open it in Firefox or any video player. Close the page that started the recording to end it.

The brain needs `ffmpeg` to make the `.mp4` (`sudo apt install ffmpeg`). Without it, the recording stays an `.mjpeg`, which only VLC opens.

## Drive it from the Quest
In the hub in VR or AR, the **Raspbot** button opens the Raspbot with its camera as your eyes. It uses the same brain path, STOP, freeze and Speed as the Raspbot page. The Quest's address must be in `drive_from`, as for Teleop.
- **Left stick:** push it to drive forward, back, sideways or diagonally.
- **Right stick:** push it left or right to turn the Raspbot. Release both sticks to stop.
- **Your head:** turn your head to turn the camera the same way. This control is on when you open **Raspbot**.
- **Head:** select **Head on** to turn head control off. Select **Head off** to turn it on again.
- **Legacy:** select **Legacy off** to use the earlier controls. The left stick drives forward and back and turns the Raspbot. The right stick turns the camera. Select **Legacy on** to return to the default controls.
- **Centre:** select **Centre** or press the right stick to centre the camera. If head control is on, the direction you look becomes the new centre.
- **Labels:** select **Labels off** to put a box and a label on each object in the picture: its name and how sure the detector is. The object in front of the car also shows the ultrasonic distance, when the camera looks ahead. The first time, the detector takes a few seconds to load. Select **Labels on** to remove them. Labels are off each time you open **Raspbot**.
- **Window:** point at the picture or its controls. Hold the grip and move or turn your controller. Release the grip to leave the window in its new position.
- **STOP** (or A / X) stops the car. Press **B**, **Y**, **Back** or **Exit** to close the module. The car stops when the module closes.

The camera's mount has two servos: servo 1 turns left and right (0° to 180°, centre 90°), servo 2 up and down (0° to 110°, centre 25°). These are the numbers in Yahboom's own code. The program on the Raspbot keeps each servo inside these limits. If a servo turns the wrong way, change `PAN_SIGN` or `TILT_SIGN` in `robots/raspbot/lab_os_raspbot.py`, then run `uv run lab-os raspbot deploy`.

## Drive with an AI tool

1. Deploy the current Raspbot program. Use the steps in [Set up the Raspbot](#set-up-the-raspbot-once).
2. Connect the AI tool on the brain’s computer. See [AI Control](ai-control.md).
3. Open **Raspbot**. Keep **STOP** in reach.
4. Put an object straight ahead in the camera view and in the ultrasonic sensor's path.
5. Ask the AI to look through the Raspbot camera and approach the object. The task stops at the 20 cm sensor threshold or after 10 seconds.

For individual moves, tell the AI to go forward, go back, or turn. Each move lasts at most one second. Check the space behind and beside the Raspbot before it goes back or turns. A missing distance reading prevents the AI from driving forward.

The hub assistant can drive from the brain’s computer when **Full Access** is on. The AI uses the page’s **Speed** setting, up to 25 % of the Raspbot's top speed.

## When something is wrong
- raspbot1 stops (black screen, keyboard and mouse off): switch it off and on. Then run `ssh raspbot1 tail -n 20 lab-os/health.log`. The health log writes a line every 10 seconds: the power flags, the 5 V input, the core's current, the temperature, the Wi-Fi link, the load, free memory and free disk. The lines before the "--- start" line show the last minute before the stop. `throttled=0x0` means no power or temperature problem.
- "raspbot1 does not answer": the Raspbot is off, or not on the router's Wi-Fi, or the program does not run. Run `ssh raspbot1 systemctl --user status lab-os-raspbot`.
- The program's log: `ssh raspbot1 journalctl --user -u lab-os-raspbot -n 50`.
- No camera picture: Yahboom's app program may hold the camera (step 1 above).
- After a change to the program, run `uv run lab-os raspbot deploy` again. Never edit the program on the Raspbot.
