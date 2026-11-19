# Places: running lab-os somewhere other than the lab

lab-os keeps nothing about a particular place in its code (docs/plan/current-focus.md, rule 9). A **place** is wherever a brain runs: the AI lab, the builder's home, someone else's lab. Everything about it lives in one **config folder**.

The repo's own `config/` is the **lab's** place. Another place gets its own folder, **outside the repo**, with its own `.env`.

## Start a new place
```bash
uv run lab-os new-place ~/my-lab-os                 # writes a starter (never overwrites)
uv run lab-os serve --config ~/my-lab-os            # the hub, with this place's name and devices
uv run lab-os-teleop --config ~/my-lab-os serve     # same option for teleop on its own
```
Or set `LAB_OS_CONFIG=~/my-lab-os` in your shell and leave out `--config`.

The starter has:
| File | What |
|---|---|
| `place.yaml` | `name` (the hub's title and the startup title), `venue` (the default venue), `persona` (who the assistant is, `docs/dev/personas.md`), `ai_budget_usd_month`, `chat_keep_minutes` (`docs/dev/chat.md`), `domain` (not used yet: the secure address is deferred, `docs/plan/current-focus.md` → step 7) |
| `devices.yaml` | the devices here; starts with the software arm only |
| `venues/home.yaml` | how cautious to be here (speed, motion allowed, active devices) |
| `.env.example` | copy to `.env` in the same folder (your place's folder, not lab-os's `src/lab_os/place_template/`) and put your own API keys in it |

`place.yaml` may also say what the place is, in a few words (`about: "a lab where students build robots"`): the visitors' welcome uses it ("Welcome to the AI Comp Lab, a lab where …"; `docs/guides/hub.md` → "Visitors' mode"). A venue with `visitors: true` is the one visitor mode switches to ("hey Jarvis, it's demo time", or ⚙ → Visitor mode); its `try_this:` lists the hub's cards then. A fixed move like the wave is in `gestures.yaml` (shared, like `poses.yaml`).

## Which file comes from where
- **Place files** are only ever read from the place's own folder: `place.yaml`, `devices.yaml`, `venues/`. A home brain never borrows the lab's name, devices or venues. If one is missing, lab-os stops and says so.
- **`hub-devices.yaml`** (since step 8) is a place file the hub writes itself: each device's own settings by name (⚙ → This device; `docs/guides/hub.md` → "Devices"). It appears on the first change; a place without one starts with every device at the defaults. In the lab it's `config/hub-devices.yaml`: changes from the Newline show up in `git status` like the settings page's.
- **Shared files** are read from the place's folder if it has them, else from the repo's `config/`: `theme.yaml` (one design everywhere), `poses.yaml` (per arm model), `models.yaml` and `personas/`.
- **`.env`**: the place's own `<folder>/.env`. For the repo's `config/` it's the repo's `.env` (the top folder, next to `pyproject.toml`). Variables already set in the shell win over the file. If the file isn't there, `lab-os serve` logs `no …/.env: no API keys` with the exact path it looked for. `new-place` never copies a `.env`, so keys never spread to a new place.
- **The lab's protected devices come along to every place:** anything `off_limits: true` in the repo's `config/devices.yaml` is refused at every place, and anything `borrowed: true` (the green arms and their cameras, since step 11) keeps its rules at every place (no motor setup or calibration, driven with a copy of the training calibration, which is only read), even if another folder's `devices.yaml` lists it differently. They're only drivable where a venue lists them in `active_devices`. Switching folders can never weaken them.
- **Two kinds of protection in `devices.yaml`:** `off_limits: true` = never opened (refused by name, port and USB serial; an entry without a serial blocks that whole USB model). `borrowed: true` = another project's device: lab-os may drive or use it, but `so101_setup` refuses it (also by board serial), it's never a command-line default, and `training_calibration: robots/so_follower/sheep.json` names its training calibration in LeRobot's cache (read only, the source of truth): lab-os drives with its copy in `calibration/<name>/` and refuses if the two differ.
- **One program per port, everywhere:** before an SO-101 port or a camera is opened, lab-os checks that no other program has it open (`/proc` on Linux, `lsof` elsewhere) and refuses with a sentence naming it.
- **An arm's table height:** `table_z_cm` (default 0) is where the table is in the arm's own heights, whose 0 is the bottom of its base: negative for an arm standing on a plate (`so101-white`: −1.6). The AI tools, `pick_at`, the floor and teleop then measure every height from the table (quick job 28).
- **Cameras by socket:** identical cameras share a serial, so a camera is `kind: camera` with `socket: usb-0:7` (the USB part of its `/dev/v4l/by-path/` name; `ls -l /dev/v4l/by-path/` lists them without opening anything). Never `/dev/videoN`.

## Your own arm
Add it to your `devices.yaml` (by `/dev/serial/by-id/…` path and USB serial, like the lab's), add its name to your venue's `active_devices`, then `lab-os serve --config ~/my-lab-os --arm <its name>`. `--arm` accepts `fake`, `fake-xarm1` or any SO-101 (`kind: so101`) or xArm (`kind: xarm1s`) in the place's device list. Calibration files go to the repo's `calibration/<arm name>/` (one folder per arm, so a home arm with its own name never touches the lab's).
