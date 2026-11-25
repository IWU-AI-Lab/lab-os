# Teleop with a webcam (preview)

Your bare hand in front of a webcam drives the arm. You need no headset. This is preview 2 for the demo (`docs/plan/current-focus.md` → item 7). It is a page of its own, so it cannot change how the Quest and desktop control work.

The page finds your hands in each camera picture with Google's MediaPipe hand landmarker. MediaPipe runs in the browser and works offline (`src/lab_os/web/vendor/README.md`). The page sends the same messages as the Quest's bare hands (`docs/dev/protocol.md` → `xr_input`), so the brain applies the same safety: the clutch, STOP, the limits, the speed and one controller at a time.

## Start it
1. Connect the webcam (the Logitech C615) to the brain's computer.
2. Start the brain:
   ```bash
   uv run lab-os serve
   ```
   It drives the SO-101 that is plugged in, else the fake arm. To keep the fake arm, add `--arm fake` (in a coding session, ask the builder before a real arm moves: `AGENTS.md`).
3. On the brain's computer, open **http://localhost:8080/webcam**. The teleop page also has a link to it.
4. Click **Start webcam control**. The first time, allow the camera.

**Note:** the browser gives the camera only to a secure page. Open the page on the brain's computer (`localhost`). From another computer, the page cannot use a camera.

**Note:** one program at a time can use a camera. If the page says "Another program uses this camera", close the other program, or select another camera in **Camera**. The page selects the C615 the first time. Do not use the arms' cameras: the AI uses them.

## Put the camera in place
- Put the camera in front of you, at chest height, facing you. On top of a monitor is good.
- Sit or stand 50 to 100 cm from the camera.
- Keep both hands in the picture. The page shows the picture like a mirror.
- Use a room with normal light. Do not sit with a window behind you.

## The controls
The controls are the same as the Quest's bare hands:
- Your **right hand** moves the gripper: left, right, up, down. Toward the camera is forward. Each move counts 1.5 times: 10 cm of hand moves the gripper 15 cm.
- **Tilt** your right hand (fingers toward or away from the camera) to tilt the gripper. **Turn** it (like the hand of a clock) to turn the gripper. This is the same as the Quest.
- Hold a **left pinch** (thumb on index finger), or hold **Space**: the clutch. The arm follows only while you hold it.
- **Right pinch:** the gripper. Fingers apart = open. Fingers together = closed.
- **X:** STOP. **Esc:** stop webcam control.

The picture shows your right hand in cyan and your left hand in amber. A green frame means that the arm follows. A dark red frame means that the arm is frozen.

## When the arm stops
- If your right hand leaves the picture, the arm stops. It stays frozen until you let go of the clutch. Then pinch again (or press Space again).
- If the tracking jumps more than 12 cm between two pictures, the page does the same.
- A hand counts only after the page sees it in 5 pictures in a row (about 0.2 s). A hand that shows for a moment does nothing.
- If the page gets no pictures for 250 ms (the tab is hidden, or the computer is too slow), the brain freezes the arm.
- When you hide the page or change to another tab, webcam control stops.
- STOP on any lab-os page stops the arm.

## Settings on the page
- **Move toward and away:** the page measures how far your hand is from its size in the picture. This is rough, a few cm. Clear the box, and the arm moves only left, right, up and down.
- **Swap left and right hands:** use this if the page shows your hands the wrong way (cyan on your left hand). Since 2026-11-22 the right hand is cyan without it, so a box ticked before is cleared.
- **Speed:** the same speed as the teleop page.

The page keeps these settings in this browser.

## Limits of the preview
- **Relative mode only.** The page does not know where the real arm is, so 1:1 is not available. The page sets the mode to relative when it starts.
- **One arm.** With two arms (`--left-arm`), the webcam drives only the right arm. The left arm holds.
- **Toward and away is rough.** One camera cannot measure depth well.
- **The picture is smaller than the arm's reach.** To reach further (for example down to the table), let go of the clutch, move your hand back, and pinch again.
- **The Kinect is not used yet.** The lab's Kinect (model 1414, for the Xbox 360) is not a normal webcam: Chrome cannot see it. It needs the libfreenect drivers, which need `sudo` to install on the lab desktop. It also needs its own power adapter. `docs/plan/ideas.md` → "Teleop with a webcam instead of the Quest".

## How it works (for developers)
- `src/lab_os/teleop/web/webcam.html` and `webcam.js`: the page, the camera, MediaPipe and the drawing.
- `src/lab_os/teleop/web/webcam-hands.js`: the calculations, without a camera or a page (tested with node in `tests/test_webcam_teleop.py`): which hand is which, the pinch, the wrist's position, the hand's turn, the 1€ filter, the 5 pictures in a row and the freeze.
- The wrist's position: left, right, up and down come from where the wrist is in the picture. Toward and away comes from the palm's size in the picture against its real size (MediaPipe's world landmarks, in metres) and the camera's field of view (78° diagonal for the C615).
- The page uses MediaPipe's left and right labels as they are. (MediaPipe's documents say that the labels are for a mirrored picture, but on a real webcam they are right: lab check W, 2026-11-21.) When both hands have the same label, the page uses the position in the picture.
- The hand's turn: two directions in MediaPipe's world landmarks (the wrist to the middle finger's knuckle, the index knuckle to the little finger's knuckle), smoothed, sent as a quaternion. The brain uses only the change since the grab, as for the Quest.
- The smoothing: a 1€ filter on each number, stronger for toward and away. MediaPipe's confidences are 0.7 (its default is 0.5).
- The page sends `"source": "webcam"` and no `"frame": "arm"`, so the brain uses relative mode. It sends only the right hand, so a second arm holds.
